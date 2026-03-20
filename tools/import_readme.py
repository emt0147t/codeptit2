"""
Import bài tập từ các file README.md của Code_PTIT vào Online Judge.

Hỗ trợ các format:
  ### CODE - TITLE
  ### **CODE - TITLE**

Với CODE có thể là: CPP0101, J01001, C01001, CTDL_001, PY02064, OLP017, 1179, CHELLO, etc.

Usage:
    python tools/import_readme.py                          # Import all README.md files
    python tools/import_readme.py --dry-run                # Preview without importing
    python tools/import_readme.py --file "path/to/README.md"  # Import specific file
"""
import sys
import os
import re
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, init_db
from models import Problem, TestCase


# Regex for problem header: ### CODE - TITLE  or  ### **CODE - TITLE**
# CODE = alphanumeric + underscore, at least 1 char
# Must have " - " separator to distinguish from ### **Input** etc.
PROBLEM_HEADER_RE = re.compile(
    r'^###\s+\*{0,2}([A-Za-z0-9_]+)\s*[-–—]\s*(.+?)\*{0,2}\s*$'
)

# Headers that are NOT problems (sub-sections like Input/Output)
SKIP_HEADERS = {'Input', 'Output', 'Ví dụ', 'Example', 'Chú ý', 'Note'}

# Section header (##)
SECTION_HEADER_RE = re.compile(r'^##\s+(.+)$')


def determine_difficulty(code: str, section: str) -> str:
    """Determine difficulty based on problem code and section name."""
    # Extract number from code
    num_match = re.search(r'(\d+)', code)
    if num_match:
        num = int(num_match.group(1))
        # For codes like CPP01xx, C01xxx, J01xxx - use the "hundreds" part
        code_prefix = code.rstrip('0123456789')
        if code_prefix in ('CPP', 'C', 'J', 'PY'):
            # Get the series number (e.g., 01 from CPP0101)
            series = num // 100 if num >= 100 else num // 10 if num >= 10 else 1
            if series <= 1:
                return "Easy"
            elif series <= 3:
                return "Medium"
            else:
                return "Hard"
        elif code_prefix in ('CTDL_', 'CTDL'):
            return "Medium"
        elif code_prefix in ('OLP', 'ICPC', 'PY0'):
            return "Hard"
        else:
            # Numeric-only codes like 1179
            if num < 1200:
                return "Medium"
            else:
                return "Hard"

    # Based on section name
    section_lower = section.lower()
    if any(w in section_lower for w in ['cơ bản', 'kiểu dữ liệu', 'cơ sở']):
        return "Easy"
    elif any(w in section_lower for w in ['nâng cao', 'đồ thị', 'quy hoạch', 'cây']):
        return "Hard"
    else:
        return "Medium"


