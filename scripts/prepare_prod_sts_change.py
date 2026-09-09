#!/usr/bin/env python3
"""Convert Buying Office status CSV → ProdStsChange.txt for ptmtadhc_PrdStsUpd.

Matches Confluence: Product Status Changes in bulk (not delete status).
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_REMOTE_HOST = "hrs1502"
DEFAULT_REMOTE_DIR = "/CML/target/sms/prod/trans/in/merch_tools/"
OUTPUT_NAME = "ProdStsChange.txt"
PRODUCT_COL_CANDIDATES = (
    "product number",
    "product_number",
    "productnumber",
    "product",
    "keycode",
    "prd_lvl_number",
)
DELETE_STATUS_MARKERS = ("delete", "deleted")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _pick_product_column(fieldnames: list[str] | None) -> str | None:
    if not fieldnames:
        return None
    normalized = {_norm(name): name for name in fieldnames if name}
    for candidate in PRODUCT_COL_CANDIDATES:
        if candidate in normalized:
            return normalized[candidate]
    # Fall back to first column when header is unknown but present.
    return fieldnames[0]


def extract_product_numbers(csv_path: Path) -> tuple[list[str], set[str]]:
    products: list[str] = []
    statuses: set[str] = set()

    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            has_header = csv.Sniffer().has_header(sample)
        except csv.Error:
            has_header = True

        if has_header:
            reader = csv.DictReader(fh)
            product_col = _pick_product_column(reader.fieldnames)
            if not product_col:
                raise SystemExit(f"No usable product column in {csv_path}")
            status_cols = [
                name
                for name in (reader.fieldnames or [])
                if name and "status" in _norm(name)
            ]
            for row in reader:
                raw = (row.get(product_col) or "").strip()
                if not raw:
                    continue
                # Prefer first CSV field if cell accidentally includes commas.
                product = raw.split(",")[0].strip()
                if not product.isdigit():
                    raise SystemExit(f"Non-numeric product number: {product!r}")
                products.append(product)
                for col in status_cols:
                    status = (row.get(col) or "").strip()
                    if status:
                        statuses.add(status)
        else:
            reader = csv.reader(fh)
            for row in reader:
                if not row:
                    continue
                product = (row[0] or "").strip()
                if not product or not product.isdigit():
                    raise SystemExit(f"Non-numeric product number: {product!r}")
                products.append(product)
                if len(row) > 1 and row[1].strip():
                    statuses.add(row[1].strip())

    if not products:
        raise SystemExit(f"No product numbers found in {csv_path}")
    if len(products) > 5000:
        raise SystemExit(
            f"Found {len(products)} products; Confluence weekly cap is 5000."
        )

    lowered = {_norm(s) for s in statuses}
    if any(any(marker in status for marker in DELETE_STATUS_MARKERS) for status in lowered):
        raise SystemExit(
            "This file looks like a Delete status change. "
            "Use the Delete process, not ProdStsChange.txt."
        )
    if len(statuses) > 1:
        raise SystemExit(
            "Mixed statuses in one file: "
            + ", ".join(sorted(statuses))
            + ". Process one status per file."
        )

    return products, statuses


def write_prod_sts_change(products: list[str], output_path: Path) -> None:
    output_path.write_text("\n".join(products) + "\n", encoding="utf-8")


def upload_file(
    local_path: Path,
    host: str,
    remote_dir: str,
    user: str | None,
) -> None:
    remote_dir = remote_dir if remote_dir.endswith("/") else remote_dir + "/"
    target = f"{host}:{remote_dir}{OUTPUT_NAME}"
    if user:
        target = f"{user}@{target}"
    cmd = ["scp", str(local_path), target]
    print(f"Uploading via: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise SystemExit("scp not available in this environment.") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            "Upload failed. hrs1502 is typically only reachable from the "
            "internal network/VPN with SSH access configured."
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert Buying Office CSV to ProdStsChange.txt for bulk "
            "product status updates (not Delete)."
        )
    )
    parser.add_argument("input_csv", type=Path, help="Source CSV/spreadsheet export")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(OUTPUT_NAME),
        help=f"Output path (default: {OUTPUT_NAME})",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help=f"scp output to {DEFAULT_REMOTE_HOST}:{DEFAULT_REMOTE_DIR}",
    )
    parser.add_argument("--host", default=DEFAULT_REMOTE_HOST)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    parser.add_argument("--user", default=None, help="Optional SSH username")
    args = parser.parse_args(argv)

    if not args.input_csv.is_file():
        raise SystemExit(f"Input not found: {args.input_csv}")

    products, statuses = extract_product_numbers(args.input_csv)
    write_prod_sts_change(products, args.output)

    status_note = next(iter(statuses)) if statuses else "(set on job -s flag)"
    print(f"Wrote {len(products)} products → {args.output}")
    print(f"Detected status label: {status_note}")
    print("Next: load ptmtadhc_PrdStsUpd with tar_PrdStsUpd.ksh -s <code from prdstsee>")

    if args.upload:
        upload_file(args.output, args.host, args.remote_dir, args.user)
        print("Upload completed.")
    else:
        print(
            f"Upload skipped. Copy {args.output.name} to "
            f"{args.host}:{args.remote_dir} when ready."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
