"""Quick solver coverage check."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Problem, TestCase
from tools.auto_testcases import find_matching_solver

db = SessionLocal()
cats = ['ngon-ngu-lap-trinh-cpp', 'tin-hoc-co-so-2']
output = []
for cat in cats:
    matched = 0; total = 0; no_sample = 0; solvers = {}
    problems = db.query(Problem).filter(Problem.category == cat).order_by(Problem.code).all()
    for p in problems:
        total += 1
        tc = db.query(TestCase).filter(TestCase.problem_id == p.id, TestCase.is_sample == True).first()
        if not tc: no_sample += 1; continue
        inp = tc.input_data.strip(); out = tc.expected_output.strip()
        if not inp or not out: continue
        m = find_matching_solver(inp, out)
        if m:
            matched += 1
            sname = m[0]; solvers[sname] = solvers.get(sname, 0) + 1
    output.append(f'CATEGORY: {cat}')
    output.append(f'  total={total}, matched={matched}, no_sample={no_sample}, unmatched={total-matched-no_sample}')
    for k, v in sorted(solvers.items(), key=lambda x: -x[1])[:15]:
        output.append(f'    {k}: {v}')
db.close()

with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'coverage_report.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))
print('DONE - wrote coverage_report.txt')
