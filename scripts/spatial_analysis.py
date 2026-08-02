"""Calculates the current IECS layer and sensitivity scenarios."""

from __future__ import annotations

import json
import os
from pathlib import Path

import geopandas as gpd
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

HEALTHCARE_GEOJSON = DATA_DIR / "unidades_saude_araraquara.geojson"
URBVERDE_GEOJSON = DATA_DIR / "urbverde_araraquara.geojson"
CENSUS_GEOJSON = DATA_DIR / "censo_2022_vulnerabilidade_araraquara.geojson"

OUTPUT_GEOJSON = DATA_DIR / "unidades_saude_analise_araraquara.geojson"
OUTPUT_CSV = DATA_DIR / "ranking_risco_termico.csv"
OUTPUT_SUMMARY = DATA_DIR / "resumo_estatistico.json"
OUTPUT_SENSITIVITY = DATA_DIR / "sensibilidade_iecs_araraquara.json"

BUFFER_RADIUS = 300
DEFAULT_WEIGHTS = {"heat": 0.45, "vegetation": 0.25, "social": 0.30}
SCENARIOS = [
    {
        "id": "balanced",
        "label": "Equilibrado (padrão)",
        "description": "Mantém o peso atualmente adotado no IECS.",
        "weights": DEFAULT_WEIGHTS,
    },
    {
        "id": "climate_only",
        "label": "Somente clima",
        "description": "Remove o componente social para testar o quanto o ranking depende do contexto do Censo.",
        "weights": {"heat": 0.60, "vegetation": 0.40, "social": 0.00},
    },
    {
        "id": "social_priority",
        "label": "Prioridade social",
        "description": "Aumenta a influência da vulnerabilidade social-sanitária do Censo.",
        "weights": {"heat": 0.35, "vegetation": 0.15, "social": 0.50},
    },
    {
        "id": "heat_priority",
        "label": "Prioridade de calor",
        "description": "Dá mais peso à temperatura de superfície do entorno.",
        "weights": {"heat": 0.60, "vegetation": 0.15, "social": 0.25},
    },
    {
        "id": "vegetation_priority",
        "label": "Prioridade de vegetação",
        "description": "Dá mais peso ao déficit de cobertura vegetal.",
        "weights": {"heat": 0.35, "vegetation": 0.40, "social": 0.25},
    },
    {
        "id": "equal",
        "label": "Pesos iguais",
        "description": "Distribui o peso igualmente entre calor, vegetação e dimensão social.",
        "weights": {"heat": 1 / 3, "vegetation": 1 / 3, "social": 1 / 3},
    },
]


def weighted_mean(frame: gpd.GeoDataFrame, value: str, weights: str = "overlap_area") -> float | None:
    values = pd.to_numeric(frame[value], errors="coerce")
    valid = values.notna() & frame[weights].notna() & (frame[weights] > 0)
    if not valid.any():
        return None
    return float((values[valid] * frame.loc[valid, weights]).sum() / frame.loc[valid, weights].sum())


def min_max(series: pd.Series, inverse: bool = False) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    low = values.min(skipna=True)
    high = values.max(skipna=True)
    if pd.isna(low) or pd.isna(high) or high == low:
        return pd.Series(0.5, index=series.index, dtype="float64")
    normalized = (values - low) / (high - low)
    return 1 - normalized if inverse else normalized


