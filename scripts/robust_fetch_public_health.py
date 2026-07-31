import urllib.request
import json
import re

# Comprehensive list of public health keywords in Brazilian SUS network
PUBLIC_KEYWORDS = [
    "UBS", "USF", "PSF", "UPA", "CMS", "CAPS", "NGA", "CEO", "SESA", "CTA", "SAE",
    "UNIDADE BÁSICA", "UNIDADE BASICA", "SAÚDE DA FAMÍLIA", "SAUDE DA FAMILIA",
    "POSTO DE SAÚDE", "POSTO DE SAUDE", "PRONTO ATENDIMENTO", "CENTRO MUNICIPAL DE SAÚDE",
    "CENTRO MUNICIPAL DE SAUDE", "CENTRO DE REFERÊNCIA", "CENTRO DE REFERENCIA",
    "MATERNIDADE GOTA DE LEITE", "SANTA CASA DE ARARAQUARA", "HOSPITAL DO MELHADO",
    "CENTRO DE ESTABILIZAÇÃO DO MELHADO", "CENTRO DE ESTABILIZACAO DO MELHADO",
    "HEMOCENTRO", "HOSPITAL PSIQUIÁTRICO", "HOSPITAL PSIQUIATRICO", "CAIRBAR SCHUTEL",
    "HEMOCENTRO DE ARARAQUARA", "AMBULATÓRIO", "AMBULATORIO", "VIGILÂNCIA", "VIGILANCIA",
    "CENTRO DE ESPECIALIDADES", "FARMÁCIA MUNICIPAL", "FARMACIA MUNICIPAL"
]

EXCLUDE_KEYWORDS = [
    "DROGAVEN", "DROGA VEN", "DROGA RAIA", "DROGARIA", "DROGA", "FARMÁCIA", "FARMACIA",
    "ODONTOLOGIA", "ODONTO", "ESTÉTICA", "ESTETICA", "CONSULTÓRIO", "CONSULTORIO",
    "FARMÁCIA DE MANIPULAÇÃO", "MULTIDROGAS", "UNIMED", "BRADESCO", "HAPVIDA",
    "DROGÃO SUPER", "OPTICA", "ÓPTICA", "FARMÁCIA SANTA PAULA", "HOMEOPATIA",
    "THALITA FRAIS", "PIRANI", "EDWIRGES", "VALLERINI", "SELF PSICOLOGIA", "MOSAIKOS",
    "FISIOMIX", "ROSEIRAS", "LABORATÓRIO BUAINAIN", "ARADOC"
]

def is_public_health_unit(name, tags):
    name_upper = name.upper()
    
    # Exclude commercial pharmacies & private practices
    for ex in EXCLUDE_KEYWORDS:
        if ex in name_upper:
            # Special exception for Farmácia Municipal or Santa Casa
            if "SANTA CASA" in name_upper or "MUNICIPAL" in name_upper:
                pass
            else:
                return False
                
    # Check public keywords
    for kw in PUBLIC_KEYWORDS:
        if kw in name_upper:
            return True
            
    # Check operator / ownership tags
    operator = tags.get('operator', '').upper()
    if 'PREFEITURA' in operator or 'MUNICÍPIO' in operator or 'MUNICIPIO' in operator or 'SUS' in operator or 'ESTADO' in operator or 'USP' in operator:
        return True
        
    return False

def robust_fetch_public_units():
    print("Executing robust search for PUBLIC HEALTH UNITS (Rede Pública SUS) in Araraquara...")
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Broad bounding box covering entire Araraquara municipality
    bbox = "-21.90,-48.32,-21.68,-48.05"
    query = f"""
    [out:json][timeout:45];
    (
      node["amenity"="hospital"]({bbox});
      way["amenity"="hospital"]({bbox});
      node["amenity"="clinic"]({bbox});
      way["amenity"="clinic"]({bbox});
      node["healthcare"]({bbox});
      way["healthcare"]({bbox});
      node["amenity"="doctors"]({bbox});
      way["amenity"="doctors"]({bbox});
      node["building"="hospital"]({bbox});
      way["building"="hospital"]({bbox});
    );
    out center;
    """
    
    headers = {'User-Agent': 'PETClimaResearch/1.0 (contact: user@example.com)'}
    req = urllib.request.Request(overpass_url, data=query.encode('utf-8'), headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            res = json.loads(response.read().decode('utf-8'))
            elements = res.get('elements', [])
            
            print(f"Total raw OpenStreetMap healthcare elements fetched: {len(elements)}")
            
            public_units = []
            seen_coords = set()
            
            for index, el in enumerate(elements):
                tags = el.get('tags', {})
                name = tags.get('name') or tags.get('official_name') or tags.get('description')
                
                if not name:
                    # Check if tags specify a public center without name
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
                    
                # Deduplicate by coordinate closeness (~20 meters)
                coord_key = (round(lat, 4), round(lon, 4))
                if coord_key in seen_coords:
                    continue
                    
                if is_public_health_unit(name, tags):
                    seen_coords.add(coord_key)
                    
                    name_upper = name.upper()
                    # Classify precise unit category
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

                    public_units.append({
                        "id": f"SUS-{len(public_units)+1:03d}",
                        "name": name,
                        "type": u_type,
                        "lat": lat,
                        "lon": lon,
                        "address": tags.get('addr:street', ''),
                        "suburb": suburb,
                        "network": "Rede Pública SUS"
                    })
                    
            print(f"Successfully identified and filtered {len(public_units)} PUBLIC HEALTH UNITS in Araraquara.")
            return public_units

    except Exception as e:
        print(f"Error executing robust search: {e}")
        return []

if __name__ == "__main__":
    units = robust_fetch_public_units()
    for u in units:
        print(f"- {u['name']} [{u['type']}] ({u['lat']:.4f}, {u['lon']:.4f})")
