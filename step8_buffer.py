import geopandas as gpd
import os
from tqdm import tqdm
import argparse
import shutil
import time
import stat
from shapely.ops import linemerge, unary_union
from shapely.geometry import LineString

print("▶️ step8_buffer lancé")

# -----------------------------
# ARGUMENTS CLI
# -----------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--clean", action="store_true")
args = parser.parse_args()

# -----------------------------
# PATHS
# -----------------------------
STEP7_FOLDER = "output/step7_split_lines"
BUFFER_FOLDER = "output/step1_buffer"
OUTPUT_FOLDER = "output/step8_final_lines"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -----------------------------
# SAFE DELETE (ULTRA ROBUST)
# -----------------------------
def on_rm_error(func, path, exc_info):
    """
    Force la suppression même si fichier read-only
    """
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        print(f"❌ Impossible de supprimer {path} : {e}")

def safe_rmtree(path, retries=5, delay=1):
    """
    Suppression robuste (Windows + OneDrive safe)
    """
    for i in range(retries):
        try:
            shutil.rmtree(path, onerror=on_rm_error)
            print(f"✅ Dossier supprimé : {path}")
            return
        except PermissionError:
            print(f"⚠️ Retry {i+1}/{retries} pour supprimer {path}")
            time.sleep(delay)

    raise PermissionError(f"❌ Impossible de supprimer {path} après {retries} tentatives")

# -----------------------------
# CHAikin SMOOTHING
# -----------------------------
def chaikin_smoothing(line, iterations=2):
    coords = list(line.coords)

    if len(coords) < 4:
        return line

    for _ in range(iterations):
        new_coords = [coords[0]]

        for i in range(1, len(coords) - 2):
            p0 = coords[i - 1]
            p1 = coords[i]
            p2 = coords[i + 1]

            q = (
                0.25 * p0[0] + 0.5 * p1[0] + 0.25 * p2[0],
                0.25 * p0[1] + 0.5 * p1[1] + 0.25 * p2[1]
            )

            new_coords.append(q)

        new_coords.append(coords[-1])
        coords = new_coords

    return LineString(coords)

# -----------------------------
# CLEAN
# -----------------------------
if args.clean:
    print("🧹 Nettoyage STEP8")

    if os.path.exists(OUTPUT_FOLDER):
        try:
            safe_rmtree(OUTPUT_FOLDER)
        except Exception as e:
            print(f"⚠️ Nettoyage partiel échoué : {e}")

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -----------------------------
# PARAM SNAP
# -----------------------------
SNAP_TOL = 1.0

# -----------------------------
# EXECUTION
# -----------------------------
files = os.listdir(STEP7_FOLDER)

print("🔄 Filtrage STEP7 avec buffer STEP1...")

for file in tqdm(files):

    i = file.split("_")[-1].replace(".gpkg", "")

    step7_path = os.path.join(STEP7_FOLDER, file)
    buffer_path = os.path.join(BUFFER_FOLDER, f"buffer_{i}.gpkg")
    out_path = os.path.join(OUTPUT_FOLDER, f"final_{i}.gpkg")

    if not os.path.exists(buffer_path):
        continue

    try:
        lines = gpd.read_file(step7_path)
        buffer = gpd.read_file(buffer_path)
    except Exception as e:
        print(f"❌ Erreur lecture {file} : {e}")
        continue

    if lines.empty or buffer.empty:
        continue

    # -----------------------------
    # BUFFER STEP
    # -----------------------------
    buffer_geom = buffer.geometry.iloc[0]
    buffer_safe = buffer_geom.buffer(-1)

    filtered = lines[
        lines.geometry.apply(lambda g: g.within(buffer_safe))
    ]

    if filtered.empty:
        continue

    # -----------------------------
    # MERGE
    # -----------------------------
    geom = unary_union(filtered.geometry)
    merged = linemerge(geom)

    if merged.is_empty:
        continue

    # -----------------------------
    # NORMALISATION
    # -----------------------------
    crs = filtered.crs

    if merged.geom_type == "LineString":
        lines_list = [merged]
    else:
        lines_list = list(merged.geoms)

    # -----------------------------
    # SMOOTHING
    # -----------------------------
    lines_list = [
        chaikin_smoothing(l, iterations=1)
        for l in lines_list
    ]

    # -----------------------------
    # RECONSTRUCTION
    # -----------------------------
    filtered = gpd.GeoDataFrame(
        geometry=lines_list,
        crs=crs
    )

    # -----------------------------
    # EXPORT (avec retry si lock)
    # -----------------------------
    if not filtered.empty:
        for attempt in range(3):
            try:
                filtered.to_file(out_path)
                break
            except Exception as e:
                print(f"⚠️ Retry export {attempt+1}/3 : {out_path}")
                time.sleep(1)

print("✅ STEP8 terminé")