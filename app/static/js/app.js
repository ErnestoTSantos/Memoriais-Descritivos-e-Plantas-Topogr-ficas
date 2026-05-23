const form = document.getElementById("process-form");

const errorEl = document.getElementById("error");
const resultsEl = document.getElementById("results");
const metricsEl = document.getElementById("metrics");
const segmentsBody = document.getElementById("segments-body");
const memorialEl = document.getElementById("memorial");
const segmentsCount = document.getElementById("segments-count");
const pointsAdjustmentSection = document.getElementById("points-adjustment-section");
const pointsAdjustmentBody = document.getElementById("points-adjustment-body");
const irradiationTableSection = document.getElementById("irradiation-table-section");
const irradiationTableBody = document.getElementById("irradiation-table-body");
const irradiationTableCount = document.getElementById("irradiation-table-count");
const pointsAdjustmentCount = document.getElementById("points-adjustment-count");

const statusBar = document.getElementById("processing-status-bar");
const statusText = document.getElementById("status-text");
const statusChips = document.getElementById("status-chips");
const resultsValidation = document.getElementById("results-validation");
const planimetricSummaryEl = document.getElementById("planimetric-summary");
const angularSummaryEl = document.getElementById("angular-summary");

const submitBtn = document.getElementById("submit-btn");
const btnText = submitBtn?.querySelector(".btn-text");
const btnLoading = submitBtn?.querySelector(".btn-loading");

const measurementModeEl = document.getElementById("measurement-mode");
const irradiationFields = document.querySelectorAll(".irradiation-only");

const traverseBody = document.getElementById("traverse-body");
const traverseSection = document.getElementById("traverse-section");
const addTraverseRowBtn = document.getElementById("add-traverse-row");
const traverseCountEl = document.getElementById("traverse-count");

const stationsBody = document.getElementById("stations-body");
const addStationRowBtn = document.getElementById("add-station-row");
const stationsCountEl = document.getElementById("stations-count");
const stationsValidationEl = document.getElementById("stations-validation");
const stationNamesListEl = document.getElementById("station-names-list");

const mapFitBtn = document.getElementById("map-fit-btn");
const mapLabelsBtn = document.getElementById("map-labels-btn");
const copyMemorialBtn = document.getElementById("copy-memorial-btn");
const validationItems = document.getElementById("validation-items");

let map = null;
let polygonLayer = null;
let vertexLayers = [];
let bearingLayers = [];
let currentData = null;
let mapMode = null;
let polygonBounds = null;
let showLabels = true;

function dmsToDecimal(deg, min, sec) {
  const d = parseFloat(String(deg).replace(",", "."));
  const m = parseFloat(String(min).replace(",", "."));
  const s = parseFloat(String(sec).replace(",", "."));
  if (!Number.isFinite(d) || !Number.isFinite(m) || !Number.isFinite(s)) return NaN;
  return d + m / 60.0 + s / 3600.0;
}

function getDmsDecimal(container) {
  if (!container) return NaN;
  const degVal = container.querySelector(".dms-deg")?.value?.trim() ?? "";
  const minVal = container.querySelector(".dms-min")?.value?.trim() ?? "";
  const secVal = container.querySelector(".dms-sec")?.value?.trim() ?? "";
  if (degVal === "" && minVal === "" && secVal === "") return NaN;
  const d = parseFloat(degVal) || 0;
  const m = parseFloat(minVal) || 0;
  const s = parseFloat(secVal) || 0;
  const val = d + m / 60.0 + s / 3600.0;
  return Number.isFinite(val) ? val : NaN;
}

function dmsGroupHtml(extraClass = "") {
  return `<div class="dms-group${extraClass ? " " + extraClass : ""}">` +
    `<input class="dms-deg" type="number" min="0" max="360" placeholder="GG" />` +
    `<span class="dms-sep">°</span>` +
    `<input class="dms-min" type="number" min="0" max="59" placeholder="MM" />` +
    `<span class="dms-sep">'</span>` +
    `<input class="dms-sec" type="number" min="0" max="59" placeholder="SS" />` +
    `<span class="dms-sep">"</span>` +
    `</div>`;
}

function handleDmsAutoAdvance(event) {
  const input = event.target;
  if (!input.classList.contains("dms-deg") &&
      !input.classList.contains("dms-min") &&
      !input.classList.contains("dms-sec")) return;

  const maxLen = input.classList.contains("dms-deg") ? 3 : 2;
  if (String(input.value).length >= maxLen) {
    const group = input.closest(".dms-group");
    if (!group) return;
    const inputs = Array.from(group.querySelectorAll("input"));
    const idx = inputs.indexOf(input);
    if (idx >= 0 && idx < inputs.length - 1) {
      inputs[idx + 1].focus();
      inputs[idx + 1].select();
    }
  }
}

let traverseRowCount = 0;

function addTraverseRow(station = "", sightedPoint = "", distance = "") {
  traverseRowCount++;
  const idx = traverseRowCount;
  const tr = document.createElement("tr");
  tr.dataset.rowId = idx;
  tr.innerHTML =
    `<td class="mono">${idx}</td>` +
    `<td><input class="traverse-station" type="text" list="station-names-list" value="${escapeHtml(station)}" placeholder="A" /></td>` +
    `<td><input class="traverse-point" type="text" value="${escapeHtml(sightedPoint)}" placeholder="B" /></td>` +
    `<td><input class="traverse-distance" type="number" step="any" value="${escapeHtml(String(distance))}" placeholder="25.50" /></td>` +
    `<td>${dmsGroupHtml("traverse-angle-dms")}</td>` +
    `<td><button type="button" class="btn-remove-row" onclick="removeTraverseRow(this)" title="Remover linha">` +
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">` +
    `<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>` +
    `</svg></button></td>`;
  const dmsGroup = tr.querySelector(".dms-group");
  if (dmsGroup) dmsGroup.addEventListener("keyup", handleDmsAutoAdvance);

  traverseBody.appendChild(tr);
  updateTraverseCount();
  runTraverseValidation();
}

