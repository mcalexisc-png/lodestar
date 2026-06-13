"""Agent Approval routes — review and approve/reject tool calls."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from core.database import SessionLocal
from src.auth_helpers import get_current_user, require_user
from src.agent_approval.models import AgentApproval

logger = logging.getLogger(__name__)


def setup_approval_routes() -> APIRouter:
    router = APIRouter(prefix="/api/approvals", tags=["approvals"])

    @router.get("")
    async def list_approvals(request: Request, status: str = ""):
        require_user(request)
        db: DBSession = SessionLocal()
        try:
            q = db.query(AgentApproval)
            if status:
                q = q.filter(AgentApproval.status == status)
            rows = q.order_by(AgentApproval.created_at.desc()).limit(50).all()
            return {"approvals": [{
                "id": r.id,
                "session_id": r.session_id,
                "tool_name": r.tool_name,
                "tool_args": r.tool_args,
                "explanation": r.explanation,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            } for r in rows]}
        finally:
            db.close()

    @router.get("/pending")
    async def pending_count(request: Request):
        require_user(request)
        db: DBSession = SessionLocal()
        try:
            count = db.query(AgentApproval).filter(AgentApproval.status == "pending").count()
            return {"count": count}
        finally:
            db.close()

    @router.post("/{approval_id}/approve")
    async def approve_approval(approval_id: int, request: Request):
        require_user(request)
        db: DBSession = SessionLocal()
        try:
            item = db.query(AgentApproval).filter(AgentApproval.id == approval_id).first()
            if not item:
                raise HTTPException(404, "Approval request not found")
            item.status = "approved"
            item.resolved_at = datetime.now(timezone.utc)
            db.commit()
            return {"ok": True}
        finally:
            db.close()

    @router.post("/{approval_id}/reject")
    async def reject_approval(approval_id: int, request: Request):
        require_user(request)
        db: DBSession = SessionLocal()
        try:
            item = db.query(AgentApproval).filter(AgentApproval.id == approval_id).first()
            if not item:
                raise HTTPException(404, "Approval request not found")
            item.status = "rejected"
            item.resolved_at = datetime.now(timezone.utc)
            db.commit()
            return {"ok": True}
        finally:
            db.close()

    return router
