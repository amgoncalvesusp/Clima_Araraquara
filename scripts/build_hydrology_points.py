"""Builds the Araraquara hydrology-risk point layer from the municipal bulletin."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "pontos_risco_hidrologico_araraquara.geojson"
SOURCE_URL = (
    "https://ecrie.com.br/sistema/conteudos/arquivo/a_138_0_1_11112025143530.pdf"
)


# The bulletin publishes streets/intersections, not official coordinates. Coordinates
# below are deliberately marked as approximate street-axis geocodes for orientation.
POINTS = [
    ("01", "Av. Manoel de Abreu — Jardim Zavanella", "Alagamento", "*", -21.7520278, -48.1362711),
    ("02", "Av. Prof. Gustavo Fleury Charmillot — Residencial Paraíso", "Alagamento", "*", -21.7637873, -48.1911453),
    ("03", "Av. Francisco Vaz Filho — Jardim América", "Alagamento", "*", -21.7691842, -48.1399171),
    ("04", "Ponte da Nestlé — Av. Mário Zampieri — Parque Alvorada", "Alagamento", "**", -21.7972662, -48.1598925),
    ("05", "Av. Dr. Seth-Hur Cardoso — Vila Nossa Senhora Aparecida", "Alagamento", "*", -21.8015118, -48.1249474),
    ("06", "Av. Eng. Camillo Dinucci / Av. Ermano Biancardi — Jardim Arco-Íris", "Alagamento", "*", -21.8092575, -48.1531728),
    ("07", "Av. Prof. Jorge Corrêa — Vila Santana", "Enxurrada", "**", -21.7830783, -48.1848305),
    ("08", "Rua Napoleão Selmi Dei / Rua Henrique Lupo — Vila Harmonia", "Inundação", "***", -21.7707294, -48.1711720),
    ("09", "Av. Pe. Francisco Sales Colturato / Rua Heitor Souza Pinheiro — Jardins dos Manacás", "Inundação", "***", -21.7813346, -48.1884224),
    ("10", "Estrada Abílio Augusto Corrêa — Bairro dos Machados", "Inundação", "***", None, None),
    ("11", "Rua Imaculada Conceição — Jardim Tamoio", "Inundação", "***", -21.7883005, -48.1869424),
    ("12", "Av. Maria Antônia Camargo de Oliveira — Centro", "Inundação", "***", -21.7950, -48.1770),
    ("13", "Av. Maria Antônia Camargo de Oliveira — Vila Melhado", "Inundação", "***", -21.7995008, -48.1730939),
    ("14", "Rua Pe. José de Anchieta — Suconasa", "Inundação", "***", None, None),
    ("15", "Rua Maurício Galli", "Inundação / Assoreamento", "*", -21.7511581, -48.1627006),
    ("16", "Rodovia Abdo Najn — acesso à SP-255", "Inundação", "*", -21.7902864, -48.1380062),
    ("17", "Rodovia Abdo Najn — acesso à SP-255", "Inundação", "*", -21.7933516, -48.1335823),
    ("18", "Rua Tirso Alves Corrêa — Parque Tropical", "Solapamento de margens fluvial", "*", -21.7539009, -48.2153520),
    ("19", "Av. José Barbieri Neto — trecho DAAE / Auto Posto Flora", "Enxurrada", "**", -21.7584173, -48.1792292),
    ("20", "Rua Dr. Giuseppe Aufiero Sobrinho — Jardim Nova Araraquara", "Enxurrada", "**", -21.7821833, -48.2050730),
    ("21", "Av. José Barbanti Neto — Jardim Nova Araraquara", "Enxurrada", "**", None, None),
    ("22", "Rua Nove de Julho", "Inundação", "**", -21.7694052, -48.1808032),
    ("23", "Rua Armando Sales de Oliveira", "Inundação", "**", -21.7737210, -48.1896456),
]


def main():
    features = []
    for point_id, name, phenomenon, code, lat, lon in POINTS:
        features.append(
            {
                "type": "Feature",
                "geometry": None
                if lat is None or lon is None
                else {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "id": f"HIDRO-{point_id}",
                    "name": name,
                    "phenomenon": phenomenon,
                    "intervention_code": code,
                    "coordinate_status": "aproximada"
                    if lat is not None
                    else "pendente_geocodificacao",
                    "coordinate_note": "Eixo viário aproximado; o boletim publica endereço/interseção, não coordenada oficial."
                    if lat is not None
                    else "Ponto presente no boletim municipal, ainda sem coordenada usada no mapa.",
                    "source_url": SOURCE_URL,
                    "source_date": "2025-11-11",
                },
            }
        )
    payload = {
        "type": "FeatureCollection",
        "name": "Pontos de risco hidrológico de Araraquara",
        "metadata": {
            "source": "Prefeitura de Araraquara / Defesa Civil Municipal",
            "source_url": SOURCE_URL,
            "source_date": "2025-11-11",
            "count_published": len(POINTS),
            "count_geocoded_for_map": sum(point[4] is not None for point in POINTS),
            "interpretation": "Pontos mapeados de alagamento, inundação e enxurrada; não são uma mancha contínua de inundação.",
        },
        "features": features,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Pontos hidrológicos escritos: {OUTPUT}")


if __name__ == "__main__":
    main()
