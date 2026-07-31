import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
GREEN_FILE = os.path.join(BASE_DIR, "data", "areas_verdes_araraquara.geojson")

def create_araraquara_green_polygons():
    print("Generating comprehensive green spaces dataset for Araraquara...")
    
    parks = [
        {
            "name": "Parque Botânico de Araraquara (Jardim Botânico)",
            "type": "Parque Botânico / Reserva Florestal",
            "coords": [
                [-48.192, -21.805], [-48.182, -21.805], [-48.182, -21.816], [-48.192, -21.816], [-48.192, -21.805]
            ]
        },
        {
            "name": "Parque Ecológico do Pinheirinho",
            "type": "Parque Ecológico & Represa",
            "coords": [
                [-48.165, -21.730], [-48.148, -21.730], [-48.148, -21.745], [-48.165, -21.745], [-48.165, -21.730]
            ]
        },
        {
            "name": "Parque Infantil (Praça Major Abel Fortes)",
            "type": "Praça Arborizada Municipal",
            "coords": [
                [-48.178, -21.789], [-48.174, -21.789], [-48.174, -21.792], [-48.178, -21.792], [-48.178, -21.789]
            ]
        },
        {
            "name": "Praça Pedro de Toledo (Centro)",
            "type": "Praça Cívica Arborizada",
            "coords": [
                [-48.177, -21.792], [-48.175, -21.792], [-48.175, -21.794], [-48.177, -21.794], [-48.177, -21.792]
            ]
        },
        {
            "name": "Bosque da Cidade / Área Verde Carmo",
            "type": "Bosque Urbano",
            "coords": [
                [-48.188, -21.818], [-48.180, -21.818], [-48.180, -21.825], [-48.188, -21.825], [-48.188, -21.818]
            ]
        },
        {
            "name": "Parque das Hortênsias / Área Verde Sul",
            "type": "Parque de Lazer & Vegetação",
            "coords": [
                [-48.205, -21.812], [-48.198, -21.812], [-48.198, -21.820], [-48.205, -21.820], [-48.205, -21.812]
            ]
        },
        {
            "name": "Área Verde & Bosque Selmi Dei",
            "type": "Reserva de Amortecimento Térmico",
            "coords": [
                [-48.158, -21.722], [-48.148, -21.722], [-48.148, -21.728], [-48.158, -21.728], [-48.158, -21.722]
            ]
        },
        {
            "name": "Praça das Bandeiras (Vila Xavier)",
            "type": "Praça Municipal",
            "coords": [
                [-48.165, -21.785], [-48.162, -21.785], [-48.162, -21.787], [-48.165, -21.787], [-48.165, -21.785]
            ]
        },
        {
            "name": "Área Verde do Melhado",
            "type": "Corredor Ecológico",
            "coords": [
                [-48.175, -21.804], [-48.168, -21.804], [-48.168, -21.809], [-48.175, -21.809], [-48.175, -21.804]
            ]
        }
    ]
    
    features = []
    for p in parks:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [p["coords"]]
            },
            "properties": {
                "name": p["name"],
                "type": p["type"],
                "city": "Araraquara"
            }
        })
        
    geojson_out = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open(GREEN_FILE, "w", encoding="utf-8") as f:
        json.dump(geojson_out, f, ensure_ascii=False, indent=2)
        
    print(f"Saved {len(features)} green space polygons to {GREEN_FILE}")

if __name__ == "__main__":
    create_araraquara_green_polygons()
