"""FOB Indent PO Bulk Update Agent.

Automates the Confluence procedure:
https://kmartau.atlassian.net/wiki/spaces/UPT/pages/4310681006/FOB+on+Indent+POs+-+Bulk+Update

Steps:
  1. Clean business CSV (rename headers, strip case-pack *suffix)
  2. Load rows into PROD_SUPPORT.BAU_INDENT_PO_FOB_UPD (process_date NULL)
  3. Run update PL/SQL block
  4. Run optional validation PL/SQL block
"""

__version__ = "1.0.0"
