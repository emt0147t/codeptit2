import re, os

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(base)
print(f"Working dir: {os.getcwd()}")

folders = [
    ("Code_PTIT-main/Code_PTIT-main/Ngôn ngữ lập trình C++", "cpp"),
    ("Code_PTIT-main/Code_PTIT-main/Tin học cơ sở 2", "thcs2"),
    ("Code_PTIT-main/Code_PTIT-main/Cấu trúc dữ liệu và giải thuật (DSA)", "dsa"),
    ("Code_PTIT-main/Code_PTIT-main/Lập trình hướng đối tượng", "oop"),
    ("Code_PTIT-main/Code_PTIT-main/Lập trình với Python", "py"),
    ("Code_PTIT-main/Code_PTIT-main/Thuật toán nâng cao - 2024", "adv"),
]

prob_re = re.compile(r"^###\s+(\S+)\s*[–-]\s*(.+)", re.MULTILINE)

for folder, tag in folders:
    readme = os.path.join(folder, "README.md")
    if os.path.exists(readme):
        content = open(readme, "r", encoding="utf-8").read()
        codes = [m.group(1) for m in prob_re.finditer(content)]
        prefixes = set()
        for c in codes:
            m2 = re.match(r"^([A-Za-z_]+)", c)
            if m2:
                prefixes.add(m2.group(1))
            elif c[:1].isdigit():
                prefixes.add("NUMERIC")
        print(f"{tag}: {sorted(prefixes)}")
