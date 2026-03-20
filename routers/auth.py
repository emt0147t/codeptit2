"""
Authentication routes: login, register, logout.
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from config import BASE_DIR
from sqlalchemy.orm import Session

from database import get_db
from models import User
import bcrypt as _bcrypt

from starlette.concurrency import run_in_threadpool
import re

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


async def hash_password(password: str) -> str:
    return await run_in_threadpool(
        lambda: _bcrypt.hashpw(password.encode('utf-8'), _bcrypt.gensalt()).decode('utf-8')
    )


async def verify_password(password: str, hashed: str) -> bool:
    return await run_in_threadpool(
        lambda: _bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    )


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Get current user from session."""
    user_id = request.session.get("user_id")
    if user_id:
        return db.query(User).filter(User.id == user_id).first()
    return None


def require_login(request: Request, db: Session = Depends(get_db)):
    """Require user to be logged in."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Please login first")
    return user


def require_admin(request: Request, db: Session = Depends(get_db)):
    """Require user to be admin."""
    user = require_login(request, db)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/login")
async def login_page(request: Request):
    user = get_current_user(request, next(get_db()))
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request, "error": None
    })


import time
auth_rate_limit = {}

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Basic IP Rate Limiting for Login (Max 5 attempts per IP per minute)
    ip = request.client.host
    current_time = time.time()
    
    if ip not in auth_rate_limit:
        auth_rate_limit[ip] = {"logins": 0, "login_time": current_time, "registers": 0, "register_time": current_time}
    
    if current_time - auth_rate_limit[ip]["login_time"] > 60:
        auth_rate_limit[ip]["logins"] = 0
        auth_rate_limit[ip]["login_time"] = current_time
        
    if auth_rate_limit[ip]["logins"] >= 5:
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Bạn đăng nhập sai quá nhiều. Vui lòng thử lại sau 1 phút."
        })
    auth_rate_limit[ip]["logins"] += 1

    user = db.query(User).filter(User.username == username).first()
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Sai tên đăng nhập hoặc mật khẩu"
        })
    
    is_valid = await verify_password(password, user.password_hash)
    if not is_valid:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Sai tên đăng nhập hoặc mật khẩu"
        })
        
    # Reset count on success
    auth_rate_limit[ip]["logins"] = 0
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=302)


@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {
        "request": request, "error": None
    })


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db)
):
    ip = request.client.host
    current_time = time.time()
    if ip not in auth_rate_limit:
        auth_rate_limit[ip] = {"logins": 0, "login_time": current_time, "registers": 0, "register_time": current_time}
        
    if current_time - auth_rate_limit[ip]["register_time"] > 60:
        auth_rate_limit[ip]["registers"] = 0
        auth_rate_limit[ip]["register_time"] = current_time
        
    if auth_rate_limit[ip]["registers"] >= 3:
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "Đăng ký quá nhanh. Vui lòng thử lại sau 1 phút."
        })
    auth_rate_limit[ip]["registers"] += 1

    # Validate
    if password != password_confirm:
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "Mật khẩu không khớp"
        })
        
    # Regex validation
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "Định dạng email không hợp lệ"
        })
        
    if len(password) < 6:
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "Mật khẩu phải chứa ít nhất 6 ký tự"
        })

    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "Tên đăng nhập đã tồn tại"
        })

    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "Email đã tồn tại"
        })

    # Create user hash in background threadpool
    hashed_pwd = await hash_password(password)
    user = User(
        username=username,
        email=email,
        password_hash=hashed_pwd,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)
