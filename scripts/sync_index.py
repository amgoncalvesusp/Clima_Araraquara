"""Keeps the legacy filename aligned with the current external-data app shell."""

import os
import shutil


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
HTML_SRC = os.path.join(BASE_DIR, "index.html")
HTML_DST = os.path.join(BASE_DIR, "mapa_interativo_araraquara.html")

shutil.copyfile(HTML_SRC, HTML_DST)
print("mapa_interativo_araraquara.html aligned with index.html")
