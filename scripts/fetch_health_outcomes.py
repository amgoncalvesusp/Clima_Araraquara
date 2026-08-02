"""Aggregates SIH/SUS hospitalizations for Araraquara without publishing records."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from dbfread import DBF
import pyreaddbc


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT_CACHE = Path("C:/Temp/pet-clima-datasus-sih")
OUTPUT = DATA_DIR / "desfechos_saude_araraquara.json"
MUNICIPALITY_CODE = "350320"


def month_from_name(path: Path) -> str:
    match = re.search(r"RDSP(\d{4})\.dbc$", path.name, re.IGNORECASE)
    if not match:
        raise ValueError(f"Nome de arquivo SIH inesperado: {path.name}")
    value = match.group(1)
    return f"20{value[:2]}-{value[2:]}"


def classify_cid(code: str) -> str | None:
    value = (code or "").upper().strip()
    if value.startswith("J"):
        return "respiratory"
    if value.startswith("I"):
        return "circulatory"
    if value.startswith("E86"):
        return "dehydration"
    if value.startswith("T67"):
        return "heat_related"
    return None


def convert_dbc(path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{path.stem}.dbf"
    if not target.exists():
        pyreaddbc.dbc2dbf(str(path), str(target))
    return target


def aggregate_file(path: Path, output_dir: Path) -> dict:
    month = month_from_name(path)
    dbf = DBF(convert_dbc(path, output_dir), load=False, encoding="latin1")
    counts = defaultdict(int)
    rows = 0
    for record in dbf:
        if str(record.get("MUNIC_RES", "")).strip() != MUNICIPALITY_CODE:
            continue
        rows += 1
        counts["hospitalizations_total"] += 1
        counts["deaths"] += int(record.get("MORTE", 0) or 0)
        group = classify_cid(str(record.get("DIAG_PRINC", "")))
        if group:
            counts[group] += 1
    return {
        "period": month,
        "hospitalizations_total": counts["hospitalizations_total"],
        "respiratory": counts["respiratory"],
        "circulatory": counts["circulatory"],
        "dehydration": counts["dehydration"],
        "heat_related": counts["heat_related"],
        "deaths": counts["deaths"],
        "records_after_municipality_filter": rows,
    }


def build_output(cache_dir: Path, output: Path = OUTPUT) -> dict:
    files = sorted(cache_dir.glob("RDSP*.dbc"))
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo RDSP*.dbc encontrado em {cache_dir}")
    dbf_dir = cache_dir / "dbf"
    series = [aggregate_file(path, dbf_dir) for path in files]
    series.sort(key=lambda item: item["period"])
    annual = defaultdict(lambda: defaultdict(int))
    for item in series:
        year = item["period"][:4]
        for key, value in item.items():
            if key not in {"period", "records_after_municipality_filter"}:
                annual[year][key] += value
    annual_series = [
        {"period": year, **dict(values)}
        for year, values in sorted(annual.items())
    ]
    result = {
        "title": "Desfechos de saúde agregados — Araraquara",
        "source": "Ministério da Saúde / DATASUS — Sistema de Informações Hospitalares do SUS (SIH/SUS)",
        "source_url": "https://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nrSP.def",
        "coverage": {
            "system": "SIH/SUS",
            "geography": "município de residência do paciente",
            "municipality": "Araraquara",
            "municipality_code": MUNICIPALITY_CODE,
            "period_start": series[0]["period"],
            "period_end": series[-1]["period"],
            "months": len(series),
            "records_after_municipality_filter": sum(item["records_after_municipality_filter"] for item in series),
        },
        "series": series,
        "annual": annual_series,
        "ambulatory_attendance": {
            "status": "not_loaded",
            "system": "SIA/SUS",
            "note": "A produção ambulatorial exige uma extração separada do SIA/SUS; não foi misturada ao SIH para evitar comparar unidades de medida diferentes.",
            "source_url": "https://tabnet.datasus.gov.br/cgi/deftohtm.exe?qauf.def",
        },
        "method": {
            "unit_of_count": "AIH/registro de internação do SIH/SUS, filtrado por MUNIC_RES=350320",
            "climate_sensitive_groups": {
                "respiratory": "CID-10 começando por J",
                "circulatory": "CID-10 começando por I",
                "dehydration": "CID-10 E86",
                "heat_related": "CID-10 T67",
            },
        },
        "limitations": [
            "Cobre somente internações financiadas pelo SUS; não representa toda a demanda assistencial.",
            "É um contexto municipal de residência, não uma atribuição causal a uma unidade de saúde.",
            "Os grupos CID são filtros amplos para exploração e não demonstram que o evento foi causado pelo clima.",
            "Os dados administrativos podem ser atualizados retroativamente e devem ser reprocessados antes de uma análise final.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = build_output(args.cache_dir, args.output)
    print(json.dumps(result["coverage"], ensure_ascii=False, indent=2))
