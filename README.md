**Stade de Pratique — Pipeline de Génération et d’Analyse de Réseau**

Stade de Pratique est un pipeline SIG Python permettant de :

- générer automatiquement un réseau géographique à partir de flux linéaires M3,
- découper et nettoyer ce réseau par tuiles,
- reconstruire des lignes fusionnées et lissées,
- produire un réseau final homogène,
- calculer des statistiques kilométriques par entité géographique(EPCI, départements, régions, massifs forestiers, etc.).

Le projet repose sur :
- GeoPandas
- Shapely
- Tkinter
- Joblib
- tqdm
- des traitements spatiaux optimisés pour de gros volumes de données SIG.

**Fonctionnalités principales**

Le pipeline :
- découpe les données en tuiles,
- génère des buffers,
- produit des lignes Voronoï,
- extrait les sommets,
- découpe les segments,
- reconstruit les lignes finales.

Cela permet :
- de reprendre un calcul interrompu,
- de tester une étape spécifique,
- d’éviter de relancer l’ensemble du pipeline.
- gestion via Interface graphique Tkinter

l'UI Tkinter permet de  :
- sélectionner les fichiers d’entrée,
- choisir le dossier output,
- charger le catalogue géographique,
- sélectionner dynamiquement le champ attributaire,
- activer le nettoyage des outputs,
- reprendre le pipeline à une étape donnée,
- lancer le calcul sans ligne de commande.
- Analyse géographique

Le module geo_analysis.py permet de :
- découper spatialement le réseau par entité,
- calculer les kilomètres de réseau,
- agréger les résultats,
- exporter :
    - un GeoJSON enrichi,
    - un CSV de synthèse.

Compatible avec :
- EPCI,
- départements,
- régions,
- zones naturelles,
- catalogues géographiques personnalisés (formats geojson)

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

Prérequis
Python

Compatible :
- Python 3.10+
recommandé : Python 3.13

Libraries utilisées
- GeoPandas
- Shapely
- Fiona
- PyProj
- Rtree
- Joblib
- Tkinter
- tqdm

Installation complète
Clone du projet : git clone [https://github.com/RemyDem22/Stade-de-Pratique.git

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

