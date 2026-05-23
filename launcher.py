import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import geopandas as gpd


# =========================================================
# ROOT
# =========================================================

root = tk.Tk()
root.title("Stade de Pratique")
root.geometry("720x900")
root.configure(bg="#111315")

root.option_add("*Font", ("Segoe UI", 10))


# =========================================================
# STYLE
# =========================================================

style = ttk.Style()
style.theme_use("clam")

BG = "#111315"
CARD = "#1A1D21"
TEXT = "#EAECEF"
SUBTEXT = "#9CA3AF"
ACCENT = "#3B82F6"

style.configure(
    "Dark.TFrame",
    background=CARD
)

style.configure(
    "Dark.TLabel",
    background=CARD,
    foreground=TEXT,
    font=("Segoe UI", 10)
)

style.configure(
    "Title.TLabel",
    background=BG,
    foreground=TEXT,
    font=("Segoe UI", 20, "bold")
)

style.configure(
    "Subtitle.TLabel",
    background=BG,
    foreground=SUBTEXT,
    font=("Segoe UI", 10)
)

style.configure(
    "Dark.TButton",
    background=ACCENT,
    foreground="white",
    borderwidth=0,
    focusthickness=0,
    padding=8,
    font=("Segoe UI Semibold", 10)
)

style.map(
    "Dark.TButton",
    background=[("active", "#2563EB")]
)

style.configure(
    "Dark.TCheckbutton",
    background=CARD,
    foreground=TEXT
)

style.configure(
    "Dark.TMenubutton",
    background=CARD,
    foreground=TEXT
)


# =========================================================
# VARIABLES
# =========================================================

output_var = tk.StringVar()

grid_var = tk.StringVar()
m3_var = tk.StringVar()
catalog_var = tk.StringVar()

field_var = tk.StringVar()

clean_var = tk.BooleanVar()
step_var = tk.StringVar(value="step1")


# =========================================================
# PATHS
# =========================================================

BASE_DATA = os.path.join(os.getcwd(), "data")

DIR_M3 = os.path.join(BASE_DATA, "m3")
DIR_GRID = os.path.join(BASE_DATA, "grid")
DIR_CATALOG = os.path.join(BASE_DATA, "catalogue_geographique")


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
        messagebox.showerror(
            "Erreur",
            "Sélectionne un catalogue géographique"
        )
        return

    try:

        gdf = gpd.read_file(path)

        fields = [
            c for c in gdf.columns
            if c != "geometry"
        ]

        field_dropdown["values"] = fields

        if fields:
            field_var.set(fields[0])

    except Exception as e:
        messagebox.showerror("Erreur", str(e))


# =========================================================
# RUN PIPELINE
# =========================================================

def run_pipeline():

    output = output_var.get()
    grid = grid_var.get()
    m3 = m3_var.get()
    catalog = catalog_var.get()
    field = field_var.get()

    if not output or not grid or not m3:
        messagebox.showerror(
            "Erreur",
            "Output, grille et M3 obligatoires"
        )
        return

    cmd = [
        "python",
        "main.py",

        "--output", output,
        "--grid", grid,
        "--m3", m3,

        "--catalog", catalog,
        "--aera-field", field,

        "--from-step", step_var.get()
    ]

    if clean_var.get():
        cmd.append("--clean")

    try:

        subprocess.run(cmd, check=True)

        messagebox.showinfo(
            "Pipeline terminé",
            "Le traitement est terminé avec succès."
        )

    except subprocess.CalledProcessError:

        messagebox.showerror(
            "Erreur",
            "Erreur pendant l'exécution du pipeline."
        )


# =========================================================
# CARD COMPONENT
# =========================================================

def create_card(parent, title, subtitle=None):

    card = ttk.Frame(
        parent,
        style="Dark.TFrame",
        padding=20
    )

    card.pack(
        fill="x",
        padx=30,
        pady=10
    )

    ttk.Label(
        card,
        text=title,
        style="Dark.TLabel",
        font=("Segoe UI", 11, "bold")
    ).pack(anchor="w")

    if subtitle:
        ttk.Label(
            card,
            text=subtitle,
            style="Dark.TLabel",
            foreground=SUBTEXT
        ).pack(anchor="w", pady=(2, 10))

    return card


