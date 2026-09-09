# Yuvi

## Bulk upload for status to NFR

Converts Buying Office product-status CSVs into `ProdStsChange.txt` for the Confluence bulk status-change job (not Delete).

### Files
- `ProdStsChange.txt` — current NFR upload file (1,003 products)
- `scripts/prepare_prod_sts_change.py` — converter (+ optional `scp` upload)
- `.cursor/skills/bulk-product-status-update/` — Cursor agent skill

### Prepare file
```bash
python3 scripts/prepare_prod_sts_change.py Status_update_NFR.csv -o ProdStsChange.txt
```

### Upload (from inside network)
```bash
python3 scripts/prepare_prod_sts_change.py Status_update_NFR.csv --upload
```

Places file at `hrs1502:/CML/target/sms/prod/trans/in/merch_tools/ProdStsChange.txt`.

Then run job `ptmtadhc_PrdStsUpd` with:
```bash
tar_PrdStsUpd.ksh -s <NFR status code from prdstsee>
```
