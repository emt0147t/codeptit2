"""
Submission routes: submit code, view results.
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from config import BASE_DIR
from sqlalchemy.orm import Session

import threading
from database import get_db, SessionLocal
from models import Problem, Submission, SubmissionStatus, User
from routers.auth import get_current_user, require_login
from judge.executor import Judge
from config import SUBMISSIONS_PER_PAGE, SUPPORTED_LANGUAGES
from sqlalchemy.orm import joinedload

router = APIRouter(tags=["submissions"])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Limit concurrent judging to 2 to prevent CPU 100% and OOM on 1GB RAM servers
judge_semaphore = threading.Semaphore(2)

def run_judge_async(submission_id: int):
    """Run judge in background thread with concurrency limit."""
    with judge_semaphore:
        db = SessionLocal()
        try:
            judge = Judge(db)
            judge.evaluate(submission_id)
        finally:
            db.close()



@router.post("/submit")
async def submit_code(
    request: Request,
    background_tasks: BackgroundTasks,
    problem_id: int = Form(...),
    language: str = Form(...),
    source_code: str = Form(...),
    db: Session = Depends(get_db)
):
    user = require_login(request, db)

    # Validate
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language")

    if not source_code.strip():
        raise HTTPException(status_code=400, detail="Source code is empty")

    # Create submission
    source_code = source_code[:50000]  # Prevent DB bloat
    submission = Submission(
        user_id=user.id,
        problem_id=problem.id,
        language=language,
        source_code=source_code,
        status=SubmissionStatus.PENDING,
    )
    db.add(submission)

    # Update stats
    problem.total_submissions += 1
    user.total_submissions += 1

    db.commit()
    db.refresh(submission)

    # Run judge in background
    background_tasks.add_task(run_judge_async, submission.id)

    return RedirectResponse(
        url=f"/submission/{submission.id}", status_code=302
    )


@router.get("/submission/{submission_id}")
async def submission_detail(
    request: Request,
    submission_id: int,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    submission = db.query(Submission).options(
        joinedload(Submission.user),
        joinedload(Submission.problem),
        joinedload(Submission.results)
    ).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    problem = submission.problem

    return templates.TemplateResponse("submission_detail.html", {
        "request": request,
        "user": user,
        "submission": submission,
        "problem": problem,
        "results": submission.results,
    })


@router.get("/api/submission/{submission_id}/status")
async def submission_status_api(
    submission_id: int,
    db: Session = Depends(get_db)
):
    """JSON endpoint for polling submission status without page reload."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return JSONResponse({"error": "not found"}, status_code=404)

    results = []
    for i, r in enumerate(submission.results):
        results.append({
            "index": i + 1,
            "status": str(r.status),
            "time_ms": round(r.time_ms or 0),
        })

    return JSONResponse({
        "status": str(submission.status),
        "score": round(submission.score or 0),
        "time_ms": round(submission.time_ms or 0),
        "compile_error": submission.compile_error or "",
        "results": results,
        "done": str(submission.status) != "Pending",
    })


@router.get("/submissions")
async def submission_list(
    request: Request,
    page: int = 1,
    problem_code: str = "",
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    query = db.query(Submission).options(
        joinedload(Submission.user),
        joinedload(Submission.problem)
    )

    if problem_code:
        problem = db.query(Problem).filter(Problem.code == problem_code).first()
        if problem:
            query = query.filter(Submission.problem_id == problem.id)

    total = query.count()
    submissions = query.order_by(Submission.created_at.desc()).offset(
        (page - 1) * SUBMISSIONS_PER_PAGE
    ).limit(SUBMISSIONS_PER_PAGE).all()

    total_pages = (total + SUBMISSIONS_PER_PAGE - 1) // SUBMISSIONS_PER_PAGE

    return templates.TemplateResponse("submissions.html", {
        "request": request,
        "user": user,
        "submissions": submissions,
        "page": page,
        "total_pages": total_pages,
        "problem_code": problem_code,
    })


@router.get("/my-submissions")
async def my_submissions(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db)
):
    user = require_login(request, db)

    query = db.query(Submission).options(
        joinedload(Submission.user),
        joinedload(Submission.problem)
    ).filter(Submission.user_id == user.id)
    total = query.count()
    submissions = query.order_by(Submission.created_at.desc()).offset(
        (page - 1) * SUBMISSIONS_PER_PAGE
    ).limit(SUBMISSIONS_PER_PAGE).all()

    total_pages = (total + SUBMISSIONS_PER_PAGE - 1) // SUBMISSIONS_PER_PAGE

    return templates.TemplateResponse("submissions.html", {
        "request": request,
        "user": user,
        "submissions": submissions,
        "page": page,
        "total_pages": total_pages,
        "problem_code": "",
        "title": "Bài nộp của tôi",
    })


import time

ranking_cache = {"timestamp": 0, "data": []}

@router.get("/ranking")
async def ranking(
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    
    current_time = time.time()
    if current_time - ranking_cache["timestamp"] > 60 or not ranking_cache["data"]:
        # Query DB if cache is older than 60 seconds
        users = db.query(User).order_by(
            User.solved_count.desc(),
            User.total_submissions.asc()
        ).limit(100).all()
        ranking_cache["data"] = users
        ranking_cache["timestamp"] = current_time
    else:
        users = ranking_cache["data"]

    return templates.TemplateResponse("ranking.html", {
        "request": request,
        "user": user,
        "users": users,
    })
