"""
Local Testcase Generation Runner
Runs a given generator script to produce input files, runs a solution script
to produce output files, and stores them in the database for a problem.
"""
import os
import sys
import subprocess
import tempfile
import argparse
from pathlib import Path

# Fix import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Problem, TestCase

def run_local_generator(problem_code: str, generator_code: str, solution_code: str, num_tests: int, language: str = "python"):
    """
    Generate test cases by executing the generator and then the solution.
    """
    db = SessionLocal()
    problem = db.query(Problem).filter(Problem.code == problem_code).first()
    if not problem:
        print(f"Lỗi: Không tìm thấy bài tập với mã {problem_code}")
        db.close()
        return False

    # Get max order to append newly generated test cases
    max_order = 0
    existing = db.query(TestCase).filter(TestCase.problem_id == problem.id).order_by(TestCase.order.desc()).first()
    if existing:
        max_order = existing.order

    with tempfile.TemporaryDirectory() as tmpdir:
        gen_path = os.path.join(tmpdir, "gen.py")
        sol_path = os.path.join(tmpdir, f"sol.{'py' if language == 'python' else 'cpp'}")
        
        with open(gen_path, "w", encoding="utf-8") as f:
            f.write(generator_code)
            
        with open(sol_path, "w", encoding="utf-8") as f:
            f.write(solution_code)
            
        # Compile solution if C++
        exe_path = os.path.join(tmpdir, "sol_exe")
        if language == "cpp":
            compile_res = subprocess.run(
                ["g++", "-std=c++17", "-O2", "-o", exe_path, sol_path],
                capture_output=True, text=True
            )
            if compile_res.returncode != 0:
                err = f"Lỗi biên dịch solution:\n{compile_res.stderr}"
                print(err)
                db.close()
                return False, err

        generated_count = 0
        accum_error = ""
        for i in range(num_tests):
            try:
                # 1. Run generator to get input
                # Pass seed/index to generator if it reads it
                gen_proc = subprocess.run(
                    ["python", gen_path, str(i)],
                    capture_output=True, text=True, timeout=5
                )
                if gen_proc.returncode != 0:
                    accum_error += f"- Lỗi chạy generator ở test {i+1}:\n{gen_proc.stderr}\n"
                    print(f"Lỗi chạy generator ở test {i+1}:\n{gen_proc.stderr}")
                    continue
                    
                tc_input = gen_proc.stdout.strip()
                if not tc_input:
                    accum_error += f"- Generator test {i+1} trả về rỗng.\n"
                    continue
                    
                # 2. Run solution to get output
                if language == "python":
                    sol_cmd = ["python", sol_path]
                else:
                    sol_cmd = [exe_path]
                    
                sol_proc = subprocess.run(
                    sol_cmd,
                    input=tc_input,
                    capture_output=True, text=True, timeout=10
                )
                
                if sol_proc.returncode != 0:
                    accum_error += f"- Lỗi chạy solution ở test {i+1}:\n{sol_proc.stderr}\n"
                    print(f"Lỗi chạy solution ở test {i+1}:\n{sol_proc.stderr}")
                    continue
                    
                tc_output = sol_proc.stdout.strip()
                
                # 3. Save to database
                max_order += 1
                tc = TestCase(
                    problem_id=problem.id,
                    input_data=tc_input,
                    expected_output=tc_output,
                    is_sample=False,
                    order=max_order
                )
                db.add(tc)
                generated_count += 1
                
            except subprocess.TimeoutExpired as e:
                accum_error += f"- Timeout (Vượt quá thời gian chạy) khi xử lý test {i+1}\n"
                print(f"Timeout khi chạy test {i+1}")
                continue
            except Exception as e:
                accum_error += f"- Lỗi hệ thống khi xử lý test {i+1}: {str(e)}\n"
                print(f"Lỗi khi xử lý test {i+1}: {e}")
                continue

        db.commit()
    db.close()
    
    if generated_count == 0 and accum_error:
        # Append the top of the generator and solution code to the error so the admin knows what failed
        accum_error += f"\n--- Generator Code (AI) ---\n{generator_code[:500]}...\n"
        
    return generated_count, accum_error

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Testcase Generator Runner")
    parser.add_argument("--code", required=True, help="Problem code (e.g., CPP0101)")
    parser.add_argument("--gen", required=True, help="Path to generator script (.py)")
    parser.add_argument("--sol", required=True, help="Path to solution script (.py, .cpp)")
    parser.add_argument("--num", type=int, default=10, help="Number of testcases to generate")
    parser.add_argument("--lang", default="python", choices=["python", "cpp"], help="Language of solution")
    
    args = parser.parse_args()
    
    try:
        with open(args.gen, "r", encoding="utf-8") as f:
            gen_code = f.read()
        with open(args.sol, "r", encoding="utf-8") as f:
            sol_code = f.read()
            
        count = run_local_generator(args.code, gen_code, sol_code, args.num, args.lang)
        if count is not False:
            print(f"Đã tạo thành công {count} test cases.")
    except Exception as e:
        print(f"Lỗi: {str(e)}")
