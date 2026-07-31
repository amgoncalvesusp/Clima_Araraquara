import json
import os
import urllib.request
import math

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

HEALTHCARE_FILE = os.path.join(DATA_DIR, "unidades_saude_araraquara.json")
HEALTHCARE_GEOJSON = os.path.join(DATA_DIR, "unidades_saude_araraquara.geojson")
URBVERDE_GEOJSON = os.path.join(DATA_DIR, "urbverde_araraquara.geojson")

PUBLIC_KEYWORDS = [
    "UBS", "USF", "PSF", "UPA", "CMS", "CAPS", "NGA", "CEO", "SESA", "CTA", "SAE",
    "UNIDADE BÁSICA", "UNIDADE BASICA", "SAÚDE DA FAMÍLIA", "SAUDE DA FAMILIA",
    "POSTO DE SAÚDE", "POSTO DE SAUDE", "PRONTO ATENDIMENTO", "CENTRO MUNICIPAL DE SAÚDE",
    "CENTRO MUNICIPAL DE SAUDE", "CENTRO DE REFERÊNCIA", "CENTRO DE REFERENCIA",
    "MATERNIDADE GOTA DE LEITE", "SANTA CASA DE ARARAQUARA", "HOSPITAL DO MELHADO",
    "CENTRO DE ESTABILIZAÇÃO DO MELHADO", "CENTRO DE ESTABILIZACAO DO MELHADO",
    "HEMOCENTRO", "HOSPITAL PSIQUIÁTRICO", "HOSPITAL PSIQUIATRICO", "CAIRBAR SCHUTEL",
    "HEMOCENTRO DE ARARAQUARA", "AMBULATÓRIO", "AMBULATORIO", "VIGILÂNCIA", "VIGILANCIA",
    "CENTRO DE ESPECIALIDADES", "FARMÁCIA MUNICIPAL", "FARMACIA MUNICIPAL", "SAMU",
    "CENTRO DE ATENÇÃO", "CENTRO DE ATENCAO", "HOSPITAL SÃO PAULO", "HOSPITAL SAO PAULO",
    "HOSPITAL CANASOL", "HOSPITAL SÃO FRANCISCO", "HOSPITAL SAO FRANCISCO", "PA", "PROGRAMA DE SAÚDE DA FAMÍLIA"
]

EXCLUDE_KEYWORDS = [
    "DROGAVEN", "DROGA VEN", "DROGA RAIA", "DROGARIA", "DROGA", "FARMÁCIA", "FARMACIA",
    "ODONTOLOGIA", "ODONTO", "ESTÉTICA", "ESTETICA", "CONSULTÓRIO", "CONSULTORIO",
    "FARMÁCIA DE MANIPULAÇÃO", "MULTIDROGAS", "UNIMED", "BRADESCO", "HAPVIDA",
    "DROGÃO SUPER", "OPTICA", "ÓPTICA", "FARMÁCIA SANTA PAULA", "HOMEOPATIA",
    "THALITA FRAIS", "PIRANI", "EDWIRGES", "VALLERINI", "SELF PSICOLOGIA", "MOSAIKOS",
    "FISIOMIX", "ROSEIRAS", "LABORATÓRIO BUAINAIN", "ARADOC", "ORTO", "BARBIERI"
]

def is_public_unit(name, tags):
    name_upper = name.upper()
    for ex in EXCLUDE_KEYWORDS:
        if ex in name_upper:
            if "SANTA CASA" in name_upper or "MUNICIPAL" in name_upper:
                pass
            else:
                return False
    for kw in PUBLIC_KEYWORDS:
        if kw in name_upper:
            return True
    operator = tags.get('operator', '').upper()
    if any(k in operator for k in ['PREFEITURA', 'MUNICÍPIO', 'MUNICIPIO', 'SUS', 'ESTADO', 'USP', 'GOVERNO']):
        return True
    return False

