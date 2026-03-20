"""Deeper analysis of problem patterns for auto-solver."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Problem, TestCase

db = SessionLocal()

for cat in ['ngon-ngu-lap-trinh-cpp', 'tin-hoc-co-so-2']:
    print(f"\n{'='*60}")
    print(f"  {cat}")
    print(f"{'='*60}")
    
    probs = db.query(Problem).filter(
        Problem.category == cat
    ).order_by(Problem.code).all()
    
    for p in probs:
        tcs = db.query(TestCase).filter(TestCase.problem_id == p.id).all()
        if not tcs:
            continue
        tc = tcs[0]
        inp_lines = tc.input_data.strip().split('\n')
        out_lines = tc.expected_output.strip().split('\n')
        
        # Detect format
        first_line = inp_lines[0].strip()
        has_T = False
        try:
            T = int(first_line)
            if T > 0 and len(inp_lines) == T + 1 and len(out_lines) == T:
                has_T = True
        except:
            pass
        
        inp_short = tc.input_data[:60].replace('\n', '|')
        out_short = tc.expected_output[:60].replace('\n', '|')
        desc_short = (p.input_description or '')[:80].replace('\n', ' ')
        
        fmt = "T+vals" if has_T else "direct"
        print(f"{p.code:12s} [{fmt:8s}] IN={inp_short:30s} OUT={out_short:30s} DESC={desc_short}")

db.close()
