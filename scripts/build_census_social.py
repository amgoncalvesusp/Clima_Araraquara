"""Builds a Census 2022 social-sanitary layer for Araraquara.

The resulting score is a project composite, not an official IBGE index. It is
calculated at census-sector level and later area-weighted inside each health
unit's 300 m buffer by the spatial analysis pipeline.
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT_CACHE = Path("C:/Temp/pet-clima-ibge")
OUTPUT = DATA_DIR / "censo_2022_vulnerabilidade_araraquara.geojson"

IBGE_URLS = {
    "basic": "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Setor_csv/Agregados_por_setores_basico_BR_20260520.zip",
    "demography": "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Setor_csv/Agregados_por_setores_demografia_BR.zip",
    "income": "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios_Rendimento_do_Responsavel/Agregados_por_setores_renda_responsavel_BR_20260508_csv.zip",
    "mesh": "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/shp/UF/SP_setores_CD2022.zip",
}

ARARAQUARA_CODE = "3503208"


def download(url: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return target
    request = Request(url, headers={"User-Agent": "PET-Saude-Clima/1.0"})
    with urlopen(request, timeout=120) as response:
        target.write_bytes(response.read())
    return target


def read_zip_csv(zip_path: Path, preferred_name: str, columns: list[str]) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as archive:
        candidates = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        candidate = next((name for name in candidates if preferred_name.lower() in name.lower()), candidates[0])
        with archive.open(candidate) as stream:
            frame = pd.read_csv(stream, sep=";", encoding="latin1", dtype=str, low_memory=False)
    selected = [column for column in columns if column in frame.columns]
    return frame[selected].copy()


def read_mesh(zip_path: Path, cache_dir: Path) -> gpd.GeoDataFrame:
    extract_dir = cache_dir / "sp_shp"
    shp = extract_dir / "SP_setores_CD2022.shp"
    if not shp.exists():
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)
    mesh = gpd.read_file(shp)
    return mesh.loc[mesh["CD_MUN"].astype(str) == ARARAQUARA_CODE].copy()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.replace({"X": pd.NA, "x": pd.NA}), errors="coerce")


def min_max(series: pd.Series, inverse: bool = False) -> pd.Series:
    values = numeric(series)
    low = values.min(skipna=True)
    high = values.max(skipna=True)
    if pd.isna(low) or pd.isna(high) or high == low:
        return pd.Series(0.5, index=series.index, dtype="float64")
    result = (values - low) / (high - low)
    return 1 - result if inverse else result


def build_layer(cache_dir: Path, output: Path = OUTPUT) -> dict:
    paths = {
        key: download(url, cache_dir / Path(url).name)
        for key, url in IBGE_URLS.items()
    }
    mesh = read_mesh(paths["mesh"], cache_dir)
    mesh["CD_SETOR"] = mesh["CD_SETOR"].astype(str)

    basic = read_zip_csv(paths["basic"], "basico", ["CD_SETOR", "v0001", "v0005", "v0007"])
    demography = read_zip_csv(paths["demography"], "demografia", ["CD_setor", "V01006", "V01031", "V01032", "V01040", "V01041"])
    income = read_zip_csv(paths["income"], "renda", ["CD_SETOR", "V06004", "V06005", "V06006"])

    basic = basic.rename(columns={"CD_SETOR": "CD_SETOR"})
    demography = demography.rename(columns={"CD_setor": "CD_SETOR"})
    for frame in (basic, demography, income):
        frame["CD_SETOR"] = frame["CD_SETOR"].astype(str)

    values = mesh.merge(basic, on="CD_SETOR", how="left")
    values = values.merge(demography, on="CD_SETOR", how="left")
    values = values.merge(income, on="CD_SETOR", how="left")

    values["census_population"] = numeric(values["V01006"]).fillna(numeric(values["v0001"]))
    values["census_income_median"] = numeric(values["V06006"])
    values["census_income_mean"] = numeric(values["V06004"])
    values["census_income_responsible_count"] = numeric(values["V06005"])
    population = values["census_population"].replace(0, pd.NA)
    values["census_share_children"] = (numeric(values["V01031"]).fillna(0) + numeric(values["V01032"]).fillna(0)) / population
    values["census_share_elderly"] = (numeric(values["V01040"]).fillna(0) + numeric(values["V01041"]).fillna(0)) / population
    values["census_crowding"] = numeric(values["v0005"])

    values["income_component"] = min_max(values["census_income_median"], inverse=True)
    values["elderly_component"] = min_max(values["census_share_elderly"])
    values["children_component"] = min_max(values["census_share_children"])
    values["crowding_component"] = min_max(values["census_crowding"])
    components = values[["income_component", "elderly_component", "children_component", "crowding_component"]]
    values["vulnerability_score_0_100"] = (
        components["income_component"] * 0.50
        + components["elderly_component"] * 0.20
        + components["children_component"] * 0.20
        + components["crowding_component"] * 0.10
    ) * 100
    values["vulnerability_score_5"] = values["vulnerability_score_0_100"] / 20
    values["vulnerability_source"] = "IBGE Censo 2022; indice composto do projeto"
    values["vulnerability_method"] = "50% renda mediana inversa + 20% idosos + 20% criancas + 10% adensamento"
    values["data_quality"] = values["census_population"].notna().map({True: "ok", False: "sem_dado_setorial"})

    keep = [
        "CD_SETOR", "NM_MUN", "SITUACAO", "geometry", "census_population",
        "census_income_median", "census_income_mean", "census_income_responsible_count",
        "census_share_children", "census_share_elderly", "census_crowding",
        "vulnerability_score_0_100", "vulnerability_score_5", "vulnerability_source",
        "vulnerability_method", "data_quality",
    ]
    output_gdf = values[keep].to_crs(epsg=4326)
    output.parent.mkdir(parents=True, exist_ok=True)
    output_gdf.to_file(output, driver="GeoJSON", engine="pyogrio", index=False)
    metadata = {
        "source": "IBGE Censo Demografico 2022 — agregados por setores censitarios",
        "source_urls": list(IBGE_URLS.values()),
        "municipality_code": ARARAQUARA_CODE,
        "sector_count": int(len(output_gdf)),
        "sectors_with_population": int(output_gdf["census_population"].notna().sum()),
        "score_is_official": False,
        "score_note": "Indice composto criado para este projeto; nao e um indice oficial do IBGE.",
    }
    output.with_suffix(".metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(build_layer(args.cache_dir, args.output), ensure_ascii=False, indent=2))