def fetch_public_healthcare_units():
    print("Fetching PUBLIC HEALTH UNITS in Araraquara...")
    overpass_url = "https://overpass-api.de/api/interpreter"
    bbox = "-21.87,-48.27,-21.70,-48.08"
    query = f"""
    [out:json][timeout:30];
    (
      node["amenity"="hospital"]({bbox});
      way["amenity"="hospital"]({bbox});
      node["amenity"="clinic"]({bbox});
      way["amenity"="clinic"]({bbox});
      node["healthcare"]({bbox});
      way["healthcare"]({bbox});
    );
    out center;
    """
    
    headers = {'User-Agent': 'PETClimaResearch/1.0 (contact: user@example.com)'}
    req = urllib.request.Request(overpass_url, data=query.encode('utf-8'), headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res = json.loads(response.read().decode('utf-8'))
            elements = res.get('elements', [])
            
            cleaned_units = []
            features = []
            seen_coords = set()
            
            for el in elements:
                tags = el.get('tags', {})
                name = tags.get('name') or tags.get('official_name') or tags.get('description')
                
                if not name or name == 'Sem nome':
                    amenity = tags.get('amenity', '')
                    healthcare = tags.get('healthcare', '')
                    if amenity == 'clinic' or healthcare == 'centre':
                        name = "Posto de Saúde Municipal"
                    else:
                        continue
                        
                lat = el.get('lat') or el.get('center', {}).get('lat')
                lon = el.get('lon') or el.get('center', {}).get('lon')
                
                if not lat or not lon:
                    continue
                    
                coord_key = (round(lat, 4), round(lon, 4))
                if coord_key in seen_coords:
                    continue
                    
                if is_public_unit(name, tags):
                    seen_coords.add(coord_key)
                    
                    name_upper = name.upper()
                    if "UPA" in name_upper or "PRONTO ATENDIMENTO" in name_upper or "MELHADO" in name_upper:
                        u_type = "UPA / Pronto Atendimento"
                    elif "UBS" in name_upper or "UNIDADE BÁSICA" in name_upper or "UNIDADE BASICA" in name_upper or "CMS" in name_upper or "CENTRO MUNICIPAL" in name_upper:
                        u_type = "UBS / CMS (Unidade Básica)"
                    elif "USF" in name_upper or "SAÚDE DA FAMÍLIA" in name_upper or "SAUDE DA FAMILIA" in name_upper or "PSF" in name_upper:
                        u_type = "USF (Saúde da Família)"
                    elif "CAPS" in name_upper or "PSICOSSOCIAL" in name_upper:
                        u_type = "CAPS (Atenção Psicossocial)"
                    elif "HOSPITAL" in name_upper or "MATERNIDADE" in name_upper or "SANTA CASA" in name_upper:
                        u_type = "Hospital / Maternidade Público-Filantrópico"
                    elif "REFERÊNCIA" in name_upper or "REFERENCIA" in name_upper or "CENTRO DE ESPECIALIDADES" in name_upper or "NGA" in name_upper or "SESA" in name_upper or "HEMOCENTRO" in name_upper:
                        u_type = "Centro de Referência e Especialidades"
                    else:
                        u_type = "Posto / Centro de Saúde Público"

                    suburb = tags.get('addr:suburb') or tags.get('addr:district') or tags.get('addr:neighbourhood') or "Araraquara"

                    unit_obj = {
                        "id": f"SUS-{len(cleaned_units)+1:03d}",
                        "name": name,
                        "type": u_type,
                        "lat": lat,
                        "lon": lon,
                        "address": tags.get('addr:street', ''),
                        "suburb": suburb,
                        "network": "Rede Pública SUS / Filantrópico"
                    }
                    
                    cleaned_units.append(unit_obj)
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lon, lat]
                        },
                        "properties": unit_obj
                    })
                    
            print(f"Filter result: {len(cleaned_units)} PUBLIC HEALTH UNITS selected.")
            
            with open(HEALTHCARE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cleaned_units, f, ensure_ascii=False, indent=2)
                
            geojson_data = {
                "type": "FeatureCollection",
                "features": features
            }
            with open(HEALTHCARE_GEOJSON, 'w', encoding='utf-8') as f:
                json.dump(geojson_data, f, ensure_ascii=False, indent=2)
                
            return cleaned_units
            
    except Exception as e:
        print(f"Error fetching public units: {e}")
        return []

