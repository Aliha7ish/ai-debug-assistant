from fastapi import FastAPI, Request, Form, Depends, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

import models
import ai_service
from database import engine, get_db, Base
from auth import (
    hash_password,
    verify_password,
    create_session_token,
    verify_session_token,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE,
)

load_dotenv()

# Create tables on first boot if they don't already exist.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Debug Assistant")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Session helper
# ---------------------------------------------------------------------------

def get_current_user(request: Request, db: Session) -> models.User | None:
    """Inspect the signed session cookie and resolve it to a User row, or None."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    user_id = verify_session_token(token)
    if user_id is None:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()


# ---------------------------------------------------------------------------
# Dashboard (protected)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    sessions = (
        db.query(models.ReviewSession)
        .filter(models.ReviewSession.user_id == user.id)
        .order_by(models.ReviewSession.id.desc())
        .all()
    )

    stats = {
        "total": len(sessions),
        "success": sum(1 for s in sessions if s.ai_status == "SUCCESS"),
        "failed": sum(1 for s in sessions if s.ai_status == "FAILED"),
    }

    return templates.TemplateResponse(
        request,
        "index.html",
        {"user": user, "sessions": sessions, "stats": stats},
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None})


@app.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.strip()
    email = email.strip().lower()

    existing = (
        db.query(models.User)
        .filter((models.User.username == username) | (models.User.email == email))
        .first()
    )
    if existing:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": "That username or email is already registered."},
            status_code=400,
        )

    user = models.User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": "That username or email is already registered."},
            status_code=400,
        )

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username.strip()).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid username or password."},
            status_code=400,
        )

    token = create_session_token(user.id)
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=SESSION_MAX_AGE,
        samesite="lax",
    )
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


# ---------------------------------------------------------------------------
# Issue submission -> AI pipeline (protected)
# ---------------------------------------------------------------------------

@app.post("/submit")
def submit_issue(
    request: Request,
    language: str = Form(...),
    issue_description: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    review = models.ReviewSession(
        user_id=user.id,
        language=language.strip(),
        issue_description=issue_description.strip(),
        ai_status="PENDING",
    )

    try:
        result = ai_service.analyze_issue(review.language, review.issue_description)
        review.ai_category = result["category"]
        review.ai_difficulty = result["difficulty"]
        review.ai_recommendation = result["recommendation"]
        review.ai_status = "SUCCESS"
    except Exception as e:  # noqa: BLE001 - intentional broad catch at the boundary
        review.ai_status = "FAILED"
        review.error_message = str(e)

    db.add(review)
    db.commit()

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
