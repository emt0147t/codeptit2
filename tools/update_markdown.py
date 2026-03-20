"""
Script to update the markdown description of all problems in the database 
using the exact raw text from the original README.md files.
This ensures tables, headings, and images are perfectly preserved for the UI.
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, init_db
from models import Problem

PROBLEM_HEADER_RE = re.compile(
    r'^###\s+\*{0,2}([A-Za-z0-9_]+)\s*[-–—]\s*(.+?)\*{0,2}\s*$'
)
SECTION_HEADER_RE = re.compile(r'^##\s+(.+)$')

def fix_image_paths(content: str) -> str:
    """Replace ./img/... with /static/img/..."""
    # Pattern to match ![Alt](./img/filename.ext)
    return re.sub(r'!\[(.*?)\]\(\./img/(.*?)\)', r'![\1](/static/img/\2)', content)

def fix_table_newlines(content: str) -> str:
    """Convert double spaces inside markdown table rows to <br> tags."""
    def convert_spaces(match):
        row = match.group(0)
        # Skip table headers delimiter like |---|---|
        if re.match(r'^\|[\-\|\s]+\|$', row):
            return row
        # Replace 2 or more spaces with <br>
        return re.sub(r' {2,}', '<br>', row)
    
    return re.sub(r'^\|.*\|$', convert_spaces, content, flags=re.MULTILINE)

def parse_readme_for_raw_markdown(filepath: str) -> dict:
    """Extract raw markdown for each problem from a README file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    problems = {}
    
    problem_positions = []
    for i, line in enumerate(lines):
        problem_match = PROBLEM_HEADER_RE.match(line)
        if problem_match:
            code = problem_match.group(1).strip()
            problem_positions.append({
                "line": i,
                "code": code,
            })

    for idx, pos in enumerate(problem_positions):
        start = pos["line"] + 1
        end = len(lines)
        if idx + 1 < len(problem_positions):
            end = problem_positions[idx + 1]["line"]

        # Stop at ## headers within the range
        for i in range(start, end):
            if SECTION_HEADER_RE.match(lines[i]):
                end = i
                break

        # Get raw content
        problem_content = ''.join(lines[start:end]).strip()
        # Fix images and table newlines
        problem_content = fix_image_paths(problem_content)
        problem_content = fix_table_newlines(problem_content)
        
        if problem_content:
            problems[pos["code"]] = problem_content

    return problems

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code_ptit_dir = os.path.join(base_dir, 'Code_PTIT-main', 'Code_PTIT-main')
    
    if not os.path.exists(code_ptit_dir):
        print(f"❌ Cannot find Code_PTIT repo at: {code_ptit_dir}")
        return

    # Gather raw markdowns
    all_raw_markdowns = {}
    
    for subject_dir in os.listdir(code_ptit_dir):
        dp = os.path.join(code_ptit_dir, subject_dir)
        if os.path.isdir(dp):
            readme_path = os.path.join(dp, "README.md")
            if os.path.exists(readme_path):
                print(f"📂 Reading: {subject_dir}/README.md")
                p_dict = parse_readme_for_raw_markdown(readme_path)
                all_raw_markdowns.update(p_dict)
                print(f"   -> Found {len(p_dict)} problems")

    print(f"\nTotal raw markdowns extracted: {len(all_raw_markdowns)}")

    # Update Database
    db = SessionLocal()
    updated = 0
    not_found = 0

    problems_in_db = db.query(Problem).all()
    for p in problems_in_db:
        if p.code in all_raw_markdowns:
            # We overwrite the description with the FULL markdown!
            # It will now contain Input, Output, Tables, and Images.
            p.description = all_raw_markdowns[p.code]
            updated += 1
        else:
            not_found += 1

    try:
        db.commit()
        print(f"\n✅ Successfully updated {updated} problems.")
        if not_found > 0:
            print(f"⚠️ {not_found} problems in DB were not matched with README files.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error updating DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
