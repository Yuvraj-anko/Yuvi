-- =============================================================================
-- UAT cleanup for ttmtgbss_gbss_prd_reg_prc_fl
-- Error: ORA-00001 unique constraint (ODBMS.SDIPRDMSIP1) violated
-- Batches: 83322434 (2610243247 TEST TARGET KOW), 83322435 (5000243249 SUPIMA)
-- Env: sms_uat / ORUAS
-- Source: Confluence AS/ptmtgbss_gbss_prd_reg_prc_fl job re-run instructions
-- =============================================================================
-- DO NOT rerun the cyclic until this script completes.
-- Optionally HOLD ttmtgbss_gbss_odbms_mv_files2 while cleaning.
-- =============================================================================

SET SERVEROUTPUT ON SIZE UNLIMITED

-- ---------------------------------------------------------------------------
-- 0) Capture filenames to reprocess later
-- ---------------------------------------------------------------------------
SELECT batch_num, filename
FROM   tar_gbss_prd_file_store
WHERE  batch_num IN (83322434, 83322435)
ORDER BY batch_num;

-- ---------------------------------------------------------------------------
-- 1) Backup file store (Confluence: <in>_tar_prd_file_store_<ddmm>)
-- ---------------------------------------------------------------------------
CREATE TABLE xx_tar_prd_file_store_2409 AS
SELECT *
FROM   tar_gbss_prd_file_store
WHERE  filename NOT LIKE 'KMART%';

-- Prefer scoped delete for these batches; widen only if stream must drain fully
DELETE FROM tar_gbss_prd_file_store
WHERE  batch_num IN (83322434, 83322435);

-- ---------------------------------------------------------------------------
-- 2) Inventory check before prdaddbat (STOP if rows returned)
-- ---------------------------------------------------------------------------
SELECT *
FROM   invbalee
WHERE  prd_lvl_child IN (
         SELECT prd_lvl_child
         FROM   tar_gbss_sty_prd a
         WHERE  a.batch_num IN (83322434, 83322435)
         AND    a.prd_lvl_child IS NOT NULL
       );

-- Expect: no rows. If stock exists, escalate before deleting products.

-- ---------------------------------------------------------------------------
-- 3) Remove orphan ODBMS products created across 3 failed attempts
--    Evidence: 3 product_numbers per colour_sequence per batch
-- ---------------------------------------------------------------------------
DECLARE
   CURSOR c1 IS
      SELECT *
      FROM   tar_gbss_sty_prd a
      WHERE  a.batch_num IN (83322434, 83322435)
      AND    a.product_number IS NOT NULL;
BEGIN
   FOR i IN c1 LOOP
      -- prd_lvl_child may be null if failure was early; still pass product_number
      prdaddbat(i.prd_lvl_child, i.product_number, 1);
   END LOOP;
END;
/

-- ---------------------------------------------------------------------------
-- 4) Mark sty_prd as failed so ACK/ERR path can unlock GBSS briefs
-- ---------------------------------------------------------------------------
UPDATE tar_gbss_sty_prd
SET    overall_prd_reg_status = 'F',
       upload_date            = SYSDATE + 1
WHERE  batch_num IN (83322434, 83322435)
AND    upload_date IS NULL;

-- ---------------------------------------------------------------------------
-- 5) Clear SDIPRDMSI leftovers (direct SDIPRDMSIP1 fix)
-- ---------------------------------------------------------------------------
CREATE TABLE xx_sdiprdmsi_2409 AS
SELECT *
FROM   sdiprdmsi
WHERE  batch_num IN (83322434, 83322435);

DELETE FROM sdiprdmsi
WHERE  batch_num IN (83322434, 83322435);

COMMIT;

-- ---------------------------------------------------------------------------
-- 6) Verify clean state
-- ---------------------------------------------------------------------------
SELECT 'file_store' src, COUNT(*) cnt
FROM   tar_gbss_prd_file_store
WHERE  batch_num IN (83322434, 83322435)
UNION ALL
SELECT 'sdiprdmsi', COUNT(*)
FROM   sdiprdmsi
WHERE  batch_num IN (83322434, 83322435)
UNION ALL
SELECT 'sty_prd_open', COUNT(*)
FROM   tar_gbss_sty_prd
WHERE  batch_num IN (83322434, 83322435)
AND    upload_date IS NULL;

-- Expect: all counts = 0 for open work (sty_prd may still have marked-F rows)

-- ---------------------------------------------------------------------------
-- 7) Control-M / job actions (manual)
-- ---------------------------------------------------------------------------
-- a) Force-run successor ttmtgbss_gbss_prd_reg_err_ack_wm so GBSS gets ERR
--    and briefs unlock (FAILED), OR craft ERR files per Confluence if needed.
-- b) Set failed ttmtgbss_gbss_prd_reg_prc_fl to OK only after cleanup.
-- c) Re-enable cyclic on the process job (set-to-OK removes cyclic).
-- d) FREE ttmtgbss_gbss_odbms_mv_files2 if held.
--
-- ---------------------------------------------------------------------------
-- 8) Reprocess ONE file at a time from backup (after package fix deploy)
-- ---------------------------------------------------------------------------
-- INSERT INTO tar_gbss_prd_file_store
-- SELECT * FROM xx_tar_prd_file_store_2409
-- WHERE  batch_num = 83322434;  -- or WHERE filename = '<exact name>'
-- COMMIT;
-- Then force-run ttmtgbss_gbss_prd_reg_prc_fl (or load+process chain).
-- Repeat for 83322435 only after 83322434 succeeds.
--
-- Styles:
--   2610243247 TEST TARGET KOW
--   5000243249 SUPIMA flat sheets
-- Escalate to merch if reprocess still fails data validation.
