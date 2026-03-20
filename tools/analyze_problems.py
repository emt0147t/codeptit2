"""Analyze problems to understand input/output patterns for testcase generation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Problem, TestCase
from sqlalchemy import func

db = SessionLocal()

for cat in ['ngon-ngu-lap-trinh-cpp', 'tin-hoc-co-so-2']:
    total = db.query(Problem).filter(Problem.category == cat).count()
    with_tc = db.query(Problem.id).join(TestCase).filter(Problem.category == cat).distinct().count()
    sample_tc = db.query(func.count(TestCase.id)).join(Problem).filter(
        Problem.category == cat, TestCase.is_sample == True).scalar()
    hidden_tc = db.query(func.count(TestCase.id)).join(Problem).filter(
        Problem.category == cat, TestCase.is_sample == False).scalar()
    print(f"{cat}: {total} problems, {with_tc} have testcases, {sample_tc} sample, {hidden_tc} hidden")

# Analyze input patterns for C++ problems
print("\n=== C++ Problems Sample ===")
probs = db.query(Problem).filter(
    Problem.category == 'ngon-ngu-lap-trinh-cpp'
).order_by(Problem.code).limit(15).all()

for p in probs:
    tcs = db.query(TestCase).filter(TestCase.problem_id == p.id).all()
    inp_desc = (p.input_description or "N/A")[:120].replace('\n', ' ')
    out_desc = (p.output_description or "N/A")[:120].replace('\n', ' ')
    print(f"\n{p.code}: {p.title}")
    print(f"  Input:  {inp_desc}")
    print(f"  Output: {out_desc}")
    for tc in tcs[:2]:
        inp = repr(tc.input_data[:100])
        out = repr(tc.expected_output[:100])
        print(f"  TC: {inp} -> {out}")

print("\n=== THCS2 Problems Sample ===")
probs2 = db.query(Problem).filter(
    Problem.category == 'tin-hoc-co-so-2'
).order_by(Problem.code).limit(15).all()

for p in probs2:
    tcs = db.query(TestCase).filter(TestCase.problem_id == p.id).all()
    inp_desc = (p.input_description or "N/A")[:120].replace('\n', ' ')
    out_desc = (p.output_description or "N/A")[:120].replace('\n', ' ')
    print(f"\n{p.code}: {p.title}")
    print(f"  Input:  {inp_desc}")
    print(f"  Output: {out_desc}")
    for tc in tcs[:2]:
        inp = repr(tc.input_data[:100])
        out = repr(tc.expected_output[:100])
        print(f"  TC: {inp} -> {out}")

# Count problems WITHOUT any testcases
for cat in ['ngon-ngu-lap-trinh-cpp', 'tin-hoc-co-so-2']:
    no_tc = db.query(Problem).filter(
        Problem.category == cat,
        ~Problem.id.in_(db.query(TestCase.problem_id).distinct())
    ).count()
    print(f"\n{cat}: {no_tc} problems WITHOUT any test cases")

db.close()
