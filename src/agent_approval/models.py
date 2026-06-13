"""Agent Approval model — tracks pending tool-call approval requests."""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime

from core.database import Base


class AgentApproval(Base):
    __tablename__ = "agent_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False)
    tool_args = Column(Text, default="")
    explanation = Column(String(500), default="")
    status = Column(String(20), default="pending", index=True)  # pending | approved | rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)
