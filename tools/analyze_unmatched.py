"""Analyze unmatched problems from all 6 categories and find common patterns."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from database import SessionLocal
from models import Problem, TestCase
import importlib
import tools.auto_testcases as at
importlib.reload(at)

db = SessionLocal()
ALL_CATS = [
    'ngon-ngu-lap-trinh-cpp', 'tin-hoc-co-so-2',
    'cau-truc-du-lieu-giai-thuat', 'lap-trinh-huong-doi-tuong',
    'lap-trinh-voi-python', 'thuat-toan-nang-cao',
]
cn = {
    'ngon-ngu-lap-trinh-cpp': 'C++', 'tin-hoc-co-so-2': 'THCS2',
    'cau-truc-du-lieu-giai-thuat': 'CTDL', 'lap-trinh-huong-doi-tuong': 'OOP',
    'lap-trinh-voi-python': 'PY', 'thuat-toan-nang-cao': 'TTNC',
}

lines = []
cat_counts = {}
pattern_counts = {}

for cat in ALL_CATS:
    label = cn[cat]
    probs = db.query(Problem).filter(Problem.category == cat).order_by(Problem.code).all()
    cat_um = 0
    
    for i, p in enumerate(probs):
        hc = db.query(TestCase).filter(TestCase.problem_id == p.id, TestCase.is_sample == False).count()
        if hc >= 3:
            continue
        tc = db.query(TestCase).filter(TestCase.problem_id == p.id, TestCase.is_sample == True).first()
        if not tc:
            continue
        inp = tc.input_data.strip()
        out = tc.expected_output.strip()
        if not inp or not out:
            continue
        m = at.find_matching_solver(inp, out)
        if not m:
            cat_um += 1
            # Classify the pattern
            inp_lines = inp.split('\n')
            out_lines = out.split('\n')
            
            # Detect pattern type
            pattern = "unknown"
            if len(inp_lines) == 1 and len(out_lines) == 1:
                pattern = "single_in_single_out"
            elif len(inp_lines) >= 2:
                try:
                    T = int(inp_lines[0])
                    if T > 0 and T < 100:
                        # T-test format
                        if len(out_lines) == T:
                            # Check if each test is one line
                            remaining = len(inp_lines) - 1
                            if remaining == T:
                                pattern = "T_single"
                            elif remaining == T * 2:
                                pattern = "T_pair_lines"
                            else:
                                pattern = f"T_multi({remaining}/{T})"
                        else:
                            pattern = f"T_multiout"
                    else:
                        pattern = "multi_line"
                except:
                    pattern = "multi_line"
            
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            lines.append(f"{p.code}|{label}|{pattern}|{repr(inp[:100])}|{repr(out[:100])}")
    
    cat_counts[label] = cat_um
    print(f"{label}: {cat_um} unmatched", flush=True)

db.close()

outpath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'unmatched_all.txt')
with open(outpath, 'w', encoding='utf-8') as f:
    f.write("=== PATTERN DISTRIBUTION ===\n")
    for k, v in sorted(pattern_counts.items(), key=lambda x: -x[1]):
        f.write(f"  {k}: {v}\n")
    f.write(f"\n=== CATEGORY COUNTS ===\n")
    for k, v in cat_counts.items():
        f.write(f"  {k}: {v}\n")
    f.write(f"\n=== ALL UNMATCHED ({len(lines)}) ===\n")
    for line in lines:
        f.write(line + '\n')

print(f"\n{len(lines)} total unmatched, wrote {outpath}", flush=True)
print(f"Patterns: {pattern_counts}", flush=True)
print("DONE", flush=True)
