let map;
let unitsGeoJSON = null;
let climateGeoJSON = null;

let unitsLayer = null;
let bufferLayer = null;
let climateLayer = null;

let allUnits = [];

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  loadData();
  setupEventListeners();
});

function initMap() {
  // Center on Araraquara
  map = L.map("map", {
    zoomControl: false
  }).setView([-21.794, -48.176], 13);

  L.control.zoom({ position: "topright" }).addTo(map);

  // Dark Map Tiles (CartoDB Dark Matter)
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a> | UrbVerde USP',
    subdomains: "abcd",
    maxZoom: 19
  }).addTo(map);

  addLegend();
}

async function loadData() {
  try {
    const [unitsResp, climateResp, summaryResp] = await Promise.all([
      fetch("data/unidades_saude_analise_araraquara.geojson"),
      fetch("data/urbverde_araraquara.geojson"),
      fetch("data/resumo_estatistico.json")
    ]);

    unitsGeoJSON = await unitsResp.json();
    climateGeoJSON = await climateResp.json();
    const summary = await summaryResp.json();

    updateKPIs(summary);
    renderClimateLayer(climateGeoJSON);
    renderUnitsLayer(unitsGeoJSON);

    allUnits = unitsGeoJSON.features.map(f => f.properties);
    renderSidebarList(allUnits);
  } catch (err) {
    console.error("Erro ao carregar dados:", err);
  }
}

function updateKPIs(summary) {
  document.getElementById("kpi-total").innerText = summary.total_units_analyzed || 95;
  document.getElementById("kpi-temp-avg").innerText = `${summary.avg_surface_temp_araraquara || 32.4}°C`;
  document.getElementById("kpi-temp-max").innerText = `${summary.max_surface_temp || 36.7}°C`;
  
  const criticalCount = summary.units_by_risk_level["Crítico (Altíssimo Risco)"] || 0;
  const highCount = summary.units_by_risk_level["Alto"] || 0;
  document.getElementById("kpi-critical").innerText = criticalCount + highCount;
}

function renderClimateLayer(geojsonData) {
  if (climateLayer) map.removeLayer(climateLayer);

  climateLayer = L.geoJSON(geojsonData, {
    style: feature => {
      const temp = feature.properties.surface_temp;
      return {
        fillColor: getTempColor(temp),
        weight: 0.5,
        opacity: 0.4,
        color: "#ffffff",
        fillOpacity: 0.45
      };
    },
    onEachFeature: (feature, layer) => {
      const props = feature.properties;
      layer.bindPopup(`
        <div style="font-family: sans-serif; padding: 4px;">
          <h4 style="margin: 0 0 6px 0; color: #10b981;">Grid UrbVerde Araraquara</h4>
          <p style="margin: 2px 0;"><strong>Temp. Superfície:</strong> ${props.surface_temp}°C</p>
          <p style="margin: 2px 0;"><strong>Índice Vegetação (NDVI):</strong> ${props.ndvi}</p>
          <p style="margin: 2px 0;"><strong>Ilha de Calor:</strong> ${props.heat_category}</p>
          <p style="margin: 2px 0;"><strong>Vulnerabilidade Social:</strong> Nível ${props.vulnerability_score} (${props.vulnerability_desc})</p>
        </div>
      `);
    }
  }).addTo(map);
}

function getTempColor(temp) {
  return temp >= 35.5 ? "#d90429" :
         temp >= 33.5 ? "#ef4444" :
         temp >= 31.5 ? "#f4a261" :
         temp >= 29.5 ? "#e9c46a" : "#2a9d8f";
}

function renderUnitsLayer(geojsonData) {
  if (unitsLayer) map.removeLayer(unitsLayer);
  if (bufferLayer) map.removeLayer(bufferLayer);

  bufferLayer = L.layerGroup();
  
  unitsLayer = L.geoJSON(geojsonData, {
    pointToLayer: (feature, latlng) => {
      const props = feature.properties;
      const riskColor = getRiskColor(props.risk_level);

      // Add 300m buffer circle
      L.circle(latlng, {
        radius: 300,
        color: riskColor,
        weight: 1.5,
        fillColor: riskColor,
        fillOpacity: 0.12
      }).addTo(bufferLayer);

      // Circle Marker
      return L.circleMarker(latlng, {
        radius: 7,
        fillColor: riskColor,
        color: "#ffffff",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.95
      });
    },
    onEachFeature: (feature, layer) => {
      const props = feature.properties;
      const riskColor = getRiskColor(props.risk_level);
      
      layer.bindPopup(`
        <div style="font-family: sans-serif; min-width: 220px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-size: 11px; font-weight: 700; color: ${riskColor};">#${props.ranking} RANKING</span>
            <span style="font-size: 10px; background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 4px;">${props.type}</span>
          </div>
          <h3 style="margin: 0 0 8px 0; font-size: 14px; color: #0f172a;">${props.name}</h3>
          <p style="margin: 3px 0; font-size: 12px;"><strong>Temp. Média (300m):</strong> ${props.surface_temp_300m}°C</p>
          <p style="margin: 3px 0; font-size: 12px;"><strong>Vegetação (NDVI 300m):</strong> ${props.ndvi_300m}</p>
          <p style="margin: 3px 0; font-size: 12px;"><strong>Vulnerabilidade Social:</strong> ${props.vulnerability_score_300m} / 5.0</p>
          <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 8px 0;" />
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 11px;">Índice IECS:</span>
            <strong style="font-size: 14px; color: ${riskColor};">${props.iecs_score} / 100</strong>
          </div>
        </div>
      `);
    }
  });

  bufferLayer.addTo(map);
  unitsLayer.addTo(map);
}

