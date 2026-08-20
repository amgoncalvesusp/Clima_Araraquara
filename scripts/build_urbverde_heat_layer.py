"""Download and build the UrbVerde 2021 surface-temperature layer."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import mapbox_vector_tile
import requests
from shapely.geometry import shape, mapping
from shapely.ops import unary_union


CITY_CODE = "3503208"
YEAR = 2021
ZOOM = 10
EXTENT = 4096
TILE_URL = "https://urbverde.iau.usp.br/dados/public.geodata_temperatura_por_setor_{year}/{z}/{x}/{y}.pbf"
SOURCE_URL = (
    "https://urbverde.iau.usp.br/mapa?code=3503208&viewMode=map&type=city&year=2021&"
    "category=climate&layer=surface_temp&scale=intraurbana"
)


def tile_xy(lon: float, lat: float) -> tuple[int, int]:
    n = 2**ZOOM
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def tile_geometry(geometry: dict, tile_x: int, tile_y: int) -> dict:
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


def boundary_tile_range(boundary: dict) -> set[tuple[int, int]]:
    points = []

    def visit(value):
        if isinstance(value, list) and len(value) == 2 and all(isinstance(item, (int, float)) for item in value):
            points.append(value)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for feature in boundary["features"]:
        visit(feature["geometry"]["coordinates"])
    tile_points = [tile_xy(float(lon), float(lat)) for lon, lat in points]
    min_x, max_x = min(item[0] for item in tile_points), max(item[0] for item in tile_points)
    min_y, max_y = min(item[1] for item in tile_points), max(item[1] for item in tile_points)
    return {(x, y) for x in range(min_x, max_x + 1) for y in range(min_y, max_y + 1)}


def build_layer(boundary_geojson: Path, output: Path) -> None:
    boundary = json.loads(boundary_geojson.read_text(encoding="utf-8"))
    sectors: dict[str, dict] = {}
    session = requests.Session()
    session.headers.update({"User-Agent": "PETClimaAraraquara/1.0 (open data research)"})
    for tile_x, tile_y in sorted(boundary_tile_range(boundary)):
        url = TILE_URL.format(year=YEAR, z=ZOOM, x=tile_x, y=tile_y)
        response = session.get(url, timeout=60)
        response.raise_for_status()
        if not response.content:
            continue
        decoded = mapbox_vector_tile.decode(response.content)
        for layer in decoded.values():
            for feature in layer.get("features", []):
                properties = feature.get("properties", {})
                if str(properties.get("cd_mun")) != CITY_CODE or "c3" not in properties:
                    continue
                sector_id = str(properties["cd_setor"])
                geometry = shape(tile_geometry(feature["geometry"], tile_x, tile_y))
                current = sectors.get(sector_id)
                sectors[sector_id] = (
                    {"geometry": geometry, "properties": properties}
                    if current is None
                    else {"geometry": unary_union([current["geometry"], geometry]), "properties": current["properties"]}
                )

    features = []
    for sector_id, item in sorted(sectors.items()):
        properties = item["properties"]
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(item["geometry"]),
                "properties": {
                    "id": f"URBVERDE-{YEAR}-{sector_id}",
                    "sector_id": sector_id,
                    "year": YEAR,
                    "surface_temp": round(float(properties["c3"]), 2),
                    "surface_temp_rank": properties.get("c3_rank_setor"),
                    "dataset": f"public.geodata_temperatura_por_setor_{YEAR}",
                    "city": "Araraquara",
                    "ibge_code": int(CITY_CODE),
                    "source": "UrbVerde",
                    "source_url": SOURCE_URL,
                    "layer_role": "visualização/histórico; não altera o IECE",
                },
            }
        )

    if not features:
        raise ValueError("A UrbVerde não retornou setores de Araraquara para 2021.")
    result = {
        "type": "FeatureCollection",
        "name": "Ilhas de calor — UrbVerde Araraquara 2021",
        "metadata": {
            "city": "Araraquara",
            "ibge_code": int(CITY_CODE),
            "year": YEAR,
            "dataset": f"public.geodata_temperatura_por_setor_{YEAR}",
            "source": "UrbVerde",
            "source_url": SOURCE_URL,
            "tile_url": TILE_URL,
            "count_sectors": len(features),
            "metric": "c3",
            "metric_label": "Temperatura de superfície",
            "index_note": "Camada adicional de leitura histórica; o IECS continua usando a base climática principal publicada.",
        },
        "features": features,
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Camada UrbVerde 2021 escrita: {output} ({len(features)} setores)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_layer(args.boundary, args.output)


if __name__ == "__main__":
    main()