# =========================================================
# HEADER
# =========================================================

header = tk.Frame(root, bg=BG)
header.pack(fill="x", pady=(25, 10))

ttk.Label(
    header,
    text="Stade de Pratique",
    style="Title.TLabel"
).pack()

ttk.Label(
    header,
    text="Pipeline de génération et d’analyse réseau",
    style="Subtitle.TLabel"
).pack(pady=4)


# =========================================================
# OUTPUT
# =========================================================

card = create_card(
    root,
    "Dossier de sortie"
)

ttk.Entry(
    card,
    textvariable=output_var,
    width=90
).pack(fill="x", pady=(10, 0))


# =========================================================
# GRID
# =========================================================

card = create_card(
    root,
    "Import de la grille"
)

row = tk.Frame(card, bg=CARD)
row.pack(fill="x", pady=(10, 0))

ttk.Entry(
    row,
    textvariable=grid_var,
    width=75
).pack(side="left", padx=(0, 10))

ttk.Button(
    row,
    text="Choisir",
    style="Dark.TButton",
    command=lambda: choose_file(
        grid_var,
        "Choisir la grille",
        DIR_GRID,
        [("GeoJSON", "*.geojson")]
    )
).pack(side="left")


# =========================================================
# M3
# =========================================================

card = create_card(
    root,
    "Import du fichier M3"
)

row = tk.Frame(card, bg=CARD)
row.pack(fill="x", pady=(10, 0))

ttk.Entry(
    row,
    textvariable=m3_var,
    width=75
).pack(side="left", padx=(0, 10))

ttk.Button(
    row,
    text="Choisir",
    style="Dark.TButton",
    command=lambda: choose_file(
        m3_var,
        "Choisir le fichier M3",
        DIR_M3,
        [("GeoPackage", "*.gpkg")]
    )
).pack(side="left")


# =========================================================
# CATALOG
# =========================================================

card = create_card(
    root,
    "Choix du catalogue géographique"
)

row = tk.Frame(card, bg=CARD)
row.pack(fill="x", pady=(10, 0))

ttk.Entry(
    row,
    textvariable=catalog_var,
    width=60
).pack(side="left", padx=(0, 10))

ttk.Button(
    row,
    text="Choisir",
    style="Dark.TButton",
    command=lambda: choose_file(
        catalog_var,
        "Choisir le catalogue",
        DIR_CATALOG,
        [("GeoJSON", "*.geojson")]
    )
).pack(side="left")

ttk.Button(
    row,
    text="Charger les champs",
    style="Dark.TButton",
    command=load_aera_fields
).pack(side="left", padx=(10, 0))


# =========================================================
# FIELD
# =========================================================

card = create_card(
    root,
    "Choix du champ attributaire pour le nom"
)

field_dropdown = ttk.Combobox(
    card,
    textvariable=field_var,
    state="readonly",
    width=60
)

field_dropdown.pack(fill="x", pady=(10, 0))


# =========================================================
# OPTIONS
# =========================================================

card = create_card(
    root,
    "Options"
)

options_row = tk.Frame(card, bg=CARD)
options_row.pack(fill="x", pady=(10, 0))

ttk.Label(
    options_row,
    text="Reprendre depuis",
    style="Dark.TLabel"
).pack(side="left", padx=(0, 10))

ttk.OptionMenu(
    options_row,
    step_var,
    step_var.get(),
    "step1",
    "step7",
    "step8",
    "merge",
    "aera"
).pack(side="left")

ttk.Checkbutton(
    options_row,
    text="Clean",
    variable=clean_var,
    style="Dark.TCheckbutton"
).pack(side="left", padx=25)


# =========================================================
# RUN BUTTON
# =========================================================

run_frame = tk.Frame(root, bg=BG)
run_frame.pack(fill="x", pady=30)

launch_btn = tk.Button(
    run_frame,
    text="Lancer le pipeline",
    bg=ACCENT,
    fg="white",
    activebackground="#2563EB",
    activeforeground="white",
    relief="flat",
    font=("Segoe UI", 11, "bold"),
    padx=25,
    pady=12,
    command=run_pipeline
)

launch_btn.pack()


# =========================================================
# START
# =========================================================

root.mainloop()