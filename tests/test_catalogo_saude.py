import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class CatalogoSaudeTest(unittest.TestCase):
    def read_json(self, filename):
        with (DATA / filename).open(encoding="utf-8") as file:
            return json.load(file)

    def test_pending_catalog_has_two_candidates_and_no_analysis_values(self):
        candidates = self.read_json("unidades_sugeridas_araraquara.json")

        self.assertEqual(len(candidates), 2)
        self.assertTrue(all(item["status"] == "pendente_validacao" for item in candidates))
        self.assertTrue(all(item["incluir_no_ranking"] is False for item in candidates))
        self.assertTrue(all(item["lat"] is None and item["lon"] is None for item in candidates))
        self.assertTrue(all(item["source_url"] for item in candidates))
        self.assertEqual({item["id"] for item in candidates}, {"PEND-002", "PEND-004"})

    def test_current_catalog_classifies_non_municipal_records(self):
        metadata = self.read_json("metadata_unidades_saude_araraquara.json")
        non_municipal = {
            unit_id
            for unit_id, item in metadata.items()
            if item["network_scope"] != "municipal"
        }

        self.assertEqual(
            non_municipal,
            {"SUS-011", "SUS-012", "SUS-020", "SUS-021", "SUS-022", "SUS-027", "SUS-028"},
        )

    def test_public_sources_have_required_fields(self):
        sources = self.read_json("fontes_publicas_saude_araraquara.json")

        self.assertGreaterEqual(len(sources), 5)
        for source in sources:
            self.assertTrue(source["title"])
            self.assertTrue(source["url"])
            self.assertTrue(source["use"])

    def test_combined_catalog_keeps_pending_records_out_of_analysis(self):
        catalog = self.read_json("unidades_saude_araraquara.json")
        analyzed_geojson = self.read_json("unidades_saude_araraquara.geojson")

        self.assertEqual(len(catalog), 53)
        self.assertEqual(len(analyzed_geojson["features"]), 51)
        self.assertEqual(
            sum(item["record_status"] == "pendente_validacao" for item in catalog),
            2,
        )

    def test_santa_angelina_is_present_in_the_analyzed_network(self):
        catalog = self.read_json("unidades_saude_araraquara.json")
        analyzed = self.read_json("unidades_saude_analise_araraquara.geojson")
        santa = next(item for item in catalog if item["id"] == "SUS-042")
        santa_analysis = next(
            feature["properties"]
            for feature in analyzed["features"]
            if feature["properties"]["id"] == "SUS-042"
        )

        self.assertEqual(santa["cnes"], "2063247")
        self.assertEqual(santa["suburb"], "Santa Angelina")
        self.assertEqual(santa_analysis["record_status"] if "record_status" in santa_analysis else "analisado", "analisado")
        self.assertTrue(santa_analysis["surface_temp_300m"])

    def test_confirmed_units_have_cnes_coordinates_and_analysis_records(self):
        catalog = self.read_json("unidades_saude_araraquara.json")
        analyzed = self.read_json("unidades_saude_analise_araraquara.geojson")
        analyzed_ids = {feature["properties"]["id"] for feature in analyzed["features"]}
        promoted_ids = {
            "SUS-043",
            "SUS-044",
            "SUS-045",
            "SUS-046",
            "SUS-047",
            "SUS-048",
            "SUS-049",
            "SUS-050",
            "SUS-051",
            "SUS-052",
        }

        for unit in catalog:
            if unit["id"] in promoted_ids or unit["id"] == "SUS-007":
                self.assertEqual(unit["record_status"], "analisado")
                self.assertTrue(unit["cnes"])
                self.assertIsNotNone(unit["lat"])
                self.assertIsNotNone(unit["lon"])
                self.assertIn(unit["id"], analyzed_ids)

    def test_history_and_hydrology_layers_have_traceable_coverage(self):
        history = self.read_json("historico_risco_termico_araraquara.json")
        hydrology = self.read_json("pontos_risco_hidrologico_araraquara.geojson")

        self.assertEqual(history["history_years"], [2016, 2017, 2018, 2019, 2020, 2021])
        self.assertEqual(len(history["units"]), 51)
        self.assertEqual(len(hydrology["features"]), 23)
        self.assertEqual(hydrology["metadata"]["count_geocoded_for_map"], 23)
        self.assertIn("a_286_0_1_22012026101246.pdf", hydrology["metadata"]["source_url"])
        self.assertTrue(all(len(unit["values"]) == 6 for unit in history["units"]))

    def test_census_layer_is_local_and_explicitly_composite(self):
        census = self.read_json("censo_2022_vulnerabilidade_araraquara.geojson")
        self.assertGreaterEqual(len(census["features"]), 500)
        self.assertTrue(all(feature["properties"]["vulnerability_source"] for feature in census["features"]))
        scores = [feature["properties"]["vulnerability_score_5"] for feature in census["features"] if feature["properties"]["vulnerability_score_5"] is not None]
        self.assertGreater(len(scores), 500)
        self.assertTrue(all(0 <= score <= 5 for score in scores))
        metadata = self.read_json("censo_2022_vulnerabilidade_araraquara.metadata.json")
        self.assertFalse(metadata["score_is_official"])

    def test_sensitivity_has_comparable_scenarios(self):
        sensitivity = self.read_json("sensibilidade_iecs_araraquara.json")
        self.assertEqual(sensitivity["default_scenario"], "balanced")
        self.assertGreaterEqual(len(sensitivity["scenarios"]), 5)
        for scenario in sensitivity["scenarios"]:
            self.assertAlmostEqual(sum(scenario["weights"].values()), 1, places=3)
            self.assertEqual(len(scenario["units"]), 51)
            self.assertEqual(len(scenario["top_5"]), 5)

    def test_health_outcomes_are_aggregate_and_traceable(self):
        outcomes = self.read_json("desfechos_saude_araraquara.json")
        self.assertEqual(outcomes["coverage"]["system"], "SIH/SUS")
        self.assertEqual(outcomes["coverage"]["months"], 12)
        self.assertGreater(outcomes["coverage"]["records_after_municipality_filter"], 0)
        self.assertEqual(outcomes["ambulatory_attendance"]["status"], "not_loaded")
        self.assertTrue(all("hospitalizations_total" in item for item in outcomes["series"]))

    def test_historical_health_explorer_covers_every_published_year(self):
        explorer = self.read_json("dados_historicos_saude_araraquara.json")
        coverage = explorer["coverage"]

        self.assertEqual(coverage["years"][0], 2016)
        self.assertGreaterEqual(coverage["end_year"], 2026)
        self.assertEqual(coverage["years"], list(range(2016, coverage["end_year"] + 1)))
        # Um ano so pode ser declarado completo quando os doze meses foram publicados.
        self.assertEqual(coverage["months_requested"], sum(coverage["months_by_year"].values()))
        self.assertEqual(
            sorted(coverage["partial_years"]),
            sorted(int(year) for year, months in coverage["months_by_year"].items() if months < 12),
        )
        self.assertTrue(explorer["hospital"]["source_url"])
        self.assertTrue(explorer["ambulatory"]["source_url"])
        self.assertGreater(len(explorer["hospital"]["unit_year"]), 1000)
        self.assertGreater(
            sum(bool(item.get("cnes")) for item in explorer["hospital"]["unit_year"]),
            1000,
        )
        self.assertGreater(len(explorer["hospital"]["chapters_year"]), 100)
        self.assertGreater(len(explorer["ambulatory"]["groups_year"]), 50)
        self.assertTrue(any("privada" in limitation for limitation in explorer["limitations"]))

    def test_health_explorer_exposes_xlsx_export_and_analytical_views(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("xlsx-0.20.3/package/dist/xlsx.full.min.js", html)
        self.assertIn('id="health-download-xlsx"', html)
        self.assertIn('id="health-data-visuals"', html)
        self.assertIn("function downloadHealthDataXlsx", app)
        self.assertIn("function renderHealthDataVisuals", app)


if __name__ == "__main__":
    unittest.main()
