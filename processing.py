import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon
from scipy.spatial import Voronoi
from shapely.ops import split
from shapely.geometry import MultiPoint
from tqdm import tqdm
from shapely.geometry import Polygon

BUFFER_DIST = 20
POINT_SPACING = 30

def process_tile(lines_gdf, verbose=False):

    if lines_gdf.empty:
        return gpd.GeoDataFrame()

    iterator = lines_gdf.geometry

    if verbose:
        iterator = tqdm(iterator, desc="Buffer en cours", leave=False)

    buffers = [geom.buffer(BUFFER_DIST, resolution=4) for geom in iterator]

    gdf = gpd.GeoDataFrame(geometry=buffers, crs=lines_gdf.crs)

    merged = gdf.unary_union

    return gpd.GeoDataFrame(geometry=[merged], crs=lines_gdf.crs)


def polygon_to_line(polygon_gdf):

    if polygon_gdf.empty:
        return gpd.GeoDataFrame()

    lines = polygon_gdf.boundary

    return gpd.GeoDataFrame(geometry=lines, crs=polygon_gdf.crs)


def lines_to_points(lines_gdf, distance=30):

    if lines_gdf.empty:
        return gpd.GeoDataFrame()

    points = []

    for geom in lines_gdf.geometry:

        if geom is None:
            continue

        length = geom.length

        # positions tous les X mètres
        distances = np.arange(0, length, distance)

        for d in distances:
            point = geom.interpolate(d)
            points.append(point)

    return gpd.GeoDataFrame(geometry=points, crs=lines_gdf.crs)


def create_voronoi(points_gdf, clip_gdf):
    if points_gdf.empty:
        return gpd.GeoDataFrame()

    coords = [(geom.x, geom.y) for geom in points_gdf.geometry]

    if len(coords) < 3:
        return gpd.GeoDataFrame()  # Voronoï impossible

    vor = Voronoi(coords)

    polygons = []

    for region_index in vor.point_region:
        region = vor.regions[region_index]

        if not region or -1 in region:
            continue  # ignore infini

        poly_coords = [vor.vertices[i] for i in region]
        polygon = Polygon(poly_coords)
        polygons.append(polygon)

    vor_gdf = gpd.GeoDataFrame(geometry=polygons, crs=points_gdf.crs)

    # 🔥 CLIP avec buffer
    clipped = gpd.overlay(vor_gdf, clip_gdf, how="intersection")

    return clipped


def extract_vertices(voronoi_gdf, buffer_gdf):


    if voronoi_gdf.empty:
        return gpd.GeoDataFrame()

    vertices = []

    for geom in voronoi_gdf.geometry:

        if geom is None:
            continue

        # gérer MultiPolygon
        if geom.geom_type == "Polygon":
            coords = geom.exterior.coords

            for x, y in coords:
                vertices.append((x, y))

        elif geom.geom_type == "MultiPolygon":
            for poly in geom.geoms:
                for x, y in poly.exterior.coords:
                    vertices.append((x, y))

    # création GeoDataFrame
    points = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(
            [x for x, y in vertices],
            [y for x, y in vertices]
        ),
        crs=voronoi_gdf.crs
    )

    # -----------------------------
    # CLIP avec buffer (équivalent sélection spatiale)
    # -----------------------------
    points = gpd.clip(points, buffer_gdf)

    # -----------------------------
    # SUPPRESSION DOUBLONS
    # -----------------------------
    points["coord"] = points.geometry.apply(
        lambda p: f"{round(p.x, 3)},{round(p.y, 3)}"
    )

    points = points.drop_duplicates(subset="coord")

    # garder uniquement géométrie
    points = points[["geometry"]]

    return points


def split_lines_with_points(lines_gdf, points_gdf):

    if lines_gdf.empty or points_gdf.empty:
        return gpd.GeoDataFrame()

    # union des points
    splitter = points_gdf.unary_union

    split_lines = []

    for line in lines_gdf.geometry:

        if line is None:
            continue

        try:
            result = split(line, splitter)

            for geom in result.geoms:
                split_lines.append(geom)

        except Exception:
            # si split échoue → garder ligne originale
            split_lines.append(line)

    return gpd.GeoDataFrame(geometry=split_lines, crs=lines_gdf.crs)