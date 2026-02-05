import os, shutil, uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from fastapi_pagination import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from database import get_db
import models
from utils import get_current_user, sanitize_input
from main_config import templates

router = APIRouter()
UPLOAD_DIR = "static/uploads"


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), params: Params = Depends()):
    current_user = await get_current_user(request, db)
    if not current_user: return RedirectResponse(url="/login")
    if params.size == 50: params.size = 5

    query = db.query(models.Event).order_by(models.Event.id.desc())
    page_data = paginate(db, query, params=params)
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "events_page": page_data, "user": current_user,
        "error_message": request.session.pop("error", None), "success_message": request.session.pop("success", None)
    })


@router.post("/events")
async def create_event(
        request: Request, name: str = Form(...), description: str = Form(...),
        additional_dates: List[str] = Form(...), location: str = Form(...),
        image_file: UploadFile = File(None), is_featured: bool = Form(False), db: Session = Depends(get_db)
):
    current_user = await get_current_user(request, db)
    if not current_user: return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    final_image_url = None
    if image_file and image_file.filename:
        # (Add your file type/size validation logic here exactly as it was)
        file_ext = os.path.splitext(image_file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        final_image_url = f"{str(request.base_url).rstrip('/')}/static/uploads/{unique_filename}"

    clean_name = sanitize_input(name).capitalize()
    clean_location = sanitize_input(location).capitalize()
    event_dates = sorted([datetime.fromisoformat(d) for d in additional_dates])

    if event_dates[0] < datetime.utcnow():
        request.session["error"] = "Error: Event dates cannot be in the past."
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    new_event = models.Event(
        name=clean_name, description=sanitize_input(description), location=clean_location,
        date=event_dates[0], image_url=final_image_url, is_featured=is_featured, user_id=current_user.id
    )
    for d in event_dates: new_event.dates.append(models.EventDate(date=d))
    db.add(new_event);
    db.commit()
    request.session["success"] = f"Success! '{clean_name}' created."
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)