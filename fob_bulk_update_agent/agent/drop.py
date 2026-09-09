"""Drop cleaned FOB CSV onto the SMS po_amendments share/path.

Default production UNC path (Windows):
  \\\\hrs1502\\sms_prod_sms\\prod\\trans\\in\\po_amendments

On Linux jump hosts this is typically mounted, e.g.:
  /mnt/hrs1502/sms_prod_sms/prod/trans/in/po_amendments
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_UNC = r"\\hrs1502\sms_prod_sms\prod\trans\in\po_amendments"
DEFAULT_ENV = "FOB_PO_AMENDMENTS_PATH"


def resolve_drop_path(explicit: str | Path | None = None) -> Path:
    """Resolve destination directory from CLI arg, env, or default UNC."""
    raw = explicit or os.environ.get(DEFAULT_ENV) or DEFAULT_UNC
    text = str(raw)
    # Allow writing UNC-style paths when running on Windows; on Linux users
    # should set FOB_PO_AMENDMENTS_PATH to a mounted folder.
    return Path(text)


def drop_file(
    source: Path | str,
    destination_dir: Path | str | None = None,
    *,
    filename: str | None = None,
    dry_run: bool = False,
) -> Path:
    """Copy cleaned CSV into the po_amendments inbound folder."""
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Source CSV not found: {source}")

    dest_dir = resolve_drop_path(destination_dir)
    dest_name = filename or source.name
    dest = dest_dir / dest_name

    if dry_run:
        logger.info("[dry-run] Would copy %s -> %s", source, dest)
        return dest

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    logger.info("Dropped file to %s", dest)
    return dest
