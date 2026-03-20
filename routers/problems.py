"""
Problem routes: list, detail, create (admin).
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from config import BASE_DIR
from sqlalchemy.orm import Session
from typing import Optional
import json
import io

from database import get_db
from models import Problem, TestCase, Submission, SubmissionStatus
from routers.auth import get_current_user, require_admin
from config import PROBLEMS_PER_PAGE, CATEGORIES

router = APIRouter(tags=["problems"])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/problems")
async def problem_list(
    request: Request,
    page: Optional[int] = None,
    search: str = "",
    difficulty: str = "",
    category: str = "",
    sub_category: str = "",
    db: Session = Depends(get_db)
):
    # Handle pagination persistence via cookie
    if page is None:
        cookie_page = request.cookies.get("last_problems_page")
        page = int(cookie_page) if cookie_page and cookie_page.isdigit() else 1
    
    user = get_current_user(request, db)
    query = db.query(Problem)

    if category:
        query = query.filter(Problem.category == category)
    if sub_category:
        query = query.filter(Problem.code.startswith(sub_category))
    if search:
        query = query.filter(
            (Problem.title.ilike(f"%{search}%")) |
            (Problem.code.ilike(f"%{search}%"))
        )
    if difficulty:
        query = query.filter(Problem.difficulty == difficulty)

    total = query.count()
    problems = query.order_by(Problem.code).offset(
        (page - 1) * PROBLEMS_PER_PAGE
    ).limit(PROBLEMS_PER_PAGE).all()

    total_pages = (total + PROBLEMS_PER_PAGE - 1) // PROBLEMS_PER_PAGE

    # Get solved status for current user
    solved_ids = set()
    if user:
        solved = db.query(Submission.problem_id).filter(
            Submission.user_id == user.id,
            Submission.status == SubmissionStatus.ACCEPTED
        ).distinct().all()
        solved_ids = {s[0] for s in solved}

    # Category info
    from config import SUB_CATEGORIES
    category_info = CATEGORIES.get(category) if category else None
    available_subcats = SUB_CATEGORIES.get(category, []) if category else []

    response = templates.TemplateResponse("problems.html", {
        "request": request,
        "user": user,
        "problems": problems,
        "page": page,
        "total_pages": total_pages,
        "search": search,
        "difficulty": difficulty,
        "category": category,
        "sub_category": sub_category,
        "category_info": category_info,
        "available_subcats": available_subcats,
        "solved_ids": solved_ids,
    })
    response.set_cookie(key="last_problems_page", value=str(page), max_age=3600*24*7) # 1 week
    return response


@router.get("/category/{slug}")
async def category_page(
    request: Request,
    slug: str,
    page: Optional[int] = None,
    search: str = "",
    difficulty: str = "",
    sub_category: str = "",
    db: Session = Depends(get_db)
):
    # Handle pagination persistence via cookie
    cookie_name = f"last_page_{slug}"
    if page is None:
        cookie_page = request.cookies.get(cookie_name)
        page = int(cookie_page) if cookie_page and cookie_page.isdigit() else 1
    """Redirect to /problems with category filter."""
    if slug not in CATEGORIES:
        raise HTTPException(status_code=404, detail="Category not found")

    user = get_current_user(request, db)
    query = db.query(Problem).filter(Problem.category == slug)

    if sub_category:
        query = query.filter(Problem.code.startswith(sub_category))
    if search:
        query = query.filter(
            (Problem.title.ilike(f"%{search}%")) |
            (Problem.code.ilike(f"%{search}%"))
        )
    if difficulty:
        query = query.filter(Problem.difficulty == difficulty)

    total = query.count()
    problems = query.order_by(Problem.code).offset(
        (page - 1) * PROBLEMS_PER_PAGE
    ).limit(PROBLEMS_PER_PAGE).all()

    total_pages = (total + PROBLEMS_PER_PAGE - 1) // PROBLEMS_PER_PAGE

    solved_ids = set()
    if user:
        solved = db.query(Submission.problem_id).filter(
            Submission.user_id == user.id,
            Submission.status == SubmissionStatus.ACCEPTED
        ).distinct().all()
        solved_ids = {s[0] for s in solved}

    from config import SUB_CATEGORIES
    category_info = CATEGORIES[slug]
    available_subcats = SUB_CATEGORIES.get(slug, [])

    response = templates.TemplateResponse("problems.html", {
        "request": request,
        "user": user,
        "problems": problems,
        "page": page,
        "total_pages": total_pages,
        "search": search,
        "difficulty": difficulty,
        "sub_category": sub_category,
        "category": slug,
        "category_info": category_info,
        "available_subcats": available_subcats,
        "solved_ids": solved_ids,
    })
    response.set_cookie(key=cookie_name, value=str(page), max_age=3600*24*7)
    return response


@router.get("/problem/{problem_code}")
async def problem_detail(
    request: Request,
    problem_code: str,
    page: int = 1,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    problem = db.query(Problem).filter(Problem.code == problem_code).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    sample_testcases = db.query(TestCase).filter(
        TestCase.problem_id == problem.id,
        TestCase.is_sample == True
    ).order_by(TestCase.order).all()

    # Get user's submissions for this problem
    user_submissions = []
    is_solved = False
    if user:
        user_submissions = db.query(Submission).filter(
            Submission.user_id == user.id,
            Submission.problem_id == problem.id
        ).order_by(Submission.created_at.desc()).limit(10).all()
        
        is_solved = any(sub.status == SubmissionStatus.ACCEPTED for sub in user_submissions)

    return templates.TemplateResponse("problem_detail.html", {
        "request": request,
        "user": user,
        "problem": problem,
        "sample_testcases": sample_testcases,
        "user_submissions": user_submissions,
        "is_solved": is_solved,
        "page": page,
    })


# --- Admin Routes ---
@router.get("/admin/problems/add")
async def add_problem_page(
    request: Request,
    db: Session = Depends(get_db)
):
    user = require_admin(request, db)
    return templates.TemplateResponse("admin/add_problem.html", {
        "request": request,
        "user": user,
        "error": None
    })


@router.post("/admin/problems/add")
async def add_problem(
    request: Request,
    code: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    input_description: str = Form(""),
    output_description: str = Form(""),
    sample_input: str = Form(""),
    sample_output: str = Form(""),
    difficulty: str = Form("Easy"),
    time_limit: float = Form(1.0),
    memory_limit: int = Form(256),
    db: Session = Depends(get_db)
):
    user = require_admin(request, db)

    # Check duplicate code
    existing = db.query(Problem).filter(Problem.code == code).first()
    if existing:
        return templates.TemplateResponse("admin/add_problem.html", {
            "request": request,
            "user": user,
            "error": f"Mã bài {code} đã tồn tại"
        })

    problem = Problem(
        code=code,
        title=title,
        description=description,
        input_description=input_description,
        output_description=output_description,
        sample_input=sample_input,
        sample_output=sample_output,
        difficulty=difficulty,
        time_limit=time_limit,
        memory_limit=memory_limit,
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)

    # Add sample test case
    if sample_input and sample_output:
        tc = TestCase(
            problem_id=problem.id,
            input_data=sample_input.strip(),
            expected_output=sample_output.strip(),
            is_sample=True,
            order=0
        )
        db.add(tc)
        db.commit()

    return RedirectResponse(url=f"/problem/{code}", status_code=302)


@router.get("/admin/problem/{problem_code}/testcases")
async def manage_testcases_page(
    request: Request,
    problem_code: str,
    db: Session = Depends(get_db)
):
    user = require_admin(request, db)
    problem = db.query(Problem).filter(Problem.code == problem_code).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    testcases = db.query(TestCase).filter(
        TestCase.problem_id == problem.id
    ).order_by(TestCase.order).all()

    return templates.TemplateResponse("admin/testcases.html", {
        "request": request,
        "user": user,
        "problem": problem,
        "testcases": testcases,
    })


@router.post("/admin/problem/{problem_code}/testcases/add")
async def add_testcase(
    request: Request,
    problem_code: str,
    input_data: str = Form(...),
    expected_output: str = Form(...),
    is_sample: bool = Form(False),
    db: Session = Depends(get_db)
):
    user = require_admin(request, db)
    problem = db.query(Problem).filter(Problem.code == problem_code).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    max_order = db.query(TestCase).filter(
        TestCase.problem_id == problem.id
    ).count()

    tc = TestCase(
        problem_id=problem.id,
        input_data=input_data.strip(),
        expected_output=expected_output.strip(),
        is_sample=is_sample,
        order=max_order
    )
    db.add(tc)
    db.commit()

    return RedirectResponse(
        url=f"/admin/problem/{problem_code}/testcases", status_code=302
    )


@router.post("/admin/testcase/{testcase_id}/delete")
async def delete_testcase(
    request: Request,
    testcase_id: int,
    db: Session = Depends(get_db)
):
    user = require_admin(request, db)
    tc = db.query(TestCase).filter(TestCase.id == testcase_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="TestCase not found")

    problem_code = tc.problem.code
    
    # Delete associated results first to avoid FK constraint error
    from models import SubmissionResult
    db.query(SubmissionResult).filter(SubmissionResult.testcase_id == testcase_id).delete()
    
    db.delete(tc)
    db.commit()

    return RedirectResponse(
        url=f"/admin/problem/{problem_code}/testcases", status_code=302
    )


@router.post("/admin/problem/{problem_code}/testcases/bulk")
async def bulk_add_testcases(
    request: Request,
    problem_code: str,
    bulk_data: str = Form(""),
    bulk_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Bulk add test cases. Supports two formats:
    1. Paste text with --- separator between test cases, and |||  between input/output
    2. Upload JSON file with [{"input": "...", "output": "..."}, ...]
    """
    user = require_admin(request, db)
    problem = db.query(Problem).filter(Problem.code == problem_code).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    max_order = db.query(TestCase).filter(
        TestCase.problem_id == problem.id
    ).count()

    added = 0

    if bulk_file and bulk_file.filename:
        # JSON file upload
        content = await bulk_file.read()
        text = content.decode("utf-8")

        if bulk_file.filename.endswith(".json"):
            tests = json.loads(text)
            for t in tests:
                inp = t.get("input", "").strip()
                out = t.get("output", t.get("expected_output", "")).strip()
                if inp and out:
                    tc = TestCase(
                        problem_id=problem.id,
                        input_data=inp,
                        expected_output=out,
                        is_sample=False,
                        order=max_order + added
                    )
                    db.add(tc)
                    added += 1
        else:
            # Plain text format: pairs of files or --- separated
            bulk_data = text

    if bulk_data and bulk_data.strip():
        # Parse pasted text: each test separated by ---
        # Input and output separated by |||
        tests_raw = bulk_data.strip().split("---")
        for block in tests_raw:
            block = block.strip()
            if not block:
                continue
            if "|||" in block:
                parts = block.split("|||")
                inp = parts[0].strip()
                out = parts[1].strip() if len(parts) > 1 else ""
            else:
                # Try splitting by empty line
                lines = block.split("\n")
                mid = len(lines) // 2
                inp = "\n".join(lines[:mid]).strip()
                out = "\n".join(lines[mid:]).strip()
            if inp and out:
                tc = TestCase(
                    problem_id=problem.id,
                    input_data=inp,
                    expected_output=out,
                    is_sample=False,
                    order=max_order + added
                )
                db.add(tc)
                added += 1

    db.commit()

    return RedirectResponse(
        url=f"/admin/problem/{problem_code}/testcases?msg=Added+{added}+test+cases",
        status_code=302
    )


