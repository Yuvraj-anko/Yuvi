"""FOB Indent PO CSV Cleaner — simple upload/download web app.

Anyone with the URL can upload a business CSV and download the cleaned
file (same original filename). No GitHub or Cursor access required.
"""

from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agent.transform import summarize, transform_csv

logger = logging.getLogger("fob.web")

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="FOB Indent PO CSV Cleaner",
    description="Upload a business FOB CSV; download cleaned headers + case-pack strip.",
    version="1.0.0",
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>FOB Indent PO CSV Cleaner</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>
  <div class="bg"></div>
  <main class="shell">
    <header class="brand">
      <p class="mark">FOB Indent</p>
      <h1>PO CSV Cleaner</h1>
      <p class="lede">Upload the business file. Download the cleaned CSV with the same name — headers remapped, case-pack <code>*</code> suffixes removed.</p>
    </header>

    <form id="form" class="panel" action="/clean" method="post" enctype="multipart/form-data">
      <label class="drop" id="drop" for="file">
        <input id="file" name="file" type="file" accept=".csv,text/csv" required />
        <span class="drop-title">Drop CSV here or browse</span>
        <span class="drop-hint" id="file-name">Accepts PO Number / CASE PACK ID / FOB</span>
      </label>
      <button type="submit" id="submit" disabled>Clean &amp; download</button>
      <p class="status" id="status" hidden></p>
    </form>

    <footer class="foot">
      <p>Maps to <code>PGM_PO_NUMBER</code>, <code>PRD_LVL_NUMBER</code>, <code>NEW_FOB</code>. Output keeps the original filename.</p>
    </footer>
  </main>
  <script src="/static/app.js"></script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.post("/clean")
async def clean(file: UploadFile = File(...)) -> StreamingResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    name = Path(file.filename).name
    if not name.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    with tempfile.TemporaryDirectory(prefix="fob_clean_") as tmp:
        tmp_dir = Path(tmp)
        in_path = tmp_dir / name
        out_path = tmp_dir / f"cleaned_{name}"
        in_path.write_bytes(raw)
        try:
            transform_csv(in_path, out_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover
            logger.exception("Transform failed")
            raise HTTPException(status_code=500, detail=f"Clean failed: {exc}") from exc

        import pandas as pd

        df = pd.read_csv(out_path, dtype=str)
        stats = summarize(df)
        logger.info(
            "Cleaned %s -> rows=%s pos=%s products=%s",
            name,
            stats["row_count"],
            stats["po_count"],
            stats["product_count"],
        )
        payload = out_path.read_bytes()

    headers = {
        "Content-Disposition": f'attachment; filename="{name}"',
        "X-FOB-Row-Count": str(stats["row_count"]),
        "X-FOB-PO-Count": str(stats["po_count"]),
        "X-FOB-Product-Count": str(stats["product_count"]),
    }
    return StreamingResponse(
        io.BytesIO(payload),
        media_type="text/csv",
        headers=headers,
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
