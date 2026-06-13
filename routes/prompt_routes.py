"""Prompt Library routes — CRUD for reusable prompt templates."""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from core.database import SessionLocal
from src.auth_helpers import get_current_user, require_user
from src.prompt_library.models import PromptTemplate

logger = logging.getLogger(__name__)


def setup_prompt_routes() -> APIRouter:
    router = APIRouter(prefix="/api/prompts", tags=["prompts"])

    @router.get("")
    async def list_prompts(request: Request, category: str = "", search: str = ""):
        require_user(request)
        db: DBSession = SessionLocal()
        try:
            q = db.query(PromptTemplate)
            if category:
                q = q.filter(PromptTemplate.category == category)
            if search:
                like = f"%{search}%"
                q = q.filter(
                    PromptTemplate.name.ilike(like) |
                    PromptTemplate.description.ilike(like) |
                    PromptTemplate.body.ilike(like)
                )
            rows = q.order_by(PromptTemplate.category, PromptTemplate.name).all()
            return {"prompts": [{
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "category": r.category,
                "body": r.body,
                "tags": r.tags.split(",") if r.tags else [],
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            } for r in rows]}
        finally:
            db.close()

    @router.post("")
    async def create_prompt(request: Request):
        require_user(request)
        body = await request.json()
        name = ((body or {}).get("name") or "").strip()
        body_text = ((body or {}).get("body") or "").strip()
        if not name or not body_text:
            raise HTTPException(400, "name and body are required")
        db: DBSession = SessionLocal()
        try:
            existing = db.query(PromptTemplate).filter(PromptTemplate.name == name).first()
            if existing:
                raise HTTPException(409, f"Prompt '{name}' already exists")
            prompt = PromptTemplate(
                name=name,
                description=((body.get("description") or "")).strip(),
                category=((body.get("category") or "")).strip(),
                body=body_text,
                tags=",".join(body.get("tags", [])),
            )
            db.add(prompt)
            db.commit()
            return {"id": prompt.id, "ok": True}
        finally:
            db.close()

    @router.put("/{prompt_id}")
    async def update_prompt(prompt_id: int, request: Request):
        require_user(request)
        body = await request.json()
        db: DBSession = SessionLocal()
        try:
            prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
            if not prompt:
                raise HTTPException(404, "Prompt not found")
            if body.get("name") is not None:
                prompt.name = body["name"].strip()
            if body.get("description") is not None:
                prompt.description = body["description"].strip()
            if body.get("category") is not None:
                prompt.category = body["category"].strip()
            if body.get("body") is not None:
                prompt.body = body["body"].strip()
            if body.get("tags") is not None:
                prompt.tags = ",".join(body["tags"])
            prompt.updated_at = datetime.now(timezone.utc)
            db.commit()
            return {"ok": True}
        finally:
            db.close()

    @router.delete("/{prompt_id}")
    async def delete_prompt(prompt_id: int, request: Request):
        require_user(request)
        db: DBSession = SessionLocal()
        try:
            prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
            if not prompt:
                raise HTTPException(404, "Prompt not found")
            db.delete(prompt)
            db.commit()
            return {"ok": True}
        finally:
            db.close()

    @router.get("/categories")
    async def list_categories(request: Request):
        require_user(request)
        db: DBSession = SessionLocal()
        try:
            rows = db.query(PromptTemplate.category).distinct().order_by(PromptTemplate.category).all()
            cats = sorted(set(r[0] for r in rows if r[0]))
            return {"categories": cats}
        finally:
            db.close()

    return router
