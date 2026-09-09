# Yuvi

## FOB Indent PO Bulk Update Agent

See [`fob_bulk_update_agent/README.md`](fob_bulk_update_agent/README.md).

Automates the Confluence BAU task **FOB on Indent POs - Bulk Update**:
clean business CSV (headers + strip case-pack `*` suffix), load
`PROD_SUPPORT.BAU_INDENT_PO_FOB_UPD` via Python/Oracle with **encrypted**
credentials, then run the update and validation PL/SQL blocks.
