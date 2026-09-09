# FOB Indent PO CSV Cleaner

Cleans business FOB bulk-upload CSVs for the Confluence BAU procedure
[FOB on Indent POs - Bulk Update](https://kmartau.atlassian.net/wiki/spaces/UPT/pages/4310681006/FOB+on+Indent+POs+-+Bulk+Update).

## What it does

1. Rename headers to `PGM_PO_NUMBER`, `PRD_LVL_NUMBER`, `NEW_FOB`
   (accepts `PO Number` / `CASE PACK ID` / `FOB` and common aliases)
2. Strip case-pack suffix from product id: everything from `*` to end
   (e.g. `72647646*2A` → `72647646`)

## Setup

```bash
cd fob_bulk_update_agent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python -m agent \
  --input data/input/FOB_BULK_UPLOAD_LAURA_SMITH_7.09.csv \
  -v
```

Optional: set a specific output path with `-o /path/to/cleaned.csv`.

## Header mapping

| Business header | Cleaned header |
|-----------------|----------------|
| PO Number / PO# / PMG_PO_NUMBER | PGM_PO_NUMBER |
| CASE PACK ID / Product# | PRD_LVL_NUMBER |
| FOB / New FOB | NEW_FOB |

## Self-check

```bash
python scripts/self_check_transform.py
```
