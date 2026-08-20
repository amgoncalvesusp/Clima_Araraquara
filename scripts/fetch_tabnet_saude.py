"""Builds a traceable, aggregated TabNet health dataset for Araraquara.

The public TabNet endpoints are queried directly and only aggregated rows are
written to the repository. No patient-level record is persisted.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT_OUTPUT = DATA_DIR / "dados_historicos_saude_araraquara.json"
MUNICIPALITY_CODE = "350320"
MUNICIPALITY_OPTION = "38"
YEARS = list(range(2016, 2027))
TABNET_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "PET-Saude-Clima-Araraquara/1.0 (pesquisa acadêmica)",
}


def available_files(def_url: str, prefix: str) -> list[str]:
    """List the monthly files TabNet actually publishes for this endpoint.

    Asking for a month that does not exist yet makes TabNet reject the whole
    query, so the current competence has to be discovered instead of assumed.
    """
    response = requests.get(
        def_url, headers={"User-Agent": TABNET_HEADERS["User-Agent"]}, timeout=180
    )
    response.raise_for_status()
    text = response.content.decode("iso-8859-1", errors="replace")
    found = re.findall(
        rf'value="({prefix}(\d{{2}})(\d{{2}})\.dbf)"', text, flags=re.IGNORECASE
    )
    files = sorted(
        {
            name
            for name, year, month in found
            if 2000 + int(year) in YEARS and 1 <= int(month) <= 12
        }
    )
    if not files:
        raise RuntimeError(f"O TabNet não listou arquivos {prefix}* em {def_url}.")
    return files


def months_by_year(files: list[str], prefix: str) -> dict[str, int]:
    counter: dict[str, int] = {}
    for name in files:
        year = str(2000 + int(name[len(prefix) : len(prefix) + 2]))
        counter[year] = counter.get(year, 0) + 1
    return dict(sorted(counter.items()))


def query_tabnet(endpoint: str, line: str, increment: str, files: list[str]) -> str:
    fields: list[tuple[str, str]] = [
        ("Linha", line),
        ("Coluna", "Ano_atendimento"),
        ("Incremento", increment),
        ("SMunicípio", MUNICIPALITY_OPTION),
        ("formato", "prn"),
        ("mostre", "Mostra"),
    ]
    fields.extend(("Arquivos", filename) for filename in files)
    # TabNet is an ISO-8859-1 application. Encoding the form this way avoids
    # losing accented field names and values such as "Internações".
    body = urlencode(fields, doseq=True, encoding="latin-1", errors="replace")
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.post(
                endpoint,
                data=body.encode("ascii"),
                headers=TABNET_HEADERS,
                timeout=180,
            )
            response.raise_for_status()
            text = response.content.decode("iso-8859-1", errors="replace")
            if "Campo Incremento" in text or "não encontrado" in text.lower():
                raise RuntimeError(f"TabNet rejeitou a consulta: {text[:400]}")
            return text
        except Exception as error:  # network endpoints are occasionally slow
            last_error = error
            if attempt < 3:
                time.sleep(2**attempt)
    raise RuntimeError(f"Falha ao consultar TabNet após 4 tentativas: {last_error}")


def parse_tabnet_table(response_text: str) -> list[list[str]]:
    match = re.search(
        r"<pre>(.*?)</pre>", response_text, flags=re.IGNORECASE | re.DOTALL
    )
    if not match:
        raise ValueError("A resposta do TabNet não contém uma tabela PRE.")
    table_text = html.unescape(match.group(1)).replace("\r", "")
    rows = list(csv.reader(io.StringIO(table_text), delimiter=";", quotechar='"'))
    rows = [[cell.strip() for cell in row] for row in rows if row]
    if len(rows) < 2:
        raise ValueError("A tabela do TabNet não contém linhas suficientes.")
    return rows


def numeric(value: str) -> int | float:
    cleaned = value.strip().replace(".", "").replace(",", ".")
    if cleaned in {"", "-", "—"}:
        return 0
    number = float(cleaned)
    return int(number) if number.is_integer() else number


def matrix_to_records(rows: list[list[str]], first_key: str) -> list[dict]:
    header = rows[0]
    year_columns = {
        index: int(value)
        for index, value in enumerate(header[1:], start=1)
        if re.fullmatch(r"20\d{2}", value) and int(value) in YEARS
    }
    records: list[dict] = []
    for row in rows[1:]:
        if not row or row[0].strip().lower() == "total":
            continue
        values = {
            str(year): numeric(row[index]) if index < len(row) else 0
            for index, year in year_columns.items()
        }
        records.append({first_key: row[0], "values": values})
    return records


def split_cnes(label: str) -> tuple[str | None, str]:
    match = re.match(r"^(\d{7})\s+(.+)$", label.strip())
    return (match.group(1), match.group(2)) if match else (None, label.strip())


def flatten_values(
    records: list[dict], key: str, extra_keys: tuple[str, ...] = ()
) -> list[dict]:
    flattened: list[dict] = []
    for record in records:
        for year, value in record["values"].items():
            flattened.append(
                {
                    "year": int(year),
                    key: record[key],
                    "value": value,
                    **{extra_key: record.get(extra_key) for extra_key in extra_keys},
                }
            )
    return flattened


def build_dataset() -> dict:
    sih_endpoint = "https://tabnet.datasus.gov.br/cgi/tabcgi.exe?sih/cnv/nrSP.def"
    sia_endpoint = "https://tabnet.datasus.gov.br/cgi/tabcgi.exe?sia/cnv/qasp.def"

    sih_def = "https://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nrSP.def"
    sia_def = "https://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/qasp.def"

    sih_files = available_files(sih_def, "nrsp")
    sia_files = available_files(sia_def, "qasp")
    sih_months = months_by_year(sih_files, "nrsp")
    covered_years = sorted(int(year) for year in sih_months)
    partial_years = [int(year) for year, months in sih_months.items() if months < 12]

    unit_rows = parse_tabnet_table(
        query_tabnet(sih_endpoint, "Estabelecimento", "Internações", sih_files)
    )
    chapter_rows = parse_tabnet_table(
        query_tabnet(sih_endpoint, "Capítulo_CID-10", "Internações", sih_files)
    )
    ambulatory_rows = parse_tabnet_table(
        query_tabnet(sia_endpoint, "Grupo_procedimento", "Qtd.aprovada", sia_files)
    )

    unit_records: list[dict] = []
    for row in matrix_to_records(unit_rows, "establishment_label"):
        cnes, name = split_cnes(row["establishment_label"])
        unit_records.append(
            {"cnes": cnes, "establishment": name, "values": row["values"]}
        )

    chapter_records = matrix_to_records(chapter_rows, "chapter")
    ambulatory_records = matrix_to_records(ambulatory_rows, "procedure_group")
    return {
        "title": "Base histórica de saúde — Araraquara",
        "municipality": "Araraquara",
        "municipality_code": MUNICIPALITY_CODE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coverage": {
            "start_year": covered_years[0],
            "end_year": covered_years[-1],
            "years": covered_years,
            "months_requested": len(sih_files),
            "months_by_year": sih_months,
            "partial_years": partial_years,
            "partial_year_note": (
                "Anos parciais trazem menos meses publicados e por isso somam menos. "
                "Não leia essa diferença como queda no atendimento."
            ),
        },
        "hospital": {
            "source": "SIH/SUS — internações por local de residência",
            "source_url": "https://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nrSP.def",
            "unit_dimension": "Estabelecimento executante da internação",
            "unit_year": flatten_values(unit_records, "establishment", ("cnes",)),
            "chapters_year": flatten_values(chapter_records, "chapter"),
        },
        "ambulatory": {
            "source": "SIA/SUS — produção ambulatorial aprovada",
            "source_url": "https://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/qasp.def",
            "unit_dimension": "Não disponível nesta tabulação pública estadual",
            "groups_year": flatten_values(ambulatory_records, "procedure_group"),
        },
        "limitations": [
            "Os dados representam produção registrada e financiada pelo SUS; não incluem toda a assistência privada ou informação não faturada.",
            "O SIH permite leitura por estabelecimento hospitalar, mas não descreve o itinerário completo do usuário na APS, regulação e transporte.",
            "A produção ambulatorial foi mantida separada porque sua unidade de medida é quantidade aprovada, não internação.",
            "Os valores podem sofrer atualização retroativa no DATASUS; a data de extração deve ser preservada em cada atualização.",
            "A ausência ou baixo volume de registros não deve ser interpretada automaticamente como ausência de necessidade de cuidado.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = build_dataset()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"output": str(args.output), "coverage": result["coverage"]},
            ensure_ascii=False,
            indent=2,
        )
    )
