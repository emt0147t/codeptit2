"""
PDF Parser - Trích xuất bài tập từ file PDF và import vào database.
Hỗ trợ format PTIT (Code_PTIT) và các format tương tự.

Sử dụng:
    python tools/pdf_parser.py path/to/problems.pdf
"""
import sys
import re
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, init_db
from models import Problem, TestCase


def parse_pdf(pdf_path: str) -> list[dict]:
    """
    Parse a PDF file and extract problems.
    Returns a list of problem dicts.
    """
    try:
        import pdfplumber
    except ImportError:
        print("Cần cài đặt pdfplumber: pip install pdfplumber")
        sys.exit(1)

    problems = []
    current_problem = None
    full_text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    # Pattern to match problem headers like "CPP0101 - TÍNH TỔNG 1 ĐẾN N"
    # Also matches patterns like "BÀI 1:", "Problem 1:", etc.
    problem_pattern = re.compile(
        r'([A-Z]{2,5}\d{3,5})\s*[-–—:]\s*(.+?)(?:\n|$)',
        re.MULTILINE
    )

    matches = list(problem_pattern.finditer(full_text))

    for i, match in enumerate(matches):
        code = match.group(1).strip()
        title = match.group(2).strip()

        # Get content between this match and next match
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        content = full_text[start:end].strip()

        problem = parse_problem_content(code, title, content)
        problems.append(problem)

    return problems


def parse_problem_content(code: str, title: str, content: str) -> dict:
    """
    Parse the content of a single problem.
    Tries to extract: description, input format, output format, sample I/O.
    """
    problem = {
        "code": code,
        "title": title,
        "description": "",
        "input_description": "",
        "output_description": "",
        "sample_input": "",
        "sample_output": "",
        "difficulty": "Easy",
    }

    # Try to split content into sections
    sections = re.split(
        r'\n(?=(?:Dữ liệu vào|Input|Dữ liệu|Đầu vào)[:\s])',
        content, maxsplit=1, flags=re.IGNORECASE
    )

    problem["description"] = sections[0].strip()
    remaining = sections[1] if len(sections) > 1 else ""

    if remaining:
        # Extract input description
        input_match = re.search(
            r'(?:Dữ liệu vào|Input|Dữ liệu|Đầu vào)[:\s]*\n?(.*?)(?=(?:Kết quả|Output|Đầu ra|Ví dụ|Example))',
            remaining, re.DOTALL | re.IGNORECASE
        )
        if input_match:
            problem["input_description"] = input_match.group(1).strip()

        # Extract output description
        output_match = re.search(
            r'(?:Kết quả|Output|Đầu ra)[:\s]*\n?(.*?)(?=(?:Ví dụ|Example|Input\s|$))',
            remaining, re.DOTALL | re.IGNORECASE
        )
        if output_match:
            problem["output_description"] = output_match.group(1).strip()

        # Extract sample I/O from tables or formatted text
        # Try to find "Ví dụ" or "Example" section
        example_match = re.search(
            r'(?:Ví dụ|Example)[:\s]*\n?(.*?)$',
            remaining, re.DOTALL | re.IGNORECASE
        )
        if example_match:
            example_text = example_match.group(1).strip()
            # Try to parse table-like format
            lines = example_text.split('\n')

            # Look for Input/Output columns
            input_lines = []
            output_lines = []
            in_input = False
            in_output = False

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if re.match(r'^input', line, re.IGNORECASE):
                    in_input = True
                    in_output = False
                    continue
                elif re.match(r'^output', line, re.IGNORECASE):
                    in_output = True
                    in_input = False
                    continue

                if in_input:
                    input_lines.append(line)
                elif in_output:
                    output_lines.append(line)

            # If table parsing didn't work, try space-separated columns
            if not input_lines and not output_lines:
                # Match patterns like "2 10 20    55 210"
                for line in lines:
                    parts = re.split(r'\s{2,}|\t', line.strip())
                    if len(parts) >= 2:
                        input_lines.append(parts[0])
                        output_lines.append(parts[1])

            if input_lines:
                problem["sample_input"] = '\n'.join(input_lines)
            if output_lines:
                problem["sample_output"] = '\n'.join(output_lines)

    # Determine difficulty based on code number
    try:
        num = int(re.search(r'\d+', code).group())
        if num < 200:
            problem["difficulty"] = "Easy"
        elif num < 400:
            problem["difficulty"] = "Medium"
        else:
            problem["difficulty"] = "Hard"
    except (ValueError, AttributeError):
        pass

    return problem


def import_problems(problems: list[dict], dry_run: bool = False):
    """Import parsed problems into the database."""
    init_db()
    db = SessionLocal()

    imported = 0
    skipped = 0

    for p in problems:
        existing = db.query(Problem).filter(Problem.code == p["code"]).first()
        if existing:
            print(f"  ⏭  {p['code']} - {p['title']} (đã tồn tại)")
            skipped += 1
            continue

        if dry_run:
            print(f"  📋 {p['code']} - {p['title']} (dry run)")
            imported += 1
            continue

        problem = Problem(
            code=p["code"],
            title=p["title"],
            description=p["description"],
            input_description=p["input_description"],
            output_description=p["output_description"],
            sample_input=p["sample_input"],
            sample_output=p["sample_output"],
            difficulty=p["difficulty"],
        )
        db.add(problem)
        db.commit()
        db.refresh(problem)

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

        print(f"  ✅ {p['code']} - {p['title']}")
        imported += 1

    db.close()
    print(f"\nKết quả: {imported} bài đã import, {skipped} bài đã tồn tại")


def main():
    if len(sys.argv) < 2:
        print("Sử dụng: python tools/pdf_parser.py <file.pdf> [--dry-run]")
        print("\nOptions:")
        print("  --dry-run    Chỉ hiển thị, không import vào database")
        sys.exit(1)

    pdf_path = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    if not os.path.exists(pdf_path):
        print(f"Không tìm thấy file: {pdf_path}")
        sys.exit(1)

    print(f"📄 Đang đọc file: {pdf_path}")
    problems = parse_pdf(pdf_path)
    print(f"📋 Tìm thấy {len(problems)} bài tập\n")

    if not problems:
        print("Không tìm thấy bài tập nào trong PDF.")
        print("Hãy đảm bảo các bài có format: CODE - TÊN BÀI (VD: CPP0101 - TÍNH TỔNG)")
        sys.exit(1)

    import_problems(problems, dry_run=dry_run)


if __name__ == "__main__":
    main()
