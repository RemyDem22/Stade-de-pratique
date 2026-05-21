# Outdoorvision
Pipeline de traitement géospatial des discontinuités linéaires

# Installer les dépendances
Le code s'éxecute dans un environnement Pyhton, avec les librairies suivantes via la commande :
pip install -r requirements.txt

# Structure du projet
project/
│
├── data/                  # Données d’entrée
├── output/                # Résultats générés
│
├── step1_*.py
├── step2_*.py
├── step3_*.py
├── ...
├── step8_buffer.py
│
├── requirements.txt
│
└── README.md

# Formats supportés
GeoPackage (.gpkg)
GeoJSON (.geojson)

# Développeur
Rémy Demulier - Pôle Ressource National Transition Écologique et Sports de Nature
