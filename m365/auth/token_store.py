"""Token persistence: load/save/clear/is_expired for ~/.ms365-cli/token.json."""
import json
from datetime import datetime, timezone
from pathlib import Path

TOKEN_PATH = Path.home() / ".ms365-cli" / "token.json"


def save(data: dict) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["captured_at"] = datetime.now(timezone.utc).isoformat()
    TOKEN_PATH.write_text(json.dumps(data, indent=2))


def load() -> dict | None:
    if not TOKEN_PATH.exists():
        return None
    try:
        return json.loads(TOKEN_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def clear() -> None:
    TOKEN_PATH.unlink(missing_ok=True)


def get_token() -> str | None:
    data = load()
    if data is None:
        return None
    return data.get("access_token")


def is_expired(buffer_minutes: int = 5) -> bool:
    data = load()
    if data is None:
        return True
    expires_at = data.get("expires_at")
    if not expires_at:
        return True
    try:
        exp = datetime.fromisoformat(expires_at)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (exp - now).total_seconds() < buffer_minutes * 60
    except ValueError:
        return True


def get_teams_token() -> str | None:
    data = load()
    if data is None:
        return None
    return data.get("teams_token")


def get_skype_token() -> str | None:
    data = load()
    if data is None:
        return None
    return data.get("skype_token")


def summary() -> dict | None:
    """Return a summary dict for status display, or None if no token."""
    data = load()
    if data is None:
        return None
    return {
        "expires_at": data.get("expires_at", "unknown"),
        "scopes": data.get("scopes", "unknown"),
        "captured_at": data.get("captured_at", "unknown"),
        "has_teams_token": bool(data.get("teams_token")),
    }
