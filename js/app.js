const DATA_FILES = {
  units: "data/unidades_saude_analise_araraquara.geojson",
  baseUnits: "data/unidades_saude_araraquara.json",
  climate: "data/urbverde_araraquara.geojson",
  heat2021: "data/urbverde_ilhas_calor_2021_araraquara.geojson",
  fire: "data/mapbiomas_fogo_araraquara_2025.geojson",
  summary: "data/resumo_estatistico.json",
  censusMetadata: "data/censo_2022_vulnerabilidade_araraquara.metadata.json",
  suggestions: "data/unidades_sugeridas_araraquara.json",
  metadata: "data/metadata_unidades_saude_araraquara.json",
  sources: "data/fontes_publicas_saude_araraquara.json",
  history: "data/historico_risco_termico_araraquara.json",
  flood: "data/pontos_risco_hidrologico_araraquara.geojson",
  sensitivity: "data/sensibilidade_iecs_araraquara.json",
  healthOutcomes: "data/desfechos_saude_araraquara.json",
  healthExplorer: "data/dados_historicos_saude_araraquara.json"
};

const SCOPE_LABELS = {
  municipal: "Rede pública municipal",
  filantropico_sus: "Filantrópico / SUS",
  privado: "Privado",
  estadual_universitario: "Estadual / universitário",
  municipal_regional: "Municipal / regional"
};

const HEALTH_CHART_COLORS = ["#17613a", "#2b8a5a", "#bc6c25", "#6b7280", "#8b5e83"];

const state = {
  map: null,
  climateLayer: null,
  heat2021Layer: null,
  fireLayer: null,
  greenLayer: null,
  floodLayer: null,
  bufferLayer: null,
  unitsLayer: null,
  units: [],
  features: [],
  suggestions: [],
  metadata: {},
  summary: {},
  censusMetadata: {},
  sources: [],
  history: null,
  sensitivity: null,
  healthOutcomes: null,
  healthExplorer: null,
  healthDataSource: "hospital",
  floodFeatures: [],
  selectedId: null,
  layerVisible: { climate: true, heat2021: false, green: true, flood: true, fire: false, buffers: true },
  lastFocused: {},
  filters: { query: "", type: "ALL", risk: "ALL", scope: "municipal" }
};

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  setupEventListeners();
  loadData();
});

async function loadData() {
  try {
    const entries = await Promise.all(
      Object.entries(DATA_FILES).map(async ([key, url]) => [key, await fetchJson(url)])
    );
    const data = Object.fromEntries(entries);

    state.metadata = data.metadata;
    state.summary = data.summary;
    state.censusMetadata = data.censusMetadata;
    state.sources = data.sources;
    state.suggestions = data.suggestions;
    state.history = data.history;
    state.sensitivity = data.sensitivity;
    state.healthOutcomes = data.healthOutcomes;
    state.healthExplorer = data.healthExplorer;
    state.floodFeatures = data.flood.features;
    state.features = data.units.features.map(feature => mergeUnitMetadata(feature, data.baseUnits));
    state.units = state.features.map(feature => feature.properties);

    renderClimateLayer(data.climate);
    renderHeat2021Layer(data.heat2021);
    renderGreenLayer(data.climate);
    renderFloodLayer(data.flood);
    renderFireLayer(data.fire);
    renderSources(data.sources);
    renderPendingCatalog(data.suggestions);
    renderHistoryControls();
    renderSensitivityControls();
    renderHealthOutcomes();
    renderHealthDataControls();
    renderFilteredState();
    updateNetworkBadge(data.units.features.length, data.suggestions.length);
    document.body.classList.add("is-ready");
  } catch (error) {
    console.error("Não foi possível carregar os dados do mapa:", error);
    showAppError(error);
  }
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Falha ao carregar ${url} (${response.status})`);
  return response.json();
}

function mergeUnitMetadata(feature, baseUnits) {
  const properties = feature.properties;
  const metadata = state.metadata[properties.id] || {};
  const base = baseUnits.find(unit => unit.id === properties.id) || {};

  return {
    ...feature,
    properties: {
      ...properties,
      display_name: metadata.canonical_name || properties.name,
      network_scope: metadata.network_scope || inferNetworkScope(properties.id),
      data_quality: metadata.data_quality || "ok",
      quality_note: metadata.quality_note || "Registro com métricas espaciais calculadas.",
      address: base.address || "",
      cnes: base.cnes || null,
      coordinate_source: base.coordinate_source || ""
    }
  };
}

function inferNetworkScope(id) {
  const externalUnits = new Set(["SUS-011", "SUS-012", "SUS-020", "SUS-021", "SUS-022", "SUS-027", "SUS-028"]);
  if (externalUnits.has(id)) {
    if (["SUS-012", "SUS-020", "SUS-028"].includes(id)) return "privado";
    if (["SUS-021", "SUS-022"].includes(id)) return "estadual_universitario";
    return "filantropico_sus";
  }
  return "municipal";
}

function initMap() {
  state.map = L.map("map", { zoomControl: false, preferCanvas: true }).setView([-21.794, -48.176], 13);
  [
    ["climate-pane", 200],
    ["heat2021-pane", 250],
    ["green-pane", 300],
    ["fire-pane", 350],
    ["flood-pane", 400],
    ["units-pane", 500],
    ["buffer-pane", 600]
  ].forEach(([name, zIndex]) => {
    const pane = state.map.createPane(name);
    pane.style.zIndex = String(zIndex);
  });
  L.control.zoom({ position: "topright" }).addTo(state.map);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 19
  }).addTo(state.map);
  addMapLegend();
}

function renderClimateLayer(geojson) {
  if (state.climateLayer) state.map.removeLayer(state.climateLayer);
  state.climateLayer = L.geoJSON(geojson, {
    pane: "climate-pane",
    style: feature => ({
      fillColor: getTempColor(feature.properties.surface_temp),
      weight: 0.5,
      color: "#ffffff",
      opacity: 0.5,
      fillOpacity: 0.42
    }),
    onEachFeature: (feature, layer) => {
      const p = feature.properties;
      layer.bindPopup(`<div class="map-popup">
        <span class="popup-kicker">UrbVerde · grade 2024</span>
        <h3>Condição do entorno</h3>
        <dl class="popup-metrics">
          <div><dt>Temperatura de superfície</dt><dd>${formatNumber(p.surface_temp)} °C</dd></div>
          <div><dt>Vegetação · NDVI</dt><dd>${formatNumber(p.ndvi, 2)}</dd></div>
          <div><dt>Ilha de calor</dt><dd>${escapeHtml(p.heat_category || "não informado")}</dd></div>
        </dl>
      </div>`);
    }
  }).addTo(state.map);
}

function renderHeat2021Layer(geojson) {
  const temperatures = (geojson.features || [])
    .map(feature => Number(feature.properties?.surface_temp))
    .filter(value => Number.isFinite(value) && value > 20);
  const minTemperature = Math.min(...temperatures);
  const maxTemperature = Math.max(...temperatures);
  state.heat2021Layer = L.geoJSON(geojson, {
    pane: "heat2021-pane",
    style: feature => {
      const temperature = Number(feature.properties?.surface_temp);
      const validTemperature = Number.isFinite(temperature) && temperature > 20;
      return {
        stroke: false,
        color: "transparent",
        weight: 0,
        fillColor: validTemperature ? getHeatIslandColor(temperature, minTemperature, maxTemperature) : "transparent",
        fillOpacity: validTemperature ? 0.76 : 0
      };
    },
    onEachFeature: (feature, layer) => layer.bindTooltip(
      `Mancha de calor · UrbVerde 2021 · ${formatNumber(feature.properties.surface_temp)}°C`,
      { sticky: true }
    )
  });
}

function renderGreenLayer(geojson) {
  if (state.greenLayer) state.map.removeLayer(state.greenLayer);
  state.greenLayer = L.geoJSON(geojson, {
    pane: "green-pane",
    style: feature => ({
      fillColor: getNdviColor(feature.properties.ndvi),
      color: "#276749",
      weight: 0.8,
      fillOpacity: 0.42
    }),
    onEachFeature: (feature, layer) => {
      const p = feature.properties;
      layer.bindPopup(`<div class="map-popup">
        <span class="popup-kicker green">Vegetação observada</span>
        <h3>Proxy NDVI · UrbVerde 2024</h3>
        <dl class="popup-metrics">
          <div><dt>NDVI</dt><dd>${formatNumber(p.ndvi, 2)}</dd></div>
          <div><dt>Temperatura de superfície</dt><dd>${formatNumber(p.surface_temp)} °C</dd></div>
        </dl>
        <div class="popup-note"><strong>Limite da leitura:</strong> esta grade é um indicador espectral do entorno, não o limite cadastral de parques ou áreas verdes.</div>
      </div>`);
    }
  }).addTo(state.map);
}

function renderFloodLayer(geojson) {
  if (state.floodLayer) state.map.removeLayer(state.floodLayer);
  const mappedFeatures = geojson.features.filter(feature => feature.geometry);
  state.floodLayer = L.geoJSON({ type: "FeatureCollection", features: mappedFeatures }, {
    pane: "flood-pane",
    pointToLayer: (feature, latlng) => {
      const properties = feature.properties;
      const classification = hydrologyClass(properties);
      const icon = L.divIcon({
        className: `flood-marker ${classification}`,
        html: `<span class="flood-triangle ${classification}" aria-hidden="true"></span>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
      });
      return L.marker(latlng, { icon, pane: "flood-pane", title: properties.name || "Ponto hidrológico" });
    },
    onEachFeature: (feature, layer) => layer.bindPopup(floodPopup(feature.properties))
  });
  if (state.layerVisible.flood) state.floodLayer.addTo(state.map);
  setText("map-note-text", `${geojson.metadata.count_published} pontos municipais mapeados; ${geojson.metadata.count_geocoded_for_map} aparecem com posição aproximada no mapa.`);
}