def parse_sample_io_from_table(text: str):
    """Extract sample input/output from markdown table format."""
    sample_input = ""
    sample_output = ""

    # Pattern 1: | Input | Output |  (header row)
    #             | data  | data   |
    table_pattern = re.compile(
        r'\|\s*\*{0,2}(?:Input|Dữ liệu vào)[:\s]*\*{0,2}\s*\|\s*\*{0,2}(?:Output|Kết quả|Đầu ra)[:\s]*\*{0,2}\s*\|',
        re.IGNORECASE
    )

    # Find table
    lines = text.split('\n')
    table_start = -1
    for i, line in enumerate(lines):
        if table_pattern.search(line):
            table_start = i
            break

    if table_start >= 0:
        # Skip header and separator rows
        data_start = table_start + 1
        # Skip separator row (|---|---|)
        if data_start < len(lines) and re.match(r'\s*\|[-\s|]+\|\s*$', lines[data_start]):
            data_start += 1

        # Collect data rows
        input_parts = []
        output_parts = []
        for i in range(data_start, len(lines)):
            line = lines[i].strip()
            if not line.startswith('|'):
                break
            # Split by | and get columns
            cols = [c.strip() for c in line.split('|')]
            # Remove empty first/last from split
            cols = [c for c in cols if c]
            if len(cols) >= 2:
                input_parts.append(cols[0])
                output_parts.append(cols[1])
            elif len(cols) == 1:
                input_parts.append(cols[0])

        if input_parts:
            sample_input = '\n'.join(input_parts)
            # Clean up: replace multiple spaces that represent newlines in the cell
            sample_input = re.sub(r'\s{2,}', '\n', sample_input).strip()
        if output_parts:
            sample_output = '\n'.join(output_parts)
            sample_output = re.sub(r'\s{2,}', '\n', sample_output).strip()

    # Pattern 2: Table with Input on one row, Output on another
    # | **Input** |
    # | data |
    # | **Output** |
    # | data |
    if not sample_input and not sample_output:
        input_section = re.search(
            r'\|\s*\*{0,2}Input[:\s]*\*{0,2}\s*\|\s*\n\s*\|\s*(.+?)\s*\|\s*\n\s*\|\s*\*{0,2}Output[:\s]*\*{0,2}\s*\|\s*\n\s*\|\s*(.+?)\s*\|',
            text, re.IGNORECASE
        )
        if input_section:
            sample_input = re.sub(r'\s{2,}', '\n', input_section.group(1).strip())
            sample_output = re.sub(r'\s{2,}', '\n', input_section.group(2).strip())

    return sample_input, sample_output


def parse_problem_content(content: str, code: str, section: str):
    """Parse the content of a single problem into structured data."""
    result = {
        "description": "",
        "input_description": "",
        "output_description": "",
        "sample_input": "",
        "sample_output": "",
    }

    # Remove image references (but keep them noted)
    content_clean = re.sub(r'!\[.*?\]\(.*?\)', '[Hình minh họa]', content)

    # Split into logical sections based on bold headers
    # Common patterns: **Input**, **Output**, **Dữ liệu vào:**, **Kết quả:**
    # Also: ### **Input**, ### **Output** (H3 sub-headers)

    # Normalize H3 sub-headers to bold-only
    content_clean = re.sub(r'^###\s+\*{0,2}(Input|Output|Ví dụ|Example)\*{0,2}\s*$',
                           r'**\1**', content_clean, flags=re.MULTILINE | re.IGNORECASE)

    # Try to find Input section
    input_patterns = [
        r'\*{1,2}(?:Input|Dữ liệu vào|Dữ liệu|Đầu vào)[:\s]*\*{1,2}[:\s]*\n(.*?)(?=\*{1,2}(?:Output|Kết quả|Đầu ra|Ví dụ|Example|Test ví dụ)[:\s]*\*{1,2}|\|\s*\*{0,2}(?:Input|Output))',
        r'(?:Input|Dữ liệu vào|Dữ liệu|Đầu vào)[:\s]*\n(.*?)(?=(?:Output|Kết quả|Đầu ra|Ví dụ|Example):|\|\s*\*{0,2}(?:Input|Output))',
    ]

    for pattern in input_patterns:
        match = re.search(pattern, content_clean, re.DOTALL | re.IGNORECASE)
        if match:
            result["input_description"] = match.group(1).strip()
            break

    # Try to find Output section
    output_patterns = [
        r'\*{1,2}(?:Output|Kết quả|Đầu ra)[:\s]*\*{1,2}[:\s]*\n(.*?)(?=\*{1,2}(?:Ví dụ|Example|Test ví dụ|Giới hạn|Chú ý|Giải thích)[:\s]*\*{1,2}|\|\s*\*{0,2}(?:Input|Output))',
        r'\*{1,2}(?:Output|Kết quả|Đầu ra|Ouput)[:\s]*\*{1,2}[:\s]*\n(.*?)(?=\|\s*\*{0,2})',
    ]

    for pattern in output_patterns:
        match = re.search(pattern, content_clean, re.DOTALL | re.IGNORECASE)
        if match:
            result["output_description"] = match.group(1).strip()
            break

    # Extract sample I/O from tables
    sample_input, sample_output = parse_sample_io_from_table(content_clean)
    result["sample_input"] = sample_input
    result["sample_output"] = sample_output

    # Description = everything before the first Input/Output/Example section
    desc_end_patterns = [
        r'\*{1,2}(?:Input|Dữ liệu vào|Dữ liệu|Đầu vào)[:\s]*\*{1,2}',
        r'\*{1,2}(?:Output|Kết quả|Đầu ra)[:\s]*\*{1,2}',
        r'(?:^|\n)(?:Input|Dữ liệu vào)[:\s]*\n',
        r'\|\s*\*{0,2}(?:Input|Output)',
    ]

    desc_text = content_clean
    for pattern in desc_end_patterns:
        match = re.search(pattern, content_clean, re.IGNORECASE)
        if match:
            candidate = content_clean[:match.start()].strip()
            if candidate and len(candidate) < len(desc_text):
                desc_text = candidate

    result["description"] = desc_text.strip()

    # If we couldn't split, use entire content as description
    if not result["description"]:
        result["description"] = content_clean.strip()

    return result


