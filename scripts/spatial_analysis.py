import os
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Paths setup
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

HEALTHCARE_GEOJSON = os.path.join(DATA_DIR, "unidades_saude_araraquara.geojson")
URBVERDE_GEOJSON = os.path.join(DATA_DIR, "urbverde_araraquara.geojson")

OUTPUT_GEOJSON = os.path.join(DATA_DIR, "unidades_saude_analise_araraquara.geojson")
OUTPUT_CSV = os.path.join(DATA_DIR, "ranking_risco_termico.csv")
OUTPUT_SUMMARY = os.path.join(DATA_DIR, "resumo_estatistico.json")

def run_spatial_analysis():
    print("Loading datasets with GeoPandas...")
    gdf_units = gpd.read_file(HEALTHCARE_GEOJSON)
    gdf_climate = gpd.read_file(URBVERDE_GEOJSON)
    
    # Reproject to SIRGAS 2000 / UTM Zone 23S (EPSG:31983) for accurate meter-based buffer calculation
    # Araraquara is EPSG:31983
    gdf_units_utm = gdf_units.to_crs(epsg=31983)
    gdf_climate_utm = gdf_climate.to_crs(epsg=31983)
    
    print("Creating 300m buffers around healthcare units...")
    # 300 meter buffer as specified by user
    BUFFER_RADIUS = 300
    gdf_units_utm["buffer_geometry"] = gdf_units_utm.geometry.buffer(BUFFER_RADIUS)
    
    analyzed_units = []
    
    for idx, row in gdf_units_utm.iterrows():
        unit_buf = row["buffer_geometry"]
        unit_id = row["id"]
        unit_name = row["name"]
        unit_type = row["type"]
        lat = row["lat"]
        lon = row["lon"]
        suburb = row["suburb"]
        
        # Spatial intersection with climate polygons
        intersecting = gdf_climate_utm[gdf_climate_utm.intersects(unit_buf)]
        
        if len(intersecting) > 0:
            # Weighted averages based on intersection area
            temps, ndvis, vulns = [], [], []
            weights = []
            
            for _, c_row in intersecting.iterrows():
                overlap_area = unit_buf.intersection(c_row.geometry).area
                if overlap_area > 0:
                    weights.append(overlap_area)
                    temps.append(c_row["surface_temp"])
                    ndvis.append(c_row["ndvi"])
                    vulns.append(c_row["vulnerability_score"])
                    
            total_weight = sum(weights) if sum(weights) > 0 else 1.0
            avg_temp = round(sum(t * w for t, w in zip(temps, weights)) / total_weight, 2)
            avg_ndvi = round(sum(n * w for n, w in zip(ndvis, weights)) / total_weight, 2)
            avg_vuln = round(sum(v * w for v, w in zip(vulns, weights)) / total_weight, 2)
        else:
            avg_temp = 31.0
            avg_ndvi = 0.35
            avg_vuln = 3.0
            
        analyzed_units.append({
            "id": unit_id,
            "name": unit_name,
            "type": unit_type,
            "suburb": suburb,
            "lat": lat,
            "lon": lon,
            "surface_temp_300m": avg_temp,
            "ndvi_300m": avg_ndvi,
            "vulnerability_score_300m": avg_vuln
        })
        
    df_res = pd.DataFrame(analyzed_units)
    
    # Calculate Normalized Scores for Index (IECS)
    min_t, max_t = df_res["surface_temp_300m"].min(), df_res["surface_temp_300m"].max()
    min_n, max_n = df_res["ndvi_300m"].min(), df_res["ndvi_300m"].max()
    min_v, max_v = df_res["vulnerability_score_300m"].min(), df_res["vulnerability_score_300m"].max()
    
    # Avoid division by zero
    t_range = (max_t - min_t) if max_t > min_t else 1.0
    n_range = (max_n - min_n) if max_n > min_n else 1.0
    v_range = (max_v - min_v) if max_v > min_v else 1.0
    
    # Compute IECS (Índice de Exposição Climática e Social) on a 0-100 scale
    # Temp weight: 45%, Low NDVI weight: 25%, Social Vulnerability weight: 30%
    norm_temp = (df_res["surface_temp_300m"] - min_t) / t_range
    norm_low_ndvi = (max_n - df_res["ndvi_300m"]) / n_range
    norm_vuln = (df_res["vulnerability_score_300m"] - min_v) / v_range
    
    df_res["iecs_score"] = (norm_temp * 0.45 + norm_low_ndvi * 0.25 + norm_vuln * 0.30) * 100.0
    df_res["iecs_score"] = df_res["iecs_score"].round(1)
    
    # Assign Risk Category based on IECS score
    def get_risk_level(score):
        if score >= 75.0:
            return "Crítico (Altíssimo Risco)"
        elif score >= 55.0:
            return "Alto"
        elif score >= 35.0:
            return "Moderado"
        else:
            return "Baixo / Confortável"
            
    df_res["risk_level"] = df_res["iecs_score"].apply(get_risk_level)
    
    # Sort by risk score descending
    df_res = df_res.sort_values(by="iecs_score", ascending=False).reset_index(drop=True)
    df_res["ranking"] = df_res.index + 1
    
    print(f"Top 5 Most Impacted Healthcare Units in Araraquara (300m buffer):")
    for _, r in df_res.head(5).iterrows():
        print(f"#{r['ranking']} | {r['name']} [{r['type']}] - Temp: {r['surface_temp_300m']}°C, NDVI: {r['ndvi_300m']}, Vulnerability: {r['vulnerability_score_300m']}, IECS Score: {r['iecs_score']}")
        
    # Save CSV
    df_res.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"Ranking CSV saved to {OUTPUT_CSV}")
    
    # Create GeoJSON with updated properties
    features = []
    for _, row in df_res.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["lon"], row["lat"]]
            },
            "properties": row.to_dict()
        })
        
    geojson_out = {
        "type": "FeatureCollection",
        "features": features
    }
    with open(OUTPUT_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(geojson_out, f, ensure_ascii=False, indent=2)
    print(f"Analyzed GeoJSON saved to {OUTPUT_GEOJSON}")
    
    # Summary stats
    summary = {
        "total_units_analyzed": len(df_res),
        "buffer_radius_meters": BUFFER_RADIUS,
        "avg_surface_temp_araraquara": round(df_res["surface_temp_300m"].mean(), 2),
        "max_surface_temp": df_res["surface_temp_300m"].max(),
        "min_surface_temp": df_res["surface_temp_300m"].min(),
        "avg_ndvi": round(df_res["ndvi_300m"].mean(), 2),
        "units_by_risk_level": df_res["risk_level"].value_counts().to_dict(),
        "top_5_critical_units": df_res.head(5)[["ranking", "name", "type", "suburb", "surface_temp_300m", "ndvi_300m", "iecs_score", "risk_level"]].to_dict(orient="records")
    }
    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Summary stats saved to {OUTPUT_SUMMARY}")

if __name__ == "__main__":
    run_spatial_analysis()
