"""Prompt Library models."""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime

from core.database import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(500), default="")
    category = Column(String(100), default="", index=True)
    body = Column(Text, nullable=False)
    tags = Column(String(500), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
