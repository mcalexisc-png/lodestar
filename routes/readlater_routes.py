"""Read Later routes — bookmark web content for later reading."""

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from core.database import SessionLocal
from src.auth_helpers import get_current_user, require_user
from src.read_later.models import ReadLater

logger = logging.getLogger(__name__)


def setup_readlater_routes() -> APIRouter:
    router = APIRouter(prefix="/api/read-later", tags=["read-later"])

    @router.get("")
    async def list_items(request: Request, search: str = ""):
        require_user(request)
        db: DBSession = SessionLocal()
        try:
            q = db.query(ReadLater).order_by(ReadLater.created_at.desc())
            if search:
                like = f"%{search}%"
                q = q.filter(
                    ReadLater.title.ilike(like) |
                    ReadLater.url.ilike(like) |
                    ReadLater.notes.ilike(like)
                )
            rows = q.limit(100).all()
            return {"items": [{
                "id": r.id,
                "url": r.url,
                "title": r.title,
                "notes": r.notes,
                "tags": r.tags.split(",") if r.tags else [],
                "is_read": r.is_read,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            } for r in rows]}
        finally:
            db.close()

    @router.post("")
    async def create_item(request: Request):
        require_user(request)
        body = await request.json()
        url = ((body or {}).get("url") or "").strip()
        if not url:
            raise HTTPException(400, "url is required")
        db: DBSession = SessionLocal()
        try:
            item = ReadLater(
                url=url,
                title=((body.get("title") or "")).strip(),
                notes=((body.get("notes") or "")).strip(),
                tags=",".join(body.get("tags", [])),
            )
            db.add(item)
            db.commit()
            return {"id": item.id, "ok": True}
        finally:
            db.close()

    @router.put("/{item_id}")
    async def update_item(item_id: int, request: Request):
        require_user(request)
        body = await request.json()
        db: DBSession = SessionLocal()
        try:
            item = db.query(ReadLater).filter(ReadLater.id == item_id).first()
            if not item:
                raise HTTPException(404, "Item not found")
            if body.get("title") is not None:
                item.title = body["title"].strip()
            if body.get("notes") is not None:
                item.notes = body["notes"].strip()
            if body.get("tags") is not None:
                item.tags = ",".join(body["tags"])
            if body.get("is_read") is not None:
                item.is_read = bool(body["is_read"])
            db.commit()
            return {"ok": True}
        finally:
            db.close()

    @router.delete("/{item_id}")
    async def delete_item(item_id: int, request: Request):
        require_user(request)
        db: DBSession = SessionLocal()
        try:
            item = db.query(ReadLater).filter(ReadLater.id == item_id).first()
            if not item:
                raise HTTPException(404, "Item not found")
            db.delete(item)
            db.commit()
            return {"ok": True}
        finally:
            db.close()

    return router