window.removeTraverseRow = function removeTraverseRow(btn) {
  btn.closest("tr").remove();
  Array.from(traverseBody.querySelectorAll("tr")).forEach((tr, i) => {
    tr.querySelector("td:first-child").textContent = i + 1;
  });
  updateTraverseCount();
  runTraverseValidation();
};

function updateTraverseCount() {
  const n = traverseBody.querySelectorAll("tr").length;
  if (traverseCountEl) {
    traverseCountEl.textContent = `${n} linha${n !== 1 ? "s" : ""}`;
  }
}

function serializeTraverseTable() {
  const rows = Array.from(traverseBody.querySelectorAll("tr"));
  return rows.map(tr => {
    const station = tr.querySelector(".traverse-station")?.value?.trim() || "";
    const sightedPoint = tr.querySelector(".traverse-point")?.value?.trim() || "";
    const distanceStr = tr.querySelector(".traverse-distance")?.value?.trim() || "";
    const distanceM = parseFloat(distanceStr.replace(",", "."));
    const dmsContainer = tr.querySelector(".traverse-angle-dms");
    const angleDeg = getDmsDecimal(dmsContainer);
    return {
      station,
      sighted_point: sightedPoint,
      distance_m: distanceM,
      observed_angle_deg: angleDeg,
    };
  });
}

let traverseValidationTimeout;

function runTraverseValidation() {
  clearTimeout(traverseValidationTimeout);
  traverseValidationTimeout = setTimeout(() => {
    if (!validationItems) return;
    const rows = serializeTraverseTable();
    const valid = rows.filter(r =>
      r.station && r.sighted_point &&
      Number.isFinite(r.distance_m) && r.distance_m > 0 &&
      Number.isFinite(r.observed_angle_deg)
    );
    const errors = rows.length - valid.length;
    const items = [];

    if (valid.length > 0) {
      items.push({ type: "ok", icon: "✓", text: `${valid.length} linha${valid.length !== 1 ? "s" : ""} válida${valid.length !== 1 ? "s" : ""}` });
    }
    if (errors > 0) {
      items.push({ type: "error", icon: "✕", text: `${errors} linha${errors !== 1 ? "s" : ""} com dados incompletos ou inválidos` });
    }
    if (valid.length > 0 && valid.length < 3) {
      items.push({ type: "warn", icon: "⚠", text: "Mínimo 3 lados necessários para calcular o polígono" });
    }

    if (measurementModeEl?.value === "irradiacao") {
      const stations = serializeStations();
      const stationNames = new Set(stations.filter(s => s.name).map(s => s.name));
      if (stationNames.size > 0) {
        const unknownStations = new Set(
          valid.filter(r => r.station && !stationNames.has(r.station)).map(r => r.station)
        );
        unknownStations.forEach(name => {
          items.push({ type: "error", icon: "✕", text: `Estação '${name}' não encontrada nas estações cadastradas` });
        });
      }
    }

    if (!items.length) {
      items.push({ type: "neutral", icon: "—", text: "Aguardando dados de entrada..." });
    }

    validationItems.innerHTML = items.map(item => `
      <div class="validation-item ${item.type}">
        <span class="vi-icon">${item.icon}</span>
        <span>${escapeHtml(item.text)}</span>
      </div>
    `).join("");
  }, 250);
}
traverseBody?.addEventListener("input", runTraverseValidation);

addTraverseRowBtn?.addEventListener("click", () => addTraverseRow());
addTraverseRow("A", "B");
addTraverseRow("B", "C");
addTraverseRow("C", "A");

let stationRowCount = 0;

function addStationRow(name = "", x = "", y = "") {
  stationRowCount++;
  const idx = stationRowCount;
  const tr = document.createElement("tr");
  tr.dataset.stationId = idx;
  tr.innerHTML =
    `<td class="mono">${idx}</td>` +
    `<td><input class="station-name" type="text" value="${escapeHtml(String(name))}" placeholder="A" /></td>` +
    `<td><input class="station-x" type="number" step="any" value="${escapeHtml(String(x))}" placeholder="487654.321" /></td>` +
    `<td><input class="station-y" type="number" step="any" value="${escapeHtml(String(y))}" placeholder="7654321.123" /></td>` +
    `<td><button type="button" class="btn-remove-row" onclick="removeStationRow(this)" title="Remover estação">` +
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">` +
    `<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>` +
    `</svg></button></td>`;
  stationsBody.appendChild(tr);
  updateStationsCount();
  updateStationNameOptions();
  runStationsValidation();
}

window.removeStationRow = function removeStationRow(btn) {
  btn.closest("tr").remove();
  Array.from(stationsBody.querySelectorAll("tr")).forEach((tr, i) => {
    tr.querySelector("td:first-child").textContent = i + 1;
  });
  updateStationsCount();
  updateStationNameOptions();
  runStationsValidation();
};

function updateStationsCount() {
  const n = stationsBody ? stationsBody.querySelectorAll("tr").length : 0;
  if (stationsCountEl) {
    stationsCountEl.textContent = n === 1 ? "1 estação" : `${n} estações`;
  }
}

