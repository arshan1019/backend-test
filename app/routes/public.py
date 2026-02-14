import json
import math
from datetime import datetime

from pydantic import Json
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.params import Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
import models
from utils import get_current_user
from config import templates
from fastapi import HTTPException

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@router.get("/events", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db), page: int = Query(1, ge=1)):
    current_user = await get_current_user(request, db)
    error = request.session.pop("error", None)
    success = request.session.pop("success", None)

    items_per_page = 5
    offset = (page - 1) * items_per_page
    events = db.query(models.Event).order_by(models.Event.id.desc()).offset(offset).limit(items_per_page).all()
    total_events = db.query(models.Event).count()
    total_pages = math.ceil(total_events / items_per_page)

    return templates.TemplateResponse("index.html", {
        "request": request, "events": events,
        "featured": db.query(models.Event).filter(models.Event.is_featured == True).limit(5).all(),
        "user": current_user, "page": page, "total_pages": total_pages,
        "has_next": total_events > (offset + items_per_page),
        "has_prev": page > 1, "now": datetime.utcnow(), "error_message": error, "success_message": success
    })


@router.get("/event/{event_id}", response_class=HTMLResponse)
async def event_detail(event_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user(request, db)
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    share_text = f"I will attend to {event.name} @ {event.date.strftime('%Y-%m-%d')}"
    return templates.TemplateResponse("detail.html", {"request": request, "event": event, "share_text": share_text,
                                                      "user": current_user})


@router.get("/items")
def items(minprice: float | None = None, maxprice: float | None = None):

    if minprice is not None and maxprice is not None and minprice > maxprice:
        raise HTTPException(status_code=400, detail="minprice cannot be greater than maxprice")
    
    file_path = r"..\app\test.json"
    with open(file_path) as f:
        d = json.load(f)
        print(d)
        
        max=0
        max_prod=""
        for product in d:

            if product["price"] > max:
                max_prod = product["name"]
                max = product["price"]

        return max_prod