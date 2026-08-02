"""Updates the legacy HTML filename from the current app shell.

The app now loads data files at runtime so the catalog and visualisation do not
drift apart. A truly self-contained export should be added separately if it is
needed; this command intentionally keeps the two public entry filenames aligned.
"""

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "index.html"
TARGET = ROOT / "mapa_interativo_araraquara.html"


def build_standalone_html():
    shutil.copyfile(SOURCE, TARGET)
    print(f"Atualizado: {TARGET}")


if __name__ == "__main__":
    build_standalone_html()
