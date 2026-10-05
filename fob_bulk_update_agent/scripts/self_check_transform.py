#!/usr/bin/env python3
"""Lightweight transform self-check (no Oracle required)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.transform import strip_case_pack_suffix, transform_csv, transform_dataframe
import pandas as pd


def test_strip():
    assert strip_case_pack_suffix("72647646*2A") == "72647646"
    assert strip_case_pack_suffix("72647646") == "72647646"
    assert strip_case_pack_suffix("71186054*3C") == "71186054"


def test_header_and_star_transform():
    df = pd.DataFrame(
        {
            "PO Number": ["2632337"],
            "CASE PACK ID": ["72647646*2A"],
            "FOB": ["2.83"],
        }
    )
    out = transform_dataframe(df)
    assert list(out.columns) == ["PGM_PO_NUMBER", "PRD_LVL_NUMBER", "NEW_FOB"]
    assert out.iloc[0]["PRD_LVL_NUMBER"] == "72647646"
    assert float(out.iloc[0]["NEW_FOB"]) == 2.83


def test_sample_file():
    src = ROOT / "data" / "input" / "sample_raw_with_star_suffix.csv"
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "out.csv"
        transform_csv(src, dest)
        out = pd.read_csv(dest, dtype=str)
        assert len(out) == 4
        assert all("*" not in v for v in out["PRD_LVL_NUMBER"])
        assert list(out.columns) == ["PGM_PO_NUMBER", "PRD_LVL_NUMBER", "NEW_FOB"]


if __name__ == "__main__":
    test_strip()
    test_header_and_star_transform()
    test_sample_file()
    print("OK: transform self-check passed")
