"""CLI entrypoint for the FOB Indent PO Bulk Update agent."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent.credentials import load_encrypted_credentials
from agent.db import DbConfig, load_csv_to_db
from agent.transform import summarize, transform_csv

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "output"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "FOB Indent PO Bulk Update agent — clean CSV, load "
            "PROD_SUPPORT.BAU_INDENT_PO_FOB_UPD, run Confluence PL/SQL "
            "update + validation."
        )
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Business CSV path (PO Number / CASE PACK ID / FOB or already mapped headers)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Cleaned CSV output path (default: data/output/<input>_cleaned_<ts>.csv)",
    )
    parser.add_argument(
        "--credentials-file",
        help="Fernet-encrypted credentials file (or FOB_DB_CREDENTIALS_FILE)",
    )
    parser.add_argument(
        "--key-file",
        help="Fernet key file (or FOB_DB_KEY_FILE / FOB_DB_KEY)",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip Oracle load / PL/SQL (transform only)",
    )
    parser.add_argument(
        "--skip-update",
        action="store_true",
        help="Load staging table but do not run update PL/SQL",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Do not run validation PL/SQL after update",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Transform only; simulate DB steps without side effects",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Debug logging",
    )
    return parser


def _default_output_path(input_path: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"{input_path.stem}_cleaned_{ts}.csv"
    return DEFAULT_OUTPUT_DIR / name


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("fob.agent")

    input_path = Path(args.input)
    if not input_path.exists():
        log.error("Input file not found: %s", input_path)
        return 2

    output_path = Path(args.output) if args.output else _default_output_path(input_path)
    log.info("Transforming %s -> %s", input_path, output_path)
    transform_csv(input_path, output_path)

    import pandas as pd

    cleaned = pd.read_csv(output_path, dtype=str)
    stats = summarize(cleaned)
    log.info(
        "Cleaned rows=%s unique_pos=%s unique_products=%s",
        stats["row_count"],
        stats["po_count"],
        stats["product_count"],
    )

    report: dict = {
        "input": str(input_path),
        "cleaned_csv": str(output_path),
        "stats": stats,
        "dry_run": args.dry_run,
        "db": None,
    }

    if not args.skip_db:
        if args.dry_run:
            db_result = load_csv_to_db(
                output_path,
                config=DbConfig(
                    host="dry-run",
                    port=1521,
                    service_name="DRYRUN",
                    user="dry-run",
                    password="dry-run",
                ),
                dry_run=True,
                run_update_block=not args.skip_update,
                run_validation_block=not args.skip_validation,
            )
        else:
            creds = load_encrypted_credentials(
                enc_path=args.credentials_file,
                key_path=args.key_file,
            )
            db_result = load_csv_to_db(
                output_path,
                config=DbConfig.from_dict(creds),
                dry_run=False,
                run_update_block=not args.skip_update,
                run_validation_block=not args.skip_validation,
            )
        report["db"] = db_result
        log.info("DB result: %s", json.dumps(db_result, default=str))

    report_path = output_path.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info("Wrote run report: %s", report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
