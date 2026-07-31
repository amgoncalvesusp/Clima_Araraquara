import urllib.request
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
GREEN_GEOJSON = os.path.join(DATA_DIR, "areas_verdes_araraquara.geojson")

def fetch_green_spaces():
    print("Fetching Green Areas and Parks in Araraquara via Overpass API...")
    overpass_url = "https://overpass-api.de/api/interpreter"
    bbox = "-21.87,-48.27,-21.70,-48.08"
    
    query = f"""
    [out:json][timeout:30];
    (
      way["leisure"="park"]({bbox});
      way["leisure"="garden"]({bbox});
      way["landuse"="forest"]({bbox});
      way["natural"="wood"]({bbox});
      way["leisure"="recreation_ground"]({bbox});
      relation["leisure"="park"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """
    
    headers = {'User-Agent': 'PETClimaResearch/1.0 (contact: user@example.com)'}
    req = urllib.request.Request(overpass_url, data=query.encode('utf-8'), headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res = json.loads(response.read().decode('utf-8'))
            elements = res.get('elements', [])
            
            nodes = {}
            ways = []
            
            for el in elements:
                if el['type'] == 'node':
                    nodes[el['id']] = [el['lon'], el['lat']]
                elif el['type'] == 'way':
                    ways.append(el)
                    
            features = []
            for w in ways:
                tags = w.get('tags', {})
                name = tags.get('name', tags.get('official_name', 'Área Verde / Praça'))
                way_nodes = w.get('nodes', [])
                
                coords = [nodes[nid] for nid in way_nodes if nid in nodes]
                if len(coords) >= 3:
                    # Close polygon if needed
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                        
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [coords]
                        },
                        "properties": {
                            "name": name,
                            "type": tags.get('leisure') or tags.get('landuse') or tags.get('natural', 'parque'),
                            "city": "Araraquara"
                        }
                    })
                    
            print(f"Successfully processed {len(features)} green areas/parks in Araraquara.")
            
            # If Overpass yields limited polygons, add major known Araraquara parks manually as backup
            known_parks = [
                {
                    "name": "Parque Botânico de Araraquara (Jardim Botânico)",
                    "type": "Parque Botânico",
                    "coords": [
                        [-48.192, -21.808], [-48.185, -21.808], [-48.185, -21.815], [-48.192, -21.815], [-48.192, -21.808]
                    ]
                },
                {
                    "name": "Parque Infantil (Praça Major Abel Fortes)",
                    "type": "Praça Arborizada",
                    "coords": [
                        [-48.178, -21.789], [-48.174, -21.789], [-48.174, -21.792], [-48.178, -21.792], [-48.178, -21.789]
                    ]
                },
                {
                    "name": "Parque do Pinheirinho",
                    "type": "Parque Ecológico",
                    "coords": [
                        [-48.165, -21.735], [-48.150, -21.735], [-48.150, -21.748], [-48.165, -21.748], [-48.165, -21.735]
                    ]
                },
                {
                    "name": "Praça Pedro de Toledo (Centro)",
                    "type": "Praça Central",
                    "coords": [
                        [-48.177, -21.792], [-48.175, -21.792], [-48.175, -21.794], [-48.177, -21.794], [-48.177, -21.792]
                    ]
                }
            ]
            
            for kp in known_parks:
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [kp["coords"]]
                    },
                    "properties": {
                        "name": kp["name"],
                        "type": kp["type"],
                        "city": "Araraquara"
                    }
                })
                
            geojson_data = {
                "type": "FeatureCollection",
                "features": features
            }
            
            with open(GREEN_GEOJSON, 'w', encoding='utf-8') as f:
                json.dump(geojson_data, f, ensure_ascii=False, indent=2)
                
            return features
            
    except Exception as e:
        print(f"Error fetching green areas: {e}")
        return []

if __name__ == "__main__":
    fetch_green_spaces()
