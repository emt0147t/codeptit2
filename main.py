"""
CodePTITclone - Main Application
FastAPI-based online judge system for competitive programming practice.
"""
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from config import SECRET_KEY, CATEGORIES, BASE_DIR
from database import get_db, init_db
from models import Problem, Submission, User
from routers import auth, problems, submissions

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(title="CodePTITclone", version="1.0.0")

# Middleware
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Static files & templates – use absolute paths for Linux deployment
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Include routers
app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(submissions.router)


@app.on_event("startup")
def startup():
    """Initialize database on startup."""
    import os
    logger.info(f"Starting CodePTITclone, BASE_DIR={BASE_DIR}")
    
    # Check if we are using a remote Postgres DB or local SQLite
    is_sqlite = "sqlite" in os.getenv("DATABASE_URL", "") or not os.getenv("DATABASE_URL")
    db_exists = (BASE_DIR / 'online_judge.db').exists() if is_sqlite else True
    
    logger.info(f"DB exists/remote: {db_exists}")
    init_db()
    
    # Always ensure admin accounts are up to date
    try:
        import init_db as init_script
        init_script.create_admins()
    except Exception as e:
        logger.error(f"Failed to ensure admin accounts: {e}")

    # Check if we need to add sample problems (only on first run or remote)
    if not db_exists or not is_sqlite:
        try:
            logger.info("Initializing sample problems...")
            import init_db as init_script
            init_script.add_sample_problems()
        except Exception as e:
            logger.error(f"Failed to initialize sample problems: {e}")
            
    logger.info("Database initialized successfully")


import time

home_stats_cache = {"timestamp": 0, "data": {}}

@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    """Home page with stats and recent problems."""
    from routers.auth import get_current_user
    user = get_current_user(request, db)

    current_time = time.time()
    if current_time - home_stats_cache["timestamp"] > 60 or not home_stats_cache["data"]:
        total_problems = db.query(Problem).count()
        total_submissions = db.query(Submission).count()
        total_users = db.query(User).count()

        # Category stats
        from sqlalchemy import func
        cat_counts = dict(
            db.query(Problem.category, func.count(Problem.id))
            .group_by(Problem.category).all()
        )
        categories_with_counts = []
        for slug, info in CATEGORIES.items():
            categories_with_counts.append({
                "slug": slug,
                **info,
                "count": cat_counts.get(slug, 0),
            })
            
        home_stats_cache["data"] = {
            "total_problems": total_problems,
            "total_submissions": total_submissions,
            "total_users": total_users,
            "categories": categories_with_counts
        }
        home_stats_cache["timestamp"] = current_time

    data = home_stats_cache["data"]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "total_problems": data["total_problems"],
        "total_submissions": data["total_submissions"],
        "total_users": data["total_users"],
        "categories": data["categories"],
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)