function updateStationNameOptions() {
  if (!stationNamesListEl) return;
  const names = serializeStations()
    .map(station => station.name)
    .filter(Boolean);
  stationNamesListEl.innerHTML = [...new Set(names)]
    .map(name => `<option value="${escapeHtml(name)}"></option>`)
    .join("");
}

function serializeStations() {
  if (!stationsBody) return [];
  return Array.from(stationsBody.querySelectorAll("tr")).map(tr => ({
    name: tr.querySelector(".station-name")?.value?.trim() || "",
    x: parseFloat((tr.querySelector(".station-x")?.value || "").replace(",", ".")),
    y: parseFloat((tr.querySelector(".station-y")?.value || "").replace(",", ".")),
  }));
}

function validateStationsData(stations, observations) {
  const errors = [];
  if (!stations.length) {
    errors.push("Informe pelo menos uma estação de irradiação.");
    return errors;
  }

  const names = new Set();
  stations.forEach((s, i) => {
    if (!s.name) errors.push(`Estação ${i + 1}: nome obrigatório.`);
    else if (names.has(s.name)) errors.push(`Nome de estação duplicado: '${s.name}'.`);
    else names.add(s.name);
    if (!Number.isFinite(s.x)) errors.push(`Estação '${s.name || i + 1}': X inválido.`);
    if (!Number.isFinite(s.y)) errors.push(`Estação '${s.name || i + 1}': Y inválido.`);
  });

  if (observations && names.size > 0) {
    observations.forEach((obs, i) => {
      if (!obs.station) {
        errors.push(`Linha ${i + 1}: informe o nome da estação.`);
      } else if (!names.has(obs.station)) {
        errors.push(`Linha ${i + 1}: estação '${obs.station}' não encontrada.`);
      }
    });
  }

  return errors;
}

function runStationsValidation() {
  if (!stationsValidationEl) return;
  const mode = measurementModeEl?.value;
  if (mode !== "irradiacao") {
    stationsValidationEl.classList.add("hidden");
    return;
  }
  const stations = serializeStations();
  const observations = serializeTraverseTable();
  const errors = validateStationsData(stations, observations);

  if (!errors.length) {
    stationsValidationEl.classList.add("hidden");
    return;
  }

  stationsValidationEl.innerHTML =
    `<div class="validation-title">Validação das estações</div>` +
    errors.map(e => `<div class="validation-item error"><span class="vi-icon">✕</span><span>${escapeHtml(e)}</span></div>`).join("");
  stationsValidationEl.classList.remove("hidden");
}

stationsBody?.addEventListener("input", () => {
  updateStationsCount();
  updateStationNameOptions();
  runStationsValidation();
  runTraverseValidation();
});

addStationRowBtn?.addEventListener("click", () => addStationRow());

function updateInputMode() {
  const irradiation = measurementModeEl?.value === "irradiacao";
  irradiationFields.forEach(el => {
    el.classList.toggle("hidden", !irradiation);
  });
  document.querySelectorAll(".planimetric-only").forEach(el => {
    el.classList.toggle("hidden", irradiation);
  });
  const angleHeader = document.getElementById("traverse-angle-header");
  const tableTitle = document.getElementById("traverse-table-title");
  if (angleHeader) {
    if (irradiation) {
      angleHeader.textContent = "Azimute";
      angleHeader.title = "Azimute em GMS (graus°minutos'segundos\") — direção absoluta do norte";
    } else {
      angleHeader.textContent = "Ângulo observado";
      angleHeader.title = "Ângulo observado em GMS (graus°minutos'segundos\")";
    }
  }
  if (tableTitle) {
    tableTitle.textContent = irradiation ? "Irradiação — Observações" : "Caminhamento Topográfico";
  }
  if (irradiation && stationsBody && stationsBody.querySelectorAll("tr").length === 0) {
    addStationRow("A");
  }

  runStationsValidation();
  runTraverseValidation();
}

measurementModeEl?.addEventListener("change", updateInputMode);
updateInputMode();

function safeNumber(value) {
  if (typeof value === "number") return Number.isFinite(value) ? value : NaN;
  if (value === null || value === undefined) return NaN;
  return parseFloat(String(value).replace(",", "."));
}

function isFiniteCoord(x, y) {
  return Number.isFinite(x) && Number.isFinite(y);
}

function normalizePoint(point = {}) {
  return {
    ...point,
    vertex: point.vertex || point.name || point.label || null,
    x: safeNumber(point.x),
    y: safeNumber(point.y),
  };
}

