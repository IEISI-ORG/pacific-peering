"""Load the RIPE Atlas API key from the gitignored `secrets.yaml`.

`secrets.yaml` is never committed (see `.gitignore`) and its contents are
never logged or echoed anywhere in this codebase.
"""

from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_SECRETS_PATH = Path("secrets.yaml")
_SECRET_KEY_NAME = "ripe_atlas_key"


def load_atlas_api_key(path: Path = DEFAULT_SECRETS_PATH) -> str:
    """Load the RIPE Atlas API key.

    Args:
        path: Path to the secrets file.

    Returns:
        The API key string.

    Raises:
        FileNotFoundError: If `path` doesn't exist.
        KeyError: If `path` exists but has no `ripe_atlas_key` entry.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Expected a gitignored secrets.yaml with a "
            f"'{_SECRET_KEY_NAME}' entry holding the RIPE Atlas API key."
        )
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or _SECRET_KEY_NAME not in data:
        raise KeyError(f"{path} must contain a '{_SECRET_KEY_NAME}' entry")
    return data[_SECRET_KEY_NAME]
