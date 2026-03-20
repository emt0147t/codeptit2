# Online Judge System

Hệ thống chấm bài tự động (Online Judge) cho luyện tập lập trình.

## Tính năng

- **Quản lý bài tập**: Thêm, xem, tìm kiếm bài tập theo mã/tên/độ khó
- **Nộp bài & Chấm tự động**: Hỗ trợ Python, C, C++
- **Test Cases**: Quản lý test cases cho từng bài (admin)
- **Bảng xếp hạng**: Xếp hạng theo số bài giải được
- **Import từ PDF**: Tự động trích xuất bài tập từ file PDF
- **Tài khoản**: Đăng ký, đăng nhập, phân quyền admin

## Cài đặt & Chạy

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2. Khởi tạo database

```bash
python init_db.py
```

Sẽ tạo:
- Database SQLite (`online_judge.db`)
- Tài khoản admin (username: `admin`, password: `admin123`)
- 3 bài tập mẫu

### 3. Chạy server

```bash
python main.py
```

Truy cập: **http://localhost:8000**

## Import bài tập từ PDF

```bash
# Xem trước (không import)
python tools/pdf_parser.py path/to/problems.pdf --dry-run

# Import vào database
python tools/pdf_parser.py path/to/problems.pdf
```

**Yêu cầu format PDF**: Mỗi bài phải có header dạng `CODE - TÊN BÀI`  
Ví dụ: `CPP0101 - TÍNH TỔNG 1 ĐẾN N`

## Cấu trúc project

```
├── main.py              # FastAPI app entry point
├── config.py            # Cấu hình hệ thống
├── database.py          # Database setup
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── init_db.py           # Script khởi tạo database
├── requirements.txt     # Python dependencies
├── routers/
│   ├── auth.py          # Đăng nhập/Đăng ký
│   ├── problems.py      # Quản lý bài tập
│   └── submissions.py   # Nộp bài & kết quả
├── judge/
│   └── executor.py      # Code execution engine
├── templates/           # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── problems.html
│   ├── problem_detail.html
│   ├── submission_detail.html
│   ├── submissions.html
│   ├── ranking.html
│   ├── login.html
│   ├── register.html
│   └── admin/
│       ├── add_problem.html
│       └── testcases.html
├── static/
│   ├── css/style.css
│   └── js/main.js
└── tools/
    └── pdf_parser.py    # PDF import tool
```

## Ngôn ngữ hỗ trợ

| Ngôn ngữ | Yêu cầu |
|-----------|----------|
| Python 3  | Python 3.8+ |
| C++ 17    | g++ (MinGW trên Windows) |
| C         | gcc (MinGW trên Windows) |

## Lưu ý bảo mật

⚠️ Hệ thống này được thiết kế cho **sử dụng cá nhân/nhóm nhỏ**.
Nếu triển khai public, cần bổ sung:
- Docker sandbox cho code execution
- Rate limiting
- HTTPS
- Đổi SECRET_KEY trong config.py
