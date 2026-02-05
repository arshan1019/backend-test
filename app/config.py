# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str
    DEBUG: bool = False
    UPLOAD_DIR: str = "static/uploads"

    # tell Pydantic to read from the .env file
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
