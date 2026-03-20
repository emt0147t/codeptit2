"""
Add category column to existing problems and assign categories
based on problem code patterns.
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import SessionLocal, engine
from models import Problem
from config import CATEGORY_FOLDER_MAP


# We'll use a function-based approach since prefixes overlap between folders
# Priority: match specific first, then general
# Based on actual README folder analysis:
# cpp: CHELLO, CPP, NNLTC_, OLP, TEST_
# thcs2: C0x (C01-C07), CTEST, FPT, FTP, JP, LAB, PR, TEST, TESTMD, TST
# dsa: CTDL_, DSA, DSAKT, DSA_P, TN (when starts with TN0)
# oop: HELLOFILE, HELLOJAR, J0x, JKT, TN (when starts with TN0 - overlap with dsa)
# py: ICPC, PY, PYKT
# adv: CP0x, LATXU, S, SEQ, T (single letter), numeric codes


def guess_category(code: str) -> str:
    """Determine category based on problem code using actual README folder data."""
    c = code.upper()

    # --- Specific prefixes first ---

    # Python folder: PY, PYKT, ICPC
    if c.startswith("PY") or c.startswith("ICPC"):
        return "lap-trinh-voi-python"

    # C++ folder: CPP, NNLTC_, OLP (but not CP0x which is adv)
    if c.startswith("CPP") or c.startswith("NNLTC"):
        return "ngon-ngu-lap-trinh-cpp"

    # DSA folder: CTDL_, DSA, DSAKT, DSA_P
    if c.startswith("CTDL") or c.startswith("DSA"):
        return "cau-truc-du-lieu-giai-thuat"

    # OOP folder: J0x, JKT, HELLOFILE, HELLOJAR
    if c.startswith("J0") or c.startswith("J1") or c.startswith("J2"):
        return "lap-trinh-huong-doi-tuong"
    if c.startswith("J3") or c.startswith("J4") or c.startswith("J5") or c.startswith("J6"):
        return "lap-trinh-huong-doi-tuong"
    if c.startswith("JKT"):
        return "lap-trinh-huong-doi-tuong"
    if c.startswith("HELLO"):
        return "lap-trinh-huong-doi-tuong"

    # Tin hoc co so 2: C01-C07, CTEST, FPT, FTP, JP, LAB, PR, TEST (not TEST_), TESTMD, TST
    if re.match(r"^C0[1-7]", c):
        return "tin-hoc-co-so-2"
    if c.startswith("CTEST") or c.startswith("FPT") or c.startswith("FTP"):
        return "tin-hoc-co-so-2"
    if c.startswith("JP") or c.startswith("LAB") or c.startswith("PR"):
        return "tin-hoc-co-so-2"
    if c.startswith("TESTMD") or c.startswith("TST"):
        return "tin-hoc-co-so-2"

    # C++ folder: OLP, TEST_ (with underscore) - check after thcs2
    if c.startswith("OLP"):
        return "ngon-ngu-lap-trinh-cpp"
    if c.startswith("TEST_"):
        return "ngon-ngu-lap-trinh-cpp"

    # CHELLO appears in multiple folders, assign to C++ as primary
    if c.startswith("CHELLO"):
        return "ngon-ngu-lap-trinh-cpp"

    # Thuat toan nang cao: CP0x, LATXU, S, SEQ, T (single), numeric
    if c.startswith("CP0"):
        return "thuat-toan-nang-cao"
    if c.startswith("LATXU") or c.startswith("SEQ"):
        return "thuat-toan-nang-cao"

    # TN codes - appear in both DSA and OOP, assign to OOP
    if c.startswith("TN"):
        return "lap-trinh-huong-doi-tuong"

    # Single letter S or T followed by digits -> adv
    if re.match(r"^S\d", c) or re.match(r"^T\d", c):
        return "thuat-toan-nang-cao"

    # Numeric-only codes -> thuat toan nang cao
    if code.isdigit():
        return "thuat-toan-nang-cao"

    # TEST (without underscore, not TESTMD) -> thcs2
    if c.startswith("TEST"):
        return "tin-hoc-co-so-2"

    # C followed by single digit (not C0x already handled) -> thcs2
    if re.match(r"^C\d", c):
        return "tin-hoc-co-so-2"

    return "thuat-toan-nang-cao"  # default fallback


def main():
    # First, add column if it doesn't exist
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE problems ADD COLUMN category VARCHAR(100) DEFAULT ''"))
            conn.commit()
            print("Added 'category' column to problems table")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("Column 'category' already exists")
            else:
                print(f"Column may already exist: {e}")

    # Assign categories
    db = SessionLocal()
    problems = db.query(Problem).all()
    updated = 0
    stats = {}

    for p in problems:
        cat = guess_category(p.code)
        if cat and (not p.category or p.category == ""):
            p.category = cat
            updated += 1
        elif not cat:
            # Try to guess from code patterns
            p.category = ""

        cat_name = cat or "(uncategorized)"
        stats[cat_name] = stats.get(cat_name, 0) + 1

    db.commit()
    db.close()

    print(f"\nUpdated {updated} problems with categories\n")
    print("Distribution:")
    for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {cat:40s}: {count}")
    print(f"  {'TOTAL':40s}: {sum(stats.values())}")


if __name__ == "__main__":
    main()
