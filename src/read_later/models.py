"""Read Later model — bookmarks for web content."""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime

from core.database import Base


class ReadLater(Base):
    __tablename__ = "read_later"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), nullable=False)
    title = Column(String(500), default="")
    notes = Column(Text, default="")
    tags = Column(String(500), default="")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
