"""Quick coverage check for ALL 6 categories."""
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
cat_names = {
    'ngon-ngu-lap-trinh-cpp': 'C++',
    'tin-hoc-co-so-2': 'THCS2',
    'cau-truc-du-lieu-giai-thuat': 'CTDL&GT',
    'lap-trinh-huong-doi-tuong': 'OOP',
    'lap-trinh-voi-python': 'Python',
    'thuat-toan-nang-cao': 'TTNC',
}

lines = []
unmatched_samples = []

for cat in ALL_CATS:
    matched = 0; total = 0; no_sample = 0; has_hidden = 0; solver_counts = {}
    problems = db.query(Problem).filter(Problem.category == cat).order_by(Problem.code).all()

    for i, p in enumerate(problems):
        total += 1
        
        # Check if already has hidden TCs
        hidden_count = db.query(TestCase).filter(TestCase.problem_id == p.id, TestCase.is_sample == False).count()
        if hidden_count >= 3:
            has_hidden += 1
            continue
        
        tc = db.query(TestCase).filter(TestCase.problem_id == p.id, TestCase.is_sample == True).first()
        if not tc:
            no_sample += 1
            continue
        inp = tc.input_data.strip()
        out = tc.expected_output.strip()
        if not inp or not out:
            no_sample += 1
            continue

        t0 = time.time()
        m = at.find_matching_solver(inp, out)
        elapsed = time.time() - t0

        if m:
            matched += 1
            sname = m[0]
            solver_counts[sname] = solver_counts.get(sname, 0) + 1
        else:
            # Save for analysis
            unmatched_samples.append((cat, p.code, p.title, inp[:150], out[:150]))

    label = cat_names.get(cat, cat)
    line = f"{label:12s} | total={total:4d} | matched={matched:3d} | has_hidden={has_hidden:3d} | no_sample={no_sample:3d} | need_tc={total-matched-has_hidden-no_sample:4d}"
    lines.append(line)
    print(line, flush=True)
    for k, v in sorted(solver_counts.items(), key=lambda x: -x[1])[:10]:
        s = f"  {k}: {v}"
        lines.append(s)

db.close()

outpath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cov_all.txt')
with open(outpath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
    f.write('\n\n=== UNMATCHED SAMPLES (first 80) ===\n')
    for cat, code, title, inp, out in unmatched_samples[:80]:
        f.write(f"\n--- {code} ({cat_names.get(cat,cat)}) : {title} ---\n")
        f.write(f"IN:  {repr(inp)}\n")
        f.write(f"OUT: {repr(out)}\n")

print(f"\nWrote {outpath}", flush=True)
print(f"Total unmatched (need new solvers): {len(unmatched_samples)}", flush=True)
print("DONE", flush=True)
