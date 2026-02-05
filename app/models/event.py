from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    description = Column(String)
    date = Column(DateTime, default=datetime.utcnow)
    location = Column(String)
    image_url = Column(String, nullable=True)
    is_featured = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    # String references "User" and "EventDate"
    owner = relationship("User", back_populates="events")
    dates = relationship("EventDate", back_populates="event", cascade="all, delete-orphan")


class EventDate(Base):
    __tablename__ = "event_dates"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    date = Column(DateTime)

    event = relationship("Event", back_populates="dates")