function removeDuplicateClosingPoint(points) {
  if (!Array.isArray(points) || points.length < 2) return points;
  const first = points[0];
  const last = points[points.length - 1];
  return first[0] === last[0] && first[1] === last[1] ? points.slice(0, -1) : points;
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value, decimals = 2) {
  const num = safeNumber(value);
  return Number.isFinite(num) ? num.toFixed(decimals) : "0";
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function statusCss(status, prefix = "metric") {
  if (status === "fora_da_tolerancia") return `${prefix}-error`;
  if (status === "proximo_do_limite") return `${prefix}-warn`;
  if (status === "dentro_da_tolerancia") return `${prefix}-ok`;
  return "";
}

function contributionCss(status) {
  if (status === "alta") return { row: "row-error", cell: "td-error", chip: "chip-red" };
  if (status === "moderada") return { row: "row-warning", cell: "td-warn", chip: "chip-amber" };
  return { row: "", cell: "td-ok", chip: "chip-green" };
}

function statusTextLabel(status) {
  if (status === "alta") return "alta";
  if (status === "moderada") return "moderada";
  if (status === "baixa") return "baixa";
  if (status === "fora_da_tolerancia") return "fora";
  if (status === "proximo_do_limite") return "limite";
  if (status === "dentro_da_tolerancia") return "ok";
  return status || "n/d";
}

function formatMaybeNumber(value, decimals = 3) {
  const num = safeNumber(value);
  return Number.isFinite(num) ? formatNumber(num, decimals) : "-";
}

function formatMaybeText(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return text.trim() ? text : "-";
}

function getPlanimetricRows(data = {}, fallbackSegments = []) {
  const rows =
    safeArray(data.planimetric_table?.segments).length
      ? safeArray(data.planimetric_table.segments)
      : safeArray(data.planimetric_segments);

  if (rows.length) return rows;

  return safeArray(fallbackSegments).map(segment => ({
    ...segment,
    segment: `${segment.start_vertex || ""}-${segment.end_vertex || ""}`,
    station: segment.start_vertex,
    point_initial: segment.start_vertex,
    point_final: segment.end_vertex,
    distance: segment.distance_m,
    observed_angle: "-",
    angular_adjustment: `${formatNumber(segment.applied_angle_error_seconds, 2)}"`,
    corrected_angle: segment.azimuth_adjusted_dms || segment.azimuth_dms,
    azimuth: segment.azimuth_adjusted_dms || segment.azimuth_dms,
    east_positive: Math.max(safeNumber(segment.delta_e_m), 0),
    west_negative: Math.min(safeNumber(segment.delta_e_m), 0),
    north_positive: Math.max(safeNumber(segment.delta_n_m), 0),
    south_negative: Math.min(safeNumber(segment.delta_n_m), 0),
    delta_x: segment.delta_e_m,
    delta_y: segment.delta_n_m,
    closure_error_x: 0,
    closure_error_y: 0,
    correction_x: segment.correction_e_m,
    correction_y: segment.correction_n_m,
    adjusted_x: segment.adjusted_delta_e_m,
    adjusted_y: segment.adjusted_delta_n_m,
    accumulated_x: null,
    accumulated_y: null,
    error_contribution_percent: segment.contribution_percent,
    correction_applied: Math.hypot(safeNumber(segment.correction_e_m), safeNumber(segment.correction_n_m)),
    status: segment.contribution_status,
    messages: segment.observation ? [segment.observation] : [],
  }));
}

function rvClass(status) {
  if (status === "fora_da_tolerancia") return "rv-error";
  if (status === "proximo_do_limite") return "rv-warn";
  return "rv-ok";
}

function getCookie(name) {
  for (const cookie of (document.cookie || "").split(";")) {
    const [key, ...rest] = cookie.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return "";
}

function showToast(message, type = "default", duration = 3500) {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const icons = { success: "✓", error: "✕", warning: "⚠", default: "ℹ" };
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type] || "ℹ"}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);
  requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add("toast-show")));
  setTimeout(() => {
    toast.classList.remove("toast-show");
    setTimeout(() => toast.remove(), 250);
  }, duration);
}

function setLoading(loading) {
  if (!submitBtn) return;
  submitBtn.disabled = loading;
  btnText?.classList.toggle("hidden", loading);
  btnLoading?.classList.toggle("hidden", !loading);
}

function setStep(step) {
  document.querySelectorAll(".step").forEach((el, index) => {
    el.classList.remove("step-active", "step-done");
    if (index + 1 < step) el.classList.add("step-done");
    if (index + 1 === step) el.classList.add("step-active");
  });
}

function isProjected(points) {
  return points.some(p =>
    isFiniteCoord(p.x, p.y) && (Math.abs(p.x) > 1000 || Math.abs(p.y) > 1000)
  );
}

function initMap(mode) {
  if (map && mapMode === mode) return;
  if (map) { map.remove(); map = null; }
  mapMode = mode;
  if (mode === "projected") {
    map = L.map("map", { crs: L.CRS.Simple, minZoom: -10 });
  } else {
    map = L.map("map").setView([-15.78, -47.93], 5);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap", maxZoom: 19,
    }).addTo(map);
  }
  L.control.scale({ imperial: false, metric: true, position: "bottomleft" }).addTo(map);
}

function clearLabelLayers() {
  [...vertexLayers, ...bearingLayers].forEach(layer => {
    try { if (map?.hasLayer(layer)) map.removeLayer(layer); } catch (_) {}
  });
  vertexLayers = [];
  bearingLayers = [];
}

function clearMapLayers() {
  clearLabelLayers();
  try { if (polygonLayer && map?.hasLayer(polygonLayer)) map.removeLayer(polygonLayer); } catch (_) {}
  polygonLayer = null;
}

function renderMap(points = [], segments = []) {
  const normalized = safeArray(points).map(normalizePoint).filter(p => isFiniteCoord(p.x, p.y));
  if (normalized.length < 3) { clearMapLayers(); return; }
  const projected = isProjected(normalized);
  initMap(projected ? "projected" : "geographic");
  clearMapLayers();
  let latLngs = normalized.map(p => [p.y, p.x]).filter(p => Number.isFinite(p[0]) && Number.isFinite(p[1]));
  latLngs = removeDuplicateClosingPoint(latLngs);
  if (latLngs.length < 3) { clearMapLayers(); return; }
  polygonLayer = L.polygon(latLngs, {
    color: "#0c6c84", weight: 2.5, fillColor: "#0c6c84", fillOpacity: 0.07,
  }).addTo(map);
  polygonBounds = polygonLayer.getBounds();
  if (polygonBounds?.isValid()) map.fitBounds(polygonBounds, { padding: [48, 64] });
  if (showLabels) renderMapLabels(normalized, segments);
}

