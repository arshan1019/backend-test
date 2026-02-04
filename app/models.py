from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String)
    events = relationship("Event", back_populates="owner")


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    description = Column(String)
    # Primary date for sorting
    date = Column(DateTime, default=datetime.utcnow)
    location = Column(String)
    image_url = Column(String, nullable=True)  # Added requirement
    is_featured = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="events")
    # Relationship for "Date list" requirement
    dates = relationship("EventDate", back_populates="event", cascade="all, delete-orphan")


class EventDate(Base):
    __tablename__ = "event_dates"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    date = Column(DateTime)
    event = relationship("Event", back_populates="dates")
