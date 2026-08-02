"""Promotes pending health units after public-source validation.

The promotion list is intentionally explicit: each entry has a confirmed
municipal/CNES identity, address and usable coordinate. Items not meeting
that bar remain pending instead of receiving a guessed point.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "unidades_saude_araraquara.json"
PENDING = DATA / "unidades_sugeridas_araraquara.json"
RAW_GEOJSON = DATA / "unidades_saude_araraquara.geojson"
METADATA = DATA / "metadata_unidades_saude_araraquara.json"


OFFICIAL_BASIC_MAP = (
    "https://www.google.com/maps/d/viewer?hl=pt-BR&"
    "ll=-21.79175544415152%2C-48.1768535&"
    "mid=1z547XaGQ4BgR__QfAc0f3a1bM55Xja3v&z=12"
)
PREFEITURA_URGENCY = (
    "https://webnetserver.com.br/araraquara/secretarias/saude/"
    "sobre-a-secretaria-saude/urgencia-e-emergencia"
)
PREFEITURA_SPECIALIZED = (
    "https://webnetserver.com.br/araraquara/secretarias/saude/"
    "sobre-a-secretaria-saude/atencao-especializada/atencao-especializada"
)
PREFEITURA_ODONTOLOGY = (
    "https://webnetserver.com.br/araraquara/servicos/guia-de-servicos/saude/"
    "atendimento-odontologico"
)
CNES_BASE = "https://cnes2.datasus.gov.br/"
ARCGIS_GEOCODER = (
    "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer"
)


PROMOTIONS = {
    "PEND-001": {
        "id": "SUS-043",
        "name": 'UPA Central "Amélia Bernardini Cutrale"',
        "type": "UPA / Pronto Atendimento",
        "lat": -21.7734194,
        "lon": -48.1671244,
        "address": "Avenida Maria Antonia Camargo de Oliveira, s/n",
        "suburb": "Vila Velosa",
        "cnes": "2064731",
        "validation_source_url": PREFEITURA_URGENCY,
        "coordinate_source": "OpenStreetMap / ponto de estabelecimento",
        "quality_note": (
            "CNES, endereço e coordenada confirmados. A Prefeitura noticiou a "
            "reinauguração após reforma em janeiro de 2026."
        ),
    },
    "PEND-005": {
        "id": "SUS-044",
        "name": 'CMS Jardim Iguatemi — Enf.ª Kimiko Yuta',
        "type": "UBS / CMS (Unidade Básica)",
        "lat": -21.830978,
        "lon": -48.142236,
        "address": "Avenida Lourenço Rolfsen, s/n",
        "suburb": "Jardim Iguatemi",
        "cnes": "2065304",
        "validation_source_url": OFFICIAL_BASIC_MAP,
        "coordinate_source": "Mapa oficial da Secretaria Municipal de Saúde",
        "quality_note": (
            "CNES, endereço, operação e coordenada confirmados no cadastro "
            "municipal e no mapa oficial da Atenção Básica."
        ),
    },
    "PEND-007": {
        "id": "SUS-045",
        "name": 'CMS Jardim Roberto Selmi Dei I — Dr. Ruy de Toledo',
        "type": "UBS / CMS (Unidade Básica)",
        "lat": -21.739931,
        "lon": -48.151231,
        "address": "Rua José de Freitas Madeira, 49",
        "suburb": "Jardim Roberto Selmi Dei I",
        "cnes": "2032716",
        "validation_source_url": OFFICIAL_BASIC_MAP,
        "coordinate_source": "Mapa oficial da Secretaria Municipal de Saúde",
        "quality_note": (
            "CNES, endereço, operação e coordenada confirmados no cadastro "
            "municipal e no mapa oficial da Atenção Básica."
        ),
    },
    "PEND-008": {
        "id": "SUS-046",
        "name": 'USF Jardim Victório De Santi — Nair Damásio Claudino',
        "type": "USF (Saúde da Família)",
        "lat": -21.827171,
        "lon": -48.13438,
        "address": "Rua Francisco de Paula Lombardi, 210",
        "suburb": "Jardim Victório De Santi II",
        "cnes": "9983848",
        "validation_source_url": OFFICIAL_BASIC_MAP,
        "coordinate_source": "Mapa oficial da Secretaria Municipal de Saúde",
        "quality_note": (
            "CNES, endereço, operação e coordenada confirmados no cadastro "
            "municipal e no mapa oficial da Atenção Básica."
        ),
    },
    "PEND-009": {
        "id": "SUS-047",
        "name": 'USF Assentamento Bela Vista — Dr. Elias Zakaib',
        "type": "USF (Saúde da Família)",
        "lat": -21.914483,
        "lon": -48.192962,
        "address": "Rua Três, 04",
        "suburb": "Assentamento Bela Vista",
        "cnes": "2032708",
        "validation_source_url": OFFICIAL_BASIC_MAP,
        "coordinate_source": "Mapa oficial da Secretaria Municipal de Saúde",
        "quality_note": (
            "CNES, endereço rural, operação e coordenada confirmados no "
            "cadastro municipal e no mapa oficial da Atenção Básica."
        ),
    },
    "PEND-010": {
        "id": "SUS-048",
        "name": 'USF Assentamento Monte Alegre — Dirce Ragassi Cândido',
        "type": "USF (Saúde da Família)",
        "lat": -21.591459,
        "lon": -48.245554,
        "address": "Assentamento Monte Alegre III",
        "suburb": "Assentamento Monte Alegre III",
        "cnes": "4276582",
        "validation_source_url": OFFICIAL_BASIC_MAP,
        "coordinate_source": "Mapa oficial da Secretaria Municipal de Saúde",
        "quality_note": (
            "CNES, operação e coordenada rural confirmados no cadastro "
            "municipal e no mapa oficial da Atenção Básica."
        ),
    },
    "PEND-011": {
        "id": "SUS-049",
        "name": 'Espaço Crescer Infantojuvenil — Maria Augusta Gonçalves Mendes "Guta"',
        "type": "Centro de Referência e Especialidades",
        "lat": -21.781271007741,
        "lon": -48.18717603953,
        "address": "Avenida Padre Francisco Salles Colturato, 925",
        "suburb": "São Geraldo",
        "cnes": "5816874",
        "validation_source_url": PREFEITURA_SPECIALIZED,
        "coordinate_source": "ArcGIS World Geocoding, endereço oficial",
        "quality_note": (
            "A unidade não é um CAPS-i formal: a Prefeitura a descreve como "
            "ambulatório de saúde mental infantojuvenil, com proposta de "
            "transformação futura em CAPSij. CNES, endereço e operação confirmados."
        ),
    },
    "PEND-012": {
        "id": "SUS-050",
        "name": 'CAPS-AD "Dr. Calil Buainain"',
        "type": "CAPS (Atenção Psicossocial)",
        "lat": -21.771126013143,
        "lon": -48.182134995322,
        "address": "Avenida Professor Sebastião de Almeida Machado, 493",
        "suburb": "Santa Angelina",
        "cnes": "6767788",
        "validation_source_url": PREFEITURA_SPECIALIZED,
        "coordinate_source": "ArcGIS World Geocoding, endereço oficial",
        "quality_note": "CNES, gestão municipal, endereço, operação e coordenada confirmados.",
    },
    "PEND-013": {
        "id": "SUS-051",
        "name": 'CEO "Prof. Dr. Raphael Lia Rolfsen"',
        "type": "Centro de Referência e Especialidades",
        "lat": -21.784106982771,
        "lon": -48.157116020171,
        "address": "Rua Amazonas, 760",
        "suburb": "Vila Xavier",
        "cnes": "7581114",
        "validation_source_url": PREFEITURA_ODONTOLOGY,
        "coordinate_source": "ArcGIS World Geocoding, endereço oficial",
        "quality_note": "CNES, serviço municipal, endereço, operação e coordenada confirmados.",
    },
    "PEND-014": {
        "id": "SUS-052",
        "name": 'Centro Municipal de Referência do Autismo "Aldo Pavão Júnior"',
        "type": "Centro de Referência e Especialidades",
        "lat": -21.765828544108,
        "lon": -48.181597511772,
        "address": "Rua Nove de Julho, 3700",
        "suburb": "Jardim Dom Pedro I",
        "cnes": "4395794",
        "validation_source_url": PREFEITURA_SPECIALIZED,
        "coordinate_source": "ArcGIS World Geocoding, endereço oficial",
        "quality_note": "CNES, serviço municipal, endereço, operação e coordenada confirmados.",
    },
}


MERGE_SAO_BENTO = {
    "name": "USF Jardim São Bento — Selma Rita Canelas Ferrari Nogueira",
    "type": "USF (Saúde da Família)",
    "lat": -21.762065,
    "lon": -48.211601,
    "address": "Avenida Augusto Bernardi, s/n",
    "suburb": "Jardim São Bento",
    "cnes": "0424838",
    "validation_source_url": OFFICIAL_BASIC_MAP,
    "coordinate_source": "Mapa oficial da Secretaria Municipal de Saúde",
}


def read_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def write_json(path, value):
    with path.open("w", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")


def promote():
    catalog = read_json(CATALOG)
    pending = read_json(PENDING)
    metadata = read_json(METADATA)
    raw = read_json(RAW_GEOJSON)

    pending_by_id = {
        item["id"]: {**item, "record_status": "pendente_validacao"}
        for item in pending
    }
    current = [
        item
        for item in catalog
        if item.get("record_status") != "pendente_validacao"
        and item.get("status") != "pendente_validacao"
    ]
    current_by_id = {item["id"]: item for item in current}

    for source_id, promotion in PROMOTIONS.items():
        if source_id not in pending_by_id:
            if promotion["id"] in current_by_id:
                continue
            raise KeyError(f"Registro pendente não encontrado: {source_id}")
        source = pending_by_id.pop(source_id)
        record = {
            "id": promotion["id"],
            "name": promotion["name"],
            "type": promotion["type"],
            "lat": promotion["lat"],
            "lon": promotion["lon"],
            "address": promotion["address"],
            "suburb": promotion["suburb"],
            "cnes": promotion["cnes"],
            "network": "Rede pública municipal",
            "record_status": "analisado",
            "network_scope": "municipal",
            "data_quality": "ok",
            "canonical_name": promotion["name"],
            "quality_note": promotion["quality_note"],
            "validation_source_url": promotion["validation_source_url"],
            "coordinate_source": promotion["coordinate_source"],
        }
        current.append(record)
        current_by_id[record["id"]] = record
        metadata[record["id"]] = {
            "network_scope": "municipal",
            "data_quality": "ok",
            "canonical_name": promotion["name"],
            "quality_note": promotion["quality_note"],
        }

    pending_by_id.pop("PEND-003", None)
    sao_bento = current_by_id["SUS-007"]
    sao_bento.update(MERGE_SAO_BENTO)
    sao_bento.update(
        {
            "network": "Rede pública municipal",
            "record_status": "analisado",
            "network_scope": "municipal",
            "data_quality": "ok",
            "canonical_name": MERGE_SAO_BENTO["name"],
            "quality_note": (
                "Registro SUS-007 confirmado como a USF São Bento no CNES e "
                "no cadastro municipal; o item pendente era uma duplicata nominal."
            ),
        }
    )
    metadata["SUS-007"] = {
        "network_scope": "municipal",
        "data_quality": "ok",
        "canonical_name": MERGE_SAO_BENTO["name"],
        "quality_note": sao_bento["quality_note"],
    }

    samu = pending_by_id["PEND-002"]
    samu.update(
        {
            "name": "Base Centralizada SAMU 192 — Araraquara",
            "address": "Avenida Eitor Bim, s/n",
            "suburb": "Vila Melhado / Vila Suconasa",
            "cnes": "6395961",
            "source_label": "Prefeitura de Araraquara e CNES",
            "source_url": PREFEITURA_URGENCY,
            "next_step": (
                "Confirmar se a base atual permanece na Rua/Avenida Eitor Bim "
                "ou se foi transferida para a nova estrutura junto à UPA Central; "
                "manter uma única representação no mapa."
            ),
        }
    )

    raw_by_id = {feature["properties"]["id"]: feature for feature in raw["features"]}
    for feature_id, item in current_by_id.items():
        if feature_id not in raw_by_id:
            raw_by_id[feature_id] = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [item["lon"], item["lat"]],
                },
                "properties": {},
            }
        feature = raw_by_id[feature_id]
        feature["geometry"] = {
            "type": "Point",
            "coordinates": [item["lon"], item["lat"]],
        }
        feature["properties"].update(
            {
                "id": feature_id,
                "name": item["name"],
                "type": item["type"],
                "lat": item["lat"],
                "lon": item["lon"],
                "suburb": item["suburb"],
            }
        )

    raw["features"] = [raw_by_id[feature_id] for feature_id in current_by_id]
    write_json(CATALOG, current + list(pending_by_id.values()))
    write_json(PENDING, list(pending_by_id.values()))
    write_json(RAW_GEOJSON, raw)
    write_json(METADATA, metadata)
    print(f"Promovidas {len(PROMOTIONS)} unidades e corrigido o registro duplicado de São Bento.")
    print(f"Pendências restantes: {len(pending_by_id)}")


if __name__ == "__main__":
    promote()
