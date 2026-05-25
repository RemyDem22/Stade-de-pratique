import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import geopandas as gpd


# =========================================================
# ROOT
# =========================================================

root = tk.Tk()
root.title("Stade de Pratique - Pipeline")
root.geometry("780x520")
root.configure(bg="#F3F4F6")


# =========================================================
# STYLE
# =========================================================

style = ttk.Style()
style.theme_use("clam")

BG = "#F3F4F6"
CARD = "#FFFFFF"
TEXT = "#111827"
SUBTEXT = "#6B7280"
ACCENT = "#2563EB"

style.configure("TFrame", background=BG)
style.configure("TLabel", background=BG, foreground=TEXT)
style.configure("TLabelframe", background=CARD)
style.configure("TLabelframe.Label", background=CARD, foreground=TEXT)


style.configure(
    "Accent.TButton",
    font=("Segoe UI", 10, "bold"),
    padding=6
)


# =========================================================
# VARIABLES
# =========================================================

output_var = tk.StringVar()
grid_var = tk.StringVar()
m3_var = tk.StringVar()
catalog_var = tk.StringVar()

field_var = tk.StringVar()
step_var = tk.StringVar(value="step1")
clean_var = tk.BooleanVar()


BASE_DATA = os.path.join(os.getcwd(), "data")
DIR_M3 = os.path.join(BASE_DATA, "m3")
DIR_GRID = os.path.join(BASE_DATA, "grid")
DIR_CATALOG = os.path.join(BASE_DATA, "catalogue_geographique")


# =========================================================
# SCROLL FRAME FIX (IMPORTANT)
# =========================================================

container = ttk.Frame(root)
container.pack(fill="both", expand=True)

canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

scroll_frame = ttk.Frame(canvas)

window_id = canvas.create_window(
    (0, 0),
    window=scroll_frame,
    anchor="nw"
)

def on_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))
    canvas.itemconfig(window_id, width=event.width)

scroll_frame.bind("<Configure>", on_configure)

canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")
canvas.bind("<Configure>", lambda e: canvas.itemconfig(window_id, width=e.width))

def _on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def _bind_mousewheel(event):
    canvas.bind_all("<MouseWheel>", _on_mousewheel)


def _unbind_mousewheel(event):
    canvas.unbind_all("<MouseWheel>")

canvas.bind("<Enter>", _bind_mousewheel)
canvas.bind("<Leave>", _unbind_mousewheel)

# =========================================================
# HELPERS
# =========================================================

def choose_file(var, title, folder, filetypes):
    path = filedialog.askopenfilename(
        title=title,
        initialdir=folder,
        filetypes=filetypes
    )
    if path:
        var.set(path)


def load_aera_fields():
    path = catalog_var.get()

    if not path:
        messagebox.showerror("Erreur", "Sélectionne un catalogue géographique")
        return

    try:
        gdf = gpd.read_file(path)
        fields = [c for c in gdf.columns if c != "geometry"]

        field_dropdown["values"] = fields

        if fields:
            field_var.set(fields[0])

        messagebox.showinfo(
            "OK",
            f"{len(fields)} champs détectés dans le catalogue"
        )

    except Exception as e:
        messagebox.showerror("Erreur", str(e))


def run_pipeline():

    if not output_var.get() or not grid_var.get() or not m3_var.get():
        messagebox.showerror("Erreur", "Output, grille et M3 sont obligatoires")
        return

    cmd = [
        "python",
        "main.py",
        "--output", output_var.get(),
        "--grid", grid_var.get(),
        "--m3", m3_var.get(),
        "--catalog", catalog_var.get(),
        "--aera-field", field_var.get(),
        "--from-step", step_var.get()
    ]

    if clean_var.get():
        cmd.append("--clean")

    try:
        subprocess.run(cmd, check=True)
        messagebox.showinfo("Succès", "Pipeline terminé")

    except subprocess.CalledProcessError:
        messagebox.showerror("Erreur", "Échec du pipeline")


