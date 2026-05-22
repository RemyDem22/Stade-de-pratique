import os
import glob
import tkinter as tk
from tkinter import filedialog, messagebox
from tqdm import tqdm
import geopandas as gpd
import pandas as pd
import fiona

def choisir_dossier():
    root = tk.Tk()
    root.withdraw()
    dossier = filedialog.askdirectory(
        title="Sélectionnez le dossier contenant les fichiers GPKG"
    )
    return dossier

def fusionner_gpkg(dossier):
    fichiers_gpkg = glob.glob(os.path.join(dossier, "*.gpkg"))

    if not fichiers_gpkg:
        print("Aucun fichier .gpkg trouvé.")
        return

    print(f"{len(fichiers_gpkg)} fichiers trouvés.")

    gdfs = []

    for fichier in tqdm(fichiers_gpkg, desc="Lecture des GPKG"):
        try:
            # Liste des couches du GPKG
            couches = fiona.listlayers(fichier)

            for couche in couches:
                gdf = gpd.read_file(fichier, layer=couche)

                # Ajouter le nom du fichier source (optionnel)
                gdf["source_file"] = os.path.basename(fichier)

                gdfs.append(gdf)

        except Exception as e:
            print(f"Erreur avec {fichier} : {e}")

    if not gdfs:
        print("Aucune donnée valide à fusionner.")
        return

    print("Fusion des données...")
    gdf_final = gpd.GeoDataFrame(
        pd.concat(gdfs, ignore_index=True),
        crs=gdfs[0].crs
    )

    sortie = os.path.join(dossier, "fusion_resultat.gpkg")

    print("Écriture du fichier final...")
    gdf_final.to_file(sortie, driver="GPKG")

    print(f"\nFusion terminée :\n{sortie}")

    messagebox.showinfo(
        "Terminé",
        f"Fusion terminée.\nFichier créé :\n{sortie}"
    )

if __name__ == "__main__":
    dossier = choisir_dossier()

    if dossier:
        fusionner_gpkg(dossier)
    else:
        print("Aucun dossier sélectionné.")