"""Config management: reads .env + ~/.ms365-cli/config.yaml, supports `m365 config set`."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load ~/.ms365-cli/.env first (global), then CWD .env (local override)
_HOME_ENV = Path.home() / ".ms365-cli" / ".env"
load_dotenv(_HOME_ENV)
load_dotenv()

CONFIG_DIR = Path.home() / ".ms365-cli"
CONFIG_PATH = CONFIG_DIR / "config.yaml"


def _load_file() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_file(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(data, f)


def get(key: str, default=None):
    """Read config value: env var > config file > default."""
    env_key = f"M365_{key.upper()}"
    if val := os.getenv(env_key):
        return val
    return _load_file().get(key, default)


def set_value(key: str, value: str) -> None:
    data = _load_file()
    data[key] = value
    _save_file(data)


def require(key: str) -> str:
    val = get(key)
    if not val:
        raise SystemExit(
            f"Missing config: {key!r}. "
            f"Set M365_{key.upper()} env var or run: m365 config set --{key} <value>"
        )
    return val
