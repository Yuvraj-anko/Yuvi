"""Oracle DB load + Confluence PL/SQL runners for FOB Indent PO bulk update."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

logger = logging.getLogger(__name__)

STAGING_TABLE = "PROD_SUPPORT.BAU_INDENT_PO_FOB_UPD"

# Matches Confluence "FOB on Indent POs - Bulk Update"
UPDATE_PLSQL = """
DECLARE
    l_nRecCnt  INTEGER   := 0;
    l_nUpdCnt  INTEGER   := 0;

    CURSOR c1 IS
    SELECT pod.pmg_po_number,
           pod.pmg_dtl_tech_key,
           req.new_fob
    FROM   prod_support.bau_indent_po_fob_upd req,
           pmgdtlee  pod,
           prdmstee  prd
    WHERE  req.pmg_po_number   = pod.pmg_po_number
    AND    pod.pmg_status     <> 7
    AND    pod.prd_lvl_child   = prd.prd_lvl_child
    AND    prd.prd_lvl_number  = req.prd_lvl_number
    AND    process_date IS NULL;
BEGIN
    SELECT COUNT(*)
    INTO   l_nRecCnt
    FROM   prod_support.bau_indent_po_fob_upd
    WHERE  process_date IS NULL;

    FOR l_rec IN c1
    LOOP
        UPDATE tar_itrpodee
        SET    itr_value        = l_rec.new_fob
        WHERE  pmg_po_number    = l_rec.pmg_po_number
        AND    pmg_dtl_tech_key = l_rec.pmg_dtl_tech_key
        AND    itr_adh_code     = 'SUC';

        l_nUpdCnt := l_nUpdCnt + SQL%ROWCOUNT;
    END LOOP;

    UPDATE prod_support.bau_indent_po_fob_upd
    SET    process_date = SYSDATE
    WHERE  process_date IS NULL;

    DBMS_OUTPUT.put_line('Request Count: ' || l_nRecCnt);
    DBMS_OUTPUT.put_line('Update Count: '  || l_nUpdCnt);

    COMMIT WORK;
END;
"""

VALIDATION_PLSQL = """
DECLARE
  var_1 tar_itrpodee.itr_value%TYPE;
  var_2 tar_itrpodee.pmg_po_number%TYPE;
  var_3 tar_itrpodee.pmg_dtl_tech_key%TYPE;
  CURSOR c1 IS
    SELECT pod.pmg_po_number, pod.pmg_dtl_tech_key, req.new_fob
      FROM prod_support.bau_indent_po_fob_upd req,
           pmgdtlee                           pod,
           prdmstee                           prd
     WHERE req.pmg_po_number = pod.pmg_po_number
       AND pod.pmg_status <> 7
       AND pod.prd_lvl_child = prd.prd_lvl_child
       AND prd.prd_lvl_number = req.prd_lvl_number
       AND TRUNC(process_date) = TRUNC(SYSDATE);
BEGIN
  FOR l_rec IN c1 LOOP
    SELECT itr_value, pmg_po_number, pmg_dtl_tech_key
      INTO var_1, var_2, var_3
      FROM tar_itrpodee
     WHERE pmg_po_number = l_rec.pmg_po_number
       AND pmg_dtl_tech_key = l_rec.pmg_dtl_tech_key
       AND itr_adh_code = 'SUC';
    DBMS_OUTPUT.PUT_LINE(var_2 || '  ' || var_3 || '  ' || var_1 || '  ');
  END LOOP;
END;
"""

INSERT_SQL = f"""
INSERT INTO {STAGING_TABLE}
    (pmg_po_number, prd_lvl_number, new_fob, process_date)
VALUES
    (:pmg_po_number, :prd_lvl_number, :new_fob, NULL)
