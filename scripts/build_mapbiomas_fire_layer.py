"""Build the Araraquara-only MapBiomas Fogo annual layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import mapping


SOURCE_PAGE = "https://brasil.mapbiomas.org/mapbiomas-fogo/"
DOWNLOAD_URL = (
    "https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/"
    "collection_10/fire-col5/annual_burned_vectors_v1/"
    "mapbiomas_fire_collection5_burned_area_2025.zip"
)
YEAR = 2025


def build_layer(source_shp: Path, boundary_geojson: Path, output: Path) -> None:
    scars = gpd.read_file(source_shp)
    boundary = gpd.read_file(boundary_geojson)
    if scars.crs is None:
        raise ValueError("O shapefile do MapBiomas não informa o CRS.")
    scars = scars.to_crs(boundary.crs)
    clipped = gpd.clip(scars, boundary)
    clipped = clipped[clipped.geometry.notna() & ~clipped.geometry.is_empty].copy()
    if clipped.empty:
        raise ValueError("Nenhuma cicatriz de fogo intersectou o município de Araraquara.")

    metric = clipped.to_crs("EPSG:31983")
    clipped["burned_area_ha"] = (metric.geometry.area / 10_000).round(2).to_list()
    clipped = clipped.sort_values("id")

    features = []
    for row in clipped.itertuples(index=False):
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(row.geometry),
                "properties": {
                    "id": f"MBFOGO-{YEAR}-{int(row.id)}",
                    "year": YEAR,
                    "burned_area_ha": float(row.burned_area_ha),
                    "product": "Área queimada anual",
                    "collection": "MapBiomas Fogo Coleção 5",
                    "resolution_m": 30,
                    "source": "MapBiomas Fogo",
                    "source_url": SOURCE_PAGE,
                    "download_url": DOWNLOAD_URL,
                    "layer_role": "visualização adicional; não entra no IECE",
                },
            }
        )

    result = {
        "type": "FeatureCollection",
        "name": "Cicatrizes de fogo de Araraquara — MapBiomas Fogo Coleção 5",
        "metadata": {
            "city": "Araraquara",
            "ibge_code": 3503208,
            "year": YEAR,
            "collection": "MapBiomas Fogo Coleção 5",
            "product": "Área queimada anual em formato vetorial",
            "source_url": SOURCE_PAGE,
            "download_url": DOWNLOAD_URL,
            "boundary_source": "IBGE malha municipal 3503208",
            "count_scar_polygons": len(features),
            "resolution_m": 30,
            "method_note": "Cicatrizes anuais derivadas de imagens Landsat e classificação do MapBiomas.",
            "index_note": "Camada de contexto territorial. Não é componente do IECE nesta versão.",
        },
        "features": features,
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Camada MapBiomas Fogo escrita: {output} ({len(features)} polígonos)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-shp", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_layer(args.source_shp, args.boundary, args.output)


if __name__ == "__main__":
    main()
