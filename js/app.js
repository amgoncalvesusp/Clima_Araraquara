const DATA_FILES = {
  units: "data/unidades_saude_analise_araraquara.geojson",
  baseUnits: "data/unidades_saude_araraquara.json",
  climate: "data/urbverde_araraquara.geojson",
  green: "data/areas_verdes_araraquara.geojson",
  summary: "data/resumo_estatistico.json",
  suggestions: "data/unidades_sugeridas_araraquara.json",
  metadata: "data/metadata_unidades_saude_araraquara.json",
  sources: "data/fontes_publicas_saude_araraquara.json",
  history: "data/historico_risco_termico_araraquara.json",
  flood: "data/pontos_risco_hidrologico_araraquara.geojson",
  sensitivity: "data/sensibilidade_iecs_araraquara.json",
  healthOutcomes: "data/desfechos_saude_araraquara.json"
};

const SCOPE_LABELS = {
  municipal: "Rede pública municipal",
  filantropico_sus: "Filantrópico / SUS",
  privado: "Privado",
  estadual_universitario: "Estadual / universitário",
  municipal_regional: "Municipal / regional"
};

const state = {
  map: null,
  climateLayer: null,
  greenLayer: null,
  floodLayer: null,
  bufferLayer: null,
  unitsLayer: null,
  units: [],
  features: [],
  suggestions: [],
  metadata: {},
  sources: [],
  history: null,
  sensitivity: null,
  healthOutcomes: null,
  floodFeatures: [],
  layerVisible: { climate: true, green: true, flood: true, buffers: true },
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
    state.sources = data.sources;
    state.suggestions = data.suggestions;
    state.history = data.history;
    state.sensitivity = data.sensitivity;
    state.healthOutcomes = data.healthOutcomes;
    state.floodFeatures = data.flood.features;
    state.features = data.units.features.map(feature => mergeUnitMetadata(feature, data.baseUnits));
    state.units = state.features.map(feature => feature.properties);

    renderClimateLayer(data.climate);
    renderGreenLayer(data.green);
    renderFloodLayer(data.flood);
    renderSources(data.sources);
    renderPendingCatalog(data.suggestions);
    renderHistoryControls();
    renderSensitivityControls();
    renderHealthOutcomes();
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
      cnes: base.cnes || null
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
  state.map = L.map("map", { zoomControl: false }).setView([-21.794, -48.176], 13);
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

function renderGreenLayer(geojson) {
  if (state.greenLayer) state.map.removeLayer(state.greenLayer);
  state.greenLayer = L.geoJSON(geojson, {
    style: { fillColor: "#2f855a", color: "#276749", weight: 1.2, fillOpacity: 0.32 },
    onEachFeature: (feature, layer) => {
      const p = feature.properties;
      layer.bindPopup(`<div class="map-popup">
        <span class="popup-kicker green">Infraestrutura verde</span>
        <h3>${escapeHtml(p.name || "Área verde")}</h3>
        <p>${escapeHtml(p.type || "Área verde mapeada")} · potencial de amortecimento térmico.</p>
      </div>`);
    }
  }).addTo(state.map);
}

function renderFloodLayer(geojson) {
  if (state.floodLayer) state.map.removeLayer(state.floodLayer);
  const mappedFeatures = geojson.features.filter(feature => feature.geometry);
  state.floodLayer = L.geoJSON({ type: "FeatureCollection", features: mappedFeatures }, {
    pointToLayer: (feature, latlng) => L.circleMarker(latlng, {
      radius: 7,
      fillColor: getFloodColor(feature.properties.phenomenon),
      color: "#ffffff",
      weight: 2,
      fillOpacity: 0.95
    }),
    onEachFeature: (feature, layer) => layer.bindPopup(floodPopup(feature.properties))
  });
  if (state.layerVisible.flood) state.floodLayer.addTo(state.map);
  setText("map-note-text", `${geojson.metadata.count_published} pontos municipais mapeados; ${geojson.metadata.count_geocoded_for_map} aparecem com posição aproximada no mapa.`);
}

function floodPopup(point) {
  return `<div class="map-popup">
    <span class="popup-kicker flood">Defesa Civil · risco hidrológico</span>
    <h3>${escapeHtml(point.name)}</h3>
    <p>${escapeHtml(point.phenomenon)}</p>
    <dl class="popup-metrics">
      <div><dt>Código de intervenção</dt><dd>${escapeHtml(point.intervention_code)}</dd></div>
      <div><dt>Precisão cartográfica</dt><dd>aproximada</dd></div>
    </dl>
    <div class="popup-note flood-note">O boletim publica o ponto/endereço. A coordenada exibida é uma aproximação do eixo viário e não representa uma mancha contínua.</div>
  </div>`;
}

function renderUnitsLayer(features) {
  if (state.unitsLayer) state.map.removeLayer(state.unitsLayer);
  if (state.bufferLayer) state.map.removeLayer(state.bufferLayer);

  state.bufferLayer = L.layerGroup();
  state.unitsLayer = L.geoJSON({ type: "FeatureCollection", features }, {
    pointToLayer: (feature, latlng) => {
      const color = getRiskColor(feature.properties.risk_level);
      L.circle(latlng, {
        radius: 300,
        color,
        weight: 1,
        opacity: 0.48,
        fillColor: color,
        fillOpacity: 0.08
      }).addTo(state.bufferLayer);

      return L.circleMarker(latlng, {
        radius: 7,
        fillColor: color,
        color: "#ffffff",
        weight: 2,
        fillOpacity: 0.96
      });
    },
    onEachFeature: (feature, layer) => {
      layer.bindPopup(unitPopup(feature.properties));
    }
  }).addTo(state.map);

  if (state.layerVisible.buffers) state.bufferLayer.addTo(state.map);
}

function unitPopup(unit) {
  const color = getRiskColor(unit.risk_level);
  const scope = SCOPE_LABELS[unit.network_scope] || "Escopo a confirmar";
  const quality = unit.data_quality !== "ok"
    ? `<div class="popup-note"><strong>Revisão de cadastro:</strong> ${escapeHtml(unit.quality_note)}</div>`
    : "";
  const hydrology = hydrologyNote(unit);

  return `<div class="map-popup unit-popup">
    <div class="popup-meta"><span class="popup-kicker" style="color:${color}">#${unit.ranking} · IECS ${formatNumber(unit.iecs_score)}</span><span class="popup-scope">${escapeHtml(scope)}</span></div>
    <h3>${escapeHtml(unit.display_name)}</h3>
    <p class="popup-type">${escapeHtml(unit.type)} · ${escapeHtml(unit.suburb || "Araraquara")}</p>
    <dl class="popup-metrics">
      <div><dt>Temperatura média · 300m</dt><dd>${formatNumber(unit.surface_temp_300m)} °C</dd></div>
      <div><dt>Vegetação · NDVI 300m</dt><dd>${formatNumber(unit.ndvi_300m, 2)}</dd></div>
      <div><dt>Vulnerabilidade social · Censo 2022</dt><dd>${formatNumber(unit.vulnerability_score_300m, 2)} / 5</dd></div>
    </dl>
    ${hydrology}
    ${quality}
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
  if (!toolbar || toolbar.querySelector('[data-layer="flood"]')) return;
  const button = document.createElement("button");
  button.className = "map-tool is-active";
  button.dataset.layer = "flood";
  button.type = "button";
  button.setAttribute("aria-pressed", "true");
  button.textContent = "💧 Risco hídrico";
  toolbar.appendChild(button);
}

function toggleLayer(layerName, button) {
  const layers = { climate: state.climateLayer, green: state.greenLayer, flood: state.floodLayer, buffers: state.bufferLayer };
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
    element.innerHTML = `<strong>Como ler</strong><span><i class="legend-dot critical"></i>IECS mais alto</span><span><i class="legend-dot green"></i>área verde</span><span><i class="legend-line"></i>buffer de 300m</span>`;
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
  const value = normalize(phenomenon);
  if (value.includes("inundacao")) return "#2563eb";
  if (value.includes("enxurrada")) return "#0f766e";
  return "#7c3aed";
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
