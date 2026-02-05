from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
import models
import auth

from main_config import templates

router = APIRouter()


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html",
                                      {"request": request, "error_message": request.session.pop("error", None)})


@router.post("/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == username).first():
        return HTMLResponse("Username already exists", status_code=400)
    new_user = models.User(username=username, hashed_password=auth.get_password_hash(password))
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html",
                                      {"request": request, "error_message": request.session.pop("error", None),
                                       "success_message": request.session.pop("success", None)})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if not db_user or not auth.verify_password(password, db_user.hashed_password):
        request.session["error"] = "Invalid username or password."
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    request.session["user"] = username
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")
