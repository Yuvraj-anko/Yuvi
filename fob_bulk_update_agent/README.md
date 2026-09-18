# FOB Indent PO CSV Cleaner

Cleans business FOB bulk-upload CSVs for the Confluence BAU procedure
[FOB on Indent POs - Bulk Update](https://kmartau.atlassian.net/wiki/spaces/UPT/pages/4310681006/FOB+on+Indent+POs+-+Bulk+Update).

## What it does

1. Rename headers to `PGM_PO_NUMBER`, `PRD_LVL_NUMBER`, `NEW_FOB`
2. Strip case-pack suffix from product id (`72647646*2A` → `72647646`)
3. Return a download with the **same original filename**

## Web app (recommended for shared use)

Anyone with the URL can upload a CSV and download the cleaned file — **no GitHub or Cursor access required**.

```bash
cd fob_bulk_update_agent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
bash scripts/run_web.sh
# open http://localhost:8000
```

Host / port overrides:

```bash
HOST=0.0.0.0 PORT=8080 bash scripts/run_web.sh
```

Put this behind your company VPN / internal host and share the URL with the BAU group. New joiners only need the link (and network access), not the private repo.

## CLI (optional)

```bash
python -m agent --input data/input/FOB_BULK_UPLOAD_LAURA_SMITH_7.09.csv -v
```

Output: `data/output/<same original filename>`.

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
