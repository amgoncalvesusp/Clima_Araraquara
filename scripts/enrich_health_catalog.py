"""Enriches the human-facing health catalog without changing the analysis GeoJSON."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "unidades_saude_araraquara.json"
METADATA = DATA / "metadata_unidades_saude_araraquara.json"
PENDING = DATA / "unidades_sugeridas_araraquara.json"


def load_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def enrich_catalog():
    current = load_json(CATALOG)
    metadata = load_json(METADATA)
    pending = load_json(PENDING)

    enriched_current = []
    for item in current:
        item_metadata = metadata.get(item["id"], {})
        enriched_current.append(
            {
                **item,
                "record_status": "analisado",
                "network_scope": item_metadata.get("network_scope", "municipal"),
                "data_quality": item_metadata.get("data_quality", "ok"),
                "canonical_name": item_metadata.get("canonical_name", item["name"]),
                "quality_note": item_metadata.get(
                    "quality_note", "Registro com métricas espaciais calculadas."
                ),
            }
        )

    pending_records = [
        {
            **item,
            "record_status": "pendente_validacao",
            "network": "Rede pública municipal — cadastro a validar",
            "data_quality": "pendente",
            "canonical_name": item["name"],
            "quality_note": item["next_step"],
        }
        for item in pending
    ]

    with CATALOG.open("w", encoding="utf-8") as file:
        json.dump(enriched_current + pending_records, file, ensure_ascii=False, indent=2)
        file.write("\n")


if __name__ == "__main__":
    enrich_catalog()
    print(f"Catálogo enriquecido: {CATALOG}")
