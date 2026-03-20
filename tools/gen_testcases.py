"""
Test Case Generator for Online Judge problems.

Generates test cases of various sizes to test algorithm optimization.
Supports common problem patterns: arrays, strings, graphs, etc.

Usage:
    python tools/gen_testcases.py PROBLEM_CODE --type array_sum --sizes small,medium,large
    python tools/gen_testcases.py PROBLEM_CODE --from-solution solution.py --gen-input array
    python tools/gen_testcases.py --list-types
"""
import sys
import os
import json
import random
import string
import argparse
import subprocess
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Problem, TestCase


# Size presets
SIZES = {
    "tiny":   {"n": 5,       "max_val": 100},
    "small":  {"n": 10,      "max_val": 1000},
    "medium": {"n": 1000,    "max_val": 10**6},
    "large":  {"n": 100000,  "max_val": 10**9},
    "stress": {"n": 500000,  "max_val": 10**9},
}


# ============ Input Generators ============

def gen_array(n, max_val=10**9, min_val=1):
    """Generate n random integers."""
    arr = [random.randint(min_val, max_val) for _ in range(n)]
    return f"{n}\n{' '.join(map(str, arr))}"


def gen_sorted_array(n, max_val=10**9):
    """Generate sorted array (edge case)."""
    arr = sorted(random.randint(1, max_val) for _ in range(n))
    return f"{n}\n{' '.join(map(str, arr))}"


def gen_reverse_sorted_array(n, max_val=10**9):
    """Generate reverse sorted array (worst case for many algorithms)."""
    arr = sorted((random.randint(1, max_val) for _ in range(n)), reverse=True)
    return f"{n}\n{' '.join(map(str, arr))}"


def gen_same_elements(n, val=None):
    """Generate array with all same elements (edge case)."""
    if val is None:
        val = random.randint(1, 10**9)
    arr = [val] * n
    return f"{n}\n{' '.join(map(str, arr))}"


def gen_two_numbers(max_val=10**9):
    """Generate two random numbers."""
    a = random.randint(1, max_val)
    b = random.randint(1, max_val)
    return f"{a} {b}"


def gen_single_number(max_val=10**9):
    """Generate single number."""
    return str(random.randint(1, max_val))


def gen_string(n, charset="lowercase"):
    """Generate random string of length n."""
    if charset == "lowercase":
        s = ''.join(random.choices(string.ascii_lowercase, k=n))
    elif charset == "uppercase":
        s = ''.join(random.choices(string.ascii_uppercase, k=n))
    elif charset == "digits":
        s = ''.join(random.choices(string.digits, k=n))
    else:
        s = ''.join(random.choices(string.ascii_letters + string.digits, k=n))
    return f"{n}\n{s}"


def gen_matrix(n, m=None, max_val=100):
    """Generate n x m matrix."""
    if m is None:
        m = n
    lines = [f"{n} {m}"]
    for _ in range(n):
        row = [random.randint(0, max_val) for _ in range(m)]
        lines.append(' '.join(map(str, row)))
    return '\n'.join(lines)