def calculate_components(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["heat_component"] = min_max(result["surface_temp_300m"])
    result["vegetation_component"] = min_max(result["ndvi_300m"], inverse=True)
    result["social_component"] = min_max(result["vulnerability_score_300m"])
    result["heat_component_0_100"] = (result["heat_component"] * 100).round(1)
    result["vegetation_component_0_100"] = (result["vegetation_component"] * 100).round(1)
    result["social_component_0_100"] = (result["social_component"] * 100).round(1)
    return result


def calculate_iecs(frame: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    return (
        frame["heat_component"] * weights["heat"]
        + frame["vegetation_component"] * weights["vegetation"]
        + frame["social_component"] * weights["social"]
    ) * 100


def risk_level(score: float) -> str:
    if score >= 75:
        return "Crítico (Altíssimo Risco)"
    if score >= 55:
        return "Alto"
    if score >= 35:
        return "Moderado"
    return "Baixo / Confortável"


def numeric_or_none(value):
    if value is None or pd.isna(value):
        return None
    return round(float(value), 4)


def intersect_metrics(unit_buffer, climate: gpd.GeoDataFrame, census: gpd.GeoDataFrame) -> dict:
    result = {
        "surface_temp_300m": None,
        "ndvi_300m": None,
        "climate_data_coverage_pct": 0.0,
        "census_population_300m": None,
        "census_income_median_300m": None,
        "census_share_children_300m": None,
        "census_share_elderly_300m": None,
        "census_crowding_300m": None,
        "vulnerability_score_300m": None,
        "social_data_coverage_pct": 0.0,
        "vulnerability_data_quality": "sem_intersecao_censo",
    }

    climate_rows = climate[climate.intersects(unit_buffer)].copy()
    if not climate_rows.empty:
        climate_rows["overlap_area"] = climate_rows.geometry.intersection(unit_buffer).area
        climate_rows = climate_rows.loc[climate_rows["overlap_area"] > 0]
        result["surface_temp_300m"] = weighted_mean(climate_rows, "surface_temp")
        result["ndvi_300m"] = weighted_mean(climate_rows, "ndvi")
        result["climate_data_coverage_pct"] = round(
            min(100, climate_rows["overlap_area"].sum() / unit_buffer.area * 100), 1
        )

    census_rows = census[census.intersects(unit_buffer)].copy()
    if not census_rows.empty:
        census_rows["overlap_area"] = census_rows.geometry.intersection(unit_buffer).area
        census_rows = census_rows.loc[census_rows["overlap_area"] > 0].copy()
        census_rows["sector_area"] = census_rows.geometry.area.clip(lower=1)
        census_rows["population_weight"] = pd.to_numeric(census_rows["census_population"], errors="coerce") * (
            census_rows["overlap_area"] / census_rows["sector_area"]
        )
        census_rows["population_weight"] = census_rows["population_weight"].fillna(0)
        if census_rows["population_weight"].sum() > 0:
            census_rows["social_weight"] = census_rows["population_weight"]
        else:
            census_rows["social_weight"] = census_rows["overlap_area"]
        result["census_population_300m"] = float(census_rows["population_weight"].sum())
        for source, target in [
            ("census_income_median", "census_income_median_300m"),
            ("census_share_children", "census_share_children_300m"),
            ("census_share_elderly", "census_share_elderly_300m"),
            ("census_crowding", "census_crowding_300m"),
            ("vulnerability_score_5", "vulnerability_score_300m"),
        ]:
            result[target] = weighted_mean(census_rows, source, "social_weight")
        result["social_data_coverage_pct"] = round(
            min(100, census_rows["overlap_area"].sum() / unit_buffer.area * 100), 1
        )
        result["vulnerability_data_quality"] = "censo_2022"
    return result


def build_sensitivity(frame: pd.DataFrame) -> dict:
    default_ranks = (
        frame.assign(score=calculate_iecs(frame, DEFAULT_WEIGHTS))
        .sort_values(["score", "id"], ascending=[False, True])
        .reset_index(drop=True)
    )
    default_rank_by_id = {row.id: index + 1 for index, row in default_ranks.iterrows()}
    scenarios = []
    for scenario in SCENARIOS:
        ranked = frame.assign(score=calculate_iecs(frame, scenario["weights"]))
        ranked = ranked.sort_values(["score", "id"], ascending=[False, True]).reset_index(drop=True)
        units = []
        for index, row in ranked.iterrows():
            current_rank = index + 1
            units.append({
                "id": row["id"],
                "name": row["display_name"] if "display_name" in row else row["name"],
                "score": round(float(row["score"]), 1),
                "ranking": current_rank,
                "rank_shift_vs_default": default_rank_by_id[row["id"]] - current_rank,
            })
        scenarios.append({
            **scenario,
            "weights": {key: round(value, 4) for key, value in scenario["weights"].items()},
            "top_5": units[:5],
            "units": units,
        })
    return {
        "title": "Analise de sensibilidade do IECS",
        "method": "Cada cenário recalcula o mesmo conjunto de componentes normalizados; apenas os pesos mudam.",
        "default_scenario": "balanced",
        "components": {
            "heat": "Temperatura de superficie no buffer de 300m",
            "vegetation": "Deficit de NDVI no buffer de 300m",
            "social": "Indice social-sanitario composto com Censo 2022",
        },
        "scenarios": scenarios,
    }


def run_spatial_analysis() -> None:
    print("Loading datasets with GeoPandas...")
    gdf_units = gpd.read_file(HEALTHCARE_GEOJSON)
    gdf_climate = gpd.read_file(URBVERDE_GEOJSON)
    gdf_census = gpd.read_file(CENSUS_GEOJSON)

    gdf_units_utm = gdf_units.to_crs(epsg=31983)
    gdf_climate_utm = gdf_climate.to_crs(epsg=31983)
    gdf_census_utm = gdf_census.to_crs(epsg=31983)
    gdf_units_utm["buffer_geometry"] = gdf_units_utm.geometry.buffer(BUFFER_RADIUS)

    analyzed_units = []
    for _, row in gdf_units_utm.iterrows():
        metrics = intersect_metrics(row["buffer_geometry"], gdf_climate_utm, gdf_census_utm)
        analyzed_units.append({
            **{key: row[key] for key in row.index if key not in {"geometry", "buffer_geometry"}},
            **metrics,
        })

    result = pd.DataFrame(analyzed_units)
    for column, fallback in [("surface_temp_300m", 31.0), ("ndvi_300m", 0.35)]:
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(fallback)
    social = pd.to_numeric(result["vulnerability_score_300m"], errors="coerce")
    social_median = float(social.median()) if social.notna().any() else 2.5
    missing_social = social.isna()
    result.loc[missing_social, "vulnerability_score_300m"] = social_median
    result.loc[missing_social, "vulnerability_data_quality"] = "imputada_mediana_municipal"
    result["vulnerability_score_300m"] = pd.to_numeric(result["vulnerability_score_300m"], errors="coerce").round(2)

    result = calculate_components(result)
    result["iecs_score"] = calculate_iecs(result, DEFAULT_WEIGHTS).round(1)
    result["risk_level"] = result["iecs_score"].map(risk_level)
    result = result.sort_values(["iecs_score", "id"], ascending=[False, True]).reset_index(drop=True)
    result["ranking"] = result.index + 1
    result["vulnerability_source"] = "IBGE Censo 2022 — índice social-sanitário composto do projeto"

    print("Top 5 Most Impacted Healthcare Units in Araraquara (300m buffer):")
    for _, row in result.head(5).iterrows():
        print(f"#{row['ranking']} | {row['name']} - IECS: {row['iecs_score']}")

    result.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    features = []
    for _, row in result.iterrows():
        properties = {key: numeric_or_none(value) if isinstance(value, (float, int)) else value for key, value in row.to_dict().items()}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
            "properties": properties,
        })
    OUTPUT_GEOJSON.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "total_units_analyzed": len(result),
        "buffer_radius_meters": BUFFER_RADIUS,
        "social_source": "IBGE Censo 2022",
        "social_index_is_official": False,
        "units_with_census_intersection": int((result["vulnerability_data_quality"] == "censo_2022").sum()),
        "units_with_social_imputation": int((result["vulnerability_data_quality"] == "imputada_mediana_municipal").sum()),
        "avg_surface_temp_araraquara": round(result["surface_temp_300m"].mean(), 2),
        "max_surface_temp": result["surface_temp_300m"].max(),
        "min_surface_temp": result["surface_temp_300m"].min(),
        "avg_ndvi": round(result["ndvi_300m"].mean(), 2),
        "units_by_risk_level": result["risk_level"].value_counts().to_dict(),
        "top_5_critical_units": result.head(5)[["ranking", "name", "type", "suburb", "surface_temp_300m", "ndvi_300m", "vulnerability_score_300m", "iecs_score", "risk_level"]].to_dict(orient="records"),
    }
    OUTPUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_SENSITIVITY.write_text(json.dumps(build_sensitivity(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Ranking CSV saved to {OUTPUT_CSV}")
    print(f"Analyzed GeoJSON saved to {OUTPUT_GEOJSON}")
    print(f"Sensitivity JSON saved to {OUTPUT_SENSITIVITY}")


if __name__ == "__main__":
    run_spatial_analysis()
