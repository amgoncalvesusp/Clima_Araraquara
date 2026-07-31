# 🌿 PET Clima Araraquara: Análise Espacial de Risco Climático e Vulnerabilidade nas Unidades de Saúde

Este projeto realiza a sobreposição e correlação geográfica entre a **Rede de Atenção à Saúde de Araraquara/SP** (UBS, USF, UPA, CMS e Hospitais) e os dados socioambientais e microclimáticos da plataforma **UrbVerde (USP)**.

---

## 🎯 Objetivos do Estudo

1. **Identificar Microclimas Críticos:** Mapear quais postos de saúde estão localizados em **ilhas de calor intensas (temperatura de superfície elevada)** e em áreas com **baixa cobertura vegetal (NDVI baixo)**.
2. **Buffer de Influência de 300 Metros:** Analisar o raio de 300m de caminhada ao redor de cada posto para compreender o conforto térmico do entorno imediato da comunidade atendida.
3. **Índice de Exposição Climática e Social (IECS):** Ranquear as 95 unidades de saúde considerando:
   - **45%** Peso da Temperatura de Superfície (°C)
   - **25%** Peso da Falta de Vegetação (1 - NDVI)
   - **30%** Peso da Vulnerabilidade Social / Demográfica do Bairro (IPVS)
4. **Subsidiar Políticas Públicas:** Orientar a implantação de Soluções Baseadas na Natureza (SbN), arborização urbana e climatização prioritária nos postos mais críticos.

---

## 📊 Principais Achados (Araraquara/SP)

* **Total de Unidades Analisadas:** 95 postos e centros de saúde.
* **Temperatura Média no Entorno (300m):** 32.4°C.
* **Temperatura Máxima Registrada:** 36.7°C (Regiões Norte/Noroeste, como Valle Verde, Selmi Dei e Cecap).
* **Unidades de Altíssimo Risco (Top 5 Críticas):**
  1. **CAPS AD Dr. Calil Buainain** (IECS: 100.0 | Temp: 36.7°C | NDVI: 0.24)
  2. **USF Roxo** (IECS: 99.8 | Temp: 36.7°C | NDVI: 0.24)
  3. **UPA Valle Verde** (IECS: 96.2 | Temp: 36.5°C | NDVI: 0.25)
  4. **USF Parque das Laranjeiras** (IECS: 94.1 | Temp: 36.3°C | NDVI: 0.26)
  5. **CMS Cecap** (IECS: 92.5 | Temp: 36.1°C | NDVI: 0.26)

---

## 📂 Estrutura do Projeto

```text
PET clima/
├── data/
│   ├── unidades_saude_araraquara.geojson       # Geometria dos postos de saúde (OSM/CNES)
│   ├── urbverde_araraquara.geojson            # Grade microclimática UrbVerde (USP)
│   ├── unidades_saude_analise_araraquara.geojson # Resultado consolidado com IECS e buffers
│   ├── ranking_risco_termico.csv              # Tabela completa de ranking
│   └── resumo_estatistico.json                # Resumo das métricas do município
├── scripts/
│   ├── fetch_data.py                           # Coleta e geração da malha
│   ├── spatial_analysis.py                     # Geoprocessamento e cálculo dos buffers de 300m
│   └── generate_charts.py                      # Geração dos gráficos analíticos
├── web/
│   └── charts/                                # Gráficos salvos em PNG
├── css/
│   └── styles.css                             # Estilização do Dashboard Web
├── js/
│   └── app.js                                 # Lógica do Mapa Interativo Leaflet
├── index.html                                 # Dashboard Web Principal
└── requirements.txt                           # Dependências Python
```

---

## 🚀 Como Executar

### 1. Requisitos
* Python 3.10+
* Navegador Web Moderno (Chrome, Edge, Firefox)

### 2. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 3. Rodar Análise Geográfica e Gráficos
```bash
python scripts/fetch_data.py
python scripts/spatial_analysis.py
python scripts/generate_charts.py
```

### 4. Abrir o Dashboard Web Interativo
Abra o arquivo `index.html` diretamente no seu navegador ou inicie um servidor HTTP simples:
```bash
python -m http.server 8000
```
Acesse em: `http://localhost:8000`
