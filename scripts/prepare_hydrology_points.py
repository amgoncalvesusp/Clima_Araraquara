"""Attach the official star classification to the municipal hydrology points."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "pontos_risco_hidrologico_araraquara.geojson"
SOURCE_URL = (
    "https://ecrie.com.br/sistema/conteudos/arquivo/a_286_0_1_22012026101246.pdf"
)

SOURCE_DATE = "2026-01-22"

CLASSIFICATION = {
    "*": ("risco_atenuado", "Risco atenuado por obras estruturais", 30),
    "**": ("obras_em_execucao", "Obras estruturais em execução", 35),
    "***": ("sem_intervencao", "Sem intervenção", 35),
}
EXPECTED_IDS = {f"HIDRO-{index:02d}" for index in range(1, 24)}


def main() -> None:
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    features = data["features"]
    ids = [feature["properties"]["id"] for feature in features]
    if set(ids) != EXPECTED_IDS or len(ids) != len(set(ids)):
        raise ValueError(
            "O boletim deve estar representado uma única vez por cada ID HIDRO-01…HIDRO-23."
        )

    for feature in features:
        properties = feature["properties"]
        code = properties["intervention_code"]
        key, label, share = CLASSIFICATION[code]
        properties.update(
            {
                "classification": key,
                "classification_label": label,
                "classification_share_pct": share,
                "source_url": SOURCE_URL,
                "source_date": SOURCE_DATE,
            }
        )

    data["metadata"].update(
        {
            "source_url": SOURCE_URL,
            "source_date": SOURCE_DATE,
            "classification_legend": {
                key: {"label": label, "share_pct": share}
                for key, label, share in CLASSIFICATION.values()
            },
            "classification_note": "Asteriscos do boletim: * risco atenuado por obras estruturais; ** obras estruturais em execução; *** sem intervenção.",
            "deduplication_note": "Os 23 IDs publicados foram mantidos uma única vez. HIDRO-16 e HIDRO-17 são pontos distintos do boletim, apesar de compartilharem o mesmo eixo rodoviário.",
        }
    )
    data["metadata"]["count_geocoded_for_map"] = sum(
        feature["geometry"] is not None for feature in features
    )
    data["metadata"]["count_by_classification"] = dict(
        Counter(
            properties["classification"]
            for properties in (feature["properties"] for feature in features)
        )
    )
    OUTPUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Pontos hidrológicos preparados: {OUTPUT} ({len(features)} registros únicos)"
    )


if __name__ == "__main__":
    main()
