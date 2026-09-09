"""FOB Indent PO Bulk Update Agent.

Automates the Confluence procedure:
https://kmartau.atlassian.net/wiki/spaces/UPT/pages/4310681006/FOB+on+Indent+POs+-+Bulk+Update

Steps:
  1. Clean business CSV (rename headers, strip case-pack *suffix)
  2. Drop cleaned CSV to SMS po_amendments path
  3. Load rows into PROD_SUPPORT.BAU_INDENT_PO_FOB_UPD (process_date NULL)
  4. Run update PL/SQL block
  5. Run optional validation PL/SQL block
"""

__version__ = "1.0.0"