function getRiskColor(riskLevel) {
  switch (riskLevel) {
    case "Crítico (Altíssimo Risco)": return "#dc2626";
    case "Alto": return "#f59e0b";
    case "Moderado": return "#eab308";
    default: return "#10b981";
  }
}

function renderSidebarList(units) {
  const container = document.getElementById("units-list");
  container.innerHTML = "";

  if (units.length === 0) {
    container.innerHTML = `<div style="text-align: center; padding: 20px; color: #94a3b8;">Nenhuma unidade encontrada.</div>`;
    return;
  }

  units.forEach(u => {
    const item = document.createElement("div");
    item.className = "unit-item";
    
    let riskClass = "low";
    if (u.risk_level.includes("Crítico")) riskClass = "critical";
    else if (u.risk_level.includes("Alto")) riskClass = "high";
    else if (u.risk_level.includes("Moderado")) riskClass = "moderate";

    item.innerHTML = `
      <div class="unit-header">
        <span class="unit-rank">#${u.ranking}</span>
        <span class="risk-tag ${riskClass}">${u.risk_level}</span>
      </div>
      <div class="unit-title">${u.name}</div>
      <div class="unit-type">${u.type} • ${u.suburb}</div>
      <div class="unit-metrics">
        <span class="metric-pill">Temp: <strong>${u.surface_temp_300m}°C</strong></span>
        <span class="metric-pill">NDVI: <strong>${u.ndvi_300m}</strong></span>
        <span class="metric-pill">IECS: <strong>${u.iecs_score}</strong></span>
      </div>
    `;

    item.addEventListener("click", () => {
      map.flyTo([u.lat, u.lon], 16, { duration: 1.2 });
      
      // Find matching layer and open popup
      unitsLayer.eachLayer(layer => {
        if (layer.feature.properties.id === u.id) {
          layer.openPopup();
        }
      });
    });

    container.appendChild(item);
  });
}

function setupEventListeners() {
  const searchInput = document.getElementById("search-input");
  const filterType = document.getElementById("filter-type");
  const filterRisk = document.getElementById("filter-risk");

  function filterData() {
    const query = searchInput.value.toLowerCase().trim();
    const typeVal = filterType.value;
    const riskVal = filterRisk.value;

    const filtered = allUnits.filter(u => {
      const matchesSearch = u.name.toLowerCase().includes(query) || u.suburb.toLowerCase().includes(query);
      const matchesType = typeVal === "ALL" || u.type === typeVal;
      const matchesRisk = riskVal === "ALL" || u.risk_level === riskVal;
      return matchesSearch && matchesType && matchesRisk;
    });

    renderSidebarList(filtered);
  }

  searchInput.addEventListener("input", filterData);
  filterType.addEventListener("change", filterData);
  filterRisk.addEventListener("change", filterData);

  // Toggle Layers
  document.getElementById("btn-toggle-climate").addEventListener("click", () => {
    if (map.hasLayer(climateLayer)) map.removeLayer(climateLayer);
    else climateLayer.addTo(map);
  });

  document.getElementById("btn-toggle-buffers").addEventListener("click", () => {
    if (map.hasLayer(bufferLayer)) map.removeLayer(bufferLayer);
    else bufferLayer.addTo(map);
  });

  // Modal Charts
  const modal = document.getElementById("charts-modal");
  document.getElementById("btn-open-charts").addEventListener("click", () => {
    modal.classList.add("active");
  });
  document.getElementById("btn-close-modal").addEventListener("click", () => {
    modal.classList.remove("active");
  });
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("active");
  });
}

function addLegend() {
  const legend = L.control({ position: "bottomright" });
  legend.onAdd = function() {
    const div = L.DomUtil.create("div", "legend-control");
    div.innerHTML = `
      <div class="legend-title">Temperatura de Superfície</div>
      <div class="legend-scale"></div>
      <div class="legend-labels">
        <span>25°C (Frio)</span>
        <span>32°C</span>
        <span>38°C (Quente)</span>
      </div>
      <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 8px 0;" />
      <div class="legend-title" style="margin-bottom: 4px;">Entorno Analisado</div>
      <div style="font-size: 11px; color: #94a3b8;">⚪ Raio de 300m por Unidade</div>
    `;
    return div;
  };
  legend.addTo(map);
}
