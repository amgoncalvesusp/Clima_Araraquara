import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

UNITS_FILE = os.path.join(DATA_DIR, "unidades_saude_analise_araraquara.geojson")
CLIMATE_FILE = os.path.join(DATA_DIR, "urbverde_araraquara.geojson")
GREEN_FILE = os.path.join(DATA_DIR, "areas_verdes_araraquara.geojson")
SUMMARY_FILE = os.path.join(DATA_DIR, "resumo_estatistico.json")

OUTPUT_HTML = os.path.join(BASE_DIR, "mapa_interativo_araraquara.html")

def build_standalone_html():
    print("Building standalone HTML with Conclusions Tab...")
    
    with open(UNITS_FILE, "r", encoding="utf-8") as f:
        units_geojson = json.load(f)
        
    with open(CLIMATE_FILE, "r", encoding="utf-8") as f:
        climate_geojson = json.load(f)
        
    green_geojson = {"type": "FeatureCollection", "features": []}
    if os.path.exists(GREEN_FILE):
        with open(GREEN_FILE, "r", encoding="utf-8") as f:
            green_geojson = json.load(f)
            
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        summary_data = json.load(f)
        
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>PET Clima Araraquara - Impacto Climático e Conclusões da Análise</title>

  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">

  <!-- Leaflet CSS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />

  <style>
    :root {{
      --bg-dark: #0f172a;
      --bg-card: rgba(30, 41, 59, 0.92);
      --bg-card-hover: rgba(51, 65, 85, 0.95);
      --border-color: rgba(255, 255, 255, 0.12);
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --accent-primary: #10b981;
      --accent-warning: #f59e0b;
      --accent-danger: #ef4444;
      --accent-critical: #dc2626;
      --accent-green: #22c55e;
      --shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.6);
      --font-heading: 'Outfit', sans-serif;
      --font-body: 'Inter', sans-serif;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: var(--font-body);
      background-color: var(--bg-dark);
      color: var(--text-primary);
      height: 100vh; width: 100vw;
      overflow: hidden;
    }}

    .app-container {{
      display: grid;
      grid-template-columns: 400px 1fr;
      grid-template-rows: 64px 1fr;
      height: 100vh; width: 100vw;
    }}

    .app-header {{
      grid-column: 1 / -1;
      background: rgba(15, 23, 42, 0.96);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      display: flex; align-items: center;
      justify-content: space-between;
      padding: 0 24px; z-index: 1000;
    }}

    .brand {{ display: flex; align-items: center; gap: 12px; }}
    .brand-icon {{
      width: 38px; height: 38px;
      background: linear-gradient(135deg, #10b981, #059669);
      border-radius: 10px; display: flex;
      align-items: center; justify-content: center;
      font-size: 20px; box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
    }}

    .brand-title {{
      font-family: var(--font-heading);
      font-size: 20px; font-weight: 700; letter-spacing: -0.5px;
    }}
    .brand-title span {{ color: var(--accent-primary); }}

    .header-actions {{ display: flex; align-items: center; gap: 10px; }}

    .btn-header {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 7px 14px; border-radius: 20px;
      font-size: 12px; font-weight: 600; cursor: pointer;
      display: flex; align-items: center; gap: 6px;
      transition: all 0.2s;
    }}
    .btn-header:hover {{ background: rgba(255, 255, 255, 0.16); border-color: rgba(255, 255, 255, 0.3); }}

    .btn-header.highlight {{
      background: rgba(16, 185, 129, 0.18);
      border-color: var(--accent-primary);
      color: var(--accent-primary);
      font-weight: 700;
    }}
    .btn-header.highlight:hover {{
      background: var(--accent-primary); color: #000;
    }}

    .app-sidebar {{
      background: var(--bg-card);
      backdrop-filter: blur(16px);
      border-right: 1px solid var(--border-color);
      display: flex; flex-direction: column;
      overflow: hidden; z-index: 900;
    }}

    .sidebar-section {{ padding: 14px 18px; border-bottom: 1px solid var(--border-color); }}
    .section-title {{
      font-family: var(--font-heading);
      font-size: 13px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.8px;
      color: var(--text-secondary); margin-bottom: 10px;
    }}

    .kpi-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    .kpi-card {{
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid var(--border-color);
      padding: 10px 12px; border-radius: 8px;
    }}
    .kpi-label {{ font-size: 11px; color: var(--text-secondary); margin-bottom: 3px; }}
    .kpi-value {{ font-family: var(--font-heading); font-size: 19px; font-weight: 700; color: var(--text-primary); }}
    .kpi-value.critical {{ color: var(--accent-danger); }}
    .kpi-value.warning {{ color: var(--accent-warning); }}

    .search-input {{
      width: 100%; background: rgba(15, 23, 42, 0.9);
      border: 1px solid var(--border-color);
      border-radius: 8px; padding: 9px 12px;
      color: var(--text-primary); font-size: 13px; outline: none;
      margin-bottom: 8px;
    }}
    .search-input:focus {{ border-color: var(--accent-primary); }}

    .select-input {{
      flex: 1; background: rgba(15, 23, 42, 0.9);
      border: 1px solid var(--border-color);
      border-radius: 8px; padding: 8px 10px;
      color: var(--text-primary); font-size: 12px; outline: none; cursor: pointer;
    }}

    .units-list-container {{
      flex: 1; overflow-y: auto; padding: 12px 18px;
      display: flex; flex-direction: column; gap: 8px;
    }}
    .units-list-container::-webkit-scrollbar {{ width: 5px; }}
    .units-list-container::-webkit-scrollbar-thumb {{ background: rgba(255, 255, 255, 0.15); border-radius: 3px; }}

    .unit-item {{
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--border-color);
      border-radius: 10px; padding: 10px 12px;
      cursor: pointer; transition: all 0.2s;
      display: flex; flex-direction: column; gap: 5px;
    }}
    .unit-item:hover {{
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.3);
      transform: translateY(-1px);
    }}

    .unit-header {{ display: flex; justify-content: space-between; align-items: center; }}
    .unit-rank {{ font-family: var(--font-heading); font-size: 12px; font-weight: 700; color: var(--accent-primary); }}
    .unit-title {{ font-size: 13px; font-weight: 600; color: var(--text-primary); line-height: 1.3; }}
    .unit-type {{ font-size: 11px; color: var(--text-secondary); }}

    .unit-metrics {{ display: flex; gap: 8px; margin-top: 2px; font-size: 11px; }}
    .metric-pill {{ background: rgba(255, 255, 255, 0.05); padding: 2px 7px; border-radius: 4px; color: var(--text-secondary); }}
    .metric-pill strong {{ color: var(--text-primary); }}

    .risk-tag {{
      font-size: 10px; font-weight: 700; text-transform: uppercase;
      padding: 2px 7px; border-radius: 10px;
    }}
    .risk-tag.critical {{ background: rgba(220, 38, 38, 0.25); color: #fca5a5; border: 1px solid rgba(220, 38, 38, 0.6); }}
    .risk-tag.high {{ background: rgba(245, 158, 11, 0.25); color: #fde047; border: 1px solid rgba(245, 158, 11, 0.6); }}
    .risk-tag.moderate {{ background: rgba(234, 179, 8, 0.2); color: #fef08a; border: 1px solid rgba(234, 179, 8, 0.5); }}
    .risk-tag.low {{ background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.5); }}

    .sidebar-actions {{
      padding: 12px 18px; background: rgba(15, 23, 42, 0.95);
      border-top: 1px solid var(--border-color); display: flex; flex-wrap: wrap; gap: 6px;
    }}
    .btn {{
      flex: 1 1 calc(50% - 6px); background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border-color); color: var(--text-primary);
      padding: 8px; border-radius: 8px; font-size: 11px; font-weight: 600;
      cursor: pointer; transition: all 0.2s; text-align: center;
    }}
    .btn:hover {{ background: rgba(255, 255, 255, 0.16); border-color: rgba(255, 255, 255, 0.3); }}
    .btn.active {{ background: rgba(16, 185, 129, 0.2); border-color: var(--accent-primary); color: var(--accent-primary); }}

    #map {{ width: 100%; height: 100%; background: #0f172a; }}

    .legend-control {{
      background: rgba(15, 23, 42, 0.94);
      backdrop-filter: blur(12px); border: 1px solid var(--border-color);
      padding: 14px; border-radius: 12px; color: var(--text-primary);
      font-size: 11px; width: 260px; box-shadow: var(--shadow);
    }}
    .legend-title {{ font-family: var(--font-heading); font-weight: 700; margin-bottom: 6px; font-size: 12px; color: var(--accent-primary); }}
    .legend-scale {{ height: 8px; border-radius: 4px; background: linear-gradient(to right, #2a9d8f, #e9c46a, #f4a261, #e63946, #d90429); margin-bottom: 5px; }}
    .legend-labels {{ display: flex; justify-content: space-between; font-size: 10px; color: var(--text-secondary); margin-bottom: 10px; }}

    /* Modal Overlay Base */
    .modal-overlay {{
      position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
      background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(8px);
      z-index: 2000; display: none; align-items: center; justify-content: center;
    }}
    .modal-overlay.active {{ display: flex; }}

    .modal-card {{
      background: #0f172a; border: 1px solid var(--border-color);
      border-radius: 16px; width: 840px; max-width: 92vw; max-height: 88vh;
      overflow-y: auto; padding: 28px; box-shadow: var(--shadow);
      display: flex; flex-direction: column; gap: 20px;
    }}
    .modal-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 14px; }}
    .modal-title {{ font-family: var(--font-heading); font-size: 21px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 10px; }}
    .close-btn {{ background: none; border: none; color: var(--text-secondary); font-size: 24px; cursor: pointer; }}
    .close-btn:hover {{ color: var(--text-primary); }}

    /* Conclusions Specific Layout */
    .conclusion-grid {{
      display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 10px;
    }}
    .conclusion-card {{
      background: rgba(30, 41, 59, 0.7); border: 1px solid var(--border-color);
      border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 8px;
    }}
    .conclusion-card-number {{
      font-family: var(--font-heading); font-size: 28px; font-weight: 800; color: var(--accent-primary);
    }}
    .conclusion-card-title {{ font-family: var(--font-heading); font-size: 14px; font-weight: 700; color: var(--text-primary); }}
    .conclusion-card-desc {{ font-size: 12px; color: var(--text-secondary); line-height: 1.4; }}

    .section-block {{
      background: rgba(30, 41, 59, 0.5); border: 1px solid var(--border-color);
      border-radius: 12px; padding: 18px; display: flex; flex-direction: column; gap: 10px;
    }}
    .block-header {{ font-family: var(--font-heading); font-size: 16px; font-weight: 700; color: var(--accent-warning); display: flex; align-items: center; gap: 8px; }}
    .bullet-list {{ display: flex; flex-direction: column; gap: 8px; font-size: 13px; color: var(--text-secondary); line-height: 1.5; padding-left: 20px; }}
    .bullet-list strong {{ color: var(--text-primary); }}
  </style>
</head>
<body>

  <div class="app-container">
    
    <!-- Top Header -->
    <header class="app-header">
      <div class="brand">
        <div class="brand-icon">🌿</div>
        <div>
          <div class="brand-title">PET Clima <span>Araraquara</span></div>
        </div>
      </div>
      
      <div class="header-actions">
        <button class="btn-header highlight" id="btn-open-conclusions">💡 Principais Conclusões</button>
        <button class="btn-header" id="btn-open-help">📖 Legendas (NDVI & IECS)</button>
        <div class="header-badges">
          <div class="badge">Rede: <span>Pública SUS (41 postos)</span></div>
          <div class="badge">Buffer: <span>300m</span></div>
        </div>
      </div>
    </header>

    <!-- Sidebar Dashboard -->
    <aside class="app-sidebar">
      
      <div class="sidebar-section">
        <div class="section-title">Estatísticas da Rede Pública</div>
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">Unidades SUS</div>
            <div class="kpi-value" id="kpi-total">{summary_data.get("total_units_analyzed", 41)}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Temp. Média (300m)</div>
            <div class="kpi-value warning" id="kpi-temp-avg">{summary_data.get("avg_surface_temp_araraquara", 32.6)}°C</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Temp. Máxima</div>
            <div class="kpi-value critical" id="kpi-temp-max">{summary_data.get("max_surface_temp", 36.7)}°C</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Risco Alto / Crítico</div>
            <div class="kpi-value critical" id="kpi-critical">19</div>
          </div>
        </div>
      </div>

      <div class="sidebar-section">
        <div class="section-title">Filtros da Rede Pública</div>
        <input type="text" id="search-input" class="search-input" placeholder="Buscar UBS, UPA, USF ou bairro..." />
        <div style="display: flex; gap: 8px;">
          <select id="filter-type" class="select-input">
            <option value="ALL">Todas as Tipologias</option>
            <option value="UBS / CMS (Unidade Básica)">UBS / CMS</option>
            <option value="USF (Saúde da Família)">USF</option>
            <option value="UPA / Pronto Atendimento">UPA / Melhado</option>
            <option value="CAPS (Atenção Psicossocial)">CAPS</option>
            <option value="Hospital / Maternidade Público-Filantrópico">Hospital / Maternidade</option>
            <option value="Centro de Referência e Especialidades">Especialidades / SESA</option>
          </select>
          <select id="filter-risk" class="select-input">
            <option value="ALL">Todos os Riscos</option>
            <option value="Crítico (Altíssimo Risco)">Crítico</option>
            <option value="Alto">Alto</option>
            <option value="Moderado">Moderado</option>
            <option value="Baixo / Confortável">Baixo</option>
          </select>
        </div>
      </div>

      <div class="units-list-container" id="units-list">
        <!-- JS rendered -->
      </div>

      <div class="sidebar-actions">
        <button class="btn active" id="btn-toggle-climate">🌡️ UrbVerde</button>
        <button class="btn active" id="btn-toggle-green">🌲 Áreas Verdes</button>
        <button class="btn active" id="btn-toggle-buffers">⭕ Buffers 300m</button>
        <button class="btn" id="btn-open-conclusions-sidebar">💡 Conclusões</button>
      </div>

    </aside>

    <!-- Interactive Map -->
    <main style="position: relative;">
      <div id="map"></div>
    </main>

  </div>

  <!-- Modal Component 1: Principais Conclusões da Análise -->
  <div class="modal-overlay" id="conclusions-modal">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">💡 Principais Conclusões da Análise Espacial em Araraquara</div>
        <button class="close-btn" id="btn-close-conclusions">&times;</button>
      </div>

      <!-- KPI Summary Cards -->
      <div class="conclusion-grid">
        <div class="conclusion-card">
          <div class="conclusion-card-number">46.3%</div>
          <div class="conclusion-card-title">Dos Postos em Risco Elevado</div>
          <div class="conclusion-card-desc">19 das 41 unidades públicas de saúde (UBS, USF, UPAs) estão em zonas de Risco Alto ou Crítico de exposição térmica.</div>
        </div>
        <div class="conclusion-card">
          <div class="conclusion-card-number" style="color: var(--accent-danger);">36.7°C</div>
          <div class="conclusion-card-title">Pico Térmico no Entorno</div>
          <div class="conclusion-card-desc">Registrado na região Noroeste (Selmi Dei / Valle Verde / Cecap), onde a ausência de arborização potencializa a ilha de calor.</div>
        </div>
        <div class="conclusion-card">
          <div class="conclusion-card-number" style="color: var(--accent-green);">0.24</div>
          <div class="conclusion-card-title">NDVI Mínimo nas Periferias</div>
          <div class="conclusion-card-desc">Indica vegetação rala ou nula no raio de 300m das unidades de saúde de bairros periféricos mais populosos.</div>
        </div>
      </div>

      <!-- Main Finding 1 -->
      <div class="section-block">
        <div class="block-header">📍 1. Assimetria Geográfica e Justiça Climática Territorial</div>
        <ul class="bullet-list">
          <li><strong>Disparidade Norte-Sul Evidente:</strong> A periferia Norte e Noroeste (Selmi Dei, Valle Verde, Cecap, Laranjeiras) concentra os maiores índices de risco térmico e social. Por outro lado, postos localizados no eixo Centro-Sul (próximos ao Parque Botânico e Jardim Carmo) desfrutam de microclimas até 6°C mais amenos.</li>
          <li><strong>Sobreposição de Vulnerabilidades:</strong> As áreas com menor cobertura vegetal (NDVI &lt; 0.25) coincidem exatamente com os setores censitários do IBGE de maior vulnerabilidade socioeconômica e maior densidade de crianças e idosos.</li>
        </ul>
      </div>

      <!-- Main Finding 2 -->
      <div class="section-block">
        <div class="block-header" style="color: var(--accent-primary);">🌿 2. O Papel Protetor da Infraestrutura Verde</div>
        <ul class="bullet-list">
          <li><strong>Efeito Amortecedor das Áreas Verdes:</strong> Unidades situadas em raio inferior a 500m de grandes parques (como a Santa Casa próxima ao Parque Infantil ou a UBS Carmo perto do Parque Botânico) apresentam temperaturas significativamente menores.</li>
          <li><strong>Falta de Cobertura de Caminhada (300m):** A maioria das USFs de bairros periféricos não possui praças ou vegetação de grande porte num raio de 300m de caminhada do usuário.</li>
        </ul>
      </div>

      <!-- Actionable Directives for Public Health Management -->
      <div class="section-block">
        <div class="block-header" style="color: var(--accent-danger);">🚀 3. Diretrizes de Ação para a Gestão Pública (Prefeitura & SMS Araraquara)</div>
        <ul class="bullet-list">
          <li><strong>1. Arborização Urbana Prioritária:</strong> Plantio imediato de mudas de árvores de médio/grande porte nas calçadas e vias de acesso num raio de 300m das unidades do <strong>Top 5 Crítico</strong> (USF Roxo, UPA Valle Verde, Posto Selmi Dei, PSF Neuza Dicenzo e PSF Adolfo Leão).</li>
          <li><strong>2. Soluções Baseadas na Natureza (SbN) nos Prédios da Saúde:</strong> Implantação de telhados verdes, pergolados arborizados nas salas de espera externas e jardins de chuva no pátio dos postos.</li>
          <li><strong>3. Climatização & Salas de Hidratação para Ondas de Calor:</strong> Instalação prioritária de ar-condicionado e bebedouros de alta capacidade para atendimento de idosos e crianças com desidratação ou complicações respiratórias durante ondas de calor extremo.</li>
        </ul>
      </div>
    </div>
  </div>

  <!-- Modal Component 2: Explanatory Legends for NDVI & IECS -->
  <div class="modal-overlay" id="help-modal">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">📖 Guia de Legendas & Indicadores Climáticos</div>
        <button class="close-btn" id="btn-close-help">&times;</button>
      </div>

      <div class="info-box">
        <div class="info-box-title ndvi">
          <span>🌿</span> NDVI (Normalized Difference Vegetation Index - Índice de Vegetação)
        </div>
        <div class="info-text">
          O <strong>NDVI</strong> mede o vigor e a densidade da vegetação a partir de sensoriamento remoto (satélites NASA/Sentinel). Varia de <strong>0.00 a 1.00</strong>:
        </div>
        <table class="scale-table">
          <thead>
            <tr><th>Valores NDVI</th><th>Significado Físico</th><th>Impacto Térmico</th></tr>
          </thead>
          <tbody>
            <tr><td><strong>0.00 a 0.20</strong></td><td>Solo exposto, asfalto, concreto (ausência de vegetação)</td><td>🔴 Ilha de Calor Severa</td></tr>
            <tr><td><strong>0.21 a 0.40</strong></td><td>Vegetação rala, gramados esparsos ou poucas árvores</td><td>🟠 Retenção de Calor Elevada</td></tr>
            <tr><td><strong>0.41 a 0.65</strong></td><td>Arborização urbana moderada a boa (ruas arborizadas e praças)</td><td>🟡 Microclima Suave</td></tr>
            <tr><td><strong>0.66 a 1.00</strong></td><td>Vegetação densa (parques, bosques e florestas urbanas)</td><td>🟢 Conforto Térmico Alto (Resfriamento)</td></tr>
          </tbody>
        </table>
      </div>

      <div class="info-box">
        <div class="info-box-title iecs">
          <span>📊</span> IECS (Índice de Exposição Climática e Social - Escala 0 a 100)
        </div>
        <div class="info-text">
          O <strong>IECS</strong> é a métrica sintética de risco térmico e vulnerabilidade calculada para o raio de <strong>300 metros</strong> de cada Unidade de Saúde:
          <br/><br/>
          $$\text{{IECS}} = (\text{{Temperatura de Superfície}} \times 45\%) + (\text{{Déficit de Vegetação}} \times 25\%) + (\text{{Vulnerabilidade Social}} \times 30\%)$$
        </div>
        <table class="scale-table">
          <thead>
            <tr><th>Faixa IECS</th><th>Classificação de Risco</th><th>Ação Recomendada para o Posto</th></tr>
          </thead>
          <tbody>
            <tr><td><strong style="color:#fca5a5;">75.0 a 100.0</strong></td><td>🔴 <strong>Crítico (Altíssimo Risco)</strong></td><td>Prioridade máxima: Plantio de árvores no entorno, salas climatizadas de hidratação.</td></tr>
            <tr><td><strong style="color:#fde047;">55.0 a 74.9</strong></td><td>🟠 <strong>Alto Risco</strong></td><td>Implantação de sombreadores, jardins de chuva e ampliação da arborização.</td></tr>
            <tr><td><strong style="color:#fef08a;">35.0 a 54.9</strong></td><td>🟡 <strong>Risco Moderado</strong></td><td>Manutenção e reforço da vegetação existente nas calçadas do entorno.</td></tr>
            <tr><td><strong style="color:#6ee7b7;">0.0 a 34.9</strong></td><td>🟢 <strong>Baixo / Confortável</strong></td><td>Região favorecida por parques ou boa arborização de bairro.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Leaflet JS -->
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

  <!-- Inline Data -->
  <script>
    const UNITS_GEOJSON = {json.dumps(units_geojson, ensure_ascii=False)};
    const CLIMATE_GEOJSON = {json.dumps(climate_geojson, ensure_ascii=False)};
    const GREEN_GEOJSON = {json.dumps(green_geojson, ensure_ascii=False)};

    let map;
    let unitsLayer = null;
    let bufferLayer = null;
    let climateLayer = null;
    let greenLayer = null;
    let allUnits = [];

    document.addEventListener("DOMContentLoaded", () => {{
      initMap();
      renderClimateLayer(CLIMATE_GEOJSON);
      renderGreenLayer(GREEN_GEOJSON);
      renderUnitsLayer(UNITS_GEOJSON);

      allUnits = UNITS_GEOJSON.features.map(f => f.properties);
      renderSidebarList(allUnits);
      setupEventListeners();
    }});

    function initMap() {{
      map = L.map("map", {{ zoomControl: false }}).setView([-21.794, -48.176], 13);
      L.control.zoom({{ position: "topright" }}).addTo(map);

      L.tileLayer("https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png", {{
        attribution: '&copy; OpenStreetMap &copy; CARTO | UrbVerde USP',
        subdomains: "abcd", maxZoom: 19
      }}).addTo(map);

      addLegend();
    }}

    function renderClimateLayer(geojsonData) {{
      if (climateLayer) map.removeLayer(climateLayer);
      climateLayer = L.geoJSON(geojsonData, {{
        style: f => ({{
          fillColor: getTempColor(f.properties.surface_temp),
          weight: 0.5, opacity: 0.35, color: "#ffffff", fillOpacity: 0.45
        }}),
        onEachFeature: (f, layer) => {{
          const p = f.properties;
          layer.bindPopup(`
            <div style="font-family: sans-serif; padding: 4px;">
              <h4 style="margin:0 0 4px 0; color:#10b981;">Grid UrbVerde Araraquara</h4>
              <p style="margin:2px 0;"><strong>Temp. Superfície:</strong> ${{p.surface_temp}}°C</p>
              <p style="margin:2px 0;"><strong>Vegetação (NDVI):</strong> ${{p.ndvi}}</p>
              <p style="margin:2px 0;"><strong>Ilha de Calor:</strong> ${{p.heat_category}}</p>
              <p style="margin:2px 0;"><strong>Vulnerabilidade:</strong> Nível ${{p.vulnerability_score}} (${{p.vulnerability_desc}})</p>
            </div>
          `);
        }}
      }}).addTo(map);
    }}

    function renderGreenLayer(geojsonData) {{
      if (greenLayer) map.removeLayer(greenLayer);
      greenLayer = L.geoJSON(geojsonData, {{
        style: f => ({{
          fillColor: "#22c55e",
          weight: 1.5,
          color: "#16a34a",
          dashArray: "3, 3",
          fillOpacity: 0.55
        }}),
        onEachFeature: (f, layer) => {{
          const p = f.properties;
          layer.bindPopup(`
            <div style="font-family: sans-serif; padding: 4px;">
              <h4 style="margin:0 0 4px 0; color:#22c55e;">🌲 ${{p.name}}</h4>
              <p style="margin:2px 0; font-size:12px;"><strong>Tipo de Área Verde:</strong> ${{p.type}}</p>
              <p style="margin:2px 0; font-size:11px; color:#64748b;">Ação: Amortecimento térmico natural e absorção de CO₂</p>
            </div>
          `);
        }}
      }}).addTo(map);
    }}

    function getTempColor(t) {{
      return t >= 35.5 ? "#d90429" : t >= 33.5 ? "#ef4444" : t >= 31.5 ? "#f4a261" : t >= 29.5 ? "#e9c46a" : "#2a9d8f";
    }}

    function renderUnitsLayer(geojsonData) {{
      if (unitsLayer) map.removeLayer(unitsLayer);
      if (bufferLayer) map.removeLayer(bufferLayer);

      bufferLayer = L.layerGroup();
      unitsLayer = L.geoJSON(geojsonData, {{
        pointToLayer: (f, latlng) => {{
          const p = f.properties;
          const riskColor = getRiskColor(p.risk_level);

          L.circle(latlng, {{
            radius: 300, color: riskColor, weight: 1.5, fillColor: riskColor, fillOpacity: 0.14
          }}).addTo(bufferLayer);

          return L.circleMarker(latlng, {{
            radius: 8, fillColor: riskColor, color: "#ffffff", weight: 2, opacity: 1, fillOpacity: 0.95
          }});
        }},
        onEachFeature: (f, layer) => {{
          const p = f.properties;
          const riskColor = getRiskColor(p.risk_level);
          layer.bindPopup(`
            <div style="font-family: sans-serif; min-width: 230px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-size:11px; font-weight:700; color:${{riskColor}};">#${{p.ranking}} RANKING SUS</span>
                <span style="font-size:10px; background:rgba(0,0,0,0.08); padding:2px 6px; border-radius:4px;">${{p.type}}</span>
              </div>
              <h3 style="margin:0 0 6px 0; font-size:14px; color:#0f172a;">${{p.name}}</h3>
              <p style="margin:2px 0; font-size:12px;"><strong>Temp. Média (300m):</strong> ${{p.surface_temp_300m}}°C</p>
              <p style="margin:2px 0; font-size:12px;"><strong>Vegetação (NDVI 300m):</strong> ${{p.ndvi_300m}}</p>
              <p style="margin:2px 0; font-size:12px;"><strong>Vulnerabilidade Social:</strong> ${{p.vulnerability_score_300m}} / 5.0</p>
              <hr style="border:0; border-top:1px solid #e2e8f0; margin:6px 0;" />
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:11px;">Índice IECS:</span>
                <strong style="font-size:14px; color:${{riskColor}};">${{p.iecs_score}} / 100</strong>
              </div>
            </div>
          `);
        }}
      }});

      bufferLayer.addTo(map);
      unitsLayer.addTo(map);
    }}

    function getRiskColor(riskLevel) {{
      if (riskLevel.includes("Crítico")) return "#dc2626";
      if (riskLevel.includes("Alto")) return "#f59e0b";
      if (riskLevel.includes("Moderado")) return "#eab308";
      return "#10b981";
    }}

    function renderSidebarList(units) {{
      const container = document.getElementById("units-list");
      container.innerHTML = "";

      if (units.length === 0) {{
        container.innerHTML = `<div style="text-align:center; padding:20px; color:#94a3b8;">Nenhuma unidade encontrada.</div>`;
        return;
      }}

      units.forEach(u => {{
        const item = document.createElement("div");
        item.className = "unit-item";

        let riskClass = "low";
        if (u.risk_level.includes("Crítico")) riskClass = "critical";
        else if (u.risk_level.includes("Alto")) riskClass = "high";
        else if (u.risk_level.includes("Moderado")) riskClass = "moderate";

        item.innerHTML = `
          <div class="unit-header">
            <span class="unit-rank">#${{u.ranking}}</span>
            <span class="risk-tag ${{riskClass}}">${{u.risk_level}}</span>
          </div>
          <div class="unit-title">${{u.name}}</div>
          <div class="unit-type">${{u.type}} • ${{u.suburb}}</div>
          <div class="unit-metrics">
            <span class="metric-pill">Temp: <strong>${{u.surface_temp_300m}}°C</strong></span>
            <span class="metric-pill">NDVI: <strong>${{u.ndvi_300m}}</strong></span>
            <span class="metric-pill">IECS: <strong>${{u.iecs_score}}</strong></span>
          </div>
        `;

        item.addEventListener("click", () => {{
          map.flyTo([u.lat, u.lon], 16, {{ duration: 1.2 }});
          unitsLayer.eachLayer(layer => {{
            if (layer.feature.properties.id === u.id) layer.openPopup();
          }});
        }});

        container.appendChild(item);
      }});
    }}

    function setupEventListeners() {{
      const searchInput = document.getElementById("search-input");
      const filterType = document.getElementById("filter-type");
      const filterRisk = document.getElementById("filter-risk");

      function filterData() {{
        const q = searchInput.value.toLowerCase().trim();
        const tVal = filterType.value;
        const rVal = filterRisk.value;

        const filtered = allUnits.filter(u => {{
          const mSearch = u.name.toLowerCase().includes(q) || u.suburb.toLowerCase().includes(q);
          const mType = tVal === "ALL" || u.type === tVal;
          const mRisk = rVal === "ALL" || u.risk_level === rVal;
          return mSearch && mType && mRisk;
        }});

        renderSidebarList(filtered);
      }}

      searchInput.addEventListener("input", filterData);
      filterType.addEventListener("change", filterData);
      filterRisk.addEventListener("change", filterData);

      // Layer Toggles
      const btnClimate = document.getElementById("btn-toggle-climate");
      btnClimate.addEventListener("click", () => {{
        if (map.hasLayer(climateLayer)) {{ map.removeLayer(climateLayer); btnClimate.classList.remove("active"); }}
        else {{ climateLayer.addTo(map); btnClimate.classList.add("active"); }}
      }});

      const btnGreen = document.getElementById("btn-toggle-green");
      btnGreen.addEventListener("click", () => {{
        if (map.hasLayer(greenLayer)) {{ map.removeLayer(greenLayer); btnGreen.classList.remove("active"); }}
        else {{ greenLayer.addTo(map); btnGreen.classList.add("active"); }}
      }});

      const btnBuffers = document.getElementById("btn-toggle-buffers");
      btnBuffers.addEventListener("click", () => {{
        if (map.hasLayer(bufferLayer)) {{ map.removeLayer(bufferLayer); btnBuffers.classList.remove("active"); }}
        else {{ bufferLayer.addTo(map); btnBuffers.classList.add("active"); }}
      }});

      // Modals Handling
      const helpModal = document.getElementById("help-modal");
      const conclusionsModal = document.getElementById("conclusions-modal");

      const openModal = (m) => m.classList.add("active");
      const closeModal = (m) => m.classList.remove("active");

      document.getElementById("btn-open-help").addEventListener("click", () => openModal(helpModal));
      document.getElementById("btn-close-help").addEventListener("click", () => closeModal(helpModal));

      document.getElementById("btn-open-conclusions").addEventListener("click", () => openModal(conclusionsModal));
      document.getElementById("btn-open-conclusions-sidebar").addEventListener("click", () => openModal(conclusionsModal));
      document.getElementById("btn-close-conclusions").addEventListener("click", () => closeModal(conclusionsModal));

      helpModal.addEventListener("click", (e) => {{ if (e.target === helpModal) closeModal(helpModal); }});
      conclusionsModal.addEventListener("click", (e) => {{ if (e.target === conclusionsModal) closeModal(conclusionsModal); }});
    }}

    function addLegend() {{
      const legend = L.control({{ position: "bottomright" }});
      legend.onAdd = function() {{
        const div = L.DomUtil.create("div", "legend-control");
        div.innerHTML = `
          <div class="legend-title">Temperatura de Superfície (°C)</div>
          <div class="legend-scale"></div>
          <div class="legend-labels">
            <span>25°C (Frio)</span>
            <span>32°C</span>
            <span>38°C (Quente)</span>
          </div>
          <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin:6px 0;" />
          <div class="legend-title" style="margin-bottom:4px; color:#22c55e;">Camadas no Mapa</div>
          <div style="font-size:11px; color:#94a3b8; display:flex; flex-direction:column; gap:3px;">
            <span>🟢 <strong>Áreas Verdes & Parques:</strong> Polígonos Verdes</span>
            <span>⚪ <strong>Buffer Analisado:</strong> Raio de 300m</span>
            <span>🔴 <strong>Pontos SUS:</strong> Coloridos por IECS (0-100)</span>
          </div>
        `;
        return div;
      }};
      legend.addTo(map);
    }}
  </script>
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Standalone HTML with Conclusions Tab generated at: {OUTPUT_HTML}")

if __name__ == "__main__":
    build_standalone_html()
