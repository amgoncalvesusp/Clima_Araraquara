"""Promotes the validated Santa Angelina clinic into the analyzed catalog."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "unidades_saude_araraquara.json"
PENDING = DATA / "unidades_sugeridas_araraquara.json"
RAW_GEOJSON = DATA / "unidades_saude_araraquara.geojson"
METADATA = DATA / "metadata_unidades_saude_araraquara.json"


SANTA_ANGELINA = {
    "id": "SUS-042",
    "name": "CMS Santa Angelina \"Rafael Sorbo\"",
    "type": "UBS / CMS (Unidade Básica)",
    "lat": -21.771494,
    "lon": -48.1878883,
    "address": "Rua Habbib Khodor, 560",
    "suburb": "Santa Angelina",
    "cnes": "2063247",
    "network": "Rede Pública SUS / Filantrópico",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def promote_catalog_record(catalog):
    promoted = []
    replaced_pending = False
    for item in catalog:
        if item["id"] == "PEND-006":
            promoted.append(SANTA_ANGELINA)
            replaced_pending = True
        elif item["id"] != SANTA_ANGELINA["id"]:
            promoted.append(item)
    if not replaced_pending and not any(item["id"] == "SUS-042" for item in promoted):
        promoted.append(SANTA_ANGELINA)
    return promoted


def promote_raw_geojson(raw_geojson):
    santa_feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [SANTA_ANGELINA["lon"], SANTA_ANGELINA["lat"]],
        },
        "properties": SANTA_ANGELINA,
    }
    features = [
        feature
        for feature in raw_geojson["features"]
        if feature["properties"].get("id") != SANTA_ANGELINA["id"]
    ]
    return {**raw_geojson, "features": [*features, santa_feature]}


def main():
    catalog = promote_catalog_record(load_json(CATALOG))
    pending = [item for item in load_json(PENDING) if item["id"] != "PEND-006"]
    metadata = {
        **load_json(METADATA),
        "SUS-042": {
            "network_scope": "municipal",
            "data_quality": "ok",
            "canonical_name": "CMS Santa Angelina \"Rafael Sorbo\"",
            "quality_note": "CNES, endereço e coordenada confirmados em fontes públicas.",
        },
    }
    write_json(CATALOG, catalog)
    write_json(PENDING, pending)
    write_json(METADATA, metadata)
    write_json(RAW_GEOJSON, promote_raw_geojson(load_json(RAW_GEOJSON)))
    print("CMS Santa Angelina promovido para SUS-042")


if __name__ == "__main__":
    main()