def parse_readme(filepath: str, subject: str) -> list[dict]:
    """Parse a README.md file and extract all problems."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    problems = []
    current_section = ""

    # Find all problem headers and their positions
    problem_positions = []
    for i, line in enumerate(lines):
        # Check for section header
        section_match = SECTION_HEADER_RE.match(line)
        if section_match:
            current_section = section_match.group(1).strip()

        # Check for problem header
        problem_match = PROBLEM_HEADER_RE.match(line)
        if problem_match:
            code = problem_match.group(1).strip()
            title = problem_match.group(2).strip()
            # Remove trailing ** if present
            title = title.rstrip('*').strip()
            problem_positions.append({
                "line": i,
                "code": code,
                "title": title,
                "section": current_section,
            })

    # Extract content for each problem
    for idx, pos in enumerate(problem_positions):
        start = pos["line"] + 1
        if idx + 1 < len(problem_positions):
            end = problem_positions[idx + 1]["line"]
        else:
            end = len(lines)

        # Also stop at ## headers
        for i in range(start, end):
            if SECTION_HEADER_RE.match(lines[i]):
                end = i
                break

        problem_content = '\n'.join(lines[start:end]).strip()

        if not problem_content:
            continue

        parsed = parse_problem_content(problem_content, pos["code"], pos["section"])

        difficulty = determine_difficulty(pos["code"], pos["section"])

        problems.append({
            "code": pos["code"],
            "title": pos["title"],
            "description": parsed["description"],
            "input_description": parsed["input_description"],
            "output_description": parsed["output_description"],
            "sample_input": parsed["sample_input"],
            "sample_output": parsed["sample_output"],
            "difficulty": difficulty,
            "subject": subject,
            "section": pos["section"],
        })

    return problems


def import_to_database(all_problems: list[dict], dry_run: bool = False):
    """Import all parsed problems into the database."""
    init_db()
    db = SessionLocal()

    imported = 0
    skipped = 0
    duplicates = 0

    for p in all_problems:
        # Check if already exists
        existing = db.query(Problem).filter(Problem.code == p["code"]).first()
        if existing:
            duplicates += 1
            continue

        if dry_run:
            print(f"  📋 [{p['subject']}] {p['code']} - {p['title']} ({p['difficulty']})")
            imported += 1
            continue

        # Create problem
        # Build full description including section info
        desc_parts = []
        if p["description"]:
            desc_parts.append(p["description"])

        problem = Problem(
            code=p["code"],
            title=p["title"],
            description='\n'.join(desc_parts) if desc_parts else p["title"],
            input_description=p["input_description"],
            output_description=p["output_description"],
            sample_input=p["sample_input"],
            sample_output=p["sample_output"],
            difficulty=p["difficulty"],
            time_limit=2.0,  # Default 2s for PTIT problems
            memory_limit=256,
        )
        db.add(problem)

        try:
            db.commit()
            db.refresh(problem)
        except Exception as e:
            db.rollback()
            print(f"  ❌ {p['code']} - Error: {e}")
            skipped += 1
            continue

        # Add sample test case if available
        if p["sample_input"] and p["sample_output"]:
            tc = TestCase(
                problem_id=problem.id,
                input_data=p["sample_input"],
                expected_output=p["sample_output"],
                is_sample=True,
                order=0
            )
            db.add(tc)
            db.commit()

        imported += 1

    db.close()
    return imported, skipped, duplicates


def find_readme_files(base_dir: str) -> list[tuple[str, str]]:
    """Find all README.md files with their subject names."""
    results = []
    code_ptit_dir = None

    # Search for Code_PTIT directory
    for root, dirs, files in os.walk(base_dir):
        for d in dirs:
            if 'Code_PTIT' in d:
                code_ptit_dir = os.path.join(root, d)
                break
        if code_ptit_dir:
            break

    if not code_ptit_dir:
        print("❌ Không tìm thấy thư mục Code_PTIT")
        return results

    # Handle nested Code_PTIT-main/Code_PTIT-main structure
    inner_dir = os.path.join(code_ptit_dir, os.path.basename(code_ptit_dir))
    if os.path.exists(inner_dir):
        code_ptit_dir = inner_dir

    for item in os.listdir(code_ptit_dir):
        item_path = os.path.join(code_ptit_dir, item)
        if os.path.isdir(item_path):
            readme = os.path.join(item_path, "README.md")
            if os.path.exists(readme):
                results.append((readme, item))

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Import PTIT problems from README.md files")
    parser.add_argument("--dry-run", action="store_true", help="Preview without importing")
    parser.add_argument("--file", type=str, help="Import specific README.md file")
    parser.add_argument("--base-dir", type=str, default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        help="Base directory to search for Code_PTIT")
    args = parser.parse_args()

    all_problems = []

    if args.file:
        # Import specific file
        if not os.path.exists(args.file):
            print(f"❌ File not found: {args.file}")
            sys.exit(1)
        subject = os.path.basename(os.path.dirname(args.file))
        print(f"📂 Đang đọc: {args.file}")
        problems = parse_readme(args.file, subject)
        print(f"   → Tìm thấy {len(problems)} bài tập")
        all_problems.extend(problems)
    else:
        # Find and import all README.md files
        readme_files = find_readme_files(args.base_dir)
        if not readme_files:
            print("❌ Không tìm thấy file README.md nào trong Code_PTIT")
            sys.exit(1)

        print(f"📚 Tìm thấy {len(readme_files)} file README.md:\n")
        for filepath, subject in readme_files:
            print(f"📂 [{subject}] Đang đọc...")
            problems = parse_readme(filepath, subject)
            print(f"   → Tìm thấy {len(problems)} bài tập")
            all_problems.extend(problems)

    # Remove duplicates (keep first occurrence)
    seen_codes = set()
    unique_problems = []
    for p in all_problems:
        if p["code"] not in seen_codes:
            seen_codes.add(p["code"])
            unique_problems.append(p)

    print(f"\n{'='*60}")
    print(f"📊 Tổng cộng: {len(all_problems)} bài, {len(unique_problems)} bài không trùng")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("🔍 CHẾ ĐỘ XEM TRƯỚC (dry-run):\n")

    imported, skipped, duplicates = import_to_database(unique_problems, dry_run=args.dry_run)

    print(f"\n{'='*60}")
    print(f"✅ Kết quả:")
    print(f"   Import thành công: {imported}")
    print(f"   Bỏ qua (lỗi):     {skipped}")
    print(f"   Đã tồn tại (DB):   {duplicates}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