@router.post("/admin/problem/{problem_code}/testcases/delete-all")
async def delete_all_testcases(
    request: Request,
    problem_code: str,
    db: Session = Depends(get_db)
):
    """Delete all non-sample test cases."""
    user = require_admin(request, db)
    problem = db.query(Problem).filter(Problem.code == problem_code).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    testcases_to_delete = db.query(TestCase.id).filter(
        TestCase.problem_id == problem.id,
        TestCase.is_sample == False
    ).all()
    testcase_ids = [tc[0] for tc in testcases_to_delete]

    if testcase_ids:
        from models import SubmissionResult
        db.query(SubmissionResult).filter(SubmissionResult.testcase_id.in_(testcase_ids)).delete(synchronize_session=False)
        db.query(TestCase).filter(TestCase.id.in_(testcase_ids)).delete(synchronize_session=False)
        db.commit()

    return RedirectResponse(
        url=f"/admin/problem/{problem_code}/testcases?msg=Deleted+hidden+test+cases",
        status_code=302
    )


@router.post("/admin/problem/{problem_code}/update-limits")
async def update_problem_limits(
    request: Request,
    problem_code: str,
    time_limit: float = Form(1.0),
    memory_limit: int = Form(256),
    db: Session = Depends(get_db)
):
    """Update time/memory limits for a problem."""
    user = require_admin(request, db)
    problem = db.query(Problem).filter(Problem.code == problem_code).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    problem.time_limit = max(0.1, min(time_limit, 30.0))
    problem.memory_limit = max(16, min(memory_limit, 1024))
    db.commit()

    return RedirectResponse(
        url=f"/admin/problem/{problem_code}/testcases?msg=Limits+updated",
        status_code=302
    )

