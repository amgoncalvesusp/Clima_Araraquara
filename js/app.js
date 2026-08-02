const DATA_FILES = {
  units: "data/unidades_saude_analise_araraquara.geojson",
  baseUnits: "data/unidades_saude_araraquara.json",
  climate: "data/urbverde_araraquara.geojson",
  green: "data/areas_verdes_araraquara.geojson",
  summary: "data/resumo_estatistico.json",
  suggestions: "data/unidades_sugeridas_araraquara.json",
  metadata: "data/metadata_unidades_saude_araraquara.json",
  sources: "data/fontes_publicas_saude_araraquara.json"
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
  bufferLayer: null,
  unitsLayer: null,
  units: [],
  features: [],
  suggestions: [],
  metadata: {},
  sources: [],
  layerVisible: { climate: true, green: true, buffers: true },
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
    state.features = data.units.features.map(feature => mergeUnitMetadata(feature, data.baseUnits));
    state.units = state.features.map(feature => feature.properties);

    renderClimateLayer(data.climate);
    renderGreenLayer(data.green);
    renderSources(data.sources);
    renderPendingCatalog(data.suggestions);
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

  return `<div class="map-popup unit-popup">
    <div class="popup-meta"><span class="popup-kicker" style="color:${color}">#${unit.ranking} · IECS ${formatNumber(unit.iecs_score)}</span><span class="popup-scope">${escapeHtml(scope)}</span></div>
    <h3>${escapeHtml(unit.display_name)}</h3>
    <p class="popup-type">${escapeHtml(unit.type)} · ${escapeHtml(unit.suburb || "Araraquara")}</p>
    <dl class="popup-metrics">
      <div><dt>Temperatura média · 300m</dt><dd>${formatNumber(unit.surface_temp_300m)} °C</dd></div>
      <div><dt>Vegetação · NDVI 300m</dt><dd>${formatNumber(unit.ndvi_300m, 2)}</dd></div>
      <div><dt>Vulnerabilidade</dt><dd>${formatNumber(unit.vulnerability_score_300m, 2)} / 5</dd></div>
    </dl>
    ${quality}
  </div>`;
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

function toggleLayer(layerName, button) {
  const layers = { climate: state.climateLayer, green: state.greenLayer, buffers: state.bufferLayer };
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
  errorBox.hidden = false;
  errorBox.querySelector("p").textContent = "Abra o projeto por um servidor local (python -m http.server 8000) para permitir o carregamento dos arquivos de dados.";
  errorBox.querySelector("small").textContent = error.message;
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
