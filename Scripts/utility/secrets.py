from pathlib import Path
from typing import Dict, Iterable


def load_kv_secret(secret_path: Path, required_keys: Iterable[str] = ()) -> Dict[str, str]:
    """Load key/value secrets from a file, respecting comments and blank lines."""
    if not secret_path.is_file():
        raise FileNotFoundError(f"Missing credentials file: {secret_path}")

    creds: Dict[str, str] = {}
    for line in secret_path.read_text().splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or "=" not in cleaned:
            continue
        key, value = cleaned.split("=", 1)
        creds[key.strip()] = value.strip()

    missing = [k for k in required_keys if not creds.get(k)]
    if missing:
        raise ValueError(f"Missing required keys in secret file {secret_path}: {', '.join(missing)}")
    return creds
