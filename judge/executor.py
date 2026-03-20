"""
Code Judge Engine - Compiles, runs and evaluates user submissions.
Supports Python, C, C++ with time/memory limits.
"""
import os
import subprocess
import tempfile
import shutil
import time
import platform
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from sqlalchemy.orm import Session

from models import Submission, TestCase, SubmissionResult, SubmissionStatus, Problem, User
from config import SUPPORTED_LANGUAGES, JUDGE_TIMEOUT


class Judge:
    """Evaluates code submissions against test cases."""

    def __init__(self, db: Session):
        self.db = db

    def evaluate(self, submission_id: int):
        """Main entry point: evaluate a submission."""
        submission = self.db.query(Submission).filter(
            Submission.id == submission_id
        ).first()

        if not submission:
            return

        problem = submission.problem
        testcases = self.db.query(TestCase).filter(
            TestCase.problem_id == problem.id
        ).order_by(TestCase.order).all()

        if not testcases:
            submission.status = SubmissionStatus.ACCEPTED
            submission.score = 100.0
            self.db.commit()
            return

        lang_config = SUPPORTED_LANGUAGES.get(submission.language)
        if not lang_config:
            submission.status = SubmissionStatus.COMPILE_ERROR
            submission.compile_error = "Unsupported language"
            self.db.commit()
            return

        # Create temp directory
        tmp_dir = tempfile.mkdtemp(prefix="judge_")
        try:
            result = self._run_submission(
                submission, problem, testcases, lang_config, tmp_dir
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _run_submission(self, submission, problem, testcases, lang_config, tmp_dir):
        """Compile and run submission against all test cases."""
        ext = lang_config["extension"]
        source_file = os.path.join(tmp_dir, f"solution{ext}")
        exe_file = os.path.join(tmp_dir, "solution")

        if platform.system() == "Windows":
            exe_file += ".exe"

        # Write source code
        with open(source_file, "w", encoding="utf-8") as f:
            f.write(submission.source_code)

        # Compile if needed
        compile_cmd = lang_config.get("compile_cmd")
        if compile_cmd:
            cmd = compile_cmd.format(source=source_file, output=exe_file)
            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=30, cwd=tmp_dir
                )
                if result.returncode != 0:
                    submission.status = SubmissionStatus.COMPILE_ERROR
                    submission.compile_error = result.stderr[:2000]
                    self.db.commit()
                    return
            except subprocess.TimeoutExpired:
                submission.status = SubmissionStatus.COMPILE_ERROR
                submission.compile_error = "Compilation timed out"
                self.db.commit()
                return

        # Determine run command
        if compile_cmd:
            run_cmd = lang_config["run_cmd"].format(output=exe_file)
        else:
            run_cmd = lang_config["run_cmd"].format(source=source_file)

        # Run against each test case in parallel
        total_tests = len(testcases)
        results_list = [None] * total_tests
        
        time_limit = problem.time_limit if problem.time_limit else JUDGE_TIMEOUT
        
        # Use ThreadPoolExecutor to run testcases in parallel
        # We limit workers to avoid overloading small server CPUs
        max_workers = 4 
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a list of future tasks
            future_to_tc = {
                executor.submit(self._run_testcase, run_cmd, tc, time_limit, tmp_dir): i 
                for i, tc in enumerate(testcases)
            }
            
            from concurrent.futures import as_completed
            for future in as_completed(future_to_tc):
                index = future_to_tc[future]
                try:
                    tc_result = future.result()
                    results_list[index] = tc_result
                except Exception as e:
                    results_list[index] = {
                        "status": SubmissionStatus.RUNTIME_ERROR,
                        "time_ms": 0,
                        "memory_kb": 0,
                        "output": f"Judge thread error: {str(e)}",
                    }

        # Processes collected results
        passed = 0
        max_time = 0
        max_memory = 0
        overall_status = SubmissionStatus.ACCEPTED

        for i, tc in enumerate(testcases):
            tc_result = results_list[i]
            
            # Save result to DB
            sub_result = SubmissionResult(
                submission_id=submission.id,
                testcase_id=tc.id,
                status=tc_result["status"],
                time_ms=tc_result["time_ms"],
                memory_kb=tc_result["memory_kb"],
                actual_output=tc_result["output"][:5000],
            )
            self.db.add(sub_result)

            if tc_result["status"] == SubmissionStatus.ACCEPTED:
                passed += 1
            elif overall_status == SubmissionStatus.ACCEPTED:
                overall_status = tc_result["status"]

            max_time = max(max_time, tc_result["time_ms"])
            max_memory = max(max_memory, tc_result["memory_kb"])

        # Update submission
        submission.status = overall_status
        submission.score = (passed / total_tests) * 100.0
        submission.time_ms = max_time
        submission.memory_kb = max_memory
        self.db.commit()

        # Update user solved count if accepted
        if overall_status == SubmissionStatus.ACCEPTED:
            user = self.db.query(User).filter(User.id == submission.user_id).first()
            problem_obj = self.db.query(Problem).filter(
                Problem.id == submission.problem_id
            ).first()

            # Check if first time solving
            prev_accepted = self.db.query(Submission).filter(
                Submission.user_id == submission.user_id,
                Submission.problem_id == submission.problem_id,
                Submission.status == SubmissionStatus.ACCEPTED,
                Submission.id != submission.id
            ).first()

            if not prev_accepted:
                user.solved_count += 1
                problem_obj.accepted_count += 1

            self.db.commit()

    def _run_testcase(self, run_cmd, testcase, time_limit, tmp_dir):
        """Run code against a single test case with basic limits and process group handling."""
        start_time = time.time()
        process = None
        
        try:
            # On Unix-like systems, we start the process in a new session
            # so we can kill the entire process group if it times out
            kwargs = {}
            if platform.system() != "Windows":
                kwargs["start_new_session"] = True

            process = subprocess.Popen(
                run_cmd,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=tmp_dir,
                **kwargs
            )
            
            try:
                stdout_data, stderr_data = process.communicate(
                    input=testcase.input_data, timeout=time_limit
                )
            except subprocess.TimeoutExpired:
                # Kill the process and all its children
                if platform.system() != "Windows":
                    import signal
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    # Windows fallback
                    process.kill()
                    
                process.communicate() # wait for process to fully exit
                return {
                    "status": SubmissionStatus.TIME_LIMIT,
                    "time_ms": time_limit * 1000,
                    "memory_kb": 0,
                    "output": "",
                }

            elapsed = (time.time() - start_time) * 1000  # ms

            if process.returncode != 0:
                return {
                    "status": SubmissionStatus.RUNTIME_ERROR,
                    "time_ms": elapsed,
                    "memory_kb": 0,
                    "output": stderr_data[:2000],
                }

            actual_output = stdout_data.strip()
            expected_output = testcase.expected_output.strip()

            if self._compare_output(actual_output, expected_output):
                return {
                    "status": SubmissionStatus.ACCEPTED,
                    "time_ms": elapsed,
                    "memory_kb": 0,
                    "output": actual_output,
                }
            else:
                return {
                    "status": SubmissionStatus.WRONG_ANSWER,
                    "time_ms": elapsed,
                    "memory_kb": 0,
                    "output": actual_output,
                }

        except Exception as e:
            # Ensure process is killed on unexpected errors
            if process:
                if platform.system() != "Windows":
                    import signal
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    process.kill()

            return {
                "status": SubmissionStatus.RUNTIME_ERROR,
                "time_ms": 0,
                "memory_kb": 0,
                "output": str(e)[:2000],
            }

    def _compare_output(self, actual: str, expected: str) -> bool:
        """Compare actual output with expected output.
        Ignores trailing whitespace on each line and trailing newlines.
        """
        actual_lines = [line.rstrip() for line in actual.strip().splitlines()]
        expected_lines = [line.rstrip() for line in expected.strip().splitlines()]
        return actual_lines == expected_lines