function renderFireLayer(geojson) {
  state.fireLayer = L.geoJSON(geojson, {
    pane: "fire-pane",
    style: {
      color: "#b45309",
      weight: 0.7,
      fillColor: "#f97316",
      fillOpacity: 0.58
    },
    onEachFeature: (feature, layer) => {
      const p = feature.properties;
      layer.bindPopup(`<div class="map-popup"><span class="popup-kicker fire">MapBiomas Fogo · ${escapeHtml(p.year)}</span><h3>Cicatriz de fogo anual</h3><dl class="popup-metrics"><div><dt>Área mapeada</dt><dd>${formatNumber(p.burned_area_ha, 2)} ha</dd></div><div><dt>Produto</dt><dd>Área queimada anual</dd></div></dl><div class="popup-note fire-note">Camada adicional de contexto. Não entra no cálculo do IECS.</div></div>`);
    }
  });
}

function floodPopup(point) {
  const classification = point.classification_label || "classificação não informada";
  return `<div class="map-popup">
    <span class="popup-kicker flood">Defesa Civil · risco hidrológico</span>
    <h3>${escapeHtml(point.name)}</h3>
    <p>${escapeHtml(point.phenomenon)}</p>
    <dl class="popup-metrics">
      <div><dt>Classificação</dt><dd>${escapeHtml(classification)}</dd></div>
      <div><dt>Código / proporção</dt><dd>${escapeHtml(point.intervention_code)} · ${formatNumber(point.classification_share_pct, 0)}%</dd></div>
      <div><dt>Precisão cartográfica</dt><dd>${escapeHtml(point.coordinate_status || "aproximada")}</dd></div>
    </dl>
    <div class="popup-note flood-note">O boletim publica o ponto/endereço. A coordenada exibida é uma aproximação do eixo viário e não representa uma mancha contínua.</div>
  </div>`;
}

function renderUnitsLayer(features) {
  if (state.unitsLayer) state.map.removeLayer(state.unitsLayer);
  if (state.bufferLayer) state.map.removeLayer(state.bufferLayer);

  state.bufferLayer = L.layerGroup();
  state.unitsLayer = L.geoJSON({ type: "FeatureCollection", features }, {
    pane: "units-pane",
    pointToLayer: (feature, latlng) => {
      L.circle(latlng, {
        radius: 300,
        pane: "buffer-pane",
        color: "#111111",
        weight: 1,
        opacity: 0.48,
        fillColor: "#111111",
        fillOpacity: 0.08,
        interactive: false
      }).addTo(state.bufferLayer);

      return L.circleMarker(latlng, {
        radius: feature.properties.id === state.selectedId ? 9 : 6,
        fillColor: "#111111",
        color: "#ffffff",
        weight: feature.properties.id === state.selectedId ? 2.5 : 1.5,
        fillOpacity: 1,
        bubblingMouseEvents: false
      });
    },
    onEachFeature: (feature, layer) => {
      layer.bindPopup(unitPopup(feature.properties));
      layer.on("click", () => selectUnit(feature.properties.id));
    }
  }).addTo(state.map);

  if (state.layerVisible.buffers) state.bufferLayer.addTo(state.map);
}

function updateUnitMarkerStyles() {
  state.unitsLayer?.eachLayer(layer => {
    const selected = layer.feature?.properties?.id === state.selectedId;
    layer.setStyle({ fillColor: "#111111", fillOpacity: 1, color: "#ffffff", weight: selected ? 2.5 : 1.5 });
    layer.setRadius(selected ? 9 : 6);
  });
}

function selectUnit(id) {
  const unit = state.units.find(item => item.id === id);
  if (!unit) return;
  state.selectedId = id;
  updateUnitMarkerStyles();
  focusUnit(unit);
}

function unitPopup(unit) {
  const color = getRiskColor(unit.risk_level);
  const scope = SCOPE_LABELS[unit.network_scope] || "Escopo a confirmar";
  const quality = unit.data_quality !== "ok"
    ? `<div class="popup-note"><strong>Revisão de cadastro:</strong> ${escapeHtml(unit.quality_note)}</div>`
    : "";
  const climateQuality = unit.climate_data_quality !== "urbverde_2024"
    ? `<div class="popup-note"><strong>Cobertura climática:</strong> não houve interseção com a grade UrbVerde 2024; os valores climáticos exibidos usam fallback técnico e não devem ser comparados como medição local.</div>`
    : "";
  const hydrology = hydrologyNote(unit);

  return `<div class="map-popup unit-popup">
    <div class="popup-meta"><span class="popup-kicker" style="color:${color}">#${unit.ranking} · IECS ${formatNumber(unit.iecs_score)}</span><span class="popup-scope">${escapeHtml(scope)}</span></div>
    <h3>${escapeHtml(unit.display_name)}</h3>
    <p class="popup-type">${escapeHtml(unit.type)} · ${escapeHtml(unit.suburb || "Araraquara")}</p>
    <dl class="popup-metrics">
      <div><dt>Endereço cadastrado</dt><dd>${escapeHtml(unit.address || "não informado")}</dd></div>
      <div><dt>Coordenadas</dt><dd>${formatCoordinate(unit.lat)}, ${formatCoordinate(unit.lon)}</dd></div>
      <div><dt>Temperatura média · 300m</dt><dd>${formatNumber(unit.surface_temp_300m)} °C</dd></div>
      <div><dt>Vegetação · NDVI 300m</dt><dd>${formatNumber(unit.ndvi_300m, 2)}</dd></div>
      <div><dt>Vulnerabilidade social · Censo 2022</dt><dd>${formatNumber(unit.vulnerability_score_300m, 2)} / 5</dd></div>
    </dl>
    ${hydrology}
    ${quality}
    ${climateQuality}
  </div>`;
}