def gen_graph(n, m=None, weighted=False, max_weight=100):
    """Generate random graph with n vertices and m edges."""
    if m is None:
        m = min(n * 2, n * (n - 1) // 2)
    edges = set()
    while len(edges) < m:
        u = random.randint(1, n)
        v = random.randint(1, n)
        if u != v and (u, v) not in edges and (v, u) not in edges:
            edges.add((u, v))
    lines = [f"{n} {m}"]
    for u, v in edges:
        if weighted:
            w = random.randint(1, max_weight)
            lines.append(f"{u} {v} {w}")
        else:
            lines.append(f"{u} {v}")
    return '\n'.join(lines)


def gen_tree(n, max_weight=100, weighted=False):
    """Generate random tree with n vertices."""
    lines = [str(n)]
    for i in range(2, n + 1):
        parent = random.randint(1, i - 1)
        if weighted:
            w = random.randint(1, max_weight)
            lines.append(f"{parent} {i} {w}")
        else:
            lines.append(f"{parent} {i}")
    return '\n'.join(lines)


def gen_queries(n, q, max_val=None):
    """Generate array + queries."""
    if max_val is None:
        max_val = n
    arr = [random.randint(1, 10**9) for _ in range(n)]
    lines = [f"{n} {q}", ' '.join(map(str, arr))]
    for _ in range(q):
        l = random.randint(1, n)
        r = random.randint(l, n)
        lines.append(f"{l} {r}")
    return '\n'.join(lines)


# Map of generator types
GENERATORS = {
    "array": gen_array,
    "sorted_array": gen_sorted_array,
    "reverse_array": gen_reverse_sorted_array,
    "same_elements": gen_same_elements,
    "two_numbers": gen_two_numbers,
    "single_number": gen_single_number,
    "string": gen_string,
    "matrix": gen_matrix,
    "graph": gen_graph,
    "tree": gen_tree,
    "queries": gen_queries,
}


# ============ Solution Runner ============

def run_solution(solution_path: str, input_data: str, timeout: float = 30.0) -> str:
    """Run a solution file to generate expected output."""
    ext = os.path.splitext(solution_path)[1]
    tmp_dir = tempfile.mkdtemp()

    try:
        if ext == ".py":
            cmd = [sys.executable, solution_path]
        elif ext in (".cpp", ".cc"):
            exe = os.path.join(tmp_dir, "sol.exe" if os.name == "nt" else "sol")
            compile_result = subprocess.run(
                f"g++ -std=c++17 -O2 -o {exe} {solution_path}",
                shell=True, capture_output=True, text=True, timeout=30
            )
            if compile_result.returncode != 0:
                print(f"Compile error: {compile_result.stderr}")
                return None
            cmd = [exe]
        elif ext == ".c":
            exe = os.path.join(tmp_dir, "sol.exe" if os.name == "nt" else "sol")
            compile_result = subprocess.run(
                f"gcc -std=c11 -O2 -o {exe} {solution_path}",
                shell=True, capture_output=True, text=True, timeout=30
            )
            if compile_result.returncode != 0:
                print(f"Compile error: {compile_result.stderr}")
                return None
            cmd = [exe]
        else:
            print(f"Unsupported file type: {ext}")
            return None

        result = subprocess.run(
            cmd, input=input_data, capture_output=True, text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            print(f"Runtime error: {result.stderr[:500]}")
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print("Solution timed out")
        return None
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ============ Main Logic ============

def generate_and_import(problem_code, gen_type, sizes, solution_path=None, save_json=None):
    """Generate test cases and optionally import to database."""
    db = SessionLocal()
    problem = db.query(Problem).filter(Problem.code == problem_code).first()
    if not problem:
        print(f"Problem {problem_code} not found!")
        db.close()
        return

    gen_func = GENERATORS.get(gen_type)
    if not gen_func:
        print(f"Unknown generator type: {gen_type}")
        print(f"Available: {', '.join(GENERATORS.keys())}")
        db.close()
        return

    tests = []
    max_order = db.query(TestCase).filter(TestCase.problem_id == problem.id).count()

    for size_name in sizes:
        params = SIZES.get(size_name, SIZES["small"])
        n = params["n"]
        max_val = params["max_val"]

        print(f"\nGenerating {size_name} test (n={n})...")

        # Generate input based on generator type
        if gen_type in ("two_numbers", "single_number"):
            input_data = gen_func(max_val=max_val)
        elif gen_type == "same_elements":
            input_data = gen_func(n)
        elif gen_type in ("graph", "tree"):
            input_data = gen_func(n)
        elif gen_type == "matrix":
            side = min(int(n**0.5), 500)
            input_data = gen_func(side, side, max_val=min(max_val, 1000))
        elif gen_type == "queries":
            input_data = gen_func(n, min(n, 100000))
        elif gen_type == "string":
            input_data = gen_func(n)
        else:
            input_data = gen_func(n, max_val=max_val)

        # Get expected output
        if solution_path:
            output = run_solution(solution_path, input_data)
            if output is None:
                print(f"  Failed to get output for {size_name} test, skipping")
                continue
        else:
            output = "TODO"  # placeholder

        test = {"input": input_data, "output": output, "size": size_name}
        tests.append(test)

        # Import to database
        if output != "TODO":
            tc = TestCase(
                problem_id=problem.id,
                input_data=input_data,
                expected_output=output,
                is_sample=(size_name in ("tiny", "small") and max_order == 0),
                order=max_order + len(tests) - 1,
            )
            db.add(tc)
            print(f"  ✓ {size_name}: input={len(input_data)} chars, output={len(output)} chars")
        else:
            print(f"  ⚠ {size_name}: Generated input only (no solution provided)")

    if save_json:
        with open(save_json, "w", encoding="utf-8") as f:
            json.dump(tests, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(tests)} tests to {save_json}")

    db.commit()
    total = db.query(TestCase).filter(TestCase.problem_id == problem.id).count()
    print(f"\nProblem {problem_code} now has {total} total test cases")
    db.close()


def list_types():
    print("Available generator types:")
    print(f"{'Type':<20} {'Description'}")
    print("-" * 50)
    for name, func in GENERATORS.items():
        print(f"  {name:<18} {func.__doc__}")
    print(f"\nAvailable sizes: {', '.join(SIZES.keys())}")


def main():
    parser = argparse.ArgumentParser(description="Generate test cases for Online Judge")
    parser.add_argument("problem_code", nargs="?", help="Problem code (e.g., CPP0101)")
    parser.add_argument("--type", "-t", default="array", help="Generator type")
    parser.add_argument("--sizes", "-s", default="tiny,small,medium,large",
                       help="Comma-separated sizes: tiny,small,medium,large,stress")
    parser.add_argument("--solution", "-sol", help="Path to correct solution file (.py/.cpp/.c)")
    parser.add_argument("--save-json", help="Save generated tests to JSON file")
    parser.add_argument("--list-types", action="store_true", help="List available generator types")

    args = parser.parse_args()

    if args.list_types:
        list_types()
        return

    if not args.problem_code:
        parser.print_help()
        return

    sizes = [s.strip() for s in args.sizes.split(",")]
    generate_and_import(
        args.problem_code,
        args.type,
        sizes,
        solution_path=args.solution,
        save_json=args.save_json,
    )


if __name__ == "__main__":
    main()
