#!/usr/bin/env python3
"""Encrypt Oracle credentials for the FOB bulk update agent.

Usage:
  python scripts/encrypt_credentials.py \\
      --host <host> --port 1521 --service <SERVICE> \\
      --user <user> --password <password> \\
      --out secrets/db_credentials.enc \\
      --key-out secrets/db.key

Or generate a key first and reuse it:
  python scripts/encrypt_credentials.py --generate-key-only --key-out secrets/db.key
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.credentials import (  # noqa: E402
    encrypt_credentials,
    generate_key,
    save_encrypted,
    save_key,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Encrypt FOB agent DB credentials")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int, default=1521)
    parser.add_argument("--service", dest="service_name")
    parser.add_argument("--user")
    parser.add_argument("--password", help="If omitted, prompted securely")
    parser.add_argument("--out", default=str(ROOT / "secrets" / "db_credentials.enc"))
    parser.add_argument("--key-out", default=str(ROOT / "secrets" / "db.key"))
    parser.add_argument("--key-file", help="Reuse an existing Fernet key file")
    parser.add_argument(
        "--generate-key-only",
        action="store_true",
        help="Only write a new key file; do not encrypt credentials",
    )
    args = parser.parse_args()

    if args.key_file:
        key = Path(args.key_file).read_bytes().strip()
    else:
        key = generate_key()
        save_key(key, args.key_out)
        print(f"Wrote encryption key: {args.key_out}")
        print("Keep this key secret. Prefer FOB_DB_KEY env var in production.")

    if args.generate_key_only:
        return 0

    missing = [
        name
        for name, val in (
            ("--host", args.host),
            ("--service", args.service_name),
            ("--user", args.user),
        )
        if not val
    ]
    if missing:
        print(f"Missing required args: {', '.join(missing)}", file=sys.stderr)
        return 2

    password = args.password or getpass.getpass("DB password: ")
    token = encrypt_credentials(
        {
            "host": args.host,
            "port": args.port,
            "service_name": args.service_name,
            "user": args.user,
            "password": password,
        },
        key,
    )
    save_encrypted(token, args.out)
    print(f"Wrote encrypted credentials: {args.out}")
    print("Plaintext password was not written to disk.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
