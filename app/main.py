import os
import shutil
import uuid
import math
import re
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, UploadFile
from fastapi.params import Query, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from fastapi_pagination import add_pagination, Params
from fastapi_pagination.ext.sqlalchemy import paginate
from starlette.middleware.sessions import SessionMiddleware

import auth
import models
from database import engine, get_db

# ---------------------------------------------------------
# INITIALIZATION & CONFIGURATION
# ---------------------------------------------------------

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
add_pagination(app)

# Session and Template Setup
app.add_middleware(SessionMiddleware, secret_key="your-very-secret-key")
templates = Jinja2Templates(directory="templates")

# File Upload Setup
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------
# HELPERS / UTILITIES
# ---------------------------------------------------------

async def get_current_user(request: Request, db: Session):
    username = request.session.get("user")
    if not username:
        return None
    return db.query(models.User).filter(models.User.username == username).first()


def sanitize_input(text: str) -> str:
    """Removes HTML tags to prevent XSS and strips whitespace."""
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text).strip()


# ---------------------------------------------------------
# PUBLIC ROUTES
# ---------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
@app.get("/events", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db), page: int = Query(1, ge=1)):
    current_user = await get_current_user(request, db)

    # Session messages
    error = request.session.pop("error", None)
    success = request.session.pop("success", None)

    items_per_page = 5
    offset = (page - 1) * items_per_page

    events = db.query(models.Event).order_by(models.Event.id.desc()).offset(offset).limit(items_per_page).all()
    total_events = db.query(models.Event).count()
    total_pages = math.ceil(total_events / items_per_page)

    has_next = total_events > (offset + items_per_page)
    has_prev = page > 1
    featured = db.query(models.Event).filter(models.Event.is_featured == True).limit(5).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "events": events,
        "featured": featured,
        "user": current_user,
        "page": page,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev,
        "now": datetime.utcnow(),
        "error_message": error,
        "success_message": success
    })


@app.get("/event/{event_id}", response_class=HTMLResponse)
async def event_detail(event_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user(request, db)
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    share_text = f"I will attend to {event.name} @ {event.date.strftime('%Y-%m-%d')}"
    return templates.TemplateResponse("detail.html", {
        "request": request,
        "event": event,
        "share_text": share_text,
        "user": current_user
    })


# ---------------------------------------------------------
# AUTH ROUTES
# ---------------------------------------------------------

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    error_message = request.session.pop("error", None)
    success_message = request.session.pop("success", None)
    return templates.TemplateResponse("register.html", {
        "request": request,
        "error_message": error_message,
        "success_message": success_message
    })


@app.post("/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        return HTMLResponse("Username already exists", status_code=400)

    hashed_pw = auth.get_password_hash(password)
    new_user = models.User(username=username, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    error_message = request.session.pop("error", None)
    success_message = request.session.pop("success", None)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error_message": error_message,
        "success_message": success_message
    })


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == username).first()

    if not db_user or not auth.verify_password(password, db_user.hashed_password):
        request.session["error"] = "Invalid username or password. Please try again."
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    request.session["user"] = username
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


# ---------------------------------------------------------
# BACKEND ROUTES
# ---------------------------------------------------------

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), params: Params = Depends()):
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login")

    error = request.session.pop("error", None)
    success = request.session.pop("success", None)

    if params.size == 50:
        params.size = 5

    query = db.query(models.Event).order_by(models.Event.id.desc())
    page_data = paginate(db, query, params=params)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "events_page": page_data,
        "user": current_user,
        "error_message": error,
        "success_message": success
    })


@app.post("/events")
async def create_event(
        request: Request,
        name: str = Form(...),
        description: str = Form(...),
        additional_dates: List[str] = Form(...),
        location: str = Form(...),
        image_file: UploadFile = File(None),
        is_featured: bool = Form(False),
        db: Session = Depends(get_db)
):
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # 1. Image Handling
    final_image_url = None
    if image_file and image_file.filename:
        ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
        if image_file.content_type not in ALLOWED_TYPES:
            request.session["error"] = "Error: Invalid file type. Only JPG, PNG, and WEBP are allowed."
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

        MAX_FILE_SIZE = 10 * 1024 * 1024
        image_file.file.seek(0, 2)
        file_size = image_file.file.tell()
        image_file.file.seek(0)

        if file_size > MAX_FILE_SIZE:
            request.session["error"] = "Error: Image file is too large. Maximum size is 10MB."
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

        file_ext = os.path.splitext(image_file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)

        final_image_url = f"{str(request.base_url).rstrip('/')}/static/uploads/{unique_filename}"

    # 2. Sanitization & Formatting
    clean_name = sanitize_input(name)
    clean_location = sanitize_input(location)
    clean_description = sanitize_input(description)

    if clean_name:
        clean_name = clean_name[0].upper() + clean_name[1:]
    else:
        clean_name = "Untitled Event"

    if clean_location:
        clean_location = clean_location[0].upper() + clean_location[1:]

    # 3. Date Handling
    event_dates = [datetime.fromisoformat(d) for d in additional_dates]
    event_dates.sort()
    primary_date = event_dates[0]

    if primary_date < datetime.utcnow():
        request.session["error"] = "Error: Event dates cannot be in the past."
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    # 4. Database Persistence
    new_event = models.Event(
        name=clean_name,
        description=clean_description,
        location=clean_location,
        date=primary_date,
        image_url=final_image_url,
        is_featured=is_featured,
        user_id=current_user.id
    )

    for date in event_dates:
        new_event.dates.append(models.EventDate(date=date))

    db.add(new_event)
    db.commit()
    request.session["success"] = f"Success! '{clean_name}' created with {len(event_dates)} dates."

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)