# =========================================================
# CARD FACTORY (AVEC TEXTE AIDE)
# =========================================================

def card(title, help_text):
    frame = ttk.LabelFrame(scroll_frame, text=title, padding=12)
    frame.pack(fill="x", expand=True, padx=15, pady=8)

    label = ttk.Label(
        frame,
        text=help_text,
        foreground=SUBTEXT,
        wraplength=650,  
        justify="left"
    )
    label.pack(fill="x", pady=(0, 10))

    return frame

# =========================================================
# HEADER
# =========================================================

ttk.Label(
    scroll_frame,
    text="Stade de Pratique",
    font=("Segoe UI", 16, "bold")
).pack(pady=(15, 0))

ttk.Label(
    scroll_frame,
    text="Pipeline de génération réseau + analyse géographique",
    foreground=SUBTEXT
).pack(pady=(0, 10))


# =========================================================
# OUTPUT
# =========================================================

f = card(
    "📁 Dossier de sortie",
    "Choisis le dossier où seront exportés tous les résultats du pipeline."
)

ttk.Entry(f, textvariable=output_var).pack(fill="x", expand=True)


# =========================================================
# GRID
# =========================================================

f = card(
    "🗺️ Grille",
    "Sélectionne la grille spatiale (GeoJSON) utilisée pour découper les données."
)

ttk.Entry(f, textvariable=grid_var).pack(fill="x", expand=True)

ttk.Button(
    f,
    text="Parcourir",
    command=lambda: choose_file(
        grid_var,
        "Grille",
        DIR_GRID,
        [("GeoJSON", "*.geojson")]
    )
).pack(pady=5)


# =========================================================
# M3
# =========================================================

f = card(
    "📦 M3",
    "Sélectionne le fichier M3 contenant les données réseau initiales."
)

ttk.Entry(f, textvariable=m3_var).pack(fill="x", expand=True)

ttk.Button(
    f,
    text="Parcourir",
    command=lambda: choose_file(
        m3_var,
        "M3",
        DIR_M3,
        [("GeoPackage", "*.gpkg")]
    )
).pack(pady=5)


# =========================================================
# CATALOGUE
# =========================================================

f = card(
    "🌍 Catalogue géographique",
    "Choisis la couche géographique (EPCI, communes, etc.) pour l’analyse AERA."
)

ttk.Entry(f, textvariable=catalog_var).pack(fill="x", expand=True)

ttk.Button(
    f,
    text="Parcourir",
    command=lambda: choose_file(
        catalog_var,
        "Catalogue",
        DIR_CATALOG,
        [("GeoJSON", "*.geojson")]
    )
).pack(pady=5)

ttk.Button(
    f,
    text="Charger les champs",
    command=load_aera_fields
).pack(pady=5)


# =========================================================
# FIELD
# =========================================================

f = card(
    "🏷️ Champ attributaire",
    "Sélectionne le champ utilisé comme identifiant (nom des entités)."
)

field_dropdown = ttk.Combobox(
    f,
    textvariable=field_var,
    state="readonly"
)
field_dropdown.pack(fill="x", expand=True)


# =========================================================
# OPTIONS
# =========================================================

f = card(
    "⚙️ Options d'exécution",
    "Choisis le point de reprise et les options du pipeline."
)

ttk.OptionMenu(
    f,
    step_var,
    step_var.get(),
    "step1",
    "step7",
    "step8",
    "merge",
    "aera"
).pack(anchor="w")

ttk.Checkbutton(
    f,
    text="Nettoyer les outputs avant exécution",
    variable=clean_var
).pack(anchor="w", pady=5)


# =========================================================
# RUN
# =========================================================

ttk.Button(
    scroll_frame,
    text="Calcul du stade",
    style="Accent.TButton",
    command=run_pipeline
).pack(pady=20)


# =========================================================
# START
# =========================================================

root.mainloop()