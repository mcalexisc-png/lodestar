"""Date / timezone plugin using stdlib ``zoneinfo`` (no capabilities needed).

Answers "what time is it in <tz>" and converts a timestamp between timezones.
Pure computation: no net/fs/shell.
"""

from src.plugins.manifest import PluginManifest


def manifest() -> PluginManifest:
    return PluginManifest(
        name="datetime_tool",
        when_to_use="When the user asks the current time in a timezone, or to convert a time between timezones.",
        how='Pass JSON {"tz": str, "from_tz": str (optional), "time": ISO str (optional)}.',
        tags=["date", "time", "timezone"],
        capabilities=[],
        handler="plugins.lodestar_datetime:run",
        parameters={
            "tz": {"type": "string", "description": "Target IANA timezone, e.g. 'Asia/Tokyo'."},
            "from_tz": {"type": "string", "description": "Source timezone for conversion."},
            "time": {"type": "string", "description": "ISO 8601 time to convert (default: now)."},
        },
    )


def run(content: str, ctx: dict) -> dict:
    import json
    from datetime import datetime
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    try:
        args = json.loads(content) if content.strip().startswith("{") else {"tz": content.strip()}
    except (ValueError, TypeError):
        args = {"tz": content.strip()}

    tz_name = (args.get("tz") or "UTC").strip()
    try:
        target_tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return {"error": f"datetime_tool: unknown timezone '{tz_name}'.", "exit_code": 1}

    raw_time = (args.get("time") or "").strip()
    from_tz_name = (args.get("from_tz") or "").strip()

    try:
        if raw_time:
            dt = datetime.fromisoformat(raw_time)
            if dt.tzinfo is None:
                src_tz = ZoneInfo(from_tz_name) if from_tz_name else ZoneInfo("UTC")
                dt = dt.replace(tzinfo=src_tz)
        else:
            dt = datetime.now(tz=ZoneInfo(from_tz_name)) if from_tz_name else datetime.now(tz=ZoneInfo("UTC"))
    except (ZoneInfoNotFoundError, ValueError, KeyError) as e:
        return {"error": f"datetime_tool: {e}", "exit_code": 1}

    converted = dt.astimezone(target_tz)
    return {
        "output": converted.strftime("%Y-%m-%d %H:%M:%S %Z (%z)"),
        "iso": converted.isoformat(),
        "timezone": tz_name,
        "exit_code": 0,
    }
