from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi.templating import Jinja2Templates
import os

class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str
    DEBUG: bool = False
    UPLOAD_DIR: str = "static/uploads"

    # tell Pydantic to read from the .env file
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

# Create static/uploads directory if it doesn't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Shared templates instance
templates = Jinja2Templates(directory="templates")
