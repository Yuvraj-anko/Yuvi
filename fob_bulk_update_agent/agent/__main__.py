"""CLI entrypoint — clean FOB Indent PO bulk-upload CSVs."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from agent.transform import summarize, transform_csv

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "output"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "FOB Indent PO CSV cleaner — rename headers to "
            "PGM_PO_NUMBER / PRD_LVL_NUMBER / NEW_FOB and strip "
            "case-pack *suffix from product ids."
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
        help=(
            "Cleaned CSV output path "
            "(default: data/output/<same original filename>)"
        ),
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Debug logging",
    )
    return parser


def _default_output_path(input_path: Path) -> Path:
    """Keep the uploaded file's original name; write under data/output/."""
    return DEFAULT_OUTPUT_DIR / input_path.name


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

    report = {
        "input": str(input_path),
        "cleaned_csv": str(output_path),
        "stats": stats,
    }
    report_path = output_path.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info("Wrote run report: %s", report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
