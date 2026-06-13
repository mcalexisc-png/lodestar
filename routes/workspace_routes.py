"""Workspace routes — multi-workspace support with JSON-file persistence."""

import json
import logging
import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from core.database import SessionLocal
from src.auth_helpers import get_current_user, require_user

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
WORKSPACES_FILE = os.path.join(DATA_DIR, "workspaces.json")


def _load_workspaces() -> list[dict]:
    try:
        if os.path.isfile(WORKSPACES_FILE):
            with open(WORKSPACES_FILE, encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load workspaces: %s", e)
    return []


def _save_workspaces(workspaces: list[dict]):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = WORKSPACES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(workspaces, f, indent=2)
    os.replace(tmp, WORKSPACES_FILE)


def _get_active_workspace_id() -> str:
    from src.settings import load_settings
    return (load_settings().get("active_workspace_id") or "").strip()


def _set_active_workspace_id(ws_id: str):
    from src.settings import load_settings, save_settings
    settings = load_settings()
    settings["active_workspace_id"] = ws_id
    save_settings(settings)


def get_workspace_root() -> str:
    """Return the root path of the active workspace, or the default workspace_root setting."""
    ws_id = _get_active_workspace_id()
    if ws_id:
        workspaces = _load_workspaces()
        for ws in workspaces:
            if ws.get("id") == ws_id:
                root = ws.get("root_path", "").strip()
                if root and os.path.isdir(root):
                    return os.path.realpath(root)
    from src.settings import get_setting
    return get_setting("workspace_root", os.path.expanduser("~"))


def setup_workspace_routes() -> APIRouter:
    router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])

    @router.get("")
    async def list_workspaces(request: Request):
        require_user(request)
        workspaces = _load_workspaces()
        active_id = _get_active_workspace_id()
        return {"workspaces": workspaces, "active_id": active_id}

    @router.post("")
    async def create_workspace(request: Request):
        require_user(request)
        body = await request.json()
        name = ((body or {}).get("name") or "").strip()
        root_path = ((body or {}).get("root_path") or "").strip()
        if not name:
            raise HTTPException(400, "name is required")
        if not root_path:
            raise HTTPException(400, "root_path is required")
        resolved = os.path.realpath(os.path.expanduser(root_path))
        if not os.path.isdir(resolved):
            raise HTTPException(400, f"Directory does not exist: {resolved}")
        workspaces = _load_workspaces()
        if any(w["name"].lower() == name.lower() for w in workspaces):
            raise HTTPException(409, f"Workspace '{name}' already exists")
        ws = {
            "id": uuid.uuid4().hex[:12],
            "name": name,
            "root_path": resolved,
            "created_at": time.time(),
        }
        workspaces.append(ws)
        _save_workspaces(workspaces)
        _set_active_workspace_id(ws["id"])
        return ws

    @router.put("/{ws_id}")
    async def update_workspace(ws_id: str, request: Request):
        require_user(request)
        body = await request.json()
        workspaces = _load_workspaces()
        for ws in workspaces:
            if ws["id"] == ws_id:
                if body.get("name"):
                    ws["name"] = body["name"].strip()
                if body.get("root_path"):
                    resolved = os.path.realpath(os.path.expanduser(body["root_path"].strip()))
                    if not os.path.isdir(resolved):
                        raise HTTPException(400, f"Directory does not exist: {resolved}")
                    ws["root_path"] = resolved
                _save_workspaces(workspaces)
                return ws
        raise HTTPException(404, "Workspace not found")

    @router.delete("/{ws_id}")
    async def delete_workspace(ws_id: str, request: Request):
        require_user(request)
        workspaces = _load_workspaces()
        new_list = [w for w in workspaces if w["id"] != ws_id]
        if len(new_list) == len(workspaces):
            raise HTTPException(404, "Workspace not found")
        _save_workspaces(new_list)
        if _get_active_workspace_id() == ws_id:
            _set_active_workspace_id("")
        return {"ok": True}

    @router.post("/{ws_id}/activate")
    async def activate_workspace(ws_id: str, request: Request):
        require_user(request)
        workspaces = _load_workspaces()
        for ws in workspaces:
            if ws["id"] == ws_id:
                root = ws.get("root_path", "")
                if root and not os.path.isdir(root):
                    raise HTTPException(400, f"Workspace directory no longer exists: {root}")
                _set_active_workspace_id(ws_id)
                return {"ok": True, "workspace": ws}
        raise HTTPException(404, "Workspace not found")

    return router
