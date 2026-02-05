import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi_pagination import add_pagination

from config import settings, templates
from utils import run_migrations
import models
from database import engine

# Routers
from routes import public, auth, backend

app = FastAPI(debug=settings.DEBUG)
add_pagination(app)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, max_age=settings.SESSION_AGE, same_site="lax")

# Ensure uploads folder exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Run Alembic migrations on startup
@app.on_event("startup")
def on_startup():
    run_migrations()


# Include routers
app.include_router(public.router)
app.include_router(auth.router)
app.include_router(backend.router)
