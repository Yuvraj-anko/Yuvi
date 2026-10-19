#!/usr/bin/env bash
# Idempotent environment bootstrap for the FOB Indent PO CSV cleaner.
set -euo pipefail

cd "$(dirname "$0")/../fob_bulk_update_agent"

# The default image ships Python 3.12 but not the venv module; install it once.
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-venv
fi

# Create the virtualenv if it does not already exist.
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi

# Install / refresh dependencies inside the venv.
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

# Smoke-test the transform so a broken environment fails setup loudly.
.venv/bin/python scripts/self_check_transform.py
