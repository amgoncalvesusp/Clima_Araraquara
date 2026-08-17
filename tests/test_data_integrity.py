import json
import re
import unittest
from math import isclose
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class DataIntegrityTest(unittest.TestCase):
    def read_json(self, filename):
        with (DATA / filename).open(encoding="utf-8") as file:
            return json.load(file)

    def test_unit_geometry_and_coordinate_properties_match(self):
        raw = self.read_json("unidades_saude_araraquara.geojson")
        analysis = self.read_json("unidades_saude_analise_araraquara.geojson")

        self.assertEqual(len(raw["features"]), 52)
        for collection in (raw, analysis):
            for feature in collection["features"]:
                lon, lat = feature["geometry"]["coordinates"]
                self.assertTrue(isclose(float(feature["properties"]["lon"]), lon, abs_tol=1e-8))
                self.assertTrue(isclose(float(feature["properties"]["lat"]), lat, abs_tol=1e-8))

    def test_analysis_declares_climate_and_census_coverage(self):
        analysis = self.read_json("unidades_saude_analise_araraquara.geojson")
        summary = self.read_json("resumo_estatistico.json")
        properties = [feature["properties"] for feature in analysis["features"]]

        self.assertEqual(sum(item["climate_data_quality"] == "urbverde_2024" for item in properties), 50)
        self.assertEqual(sum(item["climate_data_quality"] != "urbverde_2024" for item in properties), 2)
        self.assertTrue(all(item["vulnerability_data_quality"] == "censo_2022" for item in properties))
        self.assertEqual(summary["units_with_climate_fallback"], 2)
        self.assertEqual(summary["units_with_social_imputation"], 0)

    def test_map_uses_ndvi_proxy_and_blue_hydrology(self):
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")

        self.assertNotIn('green: "data/areas_verdes_araraquara.geojson"', app)
        self.assertIn("renderGreenLayer(data.climate)", app)
        self.assertIn("function getNdviColor", app)
        self.assertIn('return "#2563eb";', app)
        self.assertNotIn("#7c3aed", app)
        self.assertIn("Vegetação", html)

    def test_sources_modal_exposes_audit_and_census_fields(self):
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="data-audit"', html)
        self.assertIn("function renderDataAudit", app)
        for field in [
            "census_population_300m",
            "census_income_median_300m",
            "census_share_children_300m",
            "census_share_elderly_300m",
            "census_crowding_300m",
            "vulnerability_score_300m",
        ]:
            self.assertIn(field, app)
        self.assertNotRegex(app, re.compile(r"getFloodColor[\s\S]{0,250}#7c3aed"))


if __name__ == "__main__":
    unittest.main()