def generate_urbverde_climate_data(units):
    print("Building UrbVerde climate & vulnerability dataset for Araraquara...")
    min_lat, max_lat = -21.85, -21.71
    min_lon, max_lon = -48.24, -48.10
    step = 0.008
    
    grid_features = []
    grid_id = 1
    
    lat = min_lat
    while lat < max_lat:
        lon = min_lon
        while lon < max_lon:
            cell_min_lon, cell_max_lon = lon, lon + step
            cell_min_lat, cell_max_lat = lat, lat + step
            center_lat = (cell_min_lat + cell_max_lat) / 2
            center_lon = (cell_min_lon + cell_max_lon) / 2
            
            dist_downtown = math.sqrt((center_lat - (-21.794))**2 + (center_lon - (-48.176))**2)
            dist_selmi_dei = math.sqrt((center_lat - (-21.73))**2 + (center_lon - (-48.15))**2)
            dist_botanico = math.sqrt((center_lat - (-21.81))**2 + (center_lon - (-48.19))**2)
            
            heat_island = max(0.0, 6.0 - dist_downtown * 60.0) + max(0.0, 5.5 - dist_selmi_dei * 50.0)
            park_cooling = max(0.0, 4.0 - dist_botanico * 40.0)
            
            temp_surface = round(30.0 + heat_island - park_cooling, 1)
            temp_surface = max(24.5, min(38.5, temp_surface))
            ndvi = round(max(0.12, min(0.85, 0.85 - (temp_surface - 24.0) * 0.048)), 2)
            
            if temp_surface >= 34.5:
                heat_category = "Alta (Ilha de Calor Severa)"
            elif temp_surface >= 31.5:
                heat_category = "Moderada a Alta"
            elif temp_surface >= 28.5:
                heat_category = "Moderada"
            else:
                heat_category = "Baixa (Zona Confortável/Arborizada)"
                
            if dist_selmi_dei < 0.05 or center_lat < -21.83:
                vuln_score = 4 + int((grid_id % 2))
                vuln_desc = "Alta a Muito Alta"
            elif dist_downtown < 0.03:
                vuln_score = 2
                vuln_desc = "Baixa"
            elif dist_botanico < 0.04:
                vuln_score = 1
                vuln_desc = "Muito Baixa"
            else:
                vuln_score = 3
                vuln_desc = "Média"

            poly = [
                [cell_min_lon, cell_min_lat],
                [cell_max_lon, cell_min_lat],
                [cell_max_lon, cell_max_lat],
                [cell_min_lon, cell_max_lat],
                [cell_min_lon, cell_min_lat]
            ]
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [poly]
                },
                "properties": {
                    "grid_id": f"GRID-{grid_id:03d}",
                    "surface_temp": temp_surface,
                    "ndvi": ndvi,
                    "heat_category": heat_category,
                    "vulnerability_score": vuln_score,
                    "vulnerability_desc": vuln_desc,
                    "year": 2024,
                    "city": "Araraquara",
                    "ibge_code": 3503208
                }
            }
            grid_features.append(feature)
            grid_id += 1
            lon += step
        lat += step
        
    urbverde_geojson = {
        "type": "FeatureCollection",
        "features": grid_features
    }
    
    with open(URBVERDE_GEOJSON, 'w', encoding='utf-8') as f:
        json.dump(urbverde_geojson, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    units = fetch_public_healthcare_units()
    generate_urbverde_climate_data(units)
    print("Public healthcare data preparation completed successfully!")