function renderMapLabels(points = [], segments = []) {
  if (!map) return;
  clearLabelLayers();

  points.forEach((point, index) => {
    if (!isFiniteCoord(point.x, point.y)) return;
    const label = point.vertex || `V${String(index + 1).padStart(2, "0")}`;
    const isFirst = index === 0;
    const icon = L.divIcon({
      className: "",
      html: `<div class="vertex-label${isFirst ? " first" : ""}">${escapeHtml(label)}</div>`,
      iconSize: [0, 0], iconAnchor: [12, 12],
    });
    const marker = L.marker([point.y, point.x], { icon, interactive: true })
      .bindPopup(`<strong>${escapeHtml(label)}</strong><br>X: ${formatNumber(point.x, 3)}<br>Y: ${formatNumber(point.y, 3)}`)
      .addTo(map);
    vertexLayers.push(marker);
  });

  if (!Array.isArray(segments) || !segments.length) return;
  const pointMap = {};
  points.forEach(p => { if (p.vertex) pointMap[p.vertex] = p; });
  segments.forEach(segment => {
    const from = pointMap[segment.start_vertex];
    const to = pointMap[segment.end_vertex];
    if (!from || !to) return;
    const mx = (from.x + to.x) / 2;
    const my = (from.y + to.y) / 2;
    if (!isFiniteCoord(mx, my)) return;
    const labelText = segment.bearing
      ? `${segment.bearing} · ${formatNumber(segment.distance_m, 2)}m`
      : `${formatNumber(segment.distance_m, 2)}m`;
    const icon = L.divIcon({
      className: "",
      html: `<div class="bearing-label">${escapeHtml(labelText)}</div>`,
      iconSize: [0, 0], iconAnchor: [0, 8],
    });
    bearingLayers.push(L.marker([my, mx], { icon, interactive: false }).addTo(map));
  });
}

mapFitBtn?.addEventListener("click", () => {
  if (map && polygonBounds?.isValid()) map.fitBounds(polygonBounds, { padding: [48, 64] });
});

mapLabelsBtn?.addEventListener("click", () => {
  showLabels = !showLabels;
  mapLabelsBtn.dataset.active = showLabels ? "true" : "false";
  if (!currentData) return;
  const points = safeArray(currentData.points).map(normalizePoint).filter(p => isFiniteCoord(p.x, p.y));
  if (showLabels) renderMapLabels(points, currentData.segments);
  else clearLabelLayers();
});

