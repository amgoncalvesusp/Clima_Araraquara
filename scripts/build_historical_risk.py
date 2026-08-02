"""Downloads UrbVerde sector tiles and builds a reproducible health-unit time series."""

import json
import math
from pathlib import Path

import mapbox_vector_tile
import requests
from shapely.geometry import Point, shape
from shapely.ops import transform, unary_union


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
UNITS = DATA / "unidades_saude_araraquara.geojson"
OUTPUT = DATA / "historico_risco_termico_araraquara.json"
YEARS = tuple(range(2016, 2022))
CITY_CODE = "3503208"
ZOOM = 10
EXTENT = 4096
BUFFER_METERS = 300
TILE_URL = "https://urbverde.iau.usp.br/dados/public.geodata_temperatura_por_setor_{year}/{z}/{x}/{y}.pbf"
USER_AGENT = "PETClima/1.0 (open data research)"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def tile_xy(lon, lat):
    n = 2**ZOOM
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def tile_geometry(geometry, tile_x, tile_y):
    n = 2**ZOOM

    def convert(value):
        if isinstance(value[0], (int, float)):
            world_x = tile_x + value[0] / EXTENT
            world_y = tile_y + value[1] / EXTENT
            lon = world_x / n * 360 - 180
            lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * world_y / n))))
            return [lon, lat]
        return [convert(item) for item in value]

    return {"type": geometry["type"], "coordinates": convert(geometry["coordinates"])}


def projection(lat0):
    meters_per_degree = 111_320
    lon_scale = meters_per_degree * math.cos(math.radians(lat0))

    def project(x, y, z=None):
        return x * lon_scale, y * meters_per_degree

    return project


def fetch_sector_geometries(year, tiles, project):
    sectors = {}
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    for tile_x, tile_y in tiles:
        url = TILE_URL.format(year=year, z=ZOOM, x=tile_x, y=tile_y)
        response = session.get(url, timeout=60)
        response.raise_for_status()
        if not response.content:
            continue
        decoded = mapbox_vector_tile.decode(response.content)
        for layer in decoded.values():
            for feature in layer.get("features", []):
                properties = feature.get("properties", {})
                if str(properties.get("cd_mun")) != CITY_CODE:
                    continue
                sector_id = str(properties["cd_setor"])
                geometry = transform(
                    project,
                    shape(tile_geometry(feature["geometry"], tile_x, tile_y)),
                )
                current = sectors.get(sector_id)
                if current is None:
                    sectors[sector_id] = {"geometry": geometry, "properties": properties}
                else:
                    sectors[sector_id] = {
                        "geometry": unary_union([current["geometry"], geometry]),
                        "properties": current["properties"],
                    }
    return sectors


def summarize_unit(unit, sectors, project):
    properties = unit["properties"]
    point = Point(*project(properties["lon"], properties["lat"]))
    buffer = point.buffer(BUFFER_METERS)
    intersections = []
    for sector in sectors.values():
        overlap = sector["geometry"].intersection(buffer)
        if overlap.area > 0:
            intersections.append((overlap.area, sector["properties"]))
    total_area = sum(area for area, _ in intersections)
    if not total_area:
        return {
            "surface_temp_max_300m": None,
            "sector_count": 0,
            "coverage": "sem_intersecao",
        }
    value = sum(area * float(props["c3"]) for area, props in intersections) / total_area
    return {
        "surface_temp_max_300m": round(value, 2),
        "sector_count": len(intersections),
        "coverage": "intersecao_buffer_300m",
    }


def main():
    units = load_json(UNITS)["features"]
    coordinates = [(unit["properties"]["lon"], unit["properties"]["lat"]) for unit in units]
    tiles = {
        tile_xy(lon, lat)
        for lon, lat in coordinates
    }
    center_lat = sum(lat for _, lat in coordinates) / len(coordinates)
    project = projection(center_lat)
    unit_series = {unit["properties"]["id"]: [] for unit in units}
    summary = []

    for year in YEARS:
        sectors = fetch_sector_geometries(year, tiles, project)
        values = []
        for unit in units:
            metric = summarize_unit(unit, sectors, project)
            unit_series[unit["properties"]["id"]].append({"year": year, **metric})
            if metric["surface_temp_max_300m"] is not None:
                values.append(metric["surface_temp_max_300m"])
        summary.append(
            {
                "year": year,
                "unit_count": len(values),
                "mean_surface_temp_max_300m": round(sum(values) / len(values), 2),
                "min_surface_temp_max_300m": round(min(values), 2),
                "max_surface_temp_max_300m": round(max(values), 2),
            }
        )

    output = {
        "city": "Araraquara",
        "ibge_code": int(CITY_CODE),
        "source": "UrbVerde — geodata_temperatura_por_setor",
        "source_url": "https://urbverde.iau.usp.br/",
        "source_layer_template": "public.geodata_temperatura_por_setor_{year}",
        "metric": "c3",
        "metric_label": "Temperatura máxima da superfície — média ponderada no buffer de 300m",
        "history_years": list(YEARS),
        "latest_map_year": 2024,
        "buffer_radius_meters": BUFFER_METERS,
        "note": "O mapa atual continua mostrando a camada local de 2024; os gráficos históricos usam a série setorial UrbVerde disponível de 2016 a 2021.",
        "summary": summary,
        "units": [
            {
                "id": unit["properties"]["id"],
                "name": unit["properties"]["name"],
                "suburb": unit["properties"].get("suburb", "Araraquara"),
                "values": unit_series[unit["properties"]["id"]],
            }
            for unit in units
        ],
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Histórico UrbVerde escrito: {OUTPUT}")


if __name__ == "__main__":
    main()
