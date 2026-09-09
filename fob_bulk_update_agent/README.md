# FOB Indent PO Bulk Update Agent

Automates the Confluence BAU procedure
[FOB on Indent POs - Bulk Update](https://kmartau.atlassian.net/wiki/spaces/UPT/pages/4310681006/FOB+on+Indent+POs+-+Bulk+Update).

## What it does

1. **Clean the business CSV**
   - Rename headers to `PGM_PO_NUMBER`, `PRD_LVL_NUMBER`, `NEW_FOB`
     (accepts `PO Number` / `CASE PACK ID` / `FOB` and common aliases)
   - Strip case-pack suffix from product id: everything from `*` to end
     (e.g. `72647646*2A` → `72647646`)
2. **Load** rows into `PROD_SUPPORT.BAU_INDENT_PO_FOB_UPD` with `process_date = NULL`
3. **Run** the Confluence update PL/SQL block
4. **Run** the optional validation PL/SQL block

Database credentials are **Fernet-encrypted** — never stored in plaintext.

## Setup

```bash
cd fob_bulk_update_agent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Encrypt DB credentials (one-time)

Provide host / service / user / password when ready — this writes an encrypted
blob + a key file (both gitignored under `secrets/`):

```bash
python scripts/encrypt_credentials.py \
  --host <oracle-host> \
  --port 1521 \
  --service <SERVICE_NAME> \
  --user <db_user> \
  --out secrets/db_credentials.enc \
  --key-out secrets/db.key
```

Password is prompted if `--password` is omitted. Prefer injecting the key via
env in production:

```bash
export FOB_DB_CREDENTIALS_FILE=secrets/db_credentials.enc
export FOB_DB_KEY="$(cat secrets/db.key)"
# or: export FOB_DB_KEY_FILE=secrets/db.key
```

## Run

Dry-run (transform + simulate DB — safe, no Oracle connection):

```bash
python -m agent \
  --input data/input/FOB_BULK_UPLOAD_LAURA_SMITH_7.09.csv \
  --dry-run \
  -v
```

Full production run (after credentials are encrypted):

```bash
python -m agent -i ./business.csv \
  --credentials-file secrets/db_credentials.enc \
  --key-file secrets/db.key
```

Useful flags:

| Flag | Meaning |
|------|---------|
| `--skip-db` | Transform only |
| `--skip-update` | Load staging table, do not run update PL/SQL |
| `--skip-validation` | Skip validation PL/SQL |
| `--dry-run` | No DB writes |

## Header mapping

| Business header | Cleaned header |
|-----------------|----------------|
| PO Number / PO# / PMG_PO_NUMBER | PGM_PO_NUMBER |
| CASE PACK ID / Product# | PRD_LVL_NUMBER |
| FOB / New FOB | NEW_FOB |

## Notes

- Staging insert maps `PGM_PO_NUMBER` → table column `pmg_po_number` (Confluence PL/SQL).
- `process_date` is left `NULL` on insert so the update cursor picks up new rows.
- This cloud environment cannot reach corporate Oracle; use `--dry-run` here and run the full agent from a host with DB access.
