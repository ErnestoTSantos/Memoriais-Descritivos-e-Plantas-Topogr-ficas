const form = document.getElementById("process-form");
const errorEl = document.getElementById("error");
const resultsEl = document.getElementById("results");
const metricsEl = document.getElementById("metrics");
const segmentsBody = document.getElementById("segments-body");
const memorialEl = document.getElementById("memorial");

const measurementModeEl = document.getElementById("measurement-mode");
const coordinatesTextEl = document.getElementById("coordinates-text");
const fileInputEl = document.getElementById("coordinates-file");

const irradiationFields = document.querySelectorAll(".irradiation-only");

const irradiationOriginXEl = document.querySelector('[name="irradiation_origin_x"]');
const irradiationOriginYEl = document.querySelector('[name="irradiation_origin_y"]');

const irradiationAngleErrorEl = document.querySelector('[name="irradiation_angle_error_seconds"]');
const angleErrorLimitEl = document.querySelector('[name="angle_error_limit_seconds"]');
const closureToleranceEl = document.querySelector('[name="closure_tolerance_m"]');
const stationsTextEl = document.querySelector('[name="stations_text"]');

let map;
let polygonLayer;
let currentData;
let mapMode;

function getCookie(name) {
  const cookies = document.cookie ? document.cookie.split(";") : [];
  for (const cookie of cookies) {
    const [key, ...valueParts] = cookie.trim().split("=");
    if (key === name) return decodeURIComponent(valueParts.join("="));
  }
  return "";
}

/* =========================
   MAPA
========================= */

function isProjected(points) {
  return points.some((p) => Math.abs(p.x) > 180 || Math.abs(p.y) > 90);
}

function initMap(mode) {
  if (map && mapMode === mode) return;

  if (map) map.remove();

  mapMode = mode;

  if (mode === "projected") {
    map = L.map("map", { crs: L.CRS.Simple, minZoom: -5 });
    map.setView([0, 0], 0);
  } else {
    map = L.map("map").setView([-15.78, -47.93], 5);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
  }
}

function renderMap(points) {
  const projected = isProjected(points);
  initMap(projected ? "projected" : "geographic");

  if (polygonLayer) polygonLayer.remove();

  const latLngs = points.map((p) => [p.y, p.x]);
  polygonLayer = L.polygon(latLngs).addTo(map);

  map.fitBounds(polygonLayer.getBounds(), { padding: [20, 20] });
}

/* =========================
   INPUT MODE
========================= */

function updateInputMode() {
  const isIrradiation = measurementModeEl.value === "irradiacao";

  irradiationFields.forEach(el =>
    el.classList.toggle("hidden", !isIrradiation)
  );

  fileInputEl.accept = isIrradiation ? ".csv,.txt" : ".csv,.txt,.zip";

  if (isIrradiation) {
    coordinatesTextEl.placeholder = `V-01, 30, 100
V-02, 120, 150
V-03, 210, 180

ou com estação:
V-01, E1, 30, 100
V-02, E2, 120, 150`;
  } else {
    coordinatesTextEl.placeholder = `V-01, 987654.12, 9254321.44
V-02, 987700.00, 9254360.00
V-03, 987740.50, 9254300.90`;
  }
}

measurementModeEl.addEventListener("change", updateInputMode);
updateInputMode();

/* =========================
   SUBMIT
========================= */

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorEl.textContent = "";

  const formData = new FormData(form);

  // 🔧 normalização
  formData.set(
    "irradiation_angle_error_seconds",
    (irradiationAngleErrorEl.value || "").replace(",", ".")
  );

  formData.set(
    "angle_error_limit_seconds",
    (angleErrorLimitEl.value || "").replace(",", ".")
  );

  formData.set(
    "closure_tolerance_m",
    (closureToleranceEl.value || "").replace(",", ".")
  );

  if (measurementModeEl.value === "irradiacao") {
    formData.set(
      "irradiation_origin_x",
      (irradiationOriginXEl.value || "").replace(",", ".")
    );

    formData.set(
      "irradiation_origin_y",
      (irradiationOriginYEl.value || "").replace(",", ".")
    );

    if (stationsTextEl && stationsTextEl.value) {
      formData.set("stations_text", stationsTextEl.value);
    }
  }

  try {
    const response = await fetch("/api/process", {
      method: "POST",
      headers: {"X-CSRFToken": getCookie("csrftoken")},
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Erro ao processar.");
    }

    currentData = data;
    resultsEl.classList.remove("hidden");

    metricsEl.innerHTML = `
      <span>Área: ${data.area_m2.toFixed(2)} m²</span>
      <span>Perímetro: ${data.perimeter_m.toFixed(2)} m</span>
      <span>Fechamento: ${data.closure_error_m.toFixed(4)} m</span>
      <span>Tolerância: ${data.closure_tolerance_m ?? "n/a"} m</span>
      <span>Erro angular: ${(data.irradiation_angle_error_seconds || 0).toFixed(2)} s</span>
      <span>Vértices: ${data.points.length - 1}</span>
    `;

    segmentsBody.innerHTML = data.segments.map(s => `
      <tr>
        <td>${s.start_vertex}</td>
        <td>${s.end_vertex}</td>
        <td>${s.distance_m.toFixed(2)}</td>
        <td>${s.azimuth_dms}</td>
        <td>${s.azimuth_adjusted_dms || s.azimuth_dms}</td>
        <td>${(s.applied_angle_error_seconds || 0).toFixed(2)}</td>
        <td>${s.bearing}</td>
      </tr>
    `).join("");

    memorialEl.textContent = data.memorial_text;

    renderMap(data.points.slice(0, -1));

  } catch (err) {
    errorEl.textContent = err.message;
  }
});

/* =========================
   EXPORT
========================= */

document.querySelectorAll(".actions button").forEach((button) => {
  button.addEventListener("click", async () => {

    if (!currentData) {
      errorEl.textContent = "Processe antes de exportar.";
      return;
    }

    const format = button.dataset.format;

    const payload = {
      property_name: form.property_name.value,
      owner_name: form.owner_name.value,
      municipality: form.municipality.value,
      state: form.state.value,
      datum: form.datum.value,
      coordinate_system: form.coordinate_system.value,
      measurement_mode: form.measurement_mode.value,
      irradiation_origin_x: currentData.irradiation_origin_x,
      irradiation_origin_y: currentData.irradiation_origin_y,
      irradiation_angle_error_seconds: currentData.irradiation_angle_error_seconds,
      angle_error_limit_seconds: currentData.angle_error_limit_seconds,
      closure_tolerance_m: currentData.closure_tolerance_m,
      points: currentData.points.slice(0, -1),
    };

    try {
      const response = await fetch(`/api/export/${format}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = `arquivo.${format}`;
      a.click();

      URL.revokeObjectURL(url);

    } catch (err) {
      errorEl.textContent = err.message;
    }
  });
});
