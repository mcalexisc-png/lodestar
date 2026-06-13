from sqlalchemy import Column, Integer, String, Text, DateTime, func
from core.database import Base


class CodeRun(Base):
    __tablename__ = "code_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    file_path = Column(String, nullable=True)
    language = Column(String, nullable=True)
    exit_code = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    stdout_snippet = Column(Text, nullable=True)
    stderr_snippet = Column(Text, nullable=True)


class Snippet(Base):
    __tablename__ = "snippets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    language = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    tags = Column(String, nullable=True)
    workspace_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
