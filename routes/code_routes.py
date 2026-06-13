"""Code Workspace routes — file tree, file read/write, code execution, snippets."""

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session as DBSession

from core.database import SessionLocal
from src.auth_helpers import get_current_user, require_user
from src.code_workspace.models import CodeRun, Snippet
from src.constants import LODESTAR_LITE

logger = logging.getLogger(__name__)


def _get_workspace_root() -> str:
    from src.settings import get_setting
    return get_setting("workspace_root", os.path.expanduser("~"))


def _resolve_path(raw_path: str) -> str:
    root = os.path.realpath(_get_workspace_root())
    expanded = os.path.expanduser(raw_path.strip())
    candidate = expanded if os.path.isabs(expanded) else os.path.join(root, expanded)
    resolved = os.path.realpath(candidate)
    if os.path.commonpath([resolved, root]) != root:
        raise ValueError(f"Path '{raw_path}' is outside workspace root")
    return resolved


def _safe_list_dir(path: str) -> list[dict]:
    entries = []
    try:
        for entry in sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower())):
            if entry.name.startswith("."):
                continue
            entries.append({
                "name": entry.name,
                "path": entry.path,
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else 0,
            })
    except PermissionError:
        pass
    return entries


def setup_code_routes() -> APIRouter:
    router = APIRouter(prefix="/api/code", tags=["code"])

    @router.get("/files")
    async def list_files(request: Request, root: str = ""):
        require_user(request)
        target = root if root else _get_workspace_root()
        try:
            resolved = _resolve_path(target)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if not os.path.isdir(resolved):
            raise HTTPException(400, "Not a directory")
        return {"path": resolved, "entries": _safe_list_dir(resolved)}

    @router.get("/file")
    async def read_file(request: Request, path: str):
        require_user(request)
        try:
            resolved = _resolve_path(path)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if not os.path.isfile(resolved):
            raise HTTPException(404, "File not found")
        try:
            content = Path(resolved).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise HTTPException(500, f"Failed to read file: {e}")
        ext = Path(resolved).suffix.lstrip(".")
        return {"path": resolved, "content": content, "language": ext or "plaintext"}

    @router.put("/file")
    async def write_file(request: Request):
        require_user(request)
        body = await request.json()
        raw_path = (body or {}).get("path", "")
        content = (body or {}).get("content", "")
        if not raw_path:
            raise HTTPException(400, "path is required")
        try:
            resolved = _resolve_path(raw_path)
        except ValueError as e:
            raise HTTPException(400, str(e))
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        try:
            Path(resolved).write_text(content, encoding="utf-8")
        except Exception as e:
            raise HTTPException(500, f"Failed to write file: {e}")
        return {"path": resolved, "ok": True}

    # ── Git panel ──

    @router.get("/git/status")
    async def git_status(request: Request):
        require_user(request)
        root = _get_workspace_root()
        git_dir = os.path.join(root, ".git")
        if not os.path.isdir(git_dir):
            raise HTTPException(400, "Not a git repository")
        try:
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=root, capture_output=True, text=True, timeout=10,
            ).stdout.strip()
            status_proc = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root, capture_output=True, text=True, timeout=10,
            )
            files = []
            for line in status_proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                files.append({"status": line[:2].strip() or "?", "path": line[3:].strip()})
            log_proc = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                cwd=root, capture_output=True, text=True, timeout=10,
            )
            log = []
            for line in log_proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(" ", 1)
                log.append({"hash": parts[0], "message": parts[1] if len(parts) > 1 else ""})
            return {"branch": branch, "files": files, "log": log}
        except subprocess.TimeoutExpired:
            raise HTTPException(504, "git status timed out")
        except Exception as e:
            raise HTTPException(500, f"git status failed: {e}")

    @router.post("/git/commit")
    async def git_commit(request: Request):
        require_user(request)
        body = await request.json()
        message = (body or {}).get("message", "").strip()
        if not message:
            raise HTTPException(400, "Commit message is required")
        root = _get_workspace_root()
        git_dir = os.path.join(root, ".git")
        if not os.path.isdir(git_dir):
            raise HTTPException(400, "Not a git repository")
        try:
            add_result = subprocess.run(
                ["git", "add", "-A"],
                cwd=root, capture_output=True, text=True, timeout=30,
            )
            if add_result.returncode != 0:
                raise HTTPException(500, f"git add failed: {add_result.stderr.strip()}")
            commit_result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=root, capture_output=True, text=True, timeout=30,
            )
            if commit_result.returncode != 0:
                raise HTTPException(500, f"git commit failed: {commit_result.stderr.strip()}")
            return {"ok": True, "message": commit_result.stdout.strip()}
        except subprocess.TimeoutExpired:
            raise HTTPException(504, "git commit timed out")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"git commit failed: {e}")

    @router.post("/git/ai-commit-msg")
    async def git_ai_commit_msg(request: Request):
        require_user(request)
        root = _get_workspace_root()
        git_dir = os.path.join(root, ".git")
        if not os.path.isdir(git_dir):
            raise HTTPException(400, "Not a git repository")
        try:
            diff = subprocess.run(
                ["git", "diff", "--cached", "--stat"],
                cwd=root, capture_output=True, text=True, timeout=10,
            )
            diff_staged = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=root, capture_output=True, text=True, timeout=10,
            )
            diff_working = subprocess.run(
                ["git", "diff"],
                cwd=root, capture_output=True, text=True, timeout=10,
            )
            combined = diff_staged.stdout + diff_working.stdout
            summary = diff.stdout.strip()
            if not combined.strip():
                add_result = subprocess.run(
                    ["git", "add", "-A"],
                    cwd=root, capture_output=True, text=True, timeout=30,
                )
                if add_result.returncode == 0:
                    diff_staged2 = subprocess.run(
                        ["git", "diff", "--cached"],
                        cwd=root, capture_output=True, text=True, timeout=10,
                    )
                    combined = diff_staged2.stdout
                    summary = summary or subprocess.run(
                        ["git", "diff", "--cached", "--stat"],
                        cwd=root, capture_output=True, text=True, timeout=10,
                    ).stdout.strip()
            if not combined.strip():
                return {"message": "No changes to commit"}
            from src.endpoint_resolver import resolve_endpoint
            from src.llm_core import llm_call_async
            user = get_current_user(request)
            url, model, headers = resolve_endpoint("task", owner=user or None)
            if not url or not model:
                url, model, headers = resolve_endpoint("default", owner=user or None)
            if not url or not model:
                return {"message": "feat: update code"}
            prompt = (
                "Generate a concise git commit message (one line, 72 chars max) "
                "for the following diff. Use conventional commit format "
                "(feat:, fix:, refactor:, chore:, docs:, etc.).\n\n"
                f"Summary:\n{summary}\n\n"
                f"Diff (first 4000 chars):\n{combined[:4000]}"
            )
            try:
                response = await llm_call_async(
                    url, model,
                    [{"role": "system", "content": "You generate concise git commit messages. Reply with only the commit message, no extra text."},
                     {"role": "user", "content": prompt}],
                    temperature=0.1, max_tokens=100, headers=headers, timeout=30,
                )
                msg = response.strip().split("\n")[0][:72].strip()
                return {"message": msg or "feat: update code"}
            except Exception:
                return {"message": "feat: update code"}
        except subprocess.TimeoutExpired:
            return {"message": "fix: resolve issues"}
        except Exception as e:
            return {"message": f"chore: {e}"[:72]}

    # ── Snippets CRUD ──

    @router.get("/snippets")
    async def list_snippets(request: Request):
        require_user(request)
        db: DBSession = SessionLocal()
        try:
            rows = db.query(Snippet).order_by(Snippet.name).all()
            return {"snippets": [{
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "language": r.language,
                "body": r.body,
                "tags": json.loads(r.tags) if r.tags else [],
                "created_at": r.created_at.isoformat() if r.created_at else None,
            } for r in rows]}
        finally:
            db.close()

    @router.post("/snippets")
    async def create_snippet(request: Request):
        require_user(request)
        body = await request.json()
        if not body or not body.get("name") or not body.get("body"):
            raise HTTPException(400, "name and body are required")
        db: DBSession = SessionLocal()
        try:
            snippet = Snippet(
                name=body["name"],
                description=body.get("description", ""),
                language=body.get("language", ""),
                body=body["body"],
                tags=json.dumps(body.get("tags", [])),
            )
            db.add(snippet)
            db.commit()
            return {"id": snippet.id, "ok": True}
        finally:
            db.close()

    @router.put("/snippets/{snippet_id}")
    async def update_snippet(snippet_id: int, request: Request):
        require_user(request)
        body = await request.json()
        db: DBSession = SessionLocal()
        try:
            snippet = db.query(Snippet).filter(Snippet.id == snippet_id).first()
            if not snippet:
                raise HTTPException(404, "Snippet not found")
            if body.get("name") is not None:
                snippet.name = body["name"]
            if body.get("description") is not None:
                snippet.description = body["description"]
            if body.get("language") is not None:
                snippet.language = body["language"]
            if body.get("body") is not None:
                snippet.body = body["body"]
            if body.get("tags") is not None:
                snippet.tags = json.dumps(body["tags"])
            db.commit()
            return {"ok": True}
        finally:
            db.close()

    @router.delete("/snippets/{snippet_id}")
    async def delete_snippet(snippet_id: int, request: Request):
        require_user(request)
        db: DBSession = SessionLocal()
        try:
            snippet = db.query(Snippet).filter(Snippet.id == snippet_id).first()
            if not snippet:
                raise HTTPException(404, "Snippet not found")
            db.delete(snippet)
            db.commit()
            return {"ok": True}
        finally:
            db.close()

    # ── AI code actions ──

    @router.post("/ai")
    async def code_ai_action(request: Request):
        require_user(request)
        if LODESTAR_LITE:
            raise HTTPException(403, "ai_disabled_lite_mode")
        body = await request.json()
        file_path = (body or {}).get("file_path", "")
        action = (body or {}).get("action", "")
        user_prompt = (body or {}).get("prompt", "")
        if not file_path or not action:
            raise HTTPException(400, "file_path and action are required")
        try:
            resolved = _resolve_path(file_path)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if not os.path.isfile(resolved):
            raise HTTPException(404, "File not found")
        try:
            code = Path(resolved).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise HTTPException(500, f"Failed to read file: {e}")
        if not code.strip():
            raise HTTPException(400, "File is empty")
        ext = Path(resolved).suffix.lstrip(".")

        # Resolve AI endpoint — prefer task endpoint (which user can set to Nemotron)
        from src.endpoint_resolver import resolve_endpoint
        from src.llm_core import llm_call_async
        user = get_current_user(request)
        url, model, headers = resolve_endpoint("task", owner=user or None)
        if not url or not model:
            url, model, headers = resolve_endpoint("default", owner=user or None)
        if not url or not model:
            raise HTTPException(500, "No AI endpoint configured. Add one in Settings.")

        prompts = {
            "explain": (
                "You are a senior software engineer. Explain the following code clearly:\n"
                "- What it does at a high level\n"
                "- Key functions and their purpose\n"
                "- Any notable patterns or techniques used"
            ),
            "fix": (
                "You are a senior software engineer. Review the following code for bugs, "
                "security issues, and logic errors. List each issue found and suggest fixes."
            ),
            "refactor": (
                "You are a senior software engineer. Suggest refactoring improvements for "
                "the following code:\n- Readability and maintainability\n- Performance "
                "optimizations\n- Better error handling\n- Modern idiomatic patterns"
            ),
            "optimize": (
                "You are a performance engineer. Analyze the following code for performance "
                "bottlenecks and suggest specific optimizations."
            ),
            "comment": (
                "You are a documentation specialist. Add clear, professional comments to "
                "the following code. Return the full code with comments added. Explain "
                "non-obvious logic and document function signatures."
            ),
            "custom": user_prompt or "Review the following code.",
        }
        system_prompt = prompts.get(action, prompts["custom"])

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"File: {os.path.basename(resolved)}\nLanguage: {ext}\n\n```{ext}\n{code}\n```"},
        ]

        try:
            response = await llm_call_async(
                url, model, messages,
                temperature=0.2 if action in ("fix", "refactor") else 0.3,
                max_tokens=4096,
                headers=headers,
                timeout=120,
            )
            return {"response": response.strip(), "model": model}
        except Exception as e:
            raise HTTPException(502, f"AI call failed: {e}")

    # ── Code execution ──

    @router.post("/run")
    async def run_code(request: Request):
        require_user(request)
        if LODESTAR_LITE:
            raise HTTPException(403, "execution_disabled_lite_mode")
        body = await request.json()
        file_path = (body or {}).get("file_path", "")
        language = (body or {}).get("language", "")
        stdin_input = (body or {}).get("stdin_input", "")
        if not file_path or not language:
            raise HTTPException(400, "file_path and language are required")
        try:
            resolved = _resolve_path(file_path)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if not os.path.isfile(resolved):
            raise HTTPException(404, "File not found")

        interpreter = _get_interpreter(language)
        if not interpreter:
            raise HTTPException(400, f"No interpreter configured for language: {language}")

        import time
        start = time.monotonic()
        try:
            result = subprocess.run(
                [interpreter, resolved],
                cwd=os.path.dirname(resolved),
                capture_output=True,
                text=True,
                timeout=120,
                input=stdin_input or None,
            )
        except subprocess.TimeoutExpired:
            _record_run(resolved, language, -1, 120000, "", "Timed out after 120s")
            return {"exit_code": -1, "stdout": "", "stderr": "Timed out after 120s"}
        duration = int((time.monotonic() - start) * 1000)
        stdout = (result.stdout or "")[:50000]
        stderr = (result.stderr or "")[:50000]
        _record_run(resolved, language, result.returncode, duration, stdout, stderr)
        return {
            "exit_code": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": duration,
        }

    return router


LANGUAGE_MAP = {
    "py": "python3",
    "python": "python3",
    "js": "node",
    "javascript": "node",
    "sh": "bash",
    "bash": "bash",
    "ts": "node",
    "typescript": "node",
}


def _get_interpreter(language: str) -> str | None:
    lang = language.lower().strip()
    if lang in LANGUAGE_MAP:
        return LANGUAGE_MAP[lang]
    from src.settings import get_setting
    custom = get_setting(f"interpreter_{lang}")
    if custom:
        return custom
    return None


def _record_run(file_path: str, language: str, exit_code: int, duration_ms: int, stdout: str, stderr: str):
    try:
        db: DBSession = SessionLocal()
        run = CodeRun(
            file_path=file_path,
            language=language,
            exit_code=exit_code,
            duration_ms=duration_ms,
            stdout_snippet=stdout[:2000],
            stderr_snippet=stderr[:2000],
        )
        db.add(run)
        rows = db.query(CodeRun).count()
        if rows > 100:
            oldest = db.query(CodeRun).order_by(CodeRun.timestamp).first()
            if oldest:
                db.delete(oldest)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to record code run: {e}")
    finally:
        db.close()
