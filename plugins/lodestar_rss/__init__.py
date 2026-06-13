"""RSS / Atom reader plugin using ``feedparser`` (OPTIONAL dependency).

Declares the ``net`` capability. ``feedparser`` is not a core dependency — it
lives in the optional "tools" extras group. If it isn't installed, the tool is
still discovered but returns a clear "install to use" message rather than
erroring obscurely.
"""

from src.plugins.manifest import Capability, PluginManifest


def manifest() -> PluginManifest:
    return PluginManifest(
        name="rss_read",
        when_to_use="When the user wants the latest entries from an RSS or Atom feed URL.",
        how='Pass JSON {"url": str, "limit": int (optional)}.',
        tags=["rss", "atom", "feed", "news"],
        capabilities=[Capability.NET],
        handler="plugins.lodestar_rss:run",
        parameters={
            "url": {"type": "string", "description": "The RSS/Atom feed URL."},
            "limit": {"type": "integer", "description": "Max entries to return (default 10)."},
        },
    )


def run(content: str, ctx: dict) -> dict:
    import json

    # Capability gate (best-effort host enforcement for in-process tools).
    guard = ctx.get("require_capability")
    if guard:
        try:
            guard("net")
        except PermissionError as e:
            return {"error": str(e), "exit_code": 1}

    try:
        import feedparser  # lazy: optional dep
    except ImportError:
        return {
            "error": "rss_read: feedparser is not installed. Install the optional "
                     "tools extra (pip install feedparser) to use the RSS reader.",
            "exit_code": 1,
        }

    try:
        args = json.loads(content) if content.strip().startswith("{") else {"url": content.strip()}
    except (ValueError, TypeError):
        args = {"url": content.strip()}

    url = (args.get("url") or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        return {"error": "rss_read: 'url' must be an http(s) feed URL.", "exit_code": 1}
    limit = int(args.get("limit") or 10)

    parsed = feedparser.parse(url)
    entries = []
    for e in parsed.entries[:limit]:
        entries.append({
            "title": getattr(e, "title", ""),
            "link": getattr(e, "link", ""),
            "published": getattr(e, "published", "") or getattr(e, "updated", ""),
            "summary": (getattr(e, "summary", "") or "")[:500],
        })

    feed_title = getattr(parsed.feed, "title", url) if hasattr(parsed, "feed") else url
    lines = [f"- {e['title']} ({e['link']})" for e in entries]
    return {
        "feed": feed_title,
        "entries": entries,
        "output": f"{feed_title}: {len(entries)} entries\n" + "\n".join(lines),
        "exit_code": 0,
    }
