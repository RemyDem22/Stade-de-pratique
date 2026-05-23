# Stade de Pratique — Pipeline de Génération et d’Analyse de Réseau

### Stade de Pratique est un pipeline SIG Python permettant de :

- générer automatiquement un réseau géographique à partir de flux linéaires M3,
- découper et nettoyer ce réseau par tuiles,
- reconstruire des lignes fusionnées et lissées,
- produire un réseau final homogène,
- calculer des statistiques kilométriques par entité géographique(EPCI, départements, régions, massifs forestiers, etc.).


**Fonctionnalités principales**

Le pipeline :
- Traite les segements M3 pour recréer un réseau simplfier
- Fusionne les tuiles générés
- Calcul le stade de km parcourus selon un catalogue géographique

**Structure du projet**

Stade-de-Pratique/
│
├── main.py
├── launcher.py
├── merge.py
├── network_aera.py
│
├── step1to6_processing.py
├── step7_split.py
├── step8_buffer.py
│
├── data/
│   ├── grid/
│   ├── m3/
│   └── catalogue_geographique/
│
└── output/

Installation complète
Clone du projet : git clone https://github.com/RemyDem22/Stade-de-Pratique.git
cd Stade-de-Pratique

Installation des dépendances
pip install geopandas shapely fiona pyproj rtree joblib tqdm pandas

Préparation des données
- Flux M3 À placer dans : data/ (Format : .gpkg)
- Grille de traitement : data/ (Format : .geojson)
- Catalogue géographique : catalogue_geographique/ (Formats : .geojson)
      - Exemples :
            - EPCI
            - départements
            - régions
            - massifs forestiers
            - bassins de vie

Projet développé dans le cadre d’expérimentations SIG et génération automatique de réseaux spatiaux.

