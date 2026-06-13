"""Mutable container for lazily-initialized application components.

Route handlers import from here (at call time, not module-import time) so they
see values updated by ``_startup_event()`` after FastAPI's lifespan starts,
rather than closing over the initial ``None`` set at module-load.

Usage inside a route handler::

    from src.lazy_globals import memory_vector as _mv
    if _mv and _mv.healthy:
        _mv.add(...)

All fields start as ``None`` and are replaced by ``_startup_event()`` in
``app.py`` during the application lifespan.
"""

rag_manager = None
rag_available = False
memory_vector = None