@router.post("/admin/problem/{problem_code}/testcases/generate")
async def auto_generate_testcases(
    request: Request,
    problem_code: str,
    generator_code: str = Form(...),
    solution_code: str = Form(...),
    solution_lang: str = Form("python"),
    num_tests: int = Form(10),
    db: Session = Depends(get_db)
):
    """Auto generate test cases using provided scripts via testcase_runner."""
    user = require_admin(request, db)
    problem = db.query(Problem).filter(Problem.code == problem_code).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
        
    import sys
    import os
    tools_path = os.path.join(BASE_DIR, "tools")
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)
        
    try:
        from testcase_runner import run_local_generator
        count, run_err = run_local_generator(
            problem_code=problem_code,
            generator_code=generator_code,
            solution_code=solution_code,
            num_tests=min(50, max(1, num_tests)),
            language=solution_lang
        )
        if count is False:
            msg = f"Lỗi biên dịch/cấu hình ban đầu: {run_err}"
        elif count == 0:
            msg = f"Lỗi chạy Testcase:\n{run_err}"
        else:
            if run_err:
                 msg = f"Đã sinh {count} test cases. Có lỗi xảy ra trong một số test:\n{run_err}"
            else:
                 msg = f"Đã sinh thành công {count} test cases."
    except Exception as e:
        msg = f"Lỗi hệ thống: {str(e)}"

    from urllib.parse import quote
    return RedirectResponse(
        url=f"/admin/problem/{problem_code}/testcases?msg={quote(msg)}",
        status_code=302
    )

