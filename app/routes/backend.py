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
from schemas import EventCreate  # Correctly imported
from utils import get_current_user, sanitize_input
from config import templates

from config import settings

router = APIRouter()
UPLOAD_DIR = "static/uploads"


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), params: Params = Depends()):
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login")

    if params.size == 50:
        params.size = 5

    error = request.session.pop("error", None)
    success = request.session.pop("success", None)

    query = db.query(models.Event).order_by(models.Event.id.desc())
    page_data = paginate(db, query, params=params)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "events_page": page_data,
        "user": current_user,
        "error_message": error,
        "success_message": success
    })


@router.post("/events")
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

        # Ensure uploads directory exists
        upload_dir = os.path.join("static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        # File Size Validation (10MB)
        image_file.file.seek(0, 2)
        file_size = image_file.file.tell()
        image_file.file.seek(0)
        if file_size > 10 * 1024 * 1024:
            request.session["error"] = "Error: Image file is too large (Max 10MB)."
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

        file_ext = os.path.splitext(image_file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)

        final_image_url = f"{str(request.base_url).rstrip('/')}/static/uploads/{unique_filename}"

    # Schema Validation (Internal usage of Pydantic)
    try:
        # We pass the raw data through the schema to validate types and required fields
        event_data = EventCreate(
            name=sanitize_input(name),
            description=sanitize_input(description),
            location=sanitize_input(location),
            date=datetime.fromisoformat(additional_dates[0]),
            additional_dates=[datetime.fromisoformat(d) for d in additional_dates],
            is_featured=is_featured,
            image_url=final_image_url
        )
    except Exception as e:
        request.session["error"] = f"Validation Error: {str(e)}"
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    # Formatting and Past Date Check
    # Ensure 1st letter is uppercase
    clean_name = event_data.name[0].upper() + event_data.name[1:] if event_data.name else "Untitled"
    clean_location = event_data.location[0].upper() + event_data.location[1:] if event_data.location else ""

    # Sort dates to ensure the primary date is the earliest
    sorted_dates = sorted(event_data.additional_dates)
    if sorted_dates[0] < datetime.utcnow():
        request.session["error"] = "Error: Event dates cannot be in the past."
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    # Database Persistence
    new_event = models.Event(
        name=clean_name,
        description=event_data.description,
        location=clean_location,
        date=sorted_dates[0],
        image_url=event_data.image_url,
        is_featured=event_data.is_featured,
        user_id=current_user.id
    )

    # Add all dates to the relationship table
    for d in sorted_dates:
        new_event.dates.append(models.EventDate(date=d))

    db.add(new_event)
    db.commit()

    request.session["success"] = f"Success! '{clean_name}' created with {len(sorted_dates)} dates."
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/events/{event_id}/delete")
async def delete_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    event = db.query(models.Event).filter(models.Event.id == event_id, models.Event.user_id == current_user.id).first()
    if not event:
        request.session["error"] = "Event not found or unauthorized."
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    # Delete local image file if it exists
    if event.image_url and "/static/uploads/" in event.image_url:
        filename = event.image_url.split("/")[-1]
        old_file_path = os.path.join(settings.UPLOAD_DIR, filename)
        if os.path.exists(old_file_path):
            os.remove(old_file_path)

    db.delete(event)
    db.commit()
    request.session["success"] = "Event deleted successfully."
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/events/{event_id}/edit")
async def edit_event(
        event_id: int,
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

    event = db.query(models.Event).filter(models.Event.id == event_id, models.Event.user_id == current_user.id).first()
    if not event:
        request.session["error"] = "Event not found."
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    # Image Handling (Replace and Delete Old)
    final_image_url = event.image_url
    if image_file and image_file.filename:
        # Delete old file
        if event.image_url and "/static/uploads/" in event.image_url:
            old_filename = event.image_url.split("/")[-1]
            old_path = os.path.join(settings.UPLOAD_DIR, old_filename)
            if os.path.exists(old_path):
                os.remove(old_path)


        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        # Save new file
        file_ext = os.path.splitext(image_file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        final_image_url = f"{str(request.base_url).rstrip('/')}/static/uploads/{unique_filename}"

    #  Sanitize and Validate
    event_dates = sorted([datetime.fromisoformat(d) for d in additional_dates])
    if event_dates[0] < datetime.utcnow():
        request.session["error"] = "Error: Event dates cannot be in the past."
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    #  Update Event Object
    event.name = sanitize_input(name).capitalize()
    event.description = sanitize_input(description)
    event.location = sanitize_input(location).capitalize()
    event.date = event_dates[0]
    event.image_url = final_image_url
    event.is_featured = is_featured

    #  Update Dates (Clear old and add new)
    db.query(models.EventDate).filter(models.EventDate.event_id == event.id).delete()
    for d in event_dates:
        event.dates.append(models.EventDate(date=d))

    db.commit()
    request.session["success"] = "Event updated successfully!"
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)