form?.addEventListener("submit", async event => {
  event.preventDefault();
  errorEl.textContent = "";
  errorEl.classList.add("hidden");
  setLoading(true);
  setStep(3);

  const formData = new FormData(form);
  const mode = measurementModeEl?.value;
  const allObservations = serializeTraverseTable();
  const observations = allObservations.filter(r =>
    r.station && r.sighted_point &&
    Number.isFinite(r.distance_m) && r.distance_m > 0 &&
    Number.isFinite(r.observed_angle_deg)
  );
  if (observations.length < 3) {
    setLoading(false);
    setStep(2);
    errorEl.textContent = "Informe pelo menos 3 linhas válidas com estação, ponto visado, distância e ângulo.";
    errorEl.classList.remove("hidden");
    showToast("Dados incompletos na tabela de medições.", "error", 5000);
    return;
  }
  formData.set("traverse_observations", JSON.stringify(observations));

  if (mode === "irradiacao") {
    const stations = serializeStations();
    const stationErrors = validateStationsData(stations, observations);
    if (stationErrors.length) {
      setLoading(false);
      setStep(2);
      errorEl.textContent = stationErrors[0];
      errorEl.classList.remove("hidden");
      showToast(stationErrors[0], "error", 5000);
      return;
    }
    formData.set("stations_json", JSON.stringify(stations));
  }

  if (mode === "planimetrico") {
    const initialAzimuthContainer = document.getElementById("initial-azimuth-dms");
    const azimuthDeg = getDmsDecimal(initialAzimuthContainer);
    formData.set("initial_azimuth_deg", Number.isFinite(azimuthDeg) ? azimuthDeg.toString() : "0");
  }

  try {
    const response = await fetch("/api/process", {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Erro ao processar.");

    currentData = data;
    renderResults(data);
    resultsEl.classList.remove("hidden");
    resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
    setStep(4);
    showToast("Levantamento processado com sucesso!", "success");
  } catch (err) {
    console.error(err);
    errorEl.textContent = err?.message || "Erro inesperado.";
    errorEl.classList.remove("hidden");
    setStep(2);
    showToast(err?.message || "Erro inesperado.", "error", 5000);
  } finally {
    setLoading(false);
  }
});

function renderAngularSummary(summary) {
  if (!angularSummaryEl) return;
  if (!summary) { angularSummaryEl.classList.add("hidden"); return; }

  const isOk = summary.status === "ok";
  const isWarning = summary.status === "warning";
  const badgeClass = isOk ? "chip-green" : isWarning ? "chip-amber" : "chip-blue";

  angularSummaryEl.innerHTML = `
    <div class="angular-summary-card">
      <div class="as-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 8v4l3 3"/>
        </svg>
        Fechamento Angular
        <span class="chip ${badgeClass}">${escapeHtml(summary.status_label)}</span>
      </div>
      <div class="as-grid">
        <div><span class="ps-label">Número de lados</span><strong>${summary.n_sides}</strong></div>
        <div><span class="ps-label">Erro de fechamento</span><strong class="mono">${formatNumber(summary.angular_misclosure_seconds, 2)}&Prime;</strong></div>
        <div><span class="ps-label">Tolerância (ε√n)</span><strong class="mono">${summary.allowed_error_seconds !== null && summary.allowed_error_seconds !== undefined ? formatNumber(summary.allowed_error_seconds, 2) + "\"" : "—"}</strong></div>
        <div><span class="ps-label">Correção por lado</span><strong class="mono">${formatNumber(summary.correction_per_side_seconds, 4)}&Prime;</strong></div>
      </div>
    </div>
  `;
  angularSummaryEl.classList.remove("hidden");
}

function renderResults(data = {}) {
  const points = safeArray(data.points);
  const adjustedPoints = safeArray(data.adjusted_points).length ? safeArray(data.adjusted_points) : points;
  const segments = safeArray(data.segments);
  const planimetricTable = data.planimetric_table || {};
  const planimetricRows = getPlanimetricRows(data, segments);
  const planimetricSummary = planimetricTable.summary || {};
  const summary = data.adjustment_summary || {};

  const closureError = Number.isFinite(safeNumber(summary.linear_closure_error_m))
    ? safeNumber(summary.linear_closure_error_m)
    : safeNumber(data.closure_error_m);

  const uniquePoints = removeDuplicateClosingPoint(points.map(p => [p.x, p.y])).length;
  const perimeter = safeNumber(data.perimeter_m);
  const area = safeNumber(data.area_m2);
  renderAngularSummary(data.traverse_angular_summary || null);
  statusBar.className = "status-bar status-ok";
  statusText.textContent = "Levantamento processado com sucesso";

  const angSum = data.traverse_angular_summary;
  const angStatusChip = angSum
    ? `<span class="chip ${angSum.status === "ok" ? "chip-green" : angSum.status === "warning" ? "chip-amber" : "chip-blue"}">Angular: ${escapeHtml(angSum.status === "ok" ? "dentro tolerância" : angSum.status === "warning" ? "fora tolerância" : "n/d")}</span>`
    : "";

  statusChips.innerHTML = `
    <span class="chip chip-green">Fechamento: ${formatNumber(closureError, 4)} m</span>
    ${angStatusChip}
    <span class="chip chip-blue">${uniquePoints} vértices</span>
  `;
  const precisionRatio = perimeter > 0 && closureError > 0
    ? `1:${Math.round(perimeter / closureError).toLocaleString("pt-BR")}`
    : "1:∞";

  metricsEl.innerHTML = `
    <div class="metric-card">
      <div class="metric-label">Área</div>
      <div class="metric-value">${formatNumber(area, 2)}</div>
      <div class="metric-unit">m² · ${formatNumber(area / 10000, 4)} ha</div>
    </div>

    <div class="metric-card">
      <div class="metric-label">Perímetro</div>
      <div class="metric-value">${formatNumber(perimeter, 2)}</div>
      <div class="metric-unit">metros</div>
    </div>

    <div class="metric-card">
      <div class="metric-label">Erro de Fechamento</div>
      <div class="metric-value">${formatNumber(closureError, 4)}</div>
      <div class="metric-unit">ΔE ${formatMaybeNumber(summary.closure_dx_m, 4)} · ΔN ${formatMaybeNumber(summary.closure_dy_m, 4)}</div>
    </div>

    <div class="metric-card">
      <div class="metric-label">Precisão Linear</div>
      <div class="metric-value">${precisionRatio}</div>
      <div class="metric-unit">relação de fechamento · erro acum.: ${formatMaybeNumber(summary.accumulated_error_m, 4)} m</div>
    </div>

    ${angSum ? `
    <div class="metric-card ${angSum.status === "ok" ? "metric-ok" : angSum.status === "warning" ? "metric-warn" : ""}">
      <div class="metric-label">Fechamento Angular</div>
      <div class="metric-value">${formatNumber(angSum.angular_misclosure_seconds, 2)}</div>
      <div class="metric-unit">segundos · tol: ${angSum.allowed_error_seconds !== null && angSum.allowed_error_seconds !== undefined ? formatNumber(angSum.allowed_error_seconds, 2) + "\"" : "—"}</div>
    </div>
    ` : ""}

    <div class="metric-card">
      <div class="metric-label">Vértices</div>
      <div class="metric-value">${Math.max(points.length - 1, 0)}</div>
      <div class="metric-unit">pontos levantados</div>
    </div>
  `;
  const validationItemsList = [];
  validationItemsList.push({
    cls: "rv-ok",
    icon: "✓",
    text: `Erro de fechamento linear — ${formatNumber(closureError, 4)} m`,
  });
  if (angSum) {
    validationItemsList.push({
      cls: angSum.status === "ok" ? "rv-ok" : "rv-warn",
      icon: angSum.status === "ok" ? "✓" : "⚠",
      text: angSum.status_label,
    });
  }
  validationItemsList.push({
    cls: "rv-ok",
    icon: "✓",
    text: "Polígono válido — calculado a partir do caminhamento",
  });
  safeArray(summary.messages).forEach(message => {
    validationItemsList.push({ cls: "rv-ok", icon: "i", text: message });
  });

  resultsValidation.innerHTML = validationItemsList.map(item => `
    <div class="rv-item ${item.cls}">
      <span class="rv-icon">${item.icon}</span>
      ${escapeHtml(item.text)}
    </div>
  `).join("");
  resultsValidation.classList.remove("hidden");
  if (planimetricSummaryEl) {
    const formulas = planimetricTable.formulas || {};
    const formulaList = [formulas.projecao_e, formulas.projecao_n, formulas.bowditch_x, formulas.bowditch_y].filter(Boolean);

    planimetricSummaryEl.innerHTML = `
      <div class="ps-grid">
        <div>
          <span class="ps-label">Fechamento X/Y</span>
          <strong class="mono">${formatMaybeNumber(planimetricSummary.closure_error_x ?? summary.closure_dx_m, 4)} / ${formatMaybeNumber(planimetricSummary.closure_error_y ?? summary.closure_dy_m, 4)}</strong>
        </div>
        <div>
          <span class="ps-label">Soma Cx/Cy</span>
          <strong class="mono">${formatMaybeNumber(planimetricSummary.correction_sum_x ?? summary.correction_sum_e_m, 4)} / ${formatMaybeNumber(planimetricSummary.correction_sum_y ?? summary.correction_sum_n_m, 4)}</strong>
        </div>
        <div>
          <span class="ps-label">Coordenada inicial</span>
          <strong class="mono">X ${formatMaybeNumber(planimetricSummary.initial_coordinate_x, 4)} · Y ${formatMaybeNumber(planimetricSummary.initial_coordinate_y, 4)}</strong>
        </div>
        <div>
          <span class="ps-label">Final ajustada</span>
          <strong class="mono">X ${formatMaybeNumber(planimetricSummary.final_adjusted_coordinate_x, 4)} · Y ${formatMaybeNumber(planimetricSummary.final_adjusted_coordinate_y, 4)}</strong>
        </div>
      </div>
      <div class="formula-strip">
        ${formulaList.map(item => `<span>${escapeHtml(item)}</span>`).join("")}
      </div>
    `;
    planimetricSummaryEl.classList.toggle("hidden", planimetricRows.length === 0);
  }
  if (irradiationTableSection && irradiationTableBody) {
    const irradiationRows = safeArray(data.irradiation_table?.rows);
    const isIrradiation = data.measurement_mode === "irradiacao" && irradiationRows.length > 0;
    irradiationTableSection.classList.toggle("hidden", !isIrradiation);
    if (isIrradiation) {
      if (irradiationTableCount) {
        irradiationTableCount.textContent = `${irradiationRows.length} ponto${irradiationRows.length !== 1 ? "s" : ""}`;
      }
      let lastStation = null;
      irradiationTableBody.innerHTML = irradiationRows.map((row, index) => {
        const stationChanged = row.station_name !== lastStation;
        lastStation = row.station_name;
        return `
          <tr class="${stationChanged && index > 0 ? "irr-station-break" : ""}">
            <td>${index + 1}</td>
            <td class="mono irr-station">
              ${escapeHtml(row.station_name || "—")}
              ${stationChanged ? `<br><small class="irr-station-coords">X ${formatNumber(row.station_x, 3)} · Y ${formatNumber(row.station_y, 3)}</small>` : ""}
            </td>
            <td class="mono">${escapeHtml(row.vertex)}</td>
            <td class="mono">${formatNumber(row.distance_m, 3)}</td>
            <td class="mono">${escapeHtml(row.azimuth_dms || "—")}</td>
            <td class="mono">${formatNumber(row.azimuth_deg, 6)}</td>
            <td class="mono ${row.delta_x >= 0 ? "projection-positive" : "projection-negative"}">${formatNumber(row.delta_x, 4)}</td>
            <td class="mono ${row.delta_y >= 0 ? "projection-positive" : "projection-negative"}">${formatNumber(row.delta_y, 4)}</td>
            <td class="mono accumulated-value">${formatNumber(row.x, 4)}</td>
            <td class="mono accumulated-value">${formatNumber(row.y, 4)}</td>
          </tr>
        `;
      }).join("");
    }
  }
  segmentsCount.textContent = `${planimetricRows.length} segmento${planimetricRows.length !== 1 ? "s" : ""}`;
  segmentsBody.innerHTML = planimetricRows.map((row, index) => {
    const contributionStatus = row.status || row.contribution_status || "baixa";
    const css = contributionCss(contributionStatus);
    const notes = [...safeArray(row.messages), row.observation].filter(Boolean).slice(0, 3).join(" ");
    return `
      <tr class="${css.row}">
        <td>${index + 1}</td>
        <td>${escapeHtml(formatMaybeText(row.station))}</td>
        <td>${escapeHtml(formatMaybeText(row.point_initial))}</td>
        <td class="mono">${escapeHtml(formatMaybeText(row.point_final))}</td>
        <td class="mono">${formatMaybeNumber(row.distance ?? row.distance_m, 3)}</td>
        <td class="mono raw-value">${escapeHtml(formatMaybeText(row.observed_angle))}</td>
        <td class="mono adjustment-value">${escapeHtml(formatMaybeText(row.angular_adjustment))}</td>
        <td class="mono corrected-value">${escapeHtml(formatMaybeText(row.corrected_angle))}</td>
        <td class="mono">${escapeHtml(formatMaybeText(row.azimuth))}</td>
        <td class="mono">${escapeHtml(formatMaybeText(row.bearing))}</td>
        <td class="mono projection-positive">${formatMaybeNumber(row.east_positive, 4)}</td>
        <td class="mono projection-negative">${formatMaybeNumber(row.west_negative, 4)}</td>
        <td class="mono projection-positive">${formatMaybeNumber(row.north_positive, 4)}</td>
        <td class="mono projection-negative">${formatMaybeNumber(row.south_negative, 4)}</td>
        <td class="mono raw-value">${formatMaybeNumber(row.delta_x, 4)}</td>
        <td class="mono raw-value">${formatMaybeNumber(row.delta_y, 4)}</td>
        <td class="mono closure-value">${formatMaybeNumber(row.closure_error_x, 4)}</td>
        <td class="mono closure-value">${formatMaybeNumber(row.closure_error_y, 4)}</td>
        <td class="mono adjustment-value">${formatMaybeNumber(row.correction_x, 4)}</td>
        <td class="mono adjustment-value">${formatMaybeNumber(row.correction_y, 4)}</td>
        <td class="mono adjusted-value">${formatMaybeNumber(row.adjusted_x ?? row.adjusted_delta_x, 4)}</td>
        <td class="mono adjusted-value">${formatMaybeNumber(row.adjusted_y ?? row.adjusted_delta_y, 4)}</td>
        <td class="mono accumulated-value">${formatMaybeNumber(row.accumulated_x ?? row.adjusted_coordinate_x, 4)}</td>
        <td class="mono accumulated-value">${formatMaybeNumber(row.accumulated_y ?? row.adjusted_coordinate_y, 4)}</td>
        <td class="mono ${css.cell}">${formatMaybeNumber(row.error_contribution_percent, 2)}%</td>
        <td class="mono adjustment-value">${formatMaybeNumber(row.correction_applied, 4)}</td>
        <td><span class="status-pill ${css.chip}">${escapeHtml(statusTextLabel(contributionStatus))}</span></td>
        <td><span class="cell-note">${escapeHtml(notes)}</span></td>
      </tr>
    `;
  }).join("");
  if (pointsAdjustmentSection && pointsAdjustmentBody) {
    const pointRows = adjustedPoints
      .filter(point => point.vertex)
      .map(point => {
        const css = contributionCss(point.contribution_status || "baixa");
        return `
          <tr class="${css.row}">
            <td>${escapeHtml(point.vertex)}</td>
            <td class="mono">E ${formatNumber(point.adjusted_x ?? point.x, 4)}<br>N ${formatNumber(point.adjusted_y ?? point.y, 4)}</td>
            <td class="mono">${formatNumber(point.linear_error_component_m, 4)} m</td>
            <td class="mono">${formatNumber(point.angular_error_component_m, 4)} m</td>
            <td class="mono">±${formatNumber(point.estimated_error_m, 4)} m</td>
            <td class="mono">${formatNumber(point.correction_e_m, 4)} / ${formatNumber(point.correction_n_m, 4)}</td>
            <td>
              <span class="status-pill ${css.chip}">${escapeHtml(point.contribution_status || "baixa")}</span>
              <span class="cell-note">${escapeHtml(point.observation || "")}</span>
            </td>
          </tr>
        `;
      });
    pointsAdjustmentBody.innerHTML = pointRows.join("");
    if (pointsAdjustmentCount) {
      pointsAdjustmentCount.textContent = `${pointRows.length} ponto${pointRows.length !== 1 ? "s" : ""}`;
    }
    pointsAdjustmentSection.classList.toggle("hidden", pointRows.length === 0);
  }
  memorialEl.textContent = data.memorial_text || "";
  renderMap(points, segments);
}

copyMemorialBtn?.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(memorialEl.textContent);
    const originalHtml = copyMemorialBtn.innerHTML;
    copyMemorialBtn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      Copiado!
    `;
    showToast("Memorial copiado para a área de transferência", "success");
    setTimeout(() => { copyMemorialBtn.innerHTML = originalHtml; }, 2500);
  } catch (err) {
    console.error(err);
    showToast("Não foi possível copiar o memorial", "error");
  }
});

document.querySelectorAll(".btn-export").forEach(button => {
  button.addEventListener("click", async () => {
    if (!currentData) {
      showToast("Processe o levantamento antes de exportar", "warning");
      return;
    }

    const format = button.dataset.format;
    const labels = { pdf: "PDF", docx: "Word (DOCX)", dxf: "DXF", dwg: "DWG" };
    const originalHtml = button.innerHTML;
    button.disabled = true;
    const strong = button.querySelector(".export-info strong");
    if (strong) strong.textContent = "Gerando...";

    const payload = {
      property_name: form.property_name.value,
      owner_name: form.owner_name.value,
      municipality: form.municipality.value,
      state: form.state.value,
      datum: form.datum.value,
      coordinate_system: form.coordinate_system.value,
      measurement_mode: form.measurement_mode.value,
      equipment_angular_error_seconds: currentData.equipment_angular_error_seconds,
      memorial_text: currentData.memorial_text || "",
      planimetric_table: currentData.planimetric_table || {},
      points: safeArray(currentData.points).slice(0, -1),
    };

    try {
      const response = await fetch(`/api/export/${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let detail = `Erro ao gerar ${format.toUpperCase()}`;
        try { const err = await response.json(); detail = err.detail || detail; } catch (_) {}
        throw new Error(detail);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const filename = (form.property_name.value || "memorial").replace(/\s+/g, "_").replace(/[^\w\-]/g, "");
      link.href = url;
      link.download = `${filename}.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      showToast(`${labels[format]} exportado com sucesso!`, "success");
    } catch (err) {
      console.error(err);
      showToast(`Erro ao exportar ${format.toUpperCase()}: ${err.message}`, "error", 5000);
    } finally {
      button.disabled = false;
      button.innerHTML = originalHtml;
    }
  });
});
