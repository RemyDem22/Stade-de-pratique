"""
api.py — Backend FastAPI pour le pipeline Stade de Pratique M3
Placer ce fichier dans le même dossier que main.py

Lancer : uvicorn api:app --reload --port 8000
"""

import asyncio
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

# ── CONFIG ─────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
OUTPUT_DIR  = BASE_DIR / "output"

# Noms de fichiers attendus par step1to6_processing.py (hardcodés dans le script)
# On renommera le fichier uploadé à ces noms
INPUT_GPKG   = DATA_DIR / "Stade_rhone.gpkg"
INPUT_GRID   = DATA_DIR / "grille_rhone.geojson"

# Stockage en mémoire des jobs  { job_id: {events, done, result, error} }
JOBS: dict = {}

app = FastAPI(title="Stade de Pratique M3", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── HEALTH ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    main_exists = (BASE_DIR / "main.py").exists()
    grid_exists = INPUT_GRID.exists()
    return {
        "status": "ok",
        "pipeline": str(main_exists),   # "true" si main.py est présent
        "grid":     str(grid_exists),   # "true" si grille présente
    }


# ── LANCER LE TRAITEMENT ───────────────────────────────────────────────────
@app.post("/process")
async def start_process(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Reçoit le fichier .gpkg source (Stade_hdf.gpkg ou autre nom).
    Le sauvegarde sous le nom attendu par step1to6_processing.py.
    Lance le pipeline en arrière-plan.
    Retourne un job_id pour écouter la progression via /progress/{job_id}.
    """
    job_id = str(uuid.uuid4())[:8]
    JOBS[job_id] = {"events": [], "done": False, "result": None, "error": None}

    # Créer le dossier data/ si besoin
    DATA_DIR.mkdir(exist_ok=True)

    # Sauvegarder sous le nom attendu par le pipeline
    with open(INPUT_GPKG, "wb") as f:
        shutil.copyfileobj(file.file, f)

    push(job_id, "info", f"Fichier reçu : {file.filename} → {INPUT_GPKG.name}")
    push(job_id, "info", f"Job ID : {job_id}")

    # Vérifier que la grille est présente
    if not INPUT_GRID.exists():
        push(job_id, "error", f"Grille introuvable : {INPUT_GRID}. Placez grille_hdf.geojson dans data/")
        JOBS[job_id]["error"] = "Grille introuvable"
        JOBS[job_id]["done"]  = True
        return {"job_id": job_id}

    background_tasks.add_task(run_pipeline, job_id)
    return {"job_id": job_id}


# ── STREAM SSE ─────────────────────────────────────────────────────────────
@app.get("/progress/{job_id}")
async def progress(job_id: str):
    """
    Server-Sent Events : le client s'abonne avec EventSource('/progress/{job_id}')
    et reçoit les événements en temps réel jusqu'à l'événement 'done'.
    """
    if job_id not in JOBS:
        return JSONResponse({"error": "Job inconnu"}, status_code=404)

    async def generate():
        sent = 0
        while True:
            job    = JOBS.get(job_id, {})
            events = job.get("events", [])

            while sent < len(events):
                yield f"data: {json.dumps(events[sent])}\n\n"
                sent += 1

            if job.get("done"):
                final = {
                    "type":   "done",
                    "result": job.get("result"),
                    "error":  job.get("error"),
                }
                yield f"data: {json.dumps(final)}\n\n"
                break

            await asyncio.sleep(0.25)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── PIPELINE ───────────────────────────────────────────────────────────────

# Correspondance entre les marqueurs stdout du pipeline et les numéros d'étapes
# Les scripts émettent "▶️ main_processing lancé", "▶️ main_split lancé", etc.
STEP_MARKERS = [
    # (pattern à chercher dans la ligne,  numéro step,  label affiché)
    ("main_processing",   1, "Buffer des polygones"),
    ("step1",             1, "Buffer des polygones"),
    ("step2",             2, "Polygones → lignes"),
    ("step3",             3, "Échantillonnage de points"),
    ("step4",             4, "Diagramme de Voronoï"),
    ("step5",             5, "Voronoï → lignes"),
    ("step6",             6, "Extraction des sommets"),
    ("main_split",        7, "Découpage des lignes (split)"),
    ("split brut",        7, "Découpage des lignes (split)"),
    ("main_buffer",       8, "Filtrage final"),
    ("filtrage step7",    8, "Filtrage final"),
]


def push(job_id: str, type_: str, message: str,
         step: int = None, pct: float = None):
    evt = {"type": type_, "message": message, "ts": time.time()}
    if step is not None:
        evt["step"] = step
    if pct is not None:
        evt["pct"] = pct
    JOBS[job_id]["events"].append(evt)


def run_pipeline(job_id: str):
    """
    Lance  python main.py  et streame stdout ligne par ligne vers le SSE.
    Détecte les marqueurs de progression dans la sortie console.
    """
    try:
        push(job_id, "step", "Démarrage du pipeline M3...", pct=0)

        cmd = [sys.executable, str(BASE_DIR / "main.py")]

        # ── Correction Windows CP1252 ──────────────────────────────────────
        # Sur Windows, le terminal système utilise l'encodage CP1252 par défaut.
        # Les emojis (🚀 ✅ ❌) dans les print() de main.py provoquent un
        # UnicodeEncodeError avant même que le pipeline ne démarre.
        # PYTHONUTF8=1 force Python à utiliser UTF-8 pour stdout/stderr,
        # quel que soit l'encodage système.
        import os as _os
        env = _os.environ.copy()
        env["PYTHONUTF8"] = "1"          # Python 3.7+ — force UTF-8 I/O
        env["PYTHONIOENCODING"] = "utf-8" # fallback pour les versions < 3.7

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(BASE_DIR),
            encoding="utf-8",
            errors="replace",
            env=env,                      # <-- passe l'environnement corrigé
        )

        current_step = 0

        for raw_line in proc.stdout:
            line = raw_line.rstrip()
            if not line:
                continue

            # Toujours transmettre la ligne brute dans la console
            push(job_id, "log", line)

            # Détecter l'avancement
            line_lower = line.lower()
            for pattern, num, label in STEP_MARKERS:
                if pattern in line_lower and num > current_step:
                    current_step = num
                    pct = (num - 1) / 8 * 100
                    push(job_id, "step", f"Step {num} — {label}",
                         step=num, pct=pct)
                    break

            # Détecter les erreurs critiques (❌)
            if "❌" in line or "erreur" in line_lower:
                push(job_id, "warn", line)

        proc.wait()

        if proc.returncode != 0:
            raise RuntimeError(
                f"Pipeline terminé avec code de retour {proc.returncode}"
            )

        # Marquer step 8 terminé
        push(job_id, "step", "Step 8 — Filtrage final terminé", step=8, pct=95)
        push(job_id, "log", "Conversion des résultats en GeoJSON...")

        # Fusionner les fichiers step8 → GeoJSON WGS-84
        geojson = merge_step8(job_id)

        segs   = [f for f in geojson["features"]
                  if f["geometry"]["type"] in ("LineString", "MultiLineString")]
        total_m = sum_length_m(segs)

        result = {
            "geojson":  geojson,
            "km":       round(total_m / 1000, 2),
            "segments": len(segs),
        }

        JOBS[job_id]["result"] = result
        push(job_id, "step",
             f"✅ Terminé — {result['km']} km · {result['segments']} segments",
             pct=100)

    except Exception as exc:
        JOBS[job_id]["error"] = str(exc)
        push(job_id, "error", f"Erreur pipeline : {exc}")

    finally:
        JOBS[job_id]["done"] = True


# ── CONVERSION STEP8 → GEOJSON ─────────────────────────────────────────────

def merge_step8(job_id: str) -> dict:
    """
    Fusionne tous les output/step8_final_lines/final_*.gpkg en un GeoJSON WGS-84.
    Utilise ogr2ogr (inclus dans GDAL, présent si GeoPandas est installé).
    Si ogr2ogr est absent, tente une conversion via GeoPandas/Fiona.
    """
    step8_dir = OUTPUT_DIR / "step8_final_lines"
    gpkg_files = sorted(glob.glob(str(step8_dir / "final_*.gpkg")))

    if not gpkg_files:
        raise FileNotFoundError(
            f"Aucun fichier final_*.gpkg trouvé dans {step8_dir}. "
            "Vérifiez que le pipeline s'est bien exécuté jusqu'à l'étape 8."
        )

    push(job_id, "log", f"{len(gpkg_files)} tuile(s) à fusionner")

    # ── Essai avec ogr2ogr ──
    if shutil.which("ogr2ogr"):
        return _merge_with_ogr2ogr(job_id, gpkg_files)
    else:
        push(job_id, "warn", "ogr2ogr absent — conversion via GeoPandas")
        return _merge_with_geopandas(job_id, gpkg_files)


def _merge_with_ogr2ogr(job_id: str, gpkg_files: list) -> dict:
    all_features = []
    for gpkg in gpkg_files:
        tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
        tmp.close()
        try:
            r = subprocess.run(
                ["ogr2ogr", "-f", "GeoJSON", "-t_srs", "EPSG:4326",
                 tmp.name, gpkg],
                capture_output=True, text=True,
            )
            if r.returncode == 0:
                with open(tmp.name, encoding="utf-8") as f:
                    gj = json.load(f)
                all_features.extend(gj.get("features", []))
            else:
                push(job_id, "warn", f"ogr2ogr erreur sur {Path(gpkg).name}: {r.stderr.strip()}")
        finally:
            os.unlink(tmp.name)

    push(job_id, "log", f"{len(all_features)} feature(s) fusionnée(s)")
    return {"type": "FeatureCollection", "features": all_features}


def _merge_with_geopandas(job_id: str, gpkg_files: list) -> dict:
    """Fallback si ogr2ogr n'est pas dans le PATH."""
    import geopandas as gpd
    import pandas as pd

    gdfs = []
    for gpkg in gpkg_files:
        try:
            gdf = gpd.read_file(gpkg)
            if not gdf.empty:
                gdfs.append(gdf)
        except Exception as e:
            push(job_id, "warn", f"Lecture échouée : {Path(gpkg).name} — {e}")

    if not gdfs:
        raise RuntimeError("Aucune tuile step8 lisible")

    merged = pd.concat(gdfs, ignore_index=True)
    merged = gpd.GeoDataFrame(merged, crs=gdfs[0].crs)

    # Reprojection WGS-84 pour Leaflet
    if merged.crs and merged.crs.to_epsg() != 4326:
        merged = merged.to_crs(4326)

    push(job_id, "log", f"{len(merged)} feature(s) fusionnée(s)")

    return json.loads(merged.to_json())


# ── CALCUL LONGUEUR ────────────────────────────────────────────────────────

def haversine(p1, p2) -> float:
    R = 6_371_000
    lat1, lon1 = math.radians(p1[1]), math.radians(p1[0])
    lat2, lon2 = math.radians(p2[1]), math.radians(p2[0])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def sum_length_m(features) -> float:
    total = 0.0
    for f in features:
        geom = f["geometry"]
        segs = [geom["coordinates"]] if geom["type"] == "LineString" \
               else geom["coordinates"]
        for coords in segs:
            for i in range(1, len(coords)):
                total += haversine(coords[i - 1], coords[i])
    return total
