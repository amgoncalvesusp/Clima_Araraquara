import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
HTML_SRC = os.path.join(BASE_DIR, "mapa_interativo_araraquara.html")
HTML_DST = os.path.join(BASE_DIR, "index.html")

with open(HTML_SRC, "r", encoding="utf-8") as f:
    content = f.read()

with open(HTML_DST, "w", encoding="utf-8") as f:
    f.write(content)

print("index.html updated successfully!")
