import os
import geopandas as gpd
import pandas as pd
import fiona

def fusionner_gpkg(dossier_input, dossier_output, nom_fichier_sortie="fusion_resultat.gpkg"):

    fichiers_gpkg = [
        os.path.join(dossier_input, f)
        for f in os.listdir(dossier_input)
        if f.endswith(".gpkg")
    ]

    if not fichiers_gpkg:
        raise Exception("Aucun fichier .gpkg trouvé")

    gdfs = []

    for fichier in fichiers_gpkg:

        couches = fiona.listlayers(fichier)

        for couche in couches:

            gdf = gpd.read_file(fichier, layer=couche)
            gdf["source_file"] = os.path.basename(fichier)

            gdfs.append(gdf)

    if not gdfs:
        raise Exception("Aucune donnée valide")

    gdf_final = gpd.GeoDataFrame(
        pd.concat(gdfs, ignore_index=True),
        crs=gdfs[0].crs
    )

    os.makedirs(dossier_output, exist_ok=True)

    output_path = os.path.join(dossier_output, nom_fichier_sortie)

    gdf_final.to_file(output_path, driver="GPKG")

    print(f"✔ Fusion terminée : {output_path}")


# =========================================================
# MODE STANDALONE (OPTIONNEL)
# =========================================================

if __name__ == "__main__":

    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()

    print("\n=== MODE STANDALONE MERGE ===")

    dossier_input = filedialog.askdirectory(
        title="Sélectionnez le dossier contenant les GPKG"
    )

    if not dossier_input:
        print("[MERGE] Aucun dossier sélectionné.")
        exit()

    dossier_output = filedialog.askdirectory(
        title="Sélectionnez le dossier de sortie"
    )

    if not dossier_output:
        print("[MERGE] Aucun dossier de sortie sélectionné.")
        exit()

    fusionner_gpkg(
        dossier_input=dossier_input,
        dossier_output=dossier_output
    )