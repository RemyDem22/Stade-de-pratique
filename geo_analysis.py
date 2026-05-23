import os
import time
import geopandas as gpd
import pandas as pd
from tqdm import tqdm


# =====================================================
# MAIN FUNCTION
# =====================================================

def run_network_aera(
    network_file,
    aera_file,
    output_folder,
    aera_name_field=None,
    output_prefix="network_aera"
):

    # =====================================================
    # OUTPUT
    # =====================================================

    os.makedirs(output_folder, exist_ok=True)

    output_geojson = os.path.join(output_folder, f"{output_prefix}.geojson")
    output_csv = os.path.join(output_folder, f"{output_prefix}.csv")


    # =====================================================
    # LOAD DATA
    # =====================================================

    print("\n[GEO] Chargement du réseau...")
    network = gpd.read_file(network_file)

    print("[GEO] Chargement du catalogue geographique sélectionné...")
    aera = gpd.read_file(aera_file)


    # =====================================================
    # CRS CHECK
    # =====================================================

    print("[GEO] Vérification des projections...")

    if network.crs is None:
        raise Exception("Le réseau n'a pas de CRS.")

    if aera.crs is None:
        raise Exception("La couche geo. n'a pas de CRS.")

    if network.crs.to_epsg() != 2154:
        network = network.to_crs(2154)

    if aera.crs.to_epsg() != 2154:
        aera = aera.to_crs(2154)


    # =====================================================
    # FIELD VALIDATION (IMPORTANT)
    # =====================================================

    if aera_name_field is None:
        raise Exception(
            "[GEO] Champ attributaire non fourni. "
            "Sélection obligatoire via UI."
        )

    if aera_name_field not in aera.columns:
        raise Exception(
            f"[GEO] Champ '{aera_name_field}' introuvable dans le GeoJSON."
        )

    print(f"[GEO] Champ utilisé : {aera_name_field}")


    # =====================================================
    # SPATIAL FILTER
    # =====================================================

    print("[GEO] Sélection des entités intersectant le réseau...")

    network_union = network.geometry.union_all()

    aera = aera[aera.geometry.intersects(network_union)].copy()

    if aera.empty:
        raise Exception("[GEO] Aucune entité intersecte le réseau.")

    print(f"[GEO] {len(aera)} entités retenues.")


    # =====================================================
    # INTERSECTION (WITH PROGRESS BAR)
    # =====================================================

    print("[GEO] Découpage du réseau...")

    start = time.perf_counter()
    results = []

    for _, row in tqdm(
        aera.iterrows(),
        total=len(aera),
        desc="Découpage du catalogue géographique"
    ):

        geom = row.geometry
        name = row[aera_name_field]

        subset = network[network.intersects(geom)]

        if subset.empty:
            continue

        clipped = gpd.overlay(
            subset,
            gpd.GeoDataFrame(
                [{aera_name_field: name, "geometry": geom}],
                crs=aera.crs
            ),
            how="intersection"
        )

        if not clipped.empty:
            results.append(clipped)

    duration = round(time.perf_counter() - start, 2)
    print(f"[GEO] Intersection terminée ({duration}s)")


    if not results:
        raise Exception("[GEO] Aucune intersection trouvée.")

    intersections = gpd.GeoDataFrame(
        pd.concat(results, ignore_index=True),
        crs=network.crs
    )


    # =====================================================
    # LENGTH
    # =====================================================

    print("[GEO] Calcul des longueurs...")

    intersections["length_km"] = intersections.geometry.length / 1000


    # =====================================================
    # AGGREGATION
    # =====================================================

    print("[GEO] Agrégation...")

    summary = (
        intersections
        .groupby(aera_name_field)["length_km"]
        .sum()
        .reset_index()
    )

    summary["length_km"] = summary["length_km"].round(2)


    # =====================================================
    # JOIN BACK
    # =====================================================

    print("[GEO] Jointure finale...")

    aera_final = aera.merge(
        summary,
        on=aera_name_field,
        how="left"
    )

    aera_final["length_km"] = aera_final["length_km"].fillna(0)


    # =====================================================
    # EXPORTS
    # =====================================================

    print("[GEO] Export GeoJSON...")
    aera_final.to_file(output_geojson, driver="GeoJSON")

    print("[GEO] Export CSV...")
    summary.to_csv(output_csv, index=False, encoding="utf-8-sig")


    # =====================================================
    # DONE
    # =====================================================

    print("\n[GEO] Terminé.")
    print(f"GeoJSON : {output_geojson}")
    print(f"CSV     : {output_csv}")

    return {
        "geojson": output_geojson,
        "csv": output_csv
    }


# =========================================================
# STANDALONE MODE
# =========================================================

if __name__ == "__main__":

    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()

    print("\n=== MODE STANDALONE AERA ===")

    network_file = filedialog.askopenfilename(
        title="Réseau fusionné",
        filetypes=[("GeoPackage", "*.gpkg")]
    )

    aera_file = filedialog.askopenfilename(
        title="Catalogue AERA",
        filetypes=[("GeoJSON", "*.geojson")]
    )

    output_folder = filedialog.askdirectory(
        title="Dossier sortie"
    )

    if not network_file or not aera_file or not output_folder:
        raise Exception("Sélection incomplète.")

    run_network_aera(
        network_file=network_file,
        aera_file=aera_file,
        output_folder=output_folder,
        aera_name_field=None  # important : UI doit le fournir dans pipeline main
    )