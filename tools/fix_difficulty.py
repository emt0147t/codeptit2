"""
Fix difficulty distribution for imported problems.
Rebalances based on problem code patterns and section context.
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, init_db
from models import Problem


def better_difficulty(code: str) -> str:
    """More balanced difficulty assignment based on PTIT code patterns."""
    code_upper = code.upper()

    # Extract numeric part
    num_match = re.search(r'(\d+)', code)
    num = int(num_match.group(1)) if num_match else 0

    # Get prefix (non-digit part)
    prefix = re.match(r'([A-Za-z_]*)', code).group(1).upper()

    # ===== C series (Tin hoc co so 2) =====
    if prefix == 'C':
        series = num // 1000  # C01xxx -> 1, C04xxx -> 4
        if series <= 2:
            return "Easy"
        elif series <= 5:
            return "Medium"
        else:
            return "Hard"

    # ===== CPP series (Ngon ngu lap trinh C++) =====
    if prefix == 'CPP':
        series = num // 100  # CPP01xx -> 1
        if series <= 1:
            return "Easy"
        elif series <= 3:
            return "Medium"
        else:
            return "Hard"

    # ===== J series (Lap trinh huong doi tuong / Java) =====
    if prefix == 'J':
        series = num // 1000  # J01xxx -> 1
        if series <= 2:
            return "Easy"
        elif series <= 4:
            return "Medium"
        else:
            return "Hard"

    # ===== PY series (Lap trinh voi Python) =====
    if prefix == 'PY':
        series = num // 1000  # PY01xxx -> 1, PY02xxx -> 2
        if series <= 1:
            return "Easy"
        elif series <= 2:
            return "Medium"
        else:
            return "Hard"

    # ===== DSA series =====
    if prefix in ('DSA', 'DSA0'):
        series = num // 1000 if num >= 1000 else num // 100
        if series <= 1:
            return "Easy"
        elif series <= 5:
            return "Medium"
        else:
            return "Hard"

    # ===== CTDL series =====
    if prefix.startswith('CTDL'):
        if num <= 10:
            return "Easy"
        elif num <= 30:
            return "Medium"
        else:
            return "Hard"

    # ===== OLP series =====
    if prefix == 'OLP':
        if num <= 100:
            return "Medium"
        else:
            return "Hard"

    # ===== ICPC series =====
    if prefix == 'ICPC':
        return "Hard"

    # ===== Numeric-only codes (Thuat toan nang cao) =====
    if prefix == '' and num > 0:
        if num <= 1190:
            return "Medium"
        else:
            return "Hard"

    # ===== Special codes =====
    special_easy = ['CHELLO', 'HELLOFILE', 'HELLOJAR']
    if code_upper in special_easy:
        return "Easy"

    # Default
    return "Medium"


def main():
    init_db()
    db = SessionLocal()

    problems = db.query(Problem).all()
    updated = 0
    stats = {"Easy": 0, "Medium": 0, "Hard": 0}

    for p in problems:
        new_diff = better_difficulty(p.code)
        stats[new_diff] = stats.get(new_diff, 0) + 1
        if p.difficulty != new_diff:
            p.difficulty = new_diff
            updated += 1

    db.commit()
    db.close()

    print(f"Updated {updated} problems")
    print(f"\nNew distribution:")
    for diff, count in sorted(stats.items()):
        bar = '#' * (count // 10)
        print(f"  {diff:8s}: {count:4d} {bar}")
    print(f"  {'Total':8s}: {sum(stats.values())}")


if __name__ == "__main__":
    main()