"""


@dataclass
class DbConfig:
    host: str
    port: int
    service_name: str
    user: str
    password: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DbConfig":
        return cls(
            host=str(data["host"]),
            port=int(data["port"]),
            service_name=str(data["service_name"]),
            user=str(data["user"]),
            password=str(data["password"]),
        )

    @property
    def dsn(self) -> str:
        return f"{self.host}:{self.port}/{self.service_name}"


def _import_oracledb():
    try:
        import oracledb
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "oracledb is required. Install with: pip install -r requirements.txt"
        ) from exc
    return oracledb


def connect(config: DbConfig):
    oracledb = _import_oracledb()
    logger.info("Connecting to Oracle %s as %s", config.dsn, config.user)
    return oracledb.connect(
        user=config.user,
        password=config.password,
        dsn=config.dsn,
    )


def rows_from_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, rec in df.iterrows():
        rows.append(
            {
                "pmg_po_number": str(rec["PGM_PO_NUMBER"]),
                "prd_lvl_number": str(rec["PRD_LVL_NUMBER"]),
                "new_fob": float(rec["NEW_FOB"]),
            }
        )
    return rows


def load_staging_table(
    connection,
    rows: Sequence[dict[str, Any]],
    *,
    dry_run: bool = False,
) -> int:
    """Insert cleaned rows with process_date left NULL (Confluence requirement)."""
    if dry_run:
        logger.info("[dry-run] Would insert %s rows into %s", len(rows), STAGING_TABLE)
        return len(rows)

    if not rows:
        logger.warning("No rows to insert")
        return 0

    cursor = connection.cursor()
    try:
        cursor.executemany(INSERT_SQL, list(rows))
        connection.commit()
        logger.info("Inserted %s rows into %s", cursor.rowcount, STAGING_TABLE)
        return cursor.rowcount
    finally:
        cursor.close()


def _enable_dbms_output(cursor, size: int = 1_000_000) -> None:
    cursor.callproc("dbms_output.enable", [size])


def _fetch_dbms_output(cursor) -> list[str]:
    lines: list[str] = []
    chunk_size = 100
    # dbms_output.get_lines(lines OUT, numlines IN OUT)
    while True:
        line_var = cursor.arrayvar(str, chunk_size)
        num_var = cursor.var(int)
        num_var.setvalue(0, chunk_size)
        cursor.callproc("dbms_output.get_lines", [line_var, num_var])
        n = int(num_var.getvalue())
        values = line_var.getvalue()[:n]
        for item in values:
            if item is not None:
                lines.append(item)
        if n < chunk_size:
            break
    return lines


def run_plsql_block(
    connection,
    plsql: str,
    *,
    label: str,
    dry_run: bool = False,
) -> list[str]:
    """Execute an anonymous PL/SQL block and return DBMS_OUTPUT lines."""
    if dry_run:
        logger.info("[dry-run] Would execute PL/SQL block: %s", label)
        logger.debug("PL/SQL:\n%s", plsql)
        return [f"[dry-run] skipped {label}"]

    cursor = connection.cursor()
    try:
        _enable_dbms_output(cursor)
        cursor.execute(plsql)
        # COMMIT is inside the update block; validation block has no DML commit needs
        lines = _fetch_dbms_output(cursor)
        for line in lines:
            logger.info("[%s] %s", label, line)
        return lines
    finally:
        cursor.close()


def run_update(connection, *, dry_run: bool = False) -> list[str]:
    return run_plsql_block(
        connection, UPDATE_PLSQL, label="fob-update", dry_run=dry_run
    )


def run_validation(connection, *, dry_run: bool = False) -> list[str]:
    return run_plsql_block(
        connection, VALIDATION_PLSQL, label="fob-validation", dry_run=dry_run
    )


def load_csv_to_db(
    csv_path: Path | str,
    config: DbConfig,
    *,
    dry_run: bool = False,
    run_update_block: bool = True,
    run_validation_block: bool = True,
) -> dict[str, Any]:
    """End-to-end DB portion: load CSV rows, run update + validation PL/SQL."""
    df = pd.read_csv(csv_path, dtype={"PGM_PO_NUMBER": str, "PRD_LVL_NUMBER": str})
    rows = rows_from_dataframe(df)
    result: dict[str, Any] = {
        "staging_rows": len(rows),
        "inserted": 0,
        "update_output": [],
        "validation_output": [],
        "dry_run": dry_run,
    }

    if dry_run:
        result["inserted"] = load_staging_table(None, rows, dry_run=True)
        result["update_output"] = run_update(None, dry_run=True) if run_update_block else []
        result["validation_output"] = (
            run_validation(None, dry_run=True) if run_validation_block else []
        )
        return result

    connection = connect(config)
    try:
        result["inserted"] = load_staging_table(connection, rows, dry_run=False)
        if run_update_block:
            result["update_output"] = run_update(connection, dry_run=False)
        if run_validation_block:
            result["validation_output"] = run_validation(connection, dry_run=False)
    finally:
        connection.close()
        logger.info("Oracle connection closed")
    return result
