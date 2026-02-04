from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import List, Optional


class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


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
    date: datetime  # Main date
    additional_dates: Optional[List[datetime]] = []  # Date list requirement
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
    owner: UserOut
    dates: List[EventDateOut] = []

    class Config:
        from_attributes = True
