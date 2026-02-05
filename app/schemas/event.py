from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from .user import UserOut  # Import the User schema for nesting


class EventDateBase(BaseModel):
    date: datetime


class EventDateOut(EventDateBase):
    id: int

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    name: str
    description: str
    location: str
    date: datetime  # Primary/Main date
    additional_dates: Optional[List[datetime]] = []
    is_featured: bool = False
    image_url: Optional[str] = None


class EventOut(BaseModel):
    id: int
    name: str
    description: str
    location: str
    date: datetime
    is_featured: bool
    image_url: Optional[str]
    owner: UserOut  # Nested Pydantic model
    dates: List[EventDateOut] = []  # Nested List of models

    class Config:
        from_attributes = True
