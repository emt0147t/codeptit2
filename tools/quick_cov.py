"""Quick coverage check - self-contained, no module imports from auto_testcases."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from database import SessionLocal
from models import Problem, TestCase

# Import with explicit reload
import importlib
import tools.auto_testcases as at
importlib.reload(at)

db = SessionLocal()
cats = ['ngon-ngu-lap-trinh-cpp', 'tin-hoc-co-so-2']
results = []

for cat in cats:
    matched = 0; total = 0; no_sample = 0; solver_counts = {}
    problems = db.query(Problem).filter(Problem.category == cat).order_by(Problem.code).all()
    
    for i, p in enumerate(problems):
        total += 1
        tc = db.query(TestCase).filter(TestCase.problem_id == p.id, TestCase.is_sample == True).first()
        if not tc:
            no_sample += 1
            continue
        inp = tc.input_data.strip()
        out = tc.expected_output.strip()
        if not inp or not out:
            continue
        
        t0 = time.time()
        m = at.find_matching_solver(inp, out)
        elapsed = time.time() - t0
        
        if m:
            matched += 1
            sname = m[0]
            solver_counts[sname] = solver_counts.get(sname, 0) + 1
        
        if elapsed > 1:
            print(f"  SLOW ({elapsed:.1f}s): {p.code}", flush=True)
        
        if (i + 1) % 50 == 0:
            print(f"  [{cat}] {i+1}/{len(problems)}...", flush=True)
    
    line = f"{cat}: total={total} matched={matched} no_sample={no_sample} unmatched={total-matched-no_sample}"
    print(line, flush=True)
    results.append(line)
    for k, v in sorted(solver_counts.items(), key=lambda x: -x[1])[:20]:
        s = f"  {k}: {v}"
        results.append(s)
        print(s, flush=True)

db.close()

with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cov.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))
print("\nDONE - wrote cov.txt", flush=True)
