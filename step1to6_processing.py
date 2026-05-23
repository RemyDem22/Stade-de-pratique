import geopandas as gpd
import os
from tqdm import tqdm
import shutil
import time
import tkinter as tk
from tkinter import filedialog

from processing import process_tile, polygon_to_line, lines_to_points, create_voronoi, extract_vertices
from joblib import Parallel, delayed
from multiprocessing import Pool
import argparse

import glob


parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--grid", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--m3", required=False)
parser.add_argument("--clean", action="store_true")
args = parser.parse_args()

# -----------------------------
# PARAMETRES
# -----------------------------

BASE_OUTPUT = args.output
STEP1_FOLDER = os.path.join(BASE_OUTPUT, "step1_buffer")
STEP2_FOLDER = os.path.join(BASE_OUTPUT, "step2_lines")
STEP3_FOLDER = os.path.join(BASE_OUTPUT, "step3_points")
STEP4_FOLDER = os.path.join(BASE_OUTPUT, "step4_voronoi")
STEP5_FOLDER = os.path.join(BASE_OUTPUT, "step5_voronoi_lines")
STEP6_FOLDER = os.path.join(BASE_OUTPUT, "step6_vertices")

BUFFER_TILE = 10

USE_MULTIPROCESSING = True
N_JOBS = 6

def choose_file(title, filetypes):

    root = tk.Tk()
    root.withdraw()  # cache la fenêtre principale

    filepath = filedialog.askopenfilename(
        title=title,
        initialdir="data",
        filetypes=filetypes
    )

    if not filepath:
        raise Exception("Aucun fichier sélectionné")

    return filepath

# -----------------------------
# CHOIX DES FICHIERS
# -----------------------------

print("📂 Sélection de la couche flux...")

INPUT_FILE = args.input

GRID_FILE = args.grid

print("▶️  main_processing lancé")

# -----------------------------
# NETTOYAGE DOSSIER OUTPUT
# -----------------------------

STEP_FOLDERS = [STEP1_FOLDER, STEP2_FOLDER, STEP3_FOLDER, STEP4_FOLDER, STEP5_FOLDER, STEP6_FOLDER]

if args.clean:

    print("Nettoyage dossiers STEP1 → STEP6")

    for folder in STEP_FOLDERS:

        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"📂 Contenu de {folder} nettoyé")

            except PermissionError:
                print(f"⚠️ {folder} verrouillé, tentative...")
                time.sleep(1)
                try:
                    shutil.rmtree(folder)
                except:
                    print(f"❌ Impossible de supprimer {folder}")

# recréation des dossiers
for folder in STEP_FOLDERS:
    os.makedirs(folder, exist_ok=True)

# recréation du dossier quoi qu'il arrive
os.makedirs(BASE_OUTPUT, exist_ok=True)

# -----------------------------
# CHARGEMENT
# -----------------------------

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError("Fichier input introuvable")

if not os.path.exists(GRID_FILE):
    raise FileNotFoundError("Grille introuvable")

print("Chargement des données...")
data = gpd.read_file(INPUT_FILE)
data = data[["geometry"]]
data.sindex

print("Chargement de la grille...")
tiles = gpd.read_file(GRID_FILE)

# reprojection
if data.crs.to_epsg() != 2154:
    data = data.to_crs(2154)

if tiles.crs.to_epsg() != 2154:
    tiles = tiles.to_crs(2154)

# -----------------------------
# FONCTION
# -----------------------------

def process_one_tile(i, tile, data):

    step1_path = f"{STEP1_FOLDER}/buffer_{i}.gpkg"
    step2_path = f"{STEP2_FOLDER}/lines_{i}.gpkg"
    step3_path = f"{STEP3_FOLDER}/points_{i}.gpkg"
    step4_path = f"{STEP4_FOLDER}/voronoi_{i}.gpkg"
    step5_path = f"{STEP5_FOLDER}/voronoi_lines_{i}.gpkg"
    step6_path = f"{STEP6_FOLDER}/vertices_{i}.gpkg"

    # skip si déjà fait
    if os.path.exists(step3_path):
        return

    try:
        tile_geom = tile.geometry

        possible = data[data.intersects(tile_geom)]

        if possible.empty:
            return

        tile_buffered = tile_geom.buffer(BUFFER_TILE)
        subset = gpd.clip(possible, tile_buffered)

        if subset.empty:
            return

        # -----------------------------
        # STEP 1 : BUFFER
        # -----------------------------
        if not os.path.exists(step1_path):

            buffer = process_tile(subset)

            if buffer.empty:
                return

            buffer.to_file(step1_path)

        else:
            buffer = gpd.read_file(step1_path)

        # -----------------------------
        # STEP 2 : LIGNES
        # -----------------------------
        if not os.path.exists(step2_path):

            lines = polygon_to_line(buffer)

            if lines.empty:
                return

            lines.to_file(step2_path)

        else:
            lines = gpd.read_file(step2_path)

        # -----------------------------
        # STEP 3 : POINTS
        # -----------------------------
        points = lines_to_points(lines, distance=30)

        if not points.empty:
            points.to_file(step3_path)

        # -----------------------------
        # STEP 4 : VORONOI
        # -----------------------------
        
        if not os.path.exists(step4_path):

            voronoi = create_voronoi(points, buffer)

            if voronoi.empty:
                return

            voronoi.to_file(step4_path)

        else:
            voronoi = gpd.read_file(step4_path)

        # -----------------------------
        # STEP 5 : VORONOI → LIGNES
        # -----------------------------
        if not os.path.exists(step5_path):

            voronoi_lines = polygon_to_line(voronoi)

            if voronoi_lines.empty:
                return

            voronoi_lines.to_file(step5_path)

        else:
            voronoi_lines = gpd.read_file(step5_path)

        # -----------------------------
        # STEP 6 : EXTRACTION SOMMETS
        # -----------------------------
        if not os.path.exists(step6_path):

            vertices = extract_vertices(voronoi, buffer)

            if vertices.empty:
                return

            # 6.1 DEDUP
            vertices["key"] = vertices.geometry.apply(lambda g: (g.x, g.y))
            vertices = vertices.drop_duplicates(subset=["key"])
            vertices = vertices.drop(columns=["key"])

            # 6.2 FILTRE BUFFER -1m
            buffer_geom = buffer.geometry.iloc[0]
            buffer_safe = buffer_geom.buffer(-1)

            vertices = vertices[
                vertices.geometry.apply(lambda g: g.within(buffer_safe))
            ]

            vertices.to_file(step6_path)

        else:
            vertices = gpd.read_file(step6_path)

    except Exception as e:
        print(f"❌ Erreur tuile {i} : {e}")

# -----------------------------
# EXECUTION
# -----------------------------

print("Traitement des tuiles...")

if USE_MULTIPROCESSING:

    print(f"Mode MULTIPROCESSING intelligent ({N_JOBS} jobs)")

    tasks = (
        delayed(process_one_tile)(i, tile, data)
        for i, tile in tiles.iterrows()
    )

    Parallel(
        n_jobs=N_JOBS,
        backend="loky",
        batch_size="auto"
    )(tqdm(tasks, total=len(tiles)))

else:

    print("Mode SIMPLE (mono-thread)")

    for i, tile in tqdm(tiles.iterrows(), total=len(tiles)):
        process_one_tile(i, tile, data)

print("step1to6 terminé...")