import subprocess
import sys
import time
import argparse
import os
from tqdm import tqdm
import geopandas as gpd

# =========================================================
# ARGUMENTS
# =========================================================

parser = argparse.ArgumentParser()

parser.add_argument("--output", required=True)
parser.add_argument("--grid", required=True)
parser.add_argument("--m3", required=True)
parser.add_argument("--catalog", required=False)
parser.add_argument("--aera-field", required=False)
parser.add_argument("--clean", action="store_true")

parser.add_argument(
    "--from-step",
    type=str,
    default="step1",
    help="step1 | step7 | step8 | merge | aera"
)

args = parser.parse_args()

# =========================================================
# PIPELINE ORDER
# =========================================================

PIPELINE_ORDER = [
    "step1",
    "step7",
    "step8",
    "merge",
    "aera"
]

STEP_MAP = {
    "step1": "step1to6_processing.py",
    "step7": "step7_split.py",
    "step8": "step8_buffer.py"
}

# =========================================================
# RUN SCRIPT
# =========================================================

def run_script(script, extra_args=None):

    print(f"\n🚀 Lancement {script}")

    cmd = [sys.executable, script]

    # arguments globaux pipeline
    if args.clean:
        cmd.append("--clean")

    if extra_args:
        cmd.extend(extra_args)

    start = time.time()

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"❌ Erreur dans {script}")
        sys.exit(1)

    print(f"✅ {script} terminé en {round((time.time() - start)/60, 2)} min")

# =========================================================
# MAIN PIPELINE
# =========================================================

if __name__ == "__main__":

    print("\nLancement pipeline Stade de Pratique")

    start_total = time.time()

    # -----------------------------------------------------
    # VALIDATION FROM STEP
    # -----------------------------------------------------

    if args.from_step not in PIPELINE_ORDER:
        raise Exception(f"Step inconnu : {args.from_step}")

    start_index = PIPELINE_ORDER.index(args.from_step)
    steps_to_run = PIPELINE_ORDER[start_index:]

    print(f"Reprise à partir de : {args.from_step}")
    print(f"Steps : {steps_to_run}")

    # =====================================================
    # EXECUTION PIPELINE
    # =====================================================

    for step in steps_to_run:

        # =========================
        # STEP 1 (processing 1→6)
        # =========================
        if step == "step1":

            run_script(
                STEP_MAP["step1"],
                extra_args=[
                    "--input", args.m3,
                    "--grid", args.grid,
                    "--output", args.output
                ]
            )

        # =========================
        # STEP 7
        # =========================
        elif step == "step7":

            run_script(
                STEP_MAP["step7"],
                extra_args=[
                    "--output", args.output
                ]
            )

        # =========================
        # STEP 8
        # =========================
        elif step == "step8":

            run_script(
                STEP_MAP["step8"],
                extra_args=[
                    "--output", args.output
                ]
            )

        # =========================
        # MERGE
        # =========================
        elif step == "merge":

            from merge import fusionner_gpkg

            step8_folder = os.path.join(args.output, "step8_final_lines")
            merge_output = os.path.join(args.output, "merge")

            fusionner_gpkg(
                dossier_input=step8_folder,
                dossier_output=merge_output,
                nom_fichier_sortie="fusion_resultat.gpkg"
            )

        # =========================
        # AERA ANALYSIS
        # =========================
        elif step == "aera":

            from geo_analysis import run_network_aera

            merged_file = os.path.join(
                args.output,
                "merge",
                "fusion_resultat.gpkg"
            )

            aera_output = os.path.join(args.output, "network_aera")

            run_network_aera(
                network_file=merged_file,
                aera_file=args.catalog,
                output_folder=aera_output,
                aera_name_field=args.aera_field,
                output_prefix="network_aera"
            )

    # =====================================================
    # FIN
    # =====================================================

    total_minutes = round((time.time() - start_total) / 60, 2)

    print(f"\nPipeline terminé en {total_minutes} min")