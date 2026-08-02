import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class CatalogoSaudeTest(unittest.TestCase):
    def read_json(self, filename):
        with (DATA / filename).open(encoding="utf-8") as file:
            return json.load(file)

    def test_pending_catalog_has_fourteen_candidates_and_no_analysis_values(self):
        candidates = self.read_json("unidades_sugeridas_araraquara.json")

        self.assertEqual(len(candidates), 14)
        self.assertTrue(all(item["status"] == "pendente_validacao" for item in candidates))
        self.assertTrue(all(item["incluir_no_ranking"] is False for item in candidates))
        self.assertTrue(all(item["lat"] is None and item["lon"] is None for item in candidates))
        self.assertTrue(all(item["source_url"] for item in candidates))

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

        self.assertEqual(len(catalog), 55)
        self.assertEqual(len(analyzed_geojson["features"]), 41)
        self.assertEqual(
            sum(item["record_status"] == "pendente_validacao" for item in catalog),
            14,
        )


if __name__ == "__main__":
    unittest.main()