function hydrologyNote(unit) {
  const nearest = getNearestFloodPoint(unit);
  if (!nearest) {
    return `<div class="popup-note flood-note"><strong>Risco hidrológico:</strong> sem ponto geocodificado próximo no recorte atual.</div>`;
  }
  return `<div class="popup-note flood-note"><strong>Risco hidrológico:</strong> ${formatDistance(nearest.distance)} do ponto ${escapeHtml(nearest.point.id)} · ${escapeHtml(nearest.point.phenomenon)}. Leitura aproximada.</div>`;
}

function getNearestFloodPoint(unit) {
  const mapped = state.floodFeatures.filter(feature => feature.geometry);
  if (!mapped.length) return null;
  return mapped
    .map(point => ({
      point: point.properties,
      distance: distanceMeters(unit.lat, unit.lon, point.geometry.coordinates[1], point.geometry.coordinates[0])
    }))
    .sort((a, b) => a.distance - b.distance)[0];
}

function distanceMeters(lat1, lon1, lat2, lon2) {
  const earthRadius = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
  return earthRadius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function formatDistance(distance) {
  return distance < 1000 ? `${Math.round(distance)} m` : `${formatNumber(distance / 1000, 1)} km`;
}

function renderHistoryControls() {
  const select = document.getElementById("history-unit");
  if (!select || !state.history) return;
  const rankedUnits = [...state.history.units].sort((a, b) => {
    const rankA = state.units.find(unit => unit.id === a.id)?.ranking || 999;
    const rankB = state.units.find(unit => unit.id === b.id)?.ranking || 999;
    return rankA - rankB;
  });
  select.innerHTML = [
    `<option value="ALL">Média de todas as unidades</option>`,
    ...rankedUnits.map(unit => `<option value="${escapeHtml(unit.id)}">${escapeHtml(unit.name)}</option>`)
  ].join("");
  select.addEventListener("change", renderHistory);
  renderHistory();
}

function renderHistory() {
  const chart = document.getElementById("history-chart");
  if (!chart || !state.history) return;
  const selectedId = document.getElementById("history-unit")?.value || "ALL";
  const selectedUnit = state.history.units.find(unit => unit.id === selectedId);
  const rawSeries = selectedUnit
    ? selectedUnit.values.map(item => ({ year: item.year, value: item.surface_temp_max_300m }))
    : state.history.summary.map(item => ({ year: item.year, value: item.mean_surface_temp_max_300m }));
  const series = rawSeries.filter(item => item.value !== null && item.value !== undefined && Number.isFinite(Number(item.value)));
  const plottedSeries = series
    .map(item => ({ ...item, value: Number(item.value) }))
    .filter(item => Number.isFinite(item.value));
  const values = plottedSeries.map(item => item.value);
  if (!values.length) {
    const summary = document.getElementById("history-summary");
    if (summary) summary.innerHTML = "";
    setText("history-method-note", "Nao ha intersecao com os setores historicos UrbVerde disponiveis para esta unidade.");
    chart.innerHTML = `<div class="empty-state"><strong>Histórico indisponível</strong><span>Não há pontos suficientes para desenhar a série.</span></div>`;
    return;
  }

  const width = 720;
  const height = 270;
  const padding = { top: 26, right: 24, bottom: 42, left: 52 };
  const min = Math.floor(Math.min(...values) - 0.5);
  const max = Math.ceil(Math.max(...values) + 0.5);
  const x = index => padding.left + index * ((width - padding.left - padding.right) / Math.max(plottedSeries.length - 1, 1));
  const y = value => height - padding.bottom - ((value - min) / Math.max(max - min, 1)) * (height - padding.top - padding.bottom);
  const ticks = [0, 1, 2, 3].map(index => min + (max - min) * index / 3);
  const path = plottedSeries.map((item, index) => `${index ? "L" : "M"} ${x(index).toFixed(1)} ${y(item.value).toFixed(1)}`).join(" ");
  const grid = ticks.map(tick => `<g><line x1="${padding.left}" x2="${width - padding.right}" y1="${y(tick)}" y2="${y(tick)}" class="history-grid-line" /><text x="${padding.left - 10}" y="${y(tick) + 4}" text-anchor="end" class="history-axis-label">${formatNumber(tick)}°</text></g>`).join("");
  const labels = plottedSeries.map((item, index) => `<text x="${x(index)}" y="${height - 16}" text-anchor="middle" class="history-axis-label">${item.year}</text>`).join("");
  const dots = series.map((item, index) => `<circle cx="${x(index)}" cy="${y(item.value)}" r="5" class="history-dot"><title>${item.year}: ${formatNumber(item.value)}°C</title></circle>`).join("");
  const title = selectedUnit ? selectedUnit.name : "Média das unidades analisadas";
  chart.innerHTML = `<div class="chart-caption"><div><strong>${escapeHtml(title)}</strong><span>Temperatura máxima da superfície · buffer de 300m</span></div><span>UrbVerde · ${state.history.history_years[0]}–${state.history.history_years.at(-1)}</span></div>
    <svg class="history-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Variação anual da temperatura máxima da superfície">
      <title>Variação anual da temperatura máxima da superfície</title>${grid}<path d="${path}" class="history-line" />${dots}${labels}
    </svg>`;
  if (selectedUnit && rawSeries.length > series.length) {
    const caption = chart.querySelector(".chart-caption div");
    const note = document.createElement("small");
    note.textContent = `${rawSeries.length - series.length} ano(s) sem intersecao espacial disponivel`;
    caption?.append(note);
  }
  updateHistorySummary(plottedSeries, selectedUnit);
  renderHistoryComparison();
}

function updateHistorySummary(series, selectedUnit) {
  const target = document.getElementById("history-summary");
  if (!target || series.length < 2) return;
  const first = Number(series[0].value);
  const last = Number(series.at(-1).value);
  const delta = last - first;
  const direction = delta > 0.05 ? "subiu" : delta < -0.05 ? "caiu" : "ficou estável";
  target.innerHTML = `<div class="history-stat"><span>Primeiro registro</span><strong>${formatNumber(first)}°C</strong><small>${series[0].year}</small></div>
    <div class="history-stat"><span>Último registro</span><strong>${formatNumber(last)}°C</strong><small>${series.at(-1).year}</small></div>
    <div class="history-stat accent"><span>Variação no período</span><strong>${delta >= 0 ? "+" : ""}${formatNumber(delta)}°C</strong><small>A temperatura ${direction}</small></div>`;
  setText("history-method-note", selectedUnit
    ? "A série mostra a média ponderada dos setores UrbVerde que intersectam o buffer de 300m desta unidade."
    : "A série mostra a média entre as unidades analisadas em cada ano; ela ajuda a enxergar o movimento geral, não uma previsão.");
}

function renderHistoryComparison() {
  const target = document.getElementById("history-comparison");
  if (!target || !state.history) return;
  const rows = state.history.units.map(unit => {
    const values = unit.values
      .map(item => ({ year: item.year, value: Number(item.surface_temp_max_300m) }))
      .filter((item, index) => unit.values[index].surface_temp_max_300m !== null && unit.values[index].surface_temp_max_300m !== undefined && Number.isFinite(item.value));
    const first = values[0]?.value;
    const last = values.at(-1)?.value;
    const current = state.units.find(item => item.id === unit.id);
    return { ...unit, first, last, delta: last - first, ranking: current?.ranking || 999 };
  }).filter(row => Number.isFinite(row.last)).sort((a, b) => b.last - a.last).slice(0, 8);
  const max = Math.max(...rows.map(row => row.last), 1);
  target.innerHTML = `<div class="history-subheading"><strong>Comparação entre unidades</strong><span>top 8 em ${state.history.history_years.at(-1)}</span></div>
    <div class="history-bars">${rows.map(row => `<div class="history-bar-row"><div class="history-bar-label"><span>${escapeHtml(row.name)}</span><b>${formatNumber(row.last)}°C</b></div><div class="history-bar-track"><i style="width:${Math.max(8, row.last / max * 100)}%"></i></div><small>${row.delta >= 0 ? "+" : ""}${formatNumber(row.delta)}°C desde ${state.history.history_years[0]}</small></div>`).join("")}</div>`;
  renderHydrologyComparison();
}

function renderHydrologyComparison() {
  const target = document.getElementById("hydrology-comparison");
  if (!target) return;
  const rows = state.units.map(unit => {
    const nearest = getNearestFloodPoint(unit);
    return nearest ? { unit, ...nearest } : null;
  }).filter(Boolean).sort((a, b) => a.distance - b.distance).slice(0, 6);
  target.innerHTML = `<div class="history-subheading"><strong>Unidades mais próximas de pontos mapeados</strong><span>leitura aproximada</span></div>
    <div class="hydrology-list">${rows.map(row => `<div class="hydrology-row"><span><strong>${escapeHtml(row.unit.display_name || row.unit.name)}</strong><small>${escapeHtml(row.point.id)} · ${escapeHtml(row.point.phenomenon)}</small></span><b>${formatDistance(row.distance)}</b></div>`).join("")}</div>`;
}

function renderHealthOutcomes() {
  const data = state.healthOutcomes;
  const grid = document.getElementById("health-outcome-grid");
  const seriesTarget = document.getElementById("health-series");
  if (!data || !grid || !seriesTarget || !data.series?.length) return;

  const latest = data.annual?.at(-1) || data.series.at(-1);
  const period = data.coverage?.period_start && data.coverage?.period_end
    ? `${data.coverage.period_start} → ${data.coverage.period_end}`
    : latest.period;
  setText("health-outcome-period", `SIH/SUS · ${period}`);
  grid.innerHTML = [
    ["Internações", latest.hospitalizations_total, "total municipal"],
    ["Respiratórias", latest.respiratory, "CID-10 J"],
    ["Circulatórias", latest.circulatory, "CID-10 I"],
    ["Desidratação / calor", Number(latest.dehydration || 0) + Number(latest.heat_related || 0), "E86 + T67"],
  ].map(([label, value, note]) => `<div class="health-stat"><span>${label}</span><strong>${formatNumber(value, 0)}</strong><small>${note}</small></div>`).join("");

  const max = Math.max(...data.series.map(item => Number(item.hospitalizations_total || 0)), 1);
  seriesTarget.innerHTML = `<div class="health-series-heading"><strong>Internações por mês</strong><span>residentes de Araraquara</span></div>
    <div class="health-series-list">${data.series.map(item => `<div class="health-series-row"><span>${escapeHtml(item.period)}</span><i><b style="width:${Math.max(4, Number(item.hospitalizations_total || 0) / max * 100)}%"></b></i><strong>${formatNumber(item.hospitalizations_total, 0)}</strong></div>`).join("")}</div>`;
  const ambulatory = data.ambulatory_attendance?.status === "not_loaded"
    ? "A produção ambulatorial do SIA/SUS permanece separada: não foi somada ao SIH, porque usa outra unidade de medida."
    : "";
  setText("health-method-note", `${data.method?.unit_of_count || "Contagem agregada do SIH/SUS."} ${ambulatory}`);
}

function renderHealthDataControls() {
  const data = state.healthExplorer;
  const yearSelect = document.getElementById("health-data-year");
  if (!data || !yearSelect) return;
  const years = [...(data.coverage?.years || [])].sort((a, b) => b - a);
  yearSelect.innerHTML = years.map(year => `<option value="${year}">${year}</option>`).join("");
  yearSelect.value = String(years[0] || "");
  renderHealthDataExplorer();
}

function healthRecordsForSource(source) {
  const data = state.healthExplorer;
  if (!data) return [];
  return source === "hospital" ? data.hospital?.unit_year || [] : data.ambulatory?.groups_year || [];
}

function healthSeriesForSource(source) {
  const records = healthRecordsForSource(source);
  const validYears = new Set(state.healthExplorer?.coverage?.years || []);
  const totals = new Map();
  records.forEach(record => {
    if (!validYears.has(Number(record.year))) return;
    totals.set(Number(record.year), (totals.get(Number(record.year)) || 0) + Number(record.value || 0));
  });
  return [...totals.entries()].sort((a, b) => a[0] - b[0]).map(([year, value]) => ({ year, value }));
}

function healthUnitRows(year, search) {
  const normalized = normalize(search);
  const rows = healthRecordsForSource("hospital")
    .filter(record => Number(record.year) === Number(year) && Number(record.value || 0) > 0)
    .reduce((grouped, record) => {
      const key = `${record.cnes || ""}|${record.establishment}`;
      const current = grouped.get(key) || { cnes: record.cnes, establishment: record.establishment, value: 0 };
      current.value += Number(record.value || 0);
      grouped.set(key, current);
      return grouped;
    }, new Map());
  return [...rows.values()]
    .filter(row => !normalized || normalize(`${row.cnes || ""} ${row.establishment}`).includes(normalized))
    .sort((a, b) => b.value - a.value);
}

function healthGroupRows(year) {
  return healthRecordsForSource("ambulatory")
    .filter(record => Number(record.year) === Number(year) && Number(record.value || 0) > 0)
    .sort((a, b) => Number(b.value) - Number(a.value));
}

function healthChapterRows(year) {
  return (state.healthExplorer?.hospital?.chapters_year || [])
    .filter(record => Number(record.year) === Number(year) && Number(record.value || 0) > 0)
    .sort((a, b) => Number(b.value) - Number(a.value));
}

function shortHealthLabel(value, limit = 42) {
  const label = String(value || "");
  return label.length > limit ? `${label.slice(0, limit - 1)}…` : label;
}

function healthTrendSeries(source, year) {
  const data = state.healthExplorer;
  const years = data?.coverage?.years || [];
  const selectedRows = source === "hospital" ? healthChapterRows(year).slice(0, 5) : healthGroupRows(year).slice(0, 5);
  const records = source === "hospital" ? data?.hospital?.chapters_year || [] : data?.ambulatory?.groups_year || [];
  const key = source === "hospital" ? "chapter" : "procedure_group";

  return selectedRows.map((row, index) => {
    const values = new Map(records.filter(record => record[key] === row[key]).map(record => [Number(record.year), Number(record.value || 0)]));
    return {
      label: row[key],
      color: HEALTH_CHART_COLORS[index],
      values: years.map(chartYear => values.get(Number(chartYear)) || 0)
    };
  });
}

function healthTrendSvg(source, year) {
  const data = state.healthExplorer;
  const years = data?.coverage?.years || [];
  const series = healthTrendSeries(source, year);
  if (!series.length || !years.length) return `<p class="modal-copy">Não há dados suficientes para este gráfico.</p>`;

  const width = 720;
  const height = 250;
  const left = 48;
  const right = 14;
  const top = 16;
  const bottom = 34;
  const chartWidth = width - left - right;
  const chartHeight = height - top - bottom;
  const max = Math.max(...series.flatMap(item => item.values), 1);
  const x = index => left + (years.length === 1 ? chartWidth / 2 : index / (years.length - 1) * chartWidth);
  const y = value => top + chartHeight - (value / max * chartHeight);
  const gridValues = [0, max / 2, max];
  const grid = gridValues.map(value => `<line class="grid-line" x1="${left}" x2="${width - right}" y1="${y(value)}" y2="${y(value)}"></line><text class="axis-label" text-anchor="end" x="${left - 7}" y="${y(value) + 3}">${formatNumber(value, 0)}</text>`).join("");
  const xLabels = years.map((chartYear, index) => `<text class="axis-label" text-anchor="middle" x="${x(index)}" y="${height - 8}">${chartYear}</text>`).join("");
  const lines = series.map(item => {
    const points = item.values.map((value, index) => `${x(index)},${y(value)}`).join(" ");
    const dots = item.values.map((value, index) => `<circle class="series-dot" cx="${x(index)}" cy="${y(value)}" fill="${item.color}" r="3.5"></circle>`).join("");
    return `<polyline class="series-line" points="${points}" stroke="${item.color}"></polyline>${dots}`;
  }).join("");
  const legend = series.map(item => `<span><i style="background:${item.color}"></i>${escapeHtml(shortHealthLabel(item.label, 34))}</span>`).join("");

  return `<svg class="health-data-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Evolução dos principais ${source === "hospital" ? "capítulos CID-10" : "grupos de procedimento"}">${grid}${xLabels}${lines}</svg><div class="health-data-legend">${legend}</div>`;
}

function healthDistributionRows(source, year) {
  const rows = source === "hospital" ? healthUnitRows(year, "") : healthGroupRows(year);
  const topRows = rows.slice(0, 7).map(row => ({
    label: source === "hospital" ? row.establishment : row.procedure_group,
    value: Number(row.value || 0)
  }));
  const remainder = rows.slice(7).reduce((sum, row) => sum + Number(row.value || 0), 0);
  if (remainder > 0) topRows.push({ label: source === "hospital" ? "Demais estabelecimentos" : "Demais grupos", value: remainder });
  return topRows;
}

function healthDistributionMarkup(source, year) {
  const rows = healthDistributionRows(source, year);
  const total = rows.reduce((sum, row) => sum + row.value, 0) || 1;
  return rows.map(row => {
    const share = row.value / total * 100;
    return `<div class="health-data-distribution-row" title="${escapeHtml(row.label)}"><span class="health-data-distribution-label">${escapeHtml(shortHealthLabel(row.label))}</span><strong class="health-data-distribution-value">${formatNumber(row.value, 0)} · ${formatNumber(share, 1)}%</strong><span class="health-data-distribution-track"><i style="width:${Math.max(2, share)}%"></i></span></div>`;
  }).join("");
}

function renderHealthDataVisuals(source, year) {
  const target = document.getElementById("health-data-visuals");
  if (!target) return;
  const hospital = source === "hospital";
  const profileLabel = hospital ? "capítulos CID-10" : "grupos de procedimento";
  const concentrationLabel = hospital ? "estabelecimentos" : "grupos";
  target.innerHTML = `
    <section class="chart-card health-data-graph-card">
      <div class="chart-caption"><div><strong>Evolução do perfil de cuidado</strong><span>as cinco categorias mais frequentes em ${year}</span></div><span>${profileLabel}</span></div>
      ${healthTrendSvg(source, year)}
    </section>
    <section class="chart-card health-data-graph-card">
      <div class="chart-caption"><div><strong>Concentração no ano selecionado</strong><span>participação por ${concentrationLabel}</span></div><span>${year}</span></div>
      <div class="health-data-distribution">${healthDistributionMarkup(source, year)}</div>
    </section>`;
}

function renderHealthDataExplorer() {
  const data = state.healthExplorer;
  const year = Number(document.getElementById("health-data-year")?.value);
  const source = state.healthDataSource;
  const summary = document.getElementById("health-data-summary");
  const chart = document.getElementById("health-data-chart");
  const visuals = document.getElementById("health-data-visuals");
  const table = document.getElementById("health-data-table");
  const notes = document.getElementById("health-data-notes");
  const search = document.getElementById("health-data-unit")?.value || "";
  if (!data || !summary || !chart || !visuals || !table || !notes || !year) return;

  const hospital = source === "hospital";
  const sourceData = hospital ? data.hospital : data.ambulatory;
  const series = healthSeriesForSource(source);
  const yearTotal = series.find(item => item.year === year)?.value || 0;
  const rows = hospital ? healthUnitRows(year, search) : healthGroupRows(year);
  const visibleRows = rows.slice(0, 40);
  const totalEntities = hospital
    ? healthUnitRows(year, "").length
    : healthGroupRows(year).length;
  const unitLabel = hospital ? "estabelecimentos com registro" : "grupos de procedimento";
  const unitDimension = sourceData?.unit_dimension || "";

  summary.innerHTML = [
    ["Ano selecionado", year, "competência de atendimento"],
    [hospital ? "Internações" : "Produção aprovada", formatNumber(yearTotal, 0), hospital ? "AIH/registro SIH" : "quantidade SIA"],
    [unitLabel, formatNumber(totalEntities, 0), hospital ? "com valor acima de zero" : "com produção registrada"],
    ["Período", `${data.coverage.start_year}–${data.coverage.end_year}`, "10 anos completos"],
  ].map(([label, value, note]) => `<div class="health-data-stat"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`).join("");

  const maxSeries = Math.max(...series.map(item => item.value), 1);
  const chartTitle = hospital ? "Internações por ano" : "Produção ambulatorial aprovada por ano";
  const chartSubtitle = hospital ? "residentes de Araraquara · todas as unidades de ocorrência" : "município de Araraquara · grupos de procedimento";
  const chartBars = series.map(item => `<div class="health-data-bar-row ${item.year === year ? "is-selected" : ""}"><span>${item.year}</span><i><b style="width:${Math.max(3, item.value / maxSeries * 100)}%"></b></i><strong>${formatNumber(item.value, 0)}</strong></div>`).join("");
  let breakdown = "";
  if (hospital) {
    const chapters = (data.hospital?.chapters_year || [])
      .filter(item => Number(item.year) === year && Number(item.value || 0) > 0)
      .sort((a, b) => Number(b.value) - Number(a.value))
      .slice(0, 6);
    breakdown = `<div class="health-data-breakdown"><div class="health-data-subheading"><strong>Capítulos CID-10 mais frequentes</strong><span>${year}</span></div>${chapters.map(item => `<div class="health-data-mini-row"><span>${escapeHtml(item.chapter)}</span><b>${formatNumber(item.value, 0)}</b></div>`).join("")}</div>`;
  } else {
    breakdown = `<div class="health-data-breakdown"><div class="health-data-subheading"><strong>O que esta fonte permite</strong><span>SIA/SUS</span></div><p class="modal-copy">A produção ambulatorial está consolidada por grupo de procedimento. A tabulação pública consultada não disponibiliza a unidade executante como dimensão nesta série, por isso ela não é atribuída automaticamente às unidades do mapa.</p></div>`;
  }
  chart.innerHTML = `<div class="chart-caption"><div><strong>${chartTitle}</strong><span>${chartSubtitle}</span></div><span>${escapeHtml(sourceData?.source || "Fonte pública")}</span></div><div class="health-data-bars">${chartBars}</div>${breakdown}`;
  renderHealthDataVisuals(source, year);

  const total = rows.reduce((sum, row) => sum + Number(row.value || 0), 0) || 1;
  const tableTitle = hospital ? `Estabelecimentos no ano de ${year}` : `Grupos de procedimento em ${year}`;
  const tableRows = visibleRows.map(row => {
    const label = hospital ? `${row.establishment}${row.cnes ? ` · CNES ${row.cnes}` : ""}` : row.procedure_group;
    const share = Number(row.value || 0) / total * 100;
    return `<tr><td>${escapeHtml(label)}</td><td>${formatNumber(row.value, 0)}</td><td><span class="health-share"><i style="width:${Math.max(2, share)}%"></i></span>${formatNumber(share, 1)}%</td></tr>`;
  }).join("");
  table.innerHTML = `<div class="health-data-subheading"><strong>${tableTitle}</strong><span>${search ? `${visibleRows.length} encontrados` : `top ${Math.min(40, rows.length)} de ${rows.length}`}</span></div><div class="health-data-table-scroll"><table><thead><tr><th>${hospital ? "Estabelecimento / CNES" : "Grupo de procedimento"}</th><th>Quantidade</th><th>Participação</th></tr></thead><tbody>${tableRows || `<tr><td colspan="3" class="health-empty-cell">Nenhum registro encontrado para este filtro.</td></tr>`}</tbody></table></div>`;
  notes.innerHTML = `<strong>Como interpretar:</strong> ${escapeHtml(unitDimension)}. ${escapeHtml((data.limitations || [])[0] || "A base é agregada e deve ser lida com a documentação da fonte.")} <a href="${safeUrl(sourceData?.source_url)}" target="_blank" rel="noreferrer">Abrir fonte no DATASUS ↗</a>`;
}

function healthExportRows(year, source) {
  return source === "hospital" ? healthUnitRows(year, "") : healthGroupRows(year);
}

function downloadHealthDataCsv() {
  const year = Number(document.getElementById("health-data-year")?.value);
  const source = state.healthDataSource;
  const rows = healthExportRows(year, source);
  const header = source === "hospital" ? ["ano", "cnes", "estabelecimento", "quantidade"] : ["ano", "grupo_procedimento", "quantidade"];
  const body = rows.map(row => source === "hospital"
    ? [year, row.cnes || "", row.establishment, row.value]
    : [year, row.procedure_group, row.value]);
  const csv = [header, ...body].map(row => row.map(value => `"${String(value ?? "").replaceAll('"', '""')}"`).join(";")).join("\n");
  const blob = new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `araraquara-${source}-${year}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function downloadHealthDataXlsx() {
  const data = state.healthExplorer;
  const year = Number(document.getElementById("health-data-year")?.value);
  const source = state.healthDataSource;
  if (!data || !year) return;
  if (!window.XLSX) {
    window.alert("A biblioteca de exportação XLSX não foi carregada. Verifique a conexão e tente novamente.");
    return;
  }

  const hospital = source === "hospital";
  const rows = healthExportRows(year, source);
  const series = healthSeriesForSource(source);
  const profileRows = hospital ? healthChapterRows(year) : healthGroupRows(year);
  const sourceData = hospital ? data.hospital : data.ambulatory;
  const wb = XLSX.utils.book_new();
  const summaryRows = [
    ["Base", data.title],
    ["Município", data.municipality],
    ["Código IBGE", data.municipality_code],
    ["Fonte", sourceData.source],
    ["Ano selecionado", year],
    ["Período da série", `${data.coverage.start_year}–${data.coverage.end_year}`],
    ["Atualizado em", data.generated_at],
    ["Observação", sourceData.unit_dimension],
    ["Fonte original", sourceData.source_url]
  ];
  const seriesRows = [["ano", hospital ? "internacoes" : "producao_aprovada"], ...series.map(item => [item.year, item.value])];
  const detailRows = hospital
    ? [["ano", "cnes", "estabelecimento", "internacoes"], ...rows.map(row => [year, row.cnes || "", row.establishment, row.value])]
    : [["ano", "grupo_procedimento", "quantidade_aprovada"], ...rows.map(row => [year, row.procedure_group, row.value])];
  const profileSheetRows = hospital
    ? [["ano", "capitulo_cid10", "internacoes"], ...profileRows.map(row => [year, row.chapter, row.value])]
    : [["ano", "grupo_procedimento", "quantidade_aprovada"], ...profileRows.map(row => [year, row.procedure_group, row.value])];
  const notesRows = [["limitação / nota"], ...(data.limitations || []).map(note => [note])];

  [
    ["Resumo", summaryRows],
    ["Serie anual", seriesRows],
    [hospital ? "Estabelecimentos" : "Procedimentos", detailRows],
    [hospital ? "Capitulos CID10" : "Grupos", profileSheetRows],
    ["Notas", notesRows]
  ].forEach(([name, rowsToWrite]) => XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rowsToWrite), name));

  XLSX.writeFile(wb, `araraquara-${source}-${year}.xlsx`, { bookType: "xlsx", compression: true });
}

function renderSensitivityControls() {
  const select = document.getElementById("sensitivity-scenario");
  if (!select || !state.sensitivity) return;
  select.innerHTML = state.sensitivity.scenarios.map(scenario => `<option value="${escapeHtml(scenario.id)}">${escapeHtml(scenario.label)}</option>`).join("");
  select.addEventListener("change", renderSensitivity);
  renderSensitivity();
}

function renderSensitivity() {
  const select = document.getElementById("sensitivity-scenario");
  const sensitivity = state.sensitivity;
  if (!select || !sensitivity) return;
  const scenario = sensitivity.scenarios.find(item => item.id === select.value) || sensitivity.scenarios[0];
  const weights = scenario.weights;
  const weightLabels = { heat: "Calor", vegetation: "Vegetação", social: "Censo 2022" };
  document.getElementById("sensitivity-description").textContent = scenario.description;
  document.getElementById("sensitivity-weights").innerHTML = Object.entries(weights).map(([key, value]) => `<div class="sensitivity-weight"><span>${weightLabels[key]}</span><strong>${formatNumber(value * 100, 0)}%</strong></div>`).join("");
  const moved = scenario.units.filter(unit => Math.abs(Number(unit.rank_shift_vs_default || 0)) > 0).length;
  const topFive = scenario.top_5 || scenario.units.slice(0, 5);
  document.getElementById("sensitivity-summary").innerHTML = `<div class="sensitivity-summary-stat"><span>Unidades que mudaram</span><strong>${moved}</strong><small>de ${scenario.units.length}</small></div><div class="sensitivity-summary-stat"><span>Maior deslocamento</span><strong>${formatNumber(Math.max(...scenario.units.map(unit => Math.abs(Number(unit.rank_shift_vs_default || 0)))), 0)}</strong><small>posições</small></div><div class="sensitivity-summary-stat accent"><span>Leitura</span><strong>${scenario.id === "balanced" ? "base" : "cenário"}</strong><small>comparado ao padrão</small></div>`;
  document.getElementById("sensitivity-ranking").innerHTML = `<div class="history-subheading"><strong>Top 5 neste cenário</strong><span>IECS recalculado</span></div><div class="sensitivity-list">${topFive.map(unit => {
    const shift = Number(unit.rank_shift_vs_default || 0);
    const shiftLabel = shift > 0 ? `↑ ${shift}` : shift < 0 ? `↓ ${Math.abs(shift)}` : "—";
    const shiftClass = shift > 0 ? "up" : shift < 0 ? "down" : "same";
    return `<div class="sensitivity-row"><span class="unit-rank">${String(unit.ranking).padStart(2, "0")}</span><span><strong>${escapeHtml(unit.name)}</strong><small>IECS ${formatNumber(unit.score)}</small></span><b class="rank-shift ${shiftClass}">${shiftLabel}</b></div>`;
  }).join("")}</div>`;
}

function renderFilteredState() {
  const filtered = getFilteredUnits();
  renderUnitsLayer(filtered.map(unit => unit.feature));
  renderUnitList(filtered.map(unit => unit.properties));
  updateKpis(filtered.map(unit => unit.properties));
  updateFilterSummary(filtered.length);
}

function getFilteredUnits() {
  const { query, type, risk, scope } = state.filters;
  const normalizedQuery = normalize(query);

  return state.features
    .map(feature => ({ feature, properties: feature.properties }))
    .filter(({ properties }) => {
      const searchable = normalize(`${properties.display_name} ${properties.name} ${properties.suburb} ${properties.type}`);
      return (!normalizedQuery || searchable.includes(normalizedQuery))
        && (type === "ALL" || properties.type === type)
        && (risk === "ALL" || properties.risk_level === risk)
        && (scope === "ALL" || properties.network_scope === scope);
    })
    .sort((a, b) => (a.properties.ranking || 999) - (b.properties.ranking || 999));
}

function renderUnitList(units) {
  const container = document.getElementById("units-list");
  document.getElementById("list-count").textContent = units.length;
  container.innerHTML = "";

  if (!units.length) {
    container.innerHTML = `<div class="empty-state"><strong>Nenhuma unidade encontrada</strong><span>Tente outro nome, tipo, risco ou recorte de rede.</span></div>`;
    return;
  }

  units.forEach(unit => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "unit-row";
    item.innerHTML = `<span class="unit-rank">${String(unit.ranking).padStart(2, "0")}</span>
      <span class="unit-row-main"><strong>${escapeHtml(unit.display_name)}</strong><small>${escapeHtml(unit.type)} · ${escapeHtml(unit.suburb || "Araraquara")}</small></span>
      <span class="unit-row-score"><b>${formatNumber(unit.iecs_score)}</b><small class="risk-text ${riskClass(unit.risk_level)}">${riskShortLabel(unit.risk_level)}</small></span>`;
    item.addEventListener("click", () => focusUnit(unit));
    container.appendChild(item);
  });
}

function renderPendingCatalog(suggestions) {
  const container = document.getElementById("pending-list");
  document.getElementById("pending-count").textContent = suggestions.length;
  container.innerHTML = suggestions.map(item => `<article class="pending-row">
    <div class="pending-row-top"><span class="pending-type">${escapeHtml(item.type)}</span><span class="pending-status">aguarda validação</span></div>
    <h3>${escapeHtml(item.name)}</h3>
    <p>${escapeHtml(item.suburb)}${item.address ? ` · ${escapeHtml(item.address)}` : ""}</p>
    <div class="pending-actions"><span>${item.cnes ? `CNES ${escapeHtml(item.cnes)}` : "CNES a confirmar"}</span><a href="${safeUrl(item.source_url)}" target="_blank" rel="noreferrer">Ver fonte ↗</a></div>
  </article>`).join("");
}

function renderSources(sources) {
  document.getElementById("sources-list").innerHTML = sources.map(source => `<article class="source-row">
    <div><span class="source-index">${escapeHtml(source.id.split("-").pop().slice(0, 2))}</span><h3>${escapeHtml(source.title)}</h3></div>
    <p>${escapeHtml(source.use)}</p><a href="${safeUrl(source.url)}" target="_blank" rel="noreferrer">Abrir fonte ↗</a>
  </article>`).join("");
  renderDataAudit();
}

function renderDataAudit() {
  const target = document.getElementById("data-audit");
  if (!target || !state.features.length) return;
  const units = state.features.map(feature => feature.properties);
  const coordinateMatches = state.features.filter(feature => {
    const [lon, lat] = feature.geometry?.coordinates || [];
    return Math.abs(Number(feature.properties.lon) - Number(lon)) <= 1e-8
      && Math.abs(Number(feature.properties.lat) - Number(lat)) <= 1e-8;
  }).length;
  const addresses = units.filter(unit => String(unit.address || "").trim()).length;
  const cnes = units.filter(unit => String(unit.cnes || "").trim()).length;
  const climateCoverage = units.filter(unit => Number(unit.climate_data_coverage_pct) > 0).length;
  const climateFallback = units.filter(unit => unit.climate_data_quality !== "urbverde_2024").length;
  const censusCoverage = units.filter(unit => unit.vulnerability_data_quality === "censo_2022").length;
  const reviewCount = units.filter(unit => unit.data_quality !== "ok").length;
  const summary = state.summary || {};
  const fields = [
    "census_population_300m",
    "census_income_median_300m",
    "census_share_children_300m",
    "census_share_elderly_300m",
    "census_crowding_300m",
    "vulnerability_score_300m"
  ];
  target.innerHTML = `<section class="data-audit" aria-labelledby="data-audit-title">
    <div class="data-method"><strong id="data-audit-title">Auditoria da publicação</strong><span>Conferência programática do catálogo, geometrias e cobertura dos dados usados no IECS.</span></div>
    <div class="audit-grid">
      <div class="audit-stat"><span>Geometria ↔ coordenada</span><strong>${coordinateMatches}/${units.length}</strong><small>pontos analíticos coincidentes</small></div>
      <div class="audit-stat"><span>Endereço no catálogo</span><strong>${addresses}/${units.length}</strong><small>registros com algum endereço</small></div>
      <div class="audit-stat"><span>CNES informado</span><strong>${cnes}/${units.length}</strong><small>demais códigos aguardam conferência</small></div>
      <div class="audit-stat"><span>Cobertura UrbVerde</span><strong>${climateCoverage}/${units.length}</strong><small>${climateFallback} usam fallback climático</small></div>
      <div class="audit-stat"><span>Censo 2022</span><strong>${censusCoverage}/${units.length}</strong><small>com interseção territorial</small></div>
      <div class="audit-stat"><span>Revisão cadastral</span><strong>${reviewCount}</strong><small>registros marcados para revisão</small></div>
    </div>
    <div class="method-list"><strong>Dados do Censo usados no cálculo</strong><span>${fields.map(field => `<code>${field}</code>`).join(" · ")}</span><span>Origem: IBGE Censo Demográfico 2022, setores censitários agregados. O <code>vulnerability_score_5</code> é um índice composto deste projeto, não um indicador oficial do IBGE.</span></div>
    <div class="method-list"><strong>Regra do IECS</strong><span>45% temperatura de superfície + 25% déficit de NDVI + 30% vulnerabilidade social-sanitária do Censo 2022, calculados no buffer de 300 m.</span><span>O UrbVerde 2024 não cobre 100% do território dos registros analisados; as unidades rurais sem interseção aparecem identificadas na ficha e usam fallback técnico.</span></div>
    <div class="source-note">Resumo registrado no conjunto publicado: ${escapeHtml(String(summary.total_units_analyzed || units.length))} unidades analisadas, ${escapeHtml(String(summary.units_with_social_imputation || 0))} imputações sociais e ${escapeHtml(String(summary.units_with_climate_fallback ?? climateFallback))} fallback(s) climáticos.</div>
  </section>`;
}

function updateKpis(units) {
  const critical = units.filter(unit => unit.risk_level.includes("Crítico") || unit.risk_level === "Alto").length;
  const average = units.length ? units.reduce((sum, unit) => sum + Number(unit.surface_temp_300m || 0), 0) / units.length : 0;
  const max = units.length ? Math.max(...units.map(unit => Number(unit.surface_temp_300m || 0))) : 0;
  setText("kpi-visible", units.length);
  setText("kpi-critical", critical);
  setText("kpi-temp", `${formatNumber(average)}°`);
  setText("kpi-max", `${formatNumber(max)}°`);
  setText("scope-note", state.filters.scope === "municipal"
    ? "O ranking público municipal está separado de hospitais privados, filantrópicos e unidades estaduais."
    : "O mapa está reunindo registros de escopos diferentes; use a ficha da unidade para interpretar o contexto.");
}

function updateFilterSummary(count) {
  const scope = state.filters.scope === "ALL" ? "todos os registros" : (SCOPE_LABELS[state.filters.scope] || "recorte selecionado");
  setText("filter-summary", `${count} no mapa · ${scope}`);
}

function updateNetworkBadge(total, pending) {
  setText("network-badge", `${total} registros atuais`);
  setText("pending-badge", `${pending} para validar`);
}

function focusUnit(unit) {
  state.selectedId = unit.id;
  updateUnitMarkerStyles();
  state.map.flyTo([unit.lat, unit.lon], 16, { duration: 0.8 });
  state.unitsLayer.eachLayer(layer => {
    if (layer.feature?.properties.id === unit.id) layer.openPopup();
  });
  document.getElementById("control-panel").classList.remove("mobile-open");
  document.body.classList.remove("mobile-panel-open");
}

function setupEventListeners() {
  addFloodToolbarButton();
  document.getElementById("search-input").addEventListener("input", event => {
    state.filters.query = event.target.value;
    renderFilteredState();
  });
  ["filter-type", "filter-risk", "filter-scope"].forEach(id => {
    document.getElementById(id).addEventListener("change", event => {
      state.filters[id.replace("filter-", "")] = event.target.value;
      renderFilteredState();
    });
  });

  document.querySelectorAll("[data-layer]").forEach(button => {
    button.addEventListener("click", () => toggleLayer(button.dataset.layer, button));
  });
  document.querySelectorAll("[data-open-modal]").forEach(button => {
    button.addEventListener("click", () => openModal(button.dataset.openModal));
  });
  document.querySelectorAll("[data-health-source]").forEach(button => {
    button.addEventListener("click", () => {
      state.healthDataSource = button.dataset.healthSource;
      document.querySelectorAll("[data-health-source]").forEach(tab => {
        const active = tab === button;
        tab.classList.toggle("is-active", active);
        tab.setAttribute("aria-selected", String(active));
      });
      const unitSearch = document.getElementById("health-data-unit");
      if (unitSearch) {
        unitSearch.disabled = state.healthDataSource !== "hospital";
        unitSearch.placeholder = state.healthDataSource === "hospital" ? "nome ou CNES" : "Não disponível para esta fonte";
      }
      renderHealthDataExplorer();
    });
  });
  document.getElementById("health-data-year")?.addEventListener("change", renderHealthDataExplorer);
  document.getElementById("health-data-unit")?.addEventListener("input", renderHealthDataExplorer);
  document.getElementById("health-download-csv")?.addEventListener("click", downloadHealthDataCsv);
  document.getElementById("health-download-xlsx")?.addEventListener("click", downloadHealthDataXlsx);
  document.querySelectorAll("[data-close-modal]").forEach(button => {
    button.addEventListener("click", () => closeModal(button.dataset.closeModal));
  });
  document.querySelectorAll(".modal-backdrop").forEach(modal => {
    modal.addEventListener("click", event => {
      if (event.target === modal) closeModal(modal.id);
    });
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") document.querySelectorAll(".modal-backdrop.is-open").forEach(modal => closeModal(modal.id));
  });

  const pendingToggle = document.getElementById("toggle-pending");
  pendingToggle.addEventListener("click", () => {
    const open = pendingToggle.getAttribute("aria-expanded") === "true";
    pendingToggle.setAttribute("aria-expanded", String(!open));
    document.getElementById("pending-list").hidden = open;
  });
  document.getElementById("mobile-list-toggle").addEventListener("click", () => {
    const panel = document.getElementById("control-panel");
    const isOpen = panel.classList.toggle("mobile-open");
    document.body.classList.toggle("mobile-panel-open", isOpen);
  });
}

function addFloodToolbarButton() {
  const toolbar = document.querySelector(".map-toolbar");
  if (!toolbar) return;
  [
    ["flood", "💧 Risco hídrico"],
    ["heat2021", "🔥 Manchas de calor 2021"],
    ["fire", "🔥 Incêndios 2025"]
  ].forEach(([layer, text]) => {
    if (toolbar.querySelector(`[data-layer="${layer}"]`)) return;
    const button = document.createElement("button");
    button.className = `map-tool${state.layerVisible[layer] ? " is-active" : ""}`;
    button.dataset.layer = layer;
    button.type = "button";
    button.setAttribute("aria-pressed", String(Boolean(state.layerVisible[layer])));
    button.textContent = text;
    toolbar.appendChild(button);
  });
}

function toggleLayer(layerName, button) {
  const layers = { climate: state.climateLayer, heat2021: state.heat2021Layer, green: state.greenLayer, flood: state.floodLayer, fire: state.fireLayer, buffers: state.bufferLayer };
  const layer = layers[layerName];
  if (!layer) return;
  const visible = state.map.hasLayer(layer);
  if (visible) state.map.removeLayer(layer);
  else layer.addTo(state.map);
  state.layerVisible[layerName] = !visible;
  button.classList.toggle("is-active", !visible);
  button.setAttribute("aria-pressed", String(!visible));
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  state.lastFocused[id] = document.activeElement;
  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
  modal.querySelector("button")?.focus();
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  if (modal.contains(document.activeElement)) document.activeElement.blur();
  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");
  state.lastFocused[id]?.focus?.();
}

function addMapLegend() {
  const legend = L.control({ position: "bottomright" });
  legend.onAdd = () => {
    const element = L.DomUtil.create("div", "map-legend");
    element.innerHTML = `<strong>Como ler</strong><span><i class="legend-symbol unit"></i>unidades de saúde · pontos pretos</span><span><i class="legend-triangle flood-atenuado"></i>* risco atenuado por obras</span><span><i class="legend-triangle flood-execucao"></i>** obras em execução</span><span><i class="legend-triangle flood-sem-intervencao"></i>*** sem intervenção</span><span><i class="legend-gradient vegetation-gradient"></i>NDVI · gradiente do proxy de vegetação</span><span><i class="legend-gradient heat-gradient"></i>manchas de calor · UrbVerde 2021</span><span><i class="legend-symbol fire"></i>cicatrizes de fogo · MapBiomas 2025</span><span><i class="legend-line"></i>buffer de 300m</span>`;
    return element;
  };
  legend.addTo(state.map);
}

function showAppError(error) {
  const errorBox = document.getElementById("app-error");
  const openedAsFile = window.location.protocol === "file:";
  errorBox.hidden = false;
  errorBox.querySelector("p").textContent = openedAsFile
    ? "Este arquivo foi aberto diretamente. Inicie um servidor local (python -m http.server 8000) e acesse http://localhost:8000."
    : "O site não encontrou um dos arquivos de dados publicados. Confira se a pasta data/ foi incluída no deploy.";
  errorBox.querySelector("small").textContent = openedAsFile
    ? "file:// não permite que o navegador carregue os dados locais por fetch."
    : error.message;
}

function getHeatIslandColor(value, min, max) {
  const stops = [[0, [44, 123, 182]], [0.25, [171, 217, 233]], [0.5, [255, 255, 191]], [0.75, [253, 174, 107]], [1, [215, 25, 28]]];
  const ratio = Math.max(0, Math.min(1, (Number(value) - min) / Math.max(max - min, 0.01)));
  const upper = stops.find(stop => ratio <= stop[0]) || stops.at(-1);
  const lower = stops[stops.indexOf(upper) - 1] || upper;
  const localRatio = upper[0] === lower[0] ? 0 : (ratio - lower[0]) / (upper[0] - lower[0]);
  const color = lower[1].map((channel, index) => Math.round(channel + (upper[1][index] - channel) * localRatio));
  return `rgb(${color.join(",")})`;
}

function getTempColor(temp) {
  return temp >= 35.5 ? "#b42318" : temp >= 33.5 ? "#d97706" : temp >= 31.5 ? "#ca8a04" : temp >= 29.5 ? "#65a30d" : "#0f766e";
}

function getRiskColor(riskLevel) {
  if (riskLevel.includes("Crítico")) return "#b42318";
  if (riskLevel.includes("Alto")) return "#d97706";
  if (riskLevel.includes("Moderado")) return "#ca8a04";
  return "#15803d";
}

function getFloodColor(phenomenon) {
  return "#2563eb";
}

function hydrologyClass(point) {
  return point.classification || (point.intervention_code === "***" ? "sem_intervencao" : point.intervention_code === "**" ? "obras_em_execucao" : "risco_atenuado");
}

function getNdviColor(ndvi) {
  const value = Number(ndvi);
  if (!Number.isFinite(value) || value < 0.2) return "#d9f0d8";
  if (value < 0.35) return "#a8d5a2";
  if (value < 0.5) return "#70b66b";
  return "#2f855a";
}

function riskClass(riskLevel) {
  if (riskLevel.includes("Crítico")) return "critical";
  if (riskLevel.includes("Alto")) return "high";
  if (riskLevel.includes("Moderado")) return "moderate";
  return "low";
}

function riskShortLabel(riskLevel) {
  if (riskLevel.includes("Crítico")) return "crítico";
  if (riskLevel.includes("Alto")) return "alto";
  if (riskLevel.includes("Moderado")) return "moderado";
  return "baixo";
}

function formatNumber(value, decimals = 1) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return number.toLocaleString("pt-BR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function formatCoordinate(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(6) : "não informado";
}

function normalize(value) {
  return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
}

function safeUrl(url) {
  try {
    const parsed = new URL(url);
    return ["https:", "http:"].includes(parsed.protocol) ? parsed.href : "#";
  } catch {
    return "#";
  }
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}
