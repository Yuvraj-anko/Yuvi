"""FOB Indent PO CSV cleaner.

Cleans business FOB bulk-upload CSVs:
  1. Rename headers to PGM_PO_NUMBER / PRD_LVL_NUMBER / NEW_FOB
  2. Strip case-pack *suffix from product ids (e.g. 72647646*2A -> 72647646)
"""

__version__ = "1.0.0"
