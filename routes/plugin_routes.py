"""Routes for the in-process plugin system: list plugins and serve safe UI
panel schemas to the vanilla frontend.

Panels are returned as *sanitized declarative schemas* (or sandboxed-iframe
specs) — never executable JS. The frontend renderer (static/js/pluginPanels.js)
only knows how to render the fixed widget vocabulary, so a plugin cannot inject
arbitrary markup or scripts into the host page.
"""

import logging

from fastapi import APIRouter, Request

from src.auth_helpers import require_user

logger = logging.getLogger(__name__)


def setup_plugin_routes() -> APIRouter:
    router = APIRouter(tags=["plugins"])

    @router.get("/api/plugins")
    def list_plugins(request: Request):
        """List discovered in-process plugins and their enabled state."""
        require_user(request)
        from src.plugins import get_plugin_loader

        return {"plugins": get_plugin_loader().list_plugins()}

    @router.get("/api/plugins/panels")
    def list_panels(request: Request):
        """Return sanitized UI panel schemas for enabled plugins.

        Safe by construction: schema panels are limited to an allowlisted
        widget vocabulary and iframe panels are rendered sandboxed by the
        client. No secrets are included.
        """
        require_user(request)
        from src.plugins import get_plugin_loader

        return {"panels": get_plugin_loader().panels()}

    return router
