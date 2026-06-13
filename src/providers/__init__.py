"""Typed backend interfaces for swappable Lodestar subsystems.

Each module here defines a ``typing.Protocol`` documenting the contract that
existing concrete implementations already satisfy (ChromaDB-backed
``MemoryVectorStore``, ``EmbeddingClient``/``FastEmbedClient``, the search
provider functions in ``services/search``), plus small selection helpers that
pick a concrete implementation based on settings/``LODESTAR_LITE``.

This package introduces the seam for Phase 3 backends (embedded sqlite-vec
vector store, pluggable embeddings, API search providers) without changing any
existing behavior on its own.
"""
