"""Download the official flood-susceptibility zones of Araraquara from the SGB/CPRM WFS.

The municipal bulletin published by the Defesa Civil lists point locations only.
The continuous "risk zones" cited in the bulletin come from the national charts
"Cartas de Suscetibilidade a Movimentos Gravitacionais de Massa e Inundacoes",
produced by the Servico Geologico do Brasil (SGB-CPRM) and validated in the field.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests
from shapely.geometry import mapping, shape
from shapely.validation import make_valid


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "suscetibilidade_hidrica_araraquara.geojson"
WFS_URL = "https://geoservicos.sgb.gov.br/geoserver/ows"
CITY = "ARARAQUARA"
SOURCE_URL = "https://www.sgb.gov.br/sao-paulo-cartografia-de-suscetibilidade"
# Tolerance in degrees. 0.00005 deg is roughly 5 m, well below the 1:25.000
# plotting accuracy of the published charts, so the drawing stays faithful.
SIMPLIFY_TOLERANCE = 0.00005
PROCESSES = [
    ("suscet_inundacao", "Inundação"),
    ("suscet_enxurrada", "Enxurrada"),
]
CLASS_ORDER = {"Alta": 3, "Média": 2, "Baixa": 1}
CLASS_NOTE = {
    "Alta": "Terreno plano e baixo, colado à drenagem: a água chega primeiro e demora a escoar.",
    "Média": "Terreno de transição entre a planície e as partes altas: pode alagar em chuvas fortes.",
    "Baixa": "Terreno mais alto em relação à planície ou próximo à cabeceira do córrego.",
}


def fetch_layer(session: requests.Session, layer: str) -> list[dict]:
    response = session.get(
        WFS_URL,
        params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": f"gestao-territorial:{layer}",
            "outputFormat": "application/json",
            "CQL_FILTER": f"municipio ILIKE '{CITY}'",
        },
        timeout=300,
    )
    response.raise_for_status()
    return response.json().get("features", [])


def build_layer(output: Path) -> None:
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "RiscoEducacaoAraraquara/1.0 (open data research)"}
    )

    features = []
    processes_found = []
    for layer, process_label in PROCESSES:
        raw = fetch_layer(session, layer)
        if not raw:
            continue
        processes_found.append(process_label)
        for item in raw:
            properties = item.get("properties", {})
            geometry = shape(item["geometry"])
            if not geometry.is_valid:
                geometry = make_valid(geometry)
            geometry = geometry.simplify(SIMPLIFY_TOLERANCE)
            if geometry.is_empty:
                continue
            level = str(properties.get("classe", "")).strip()
            features.append(
                {
                    "type": "Feature",
                    "geometry": mapping(geometry),
                    "properties": {
                        "id": f"SUSC-{layer.replace('suscet_', '').upper()}-{level.upper()}",
                        "process": process_label,
                        "level": level,
                        "level_order": CLASS_ORDER.get(level, 0),
                        "level_label": f"Suscetibilidade {level.lower()} a {process_label.lower()}",
                        "plain_language": CLASS_NOTE.get(level, ""),
                        "area_km2": properties.get("area_km2"),
                        "year": properties.get("ano"),
                        "executor": properties.get("executor"),
                        "project": properties.get("projeto"),
                        "terrain_note": properties.get("obs"),
                        "source": "SGB-CPRM · Carta de Suscetibilidade",
                        "source_url": SOURCE_URL,
                        "layer_role": "leitura territorial; não altera o IECE",
                    },
                }
            )

    if not features:
        raise ValueError(
            "O WFS do SGB não retornou zonas de suscetibilidade para Araraquara."
        )

    features.sort(key=lambda item: item["properties"]["level_order"])
    missing = [label for _, label in PROCESSES if label not in processes_found]
    result = {
        "type": "FeatureCollection",
        "name": "Zonas de suscetibilidade hídrica — SGB/CPRM Araraquara",
        "metadata": {
            "city": "Araraquara",
            "source": "Serviço Geológico do Brasil (SGB-CPRM)",
            "source_url": SOURCE_URL,
            "service_url": WFS_URL,
            "processes_published": processes_found,
            "processes_without_zone": missing,
            "count_zones": len(features),
            "simplify_tolerance_deg": SIMPLIFY_TOLERANCE,
            "interpretation": (
                "Mancha contínua de propensão natural do terreno a inundar. "
                "Indica onde a água tende a chegar e se acumular, não a garantia de que "
                "um evento vai ocorrer nem a data em que ele ocorreria."
            ),
            "index_note": "Camada de leitura territorial. Não entra no cálculo do IECE.",
        },
        "features": features,
    }
    output.write_text(json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Zonas de suscetibilidade escritas: {output} ({len(features)} zonas)")
    if missing:
        print(f"Sem zona publicada para: {', '.join(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    build_layer(args.output)


if __name__ == "__main__":
    main()
