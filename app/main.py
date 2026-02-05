import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi_pagination import add_pagination
import models
from database import engine

from config import settings

# 1. Configuration that needs to be shared
# We put templates here and import it in routers to avoid circular imports
templates = Jinja2Templates(directory="templates")

# To make this accessible to routers, we hack the main_config module
import sys
from types import ModuleType

m = ModuleType("main_config")
m.templates = templates
sys.modules["main_config"] = m

# 2. App Init
models.Base.metadata.create_all(bind=engine)
app = FastAPI(debug=settings.DEBUG)
add_pagination(app)

# use secret_key from settings
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 3. Import and Register Routers
from routes import public, auth, backend

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(backend.router)
