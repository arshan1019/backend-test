import re
from fastapi import Request
from sqlalchemy.orm import Session
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
