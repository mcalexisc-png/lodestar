"""Example Lodestar in-process plugin: text statistics.

A minimal, pure-Python, zero-capability plugin that proves the Tier 2 plugin
path end to end. It computes simple statistics (characters, words, lines,
sentences) for a piece of text — no network, no filesystem, no shell.

The ``manifest`` entry point is registered in pyproject.toml under
``[project.entry-points."lodestar.tools"]``. Only this module's manifest is
imported at discovery time; ``run`` is imported lazily on first invocation.
"""

from src.plugins.manifest import PluginManifest


def manifest() -> PluginManifest:
    return PluginManifest(
        name="text_stats",
        when_to_use="When the user asks for word/character/line counts or basic statistics about a piece of text.",
        how="Pass the text to analyze as the 'input' string.",
        tags=["text", "utility", "example"],
        capabilities=[],  # pure computation: no net/fs/shell
        handler="plugins.lodestar_textstats:run",
        parameters={
            "input": {"type": "string", "description": "The text to analyze."},
        },
    )


def run(content: str, ctx: dict) -> dict:
    """Handler: ``content`` is the JSON args string or raw text."""
    text = _extract_text(content)
    if not text:
        return {"error": "text_stats: no input text provided.", "exit_code": 1}

    words = text.split()
    lines = text.splitlines() or [text]
    # Naive sentence split on . ! ? — good enough for a stats helper.
    sentences = [s for s in _split_sentences(text) if s.strip()]

    stats = {
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "").replace("\t", "")),
        "words": len(words),
        "lines": len(lines),
        "sentences": len(sentences),
        "avg_word_length": round(sum(len(w) for w in words) / len(words), 2) if words else 0,
    }
    summary = ", ".join(f"{k}={v}" for k, v in stats.items())
    return {"output": summary, "stats": stats, "exit_code": 0}


def _extract_text(content: str) -> str:
    import json

    raw = (content or "").strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return str(data.get("input") or data.get("text") or "")
        except (ValueError, TypeError):
            pass
    return raw


def _split_sentences(text: str):
    import re

    return re.split(r"[.!?]+", text)
