---
name: bulk-product-status-update
description: Convert Buying Office product-status spreadsheets into ProdStsChange.txt and prepare (optionally upload) them for the Confluence bulk status-change job on hrs1502. Use when the user asks to prepare NFR/Quit/status bulk updates, convert Status_update_*.csv, create ProdStsChange.txt, or stage files for /CML/target/sms/prod/trans/in/merch_tools/.
---

# Bulk Product Status Update (not Delete)

Follow Confluence: **Product Status Changes in bulk (not delete status)**  
https://kmartau.atlassian.net/wiki/spaces/AS/pages/4310179525/Product+Status+Changes+in+bulk+not+delete+status

## Do NOT use this for Delete

If the target status is Delete, stop and use the separate Delete process page instead.

## Agent workflow

1. Accept the Buying Office CSV/spreadsheet (usually columns like `Product Number`, `Status`).
2. Confirm one status only in the file (e.g. all NFR). Mixed statuses → split into separate runs.
3. Confirm count ≤ 5000 (weekly cap).
4. Run the converter:

```bash
python3 scripts/prepare_prod_sts_change.py INPUT.csv -o ProdStsChange.txt
```

5. Validate output:
   - Filename is `ProdStsChange.txt`
   - One numeric product number per line
   - No header, no commas, no status text
6. Upload only if host access exists:

```bash
python3 scripts/prepare_prod_sts_change.py INPUT.csv --upload
```

Default remote path: `/CML/target/sms/prod/trans/in/merch_tools/` on host `hrs1502` (override with `--host` / `--remote-dir`).

7. Tell the user to run job `ptmtadhc_PrdStsUpd` with:

```bash
tar_PrdStsUpd.ksh -s <status_code_from_prdstsee>
```

Status is set on the **job command line**, never inside `ProdStsChange.txt`.

## If upload fails

Cloud agents usually cannot resolve/reach `hrs1502`. In that case:

- Produce and share `ProdStsChange.txt` for manual copy
- Ask for SSH/VPN/self-hosted worker access if they want automated placement

## Output checklist for the user

- [ ] `ProdStsChange.txt` ready
- [ ] Placed on hrs1502 under `/CML/target/sms/prod/trans/in/merch_tools/`
- [ ] Job command line status code set
- [ ] Job `ptmtadhc_PrdStsUpd` loaded
