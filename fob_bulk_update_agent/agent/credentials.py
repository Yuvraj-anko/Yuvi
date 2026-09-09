"""Encrypt / decrypt Oracle DB credentials with Fernet (symmetric encryption).

Credentials are never stored in plain text. Generate a key once, encrypt a
JSON credential payload, then point the agent at the encrypted file + key.

Example:
  python -m scripts.encrypt_credentials \\
      --host odbms-host --port 1521 --service ODBMS \\
      --user MY_USER --password '***' \\
      --out secrets/db_credentials.enc \\
      --key-out secrets/db.key
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

REQUIRED_FIELDS = ("host", "port", "service_name", "user", "password")


class CredentialError(RuntimeError):
    """Raised when credentials cannot be loaded or decrypted."""


def generate_key() -> bytes:
    return Fernet.generate_key()


def save_key(key: bytes, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key)
    path.chmod(0o600)
    return path


def load_key(path: Path | str | None = None) -> bytes:
    """Load Fernet key from path or FOB_DB_KEY / FOB_DB_KEY_FILE env vars."""
    env_key = os.environ.get("FOB_DB_KEY")
    if env_key:
        return env_key.strip().encode("utf-8")

    key_file = path or os.environ.get("FOB_DB_KEY_FILE")
    if not key_file:
        raise CredentialError(
            "No encryption key provided. Set FOB_DB_KEY, FOB_DB_KEY_FILE, "
            "or pass --key-file."
        )
    key_path = Path(key_file)
    if not key_path.exists():
        raise CredentialError(f"Encryption key file not found: {key_path}")
    return key_path.read_bytes().strip()


def encrypt_credentials(payload: dict[str, Any], key: bytes) -> bytes:
    missing = [f for f in REQUIRED_FIELDS if f not in payload or payload[f] in (None, "")]
    if missing:
        raise CredentialError(f"Missing required credential fields: {missing}")
    # Normalize port to int for validation, store as int in JSON
    payload = dict(payload)
    payload["port"] = int(payload["port"])
    token = Fernet(key).encrypt(json.dumps(payload).encode("utf-8"))
    return token


def decrypt_credentials(token: bytes, key: bytes) -> dict[str, Any]:
    try:
        raw = Fernet(key).decrypt(token)
    except InvalidToken as exc:
        raise CredentialError(
            "Failed to decrypt credentials — wrong key or corrupt file."
        ) from exc
    data = json.loads(raw.decode("utf-8"))
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise CredentialError(f"Decrypted credentials missing fields: {missing}")
    data["port"] = int(data["port"])
    return data


def save_encrypted(token: bytes, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(token)
    path.chmod(0o600)
    return path


def load_encrypted_credentials(
    enc_path: Path | str | None = None,
    key_path: Path | str | None = None,
) -> dict[str, Any]:
    enc_file = enc_path or os.environ.get("FOB_DB_CREDENTIALS_FILE")
    if not enc_file:
        raise CredentialError(
            "No encrypted credentials file. Set FOB_DB_CREDENTIALS_FILE "
            "or pass --credentials-file."
        )
    path = Path(enc_file)
    if not path.exists():
        raise CredentialError(f"Encrypted credentials file not found: {path}")
    key = load_key(key_path)
    return decrypt_credentials(path.read_bytes(), key)