@router.post("/admin/problem/{problem_code}/testcases/ai-generate")
async def ai_generate_testcases(
    request: Request,
    problem_code: str,
    num_tests: int = Form(10),
    db: Session = Depends(get_db)
):
    """Generate testcases with Gemini AI completely autonomously."""
    user = require_admin(request, db)
    problem = db.query(Problem).filter(Problem.code == problem_code).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    import sys
    import os
    tools_path = os.path.join(BASE_DIR, "tools")
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)

    try:
        from auto_testcase_gen import auto_generate_testcases as ai_gen
        count, error_msg = ai_gen(problem_code, min(50, max(1, num_tests)))
        if count == 0:
            msg = f"Thất bại:\n{error_msg}"
        else:
            if error_msg:
                msg = f"Sinh được {count} test.\nCó cảnh báo:\n{error_msg}"
            else:
                msg = f"Thành công 🤖 AI sinh {count} test cases!"
    except Exception as e:
        msg = f"Lỗi hệ thống không lường trước: {str(e)}"

    from urllib.parse import quote
    return RedirectResponse(
        url=f"/admin/problem/{problem_code}/testcases?msg={quote(msg)}",
        status_code=302
    )

@router.get("/admin/testcase/{testcase_id}/edit")
async def edit_testcase_page(
    request: Request,
    testcase_id: int,
    db: Session = Depends(get_db)
):
    user = require_admin(request, db)
    tc = db.query(TestCase).filter(TestCase.id == testcase_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="TestCase not found")
    
    return templates.TemplateResponse("admin/edit_testcase.html", {
        "request": request,
        "user": user,
        "testcase": tc,
        "problem": tc.problem
    })

@router.post("/admin/testcase/{testcase_id}/edit")
async def update_testcase(
    request: Request,
    testcase_id: int,
    db: Session = Depends(get_db)
):
    user = require_admin(request, db)
    tc = db.query(TestCase).filter(TestCase.id == testcase_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="TestCase not found")
    
    form_data = await request.form()
    tc.input_data = form_data.get("input_data")
    tc.expected_output = form_data.get("expected_output")
    tc.is_sample = form_data.get("is_sample") == "true"
    
    db.commit()
    
    return RedirectResponse(
        url=f"/admin/problem/{tc.problem.code}/testcases?msg=Testcase+updated", status_code=303
    )
