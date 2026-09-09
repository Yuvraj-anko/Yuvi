"""CSV transform for FOB Indent PO bulk updates.

Business files typically arrive with headers like:
  PO Number, CASE PACK ID, FOB

Required load headers (Text Importer / staging table):
  PGM_PO_NUMBER, PRD_LVL_NUMBER, NEW_FOB

CASE PACK ID values often look like ``72647646*2A`` — everything from
``*`` to the end of the value must be removed before load.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd

# Canonical output headers expected by the BAU staging flow.
OUTPUT_HEADERS = ("PGM_PO_NUMBER", "PRD_LVL_NUMBER", "NEW_FOB")

# Flexible aliases for business / already-cleaned input files.
HEADER_ALIASES = {
    "pgm_po_number": "PGM_PO_NUMBER",
    "pmg_po_number": "PGM_PO_NUMBER",
    "po_number": "PGM_PO_NUMBER",
    "po number": "PGM_PO_NUMBER",
    "po#": "PGM_PO_NUMBER",
    "po": "PGM_PO_NUMBER",
    "prd_lvl_number": "PRD_LVL_NUMBER",
    "case pack id": "PRD_LVL_NUMBER",
    "case_pack_id": "PRD_LVL_NUMBER",
    "casepack id": "PRD_LVL_NUMBER",
    "product#": "PRD_LVL_NUMBER",
    "product": "PRD_LVL_NUMBER",
    "product number": "PRD_LVL_NUMBER",
    "new_fob": "NEW_FOB",
    "fob": "NEW_FOB",
    "new fob": "NEW_FOB",
}

CASE_PACK_STAR_RE = re.compile(r"\*.*$")


def _normalize_header(name: str) -> str:
    key = re.sub(r"\s+", " ", str(name).strip().lower())
    key = key.replace("-", " ")
    return HEADER_ALIASES.get(key, str(name).strip())


def strip_case_pack_suffix(value) -> str:
    """Remove ``*...`` suffix from a case-pack / product id value."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return CASE_PACK_STAR_RE.sub("", text).strip()


def transform_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Rename headers, strip case-pack suffixes, keep only required columns."""
    renamed = {_normalize_header(col): df[col] for col in df.columns}
    work = pd.DataFrame(renamed)

    missing = [h for h in OUTPUT_HEADERS if h not in work.columns]
    if missing:
        raise ValueError(
            "Input CSV is missing required columns after header mapping: "
            f"{missing}. Found columns: {list(df.columns)}"
        )

    out = work.loc[:, list(OUTPUT_HEADERS)].copy()
    out["PGM_PO_NUMBER"] = out["PGM_PO_NUMBER"].map(
        lambda v: "" if pd.isna(v) else str(v).strip()
    )
    out["PRD_LVL_NUMBER"] = out["PRD_LVL_NUMBER"].map(strip_case_pack_suffix)
    out["NEW_FOB"] = pd.to_numeric(out["NEW_FOB"], errors="coerce")

    # Drop blank / invalid rows
    out = out[
        (out["PGM_PO_NUMBER"] != "")
        & (out["PRD_LVL_NUMBER"] != "")
        & out["NEW_FOB"].notna()
    ].reset_index(drop=True)

    # Keep product ids as plain digit strings (no .0)
    out["PRD_LVL_NUMBER"] = out["PRD_LVL_NUMBER"].map(
        lambda v: str(int(float(v))) if re.fullmatch(r"\d+(\.0+)?", str(v)) else str(v)
    )
    out["PGM_PO_NUMBER"] = out["PGM_PO_NUMBER"].map(
        lambda v: str(int(float(v))) if re.fullmatch(r"\d+(\.0+)?", str(v)) else str(v)
    )
    return out


def transform_csv(input_path: Path | str, output_path: Path | str) -> Path:
    """Read business CSV, clean it, write load-ready CSV. Returns output path."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path, dtype=str)
    cleaned = transform_dataframe(df)
    cleaned.to_csv(output_path, index=False)
    return output_path


def summarize(df: pd.DataFrame) -> dict:
    return {
        "row_count": int(len(df)),
        "po_count": int(df["PGM_PO_NUMBER"].nunique()) if len(df) else 0,
        "product_count": int(df["PRD_LVL_NUMBER"].nunique()) if len(df) else 0,
    }
