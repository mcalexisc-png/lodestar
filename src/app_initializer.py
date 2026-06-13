# src/app_initializer.py
"""Initialize all application components and dependencies."""
import os
import logging
from typing import Dict, Any

from src.constants import (
    DATA_DIR, PERSONAL_DIR, RUNBOOK_DIR, UPLOAD_DIR,
    SESSIONS_FILE, DEFAULT_HOST, OPENAI_API_KEY, LODESTAR_LITE
)
from src.memory import MemoryManager
from src.memory_provider import MemoryProviderRegistry, NativeMemoryProvider
from services.memory.skills import SkillsManager
from core.session_manager import SessionManager
from core.models import set_session_manager
from src.personal_docs import PersonalDocsManager
from src.api_key_manager import APIKeyManager
from src.preset_manager import PresetManager
from src.chat_processor import ChatProcessor
from src.model_discovery import ModelDiscovery
from src.chat_handler import ChatHandler
from src.research_handler import ResearchHandler
from src.upload_handler import UploadHandler
from src.search import update_search_config

logger = logging.getLogger(__name__)

def create_directories():
    """Create necessary directories if they don't exist."""
    for directory in (DATA_DIR, PERSONAL_DIR, RUNBOOK_DIR, UPLOAD_DIR):
        os.makedirs(directory, exist_ok=True)
        
def initialize_managers(base_dir: str, rag_manager=None) -> Dict[str, Any]:
    """
    Initialize all manager and handler instances.

    Args:
        base_dir: Base directory path
        rag_manager: RAG manager instance (optional)
    Returns:
        Dictionary containing all initialized components
    """
    # Create directories first
    create_directories()

    # Initialize core managers
    memory_manager = MemoryManager(DATA_DIR)
    skills_manager = SkillsManager(DATA_DIR)
    session_manager = SessionManager(SESSIONS_FILE)
    set_session_manager(session_manager)  # Enable Session.add_message() persistence
    upload_handler = UploadHandler(base_dir, UPLOAD_DIR)
    personal_docs_manager = PersonalDocsManager(PERSONAL_DIR, rag_manager)
    api_key_manager = APIKeyManager(DATA_DIR)
    preset_manager = PresetManager(DATA_DIR)

    # Memory vector store initialization is deferred to _startup_event() to
    # avoid loading fastembed/onnxruntime at module-import time (~150 MB RSS
    # regression, Phase 4 optimization). Components receive None here; dependent
    # objects (NativeMemoryProvider, ChatProcessor) handle None gracefully and
    # are patched in deferred_init_vector_store().
    memory_vector = None

    memory_provider_registry = MemoryProviderRegistry([
        NativeMemoryProvider(memory_manager, memory_vector),
    ])

    # Initialize processors
    chat_processor = ChatProcessor(memory_manager, personal_docs_manager, memory_vector=memory_vector, skills_manager=skills_manager)
    research_handler = ResearchHandler()
    
    # Initialize chat handler with all dependencies
    chat_handler = ChatHandler(
        session_manager=session_manager,
        memory_manager=memory_manager,
        chat_processor=chat_processor,
        research_handler=research_handler,
        preset_manager=preset_manager,
        upload_handler=upload_handler,
    )
    
    # Initialize model discovery
    model_discovery = ModelDiscovery(DEFAULT_HOST, OPENAI_API_KEY)
    
    # Load and apply saved API keys
    saved_keys = api_key_manager.load()
    if "brave" in saved_keys:
        update_search_config(api_key=saved_keys["brave"])
        logger.info("Loaded Brave API key from saved configuration")
    
    return {
        "memory_manager": memory_manager,
        "memory_vector": memory_vector,
        "memory_provider_registry": memory_provider_registry,
        "skills_manager": skills_manager,
        "session_manager": session_manager,
        "upload_handler": upload_handler,
        "personal_docs_manager": personal_docs_manager,
        "api_key_manager": api_key_manager,
        "preset_manager": preset_manager,
        "chat_processor": chat_processor,
        "research_handler": research_handler,
        "chat_handler": chat_handler,
        "model_discovery": model_discovery,
        "current_presets": preset_manager.presets,
        "PERSONAL_INDEX": personal_docs_manager.index
    }


def deferred_init_vector_store(components: Dict[str, Any]) -> Any:
    """Initialize the vector store and wire it into dependent components.

    Called from _startup_event() after the server starts, not at module
    import time.  Skips fastembed/onnxruntime loading entirely for lite mode.
    Patches NativeMemoryProvider and ChatProcessor so they see the store.
    """
    from src.providers.selection import select_embedding_provider, select_vector_store
    from src.settings import load_settings

    memory_manager = components["memory_manager"]
    memory_vector = None
    try:
        settings = load_settings()
        embedding_provider = select_embedding_provider(settings, LODESTAR_LITE)
        memory_vector = select_vector_store(settings, LODESTAR_LITE, embedding_provider)

        if memory_vector is None:
            logger.info("Memory vector store unavailable; using keyword memory search")
        else:
            if memory_vector.count() == 0:
                existing = memory_manager.load()
                if existing:
                    memory_vector.rebuild(existing)
                    logger.info(f"Rebuilt memory vector index from {len(existing)} existing entries")
            stats = memory_vector.get_stats()
            logger.info("Memory vector store initialized (%s)", stats.get("backend", "unknown"))

        # Patch dependent components
        components["memory_vector"] = memory_vector
        registry = components["memory_provider_registry"]
        try:
            native = registry.get("native")
            if native is not None:
                native.memory_vector = memory_vector
        except KeyError:
            pass
        components["chat_processor"].memory_vector = memory_vector
    except Exception as e:
        logger.warning(f"Memory vector store selection failed ({e}); keyword fallback")
        memory_vector = None
        components["memory_vector"] = None

    return memory_vector
