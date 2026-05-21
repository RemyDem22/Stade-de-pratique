import subprocess
import sys
import time
import argparse

# -----------------------------
# ARGUMENTS
# -----------------------------
parser = argparse.ArgumentParser()

parser.add_argument(
    "steps",
    nargs="*",
    default=["all"],
    help="processing | split | buffer | all"
)

parser.add_argument(
    "--clean",
    action="store_true",
    help="Nettoyer les dossiers avant exécution"
)

args = parser.parse_args()

# -----------------------------
# MAPPING DES ÉTAPES
# -----------------------------
PIPELINE = {
    "processing": "step1to6_processing.py",
    "split": "step7_split.py",
    "buffer": "step8_buffer.py"
}

# -----------------------------
# FONCTION
# -----------------------------
def run_script(script):

    print(f"\n🚀 Lancement {script}")

    cmd = [sys.executable, script]

    if args.clean:
        cmd.append("--clean")

    start = time.time()

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"❌ Erreur dans {script}")
        sys.exit(1)

    print(f"✅ {script} terminé en {round((time.time()-start)/60, 2)} min")


# -----------------------------
# LOGIQUE D’EXÉCUTION
# -----------------------------
if __name__ == "__main__":

    print("Construction du stade de pratique")

    start_total = time.time()

    # si "all" → tout lancer
    if "all" in args.steps:
        steps_to_run = ["processing", "split", "buffer"]
    else:
        steps_to_run = args.steps

    # ordre garanti
    ordered_steps = ["processing", "split", "buffer"]

    for step in ordered_steps:
        if step in steps_to_run:
            run_script(PIPELINE[step])

    print(f"\n🎉 Terminé en {round((time.time()-start_total)/60, 2)} min")