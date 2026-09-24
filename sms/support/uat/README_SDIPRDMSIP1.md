# Fix ttmtgbss_gbss_prd_reg_prc_fl / SDIPRDMSIP1

## Problem

UAT job `ttmtgbss_gbss_prd_reg_prc_fl` failed with:

`ORA-00001: unique constraint (ODBMS.SDIPRDMSIP1) violated`

Constraint columns: `(BATCH_NUM, PRD_LVL_NUMBER, PRD_LVL_ID, TRAN_TYPE)`.

Failed batches: `83322434` (style `2610243247`), `83322435` (style `5000243249`).

Runtime evidence: each colour had **3** `tar_gbss_sty_prd` product numbers (job rerun without Confluence cleanup), and `SDIPRDMSI` still held headers from the first successful `p_LoadHdrToSdi` commit.

## Root causes

1. **Ops:** Reruns of `tar_GbssProcessPrdFile` without the Confluence cleanup left committed `SDIPRDMSI` rows and created extra `sty_prd` rows (`p_XmlStyColProdRef` always inserts).
2. **Code:** `p_LoadHdrToSdi` cursor did not filter `sty.batch_num = p_nSdiBatchNum` (or unprocessed flags), so historical product numbers were re-inserted.
3. **Code:** No idempotent clear of `SDIPRDMSI` for the batch before header insert.

Runbook: [ptmtgbss_gbss_prd_reg_prc_fl](https://kmartau.atlassian.net/wiki/spaces/AS/pages/4310173901/ptmtgbss_gbss_prd_reg_prc_fl)

## Package changes (`tar_gbss_prd_file_loading_pkg`)

1. `p_XmlStyColProdRef` — `NOT EXISTS` so a colour is not inserted again for the same batch.
2. `p_LoadHdrToSdi` — scope `sty_prd` to current batch / unprocessed rows; one row per colour (`MIN(ROWID)`); `DELETE FROM sdiprdmsi WHERE batch_num = ...` before insert.

## UAT remediation

Run `sms/support/uat/ttmtgbss_gbss_prd_reg_prc_fl_sdiprdmsip1_cleanup_2409.sql` on `ORUAS` **before** redeploying/reprocessing:

1. Backup + delete file_store rows for the two batches  
2. Confirm no `invbalee` stock  
3. `prdaddbat` all product numbers for those batches  
4. Mark `sty_prd` failed  
5. Delete `SDIPRDMSI` for those batches  
6. ERR/ACK successor to unlock GBSS  
7. Re-enable cyclic; reprocess **one file at a time** from backup  

Deploy the package to UAT after cleanup (or before reprocess) so reruns cannot recreate the triple-product pattern.
