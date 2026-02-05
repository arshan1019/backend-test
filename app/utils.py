import re
from fastapi import Request
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
import models


async def get_current_user(request: Request, db: Session):
    username = request.session.get("user")
    if not username:
        return None
    return db.query(models.User).filter(models.User.username == username).first()


def sanitize_input(text: str) -> str:
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text).strip()



def run_migrations(alembic_ini_path: str = "alembic.ini"):
    """
    Run Alembic migrations programmatically to upgrade the database
    to the latest version.
    
    :param alembic_ini_path: Path to alembic.ini file
    """
    alembic_cfg = Config(alembic_ini_path)
    command.upgrade(alembic_cfg, "head")
