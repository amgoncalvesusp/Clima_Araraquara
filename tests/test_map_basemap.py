import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MapBasemapTest(unittest.TestCase):
    def test_map_uses_public_osm_tiles_without_cartos_api_key(self):
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png"', app)
        self.assertIn('&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', app)
        self.assertNotIn("basemaps.cartocdn.com", app)
        self.assertNotIn("carto.com/attributions", app)


if __name__ == "__main__":
    unittest.main()
