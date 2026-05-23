import geopandas as gpd
import os
from shapely.geometry import MultiPoint
from shapely.ops import split, snap
from joblib import Parallel, delayed
import multiprocessing
import shutil
import time
from tqdm import tqdm
import argparse

# -----------------------------
# ARGUMENTS
# -----------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
parser.add_argument("--clean", action="store_true")
args = parser.parse_args()

# -----------------------------
# PATHS
# -----------------------------

BASE_OUTPUT = args.output
STEP5_FOLDER = os.path.join(BASE_OUTPUT, "step5_voronoi_lines")
STEP6_FOLDER = os.path.join(BASE_OUTPUT, "step6_vertices")
STEP7_FOLDER = os.path.join(BASE_OUTPUT, "step7_split_lines")

# -----------------------------
# SAFE DELETE (Windows friendly)
# -----------------------------
def safe_rmtree(path):
    for _ in range(5):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            time.sleep(0.5)
    print(f"⚠️  Impossible de supprimer {path}")

# -----------------------------
# SPLIT OPTIMISÉ
# -----------------------------
def split_lines_optimized(lines_gdf, points_gdf, tolerance=1e-8):

    sindex = points_gdf.sindex
    results = []

    for _, row in lines_gdf.iterrows():
        line = row.geometry

        possible_idx = list(sindex.intersection(line.bounds))
        candidate_points = points_gdf.iloc[possible_idx]

        if candidate_points.empty:
            results.append(line)
            continue

        snapped_points = [
            snap(pt.geometry, line, tolerance)
            for _, pt in candidate_points.iterrows()
        ]

        pts_on_line = [
            pt for pt in snapped_points
            if line.intersects(pt)
        ]

        if not pts_on_line:
            results.append(line)
            continue

        try:
            splitted = split(line, MultiPoint(pts_on_line))
            results.extend(splitted.geoms)
        except:
            results.append(line)

    return gpd.GeoDataFrame(geometry=results, crs=lines_gdf.crs)

# -----------------------------
# DEDUP LIGNES
# -----------------------------
def create_dedup_key(line):
    try:
        coords = list(line.coords)

        if len(coords) < 2:
            return None

        p1 = coords[0]
        p2 = coords[-1]

        return f"{min(p1, p2)}-{max(p1, p2)}"

    except:
        return None


def remove_duplicate_lines(gdf):

    gdf["dedup_key"] = gdf.geometry.apply(create_dedup_key)
    gdf = gdf.dropna(subset=["dedup_key"])
    gdf = gdf.drop_duplicates(subset=["dedup_key"])

    return gdf.drop(columns=["dedup_key"])

# -----------------------------
# TRAITEMENT D'UNE TUILE
# -----------------------------
def process_file(file):

    i = file.split("_")[-1].replace(".gpkg", "")

    step5_path = os.path.join(STEP5_FOLDER, file)
    step6_path = os.path.join(STEP6_FOLDER, f"vertices_{i}.gpkg")
    step7_path = os.path.join(STEP7_FOLDER, f"split_lines_{i}.gpkg")

    if os.path.exists(step7_path) or not os.path.exists(step6_path):
        return

    try:
        lines = gpd.read_file(step5_path)
        points = gpd.read_file(step6_path)

        if lines.empty or points.empty:
            return

        result = split_lines_optimized(lines, points)
        result = remove_duplicate_lines(result)

        if not result.empty:
            result.to_file(step7_path)

        # 🔒 libération mémoire explicite (important Windows)
        del lines, points, result

    except Exception as e:
        print(f"❌ Erreur tuile {i} : {e}")

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":

    print("main_split lancé...")

    # CLEAN propre (une seule fois)
    if args.clean:
        if os.path.exists(STEP7_FOLDER):
            safe_rmtree(STEP7_FOLDER)
            print(f"{STEP7_FOLDER} supprimé...")

    os.makedirs(STEP7_FOLDER, exist_ok=True)

    print("Lancement split brut...")

    files = [f for f in os.listdir(STEP5_FOLDER) if f.endswith(".gpkg")]

    n_jobs = max(1, multiprocessing.cpu_count() - 1)

    Parallel(n_jobs=n_jobs)(
        delayed(process_file)(file) for file in tqdm(files)
    )

    print("Step7 terminé...")