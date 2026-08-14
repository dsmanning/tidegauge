const state = {
  hours: 24,
  unit: "",
  timer: null,
  updatedTimer: null,
  american: localStorage.getItem("tidegauge-units") === "american",
  status: null,
  readings: []
};
const $ = (selector) => document.querySelector(selector);
const feet = (meters) => meters * 3.28084;
const fahrenheit = (celsius) => celsius * 9 / 5 + 32;
const batteryPercentage = (volts) => Math.min(100, Math.max(0, (volts - 3) / 1.2 * 100));

function relativeTime(timestamp) {
  const seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (seconds < 10) return "Updated just now";
  if (seconds < 60) return `Updated ${seconds} seconds ago`;
  if (seconds < 3600) return `Updated ${Math.floor(seconds / 60)} minutes ago`;
  return `Updated ${new Date(timestamp).toLocaleString()}`;
}

function refreshUpdatedLabel() {
  if (state.status?.latest?.recordedAt) {
    $("#updated").textContent = relativeTime(state.status.latest.recordedAt);
  }
}

function renderStatus(data) {
  state.status = data;
  state.unit = data.unit;
  $("#unit").textContent = data.unit;
  $("#location").textContent = data.location;
  $("#footer-location").textContent = data.location;
  const status = $("#status");
  status.className = `status ${data.mqtt.connected ? "live" : data.mqtt.error ? "error" : ""}`;
  status.querySelector("strong").textContent = data.mqtt.connected ? "Live" : data.mqtt.error ? "Connection issue" : "Reconnecting";
  if (data.latest) {
    const height = state.american ? data.latest.heightFeet : data.latest.height;
    const secondaryHeight = state.american ? data.latest.height : data.latest.heightFeet;
    $("#height").textContent = Number(height).toFixed(2);
    $("#unit").textContent = state.american ? "ft" : data.unit;
    $("#height-secondary").textContent = `${Number(secondaryHeight).toFixed(2)} ${state.american ? data.unit : "ft"}`;
    refreshUpdatedLabel();
    if (data.latest.temperature != null) {
      const temperature = state.american ? data.latest.temperatureFahrenheit : data.latest.temperature;
      const secondaryTemperature = state.american ? data.latest.temperature : data.latest.temperatureFahrenheit;
      $("#temperature").textContent = Number(temperature).toFixed(1);
      $("#temperature-secondary").textContent = `${Number(secondaryTemperature).toFixed(1)} °${state.american ? "C" : "F"}`;
      $(".temperature-value small").textContent = `°${state.american ? "F" : "C"}`;
    }
    if (data.latest.batteryPercent != null) {
      $("#battery-fill").style.setProperty("--charge", `${data.latest.batteryPercent}%`);
      $("#battery-label").textContent = `${data.latest.batteryPercent}%`;
      $("#battery").setAttribute("aria-label", `Battery ${data.latest.batteryPercent}%`);
    }
  }
  renderTideState(data.tideState);
}

function renderTideState(tideState) {
  const panel = $("#tide-state");
  const flow = tideState?.flow;
  const next = tideState?.nextTide;
  panel.className = `tide-state ${flow || "slack"}`;
  if (!next) {
    $("#tide-icon-path").setAttribute("transform", "rotate(12 14 20)");
    $("#tide-flow").textContent = "Awaiting prediction";
    $("#next-tide").textContent = "Next tide unavailable";
    return;
  }
  const minutesUntil = Math.round((next.nextTime - Date.now()) / 60_000);
  const atTide = minutesUntil <= 0;
  const minutes = Math.max(0, minutesUntil);
  const duration = minutes < 1 ? "now" : `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, "0")}`;
  const displayFlow = atTide ? "slack" : flow;
  const icon = $("#tide-icon-path");
  if (atTide) {
    icon.setAttribute("d", "M3 20h22");
    icon.removeAttribute("transform");
    panel.className = "tide-state slack";
    const tideName = `${next.nextTide[0].toUpperCase()}${next.nextTide.slice(1)}`;
    $("#tide-flow").textContent = `${tideName} water`;
    $("#next-tide").textContent = `${tideName} now`;
    return;
  }
  const angle = { slack: 12, slow: 32, rapid: 55 }[atTide ? "slack" : tideState.rate] ?? 12;
  icon.setAttribute("d", "M3 20h22m-7-7 7 7-7 7");
  icon.setAttribute("transform", `rotate(${displayFlow === "flooding" ? -angle : angle} 14 20)`);
  panel.className = `tide-state ${displayFlow}`;
  const tideName = `${next.nextTide[0].toUpperCase()}${next.nextTide.slice(1)}`;
  $("#tide-flow").textContent = atTide ? `${tideName} water` : flow === "flooding" ? "Flooding" : flow === "ebbing" ? "Ebbing" : "Slack water";
  $("#next-tide").textContent = atTide ? `${tideName} now` : `${tideName} in ${duration}`;
}

function renderChart(readings) {
  state.readings = readings;
  const svg = $("#chart");
  svg.replaceChildren();
  const tooltip = $("#chart-tooltip");
  tooltip.hidden = true;
  svg.onpointermove = null;
  svg.onpointerleave = null;
  $("#empty").classList.toggle("hidden", readings.length > 1);
  if (readings.length < 2) return;

  const compactChart = window.matchMedia("(max-width: 700px)").matches;
  const width = compactChart ? 440 : 900, height = compactChart ? 300 : 330;
  const margin = compactChart ? { top: 14, right: 44, bottom: 34, left: 44 } : { top: 15, right: 52, bottom: 35, left: 52 };
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const values = readings.map((r) => state.american ? r.heightFeet ?? feet(r.height) : r.height);
  const halfHeightSmoothingWindowMs = 7.5 * 60_000;
  let heightWindowStart = 0, heightWindowEnd = 0, heightWindowTotal = 0;
  const heightSeries = readings.map((reading) => {
    while (readings[heightWindowStart].recordedAt < reading.recordedAt - halfHeightSmoothingWindowMs) {
      heightWindowTotal -= state.american ? readings[heightWindowStart].heightFeet ?? feet(readings[heightWindowStart].height) : readings[heightWindowStart].height;
      heightWindowStart++;
    }
    while (heightWindowEnd < readings.length && readings[heightWindowEnd].recordedAt <= reading.recordedAt + halfHeightSmoothingWindowMs) {
      heightWindowTotal += state.american ? readings[heightWindowEnd].heightFeet ?? feet(readings[heightWindowEnd].height) : readings[heightWindowEnd].height;
      heightWindowEnd++;
    }
    return { ...reading, chartHeight: heightWindowTotal / (heightWindowEnd - heightWindowStart) };
  });
  const minX = readings[0].recordedAt, maxX = readings.at(-1).recordedAt;
  let minY = Math.min(...values), maxY = Math.max(...values);
  const padding = Math.max((maxY - minY) * .15, .1); minY -= padding; maxY += padding;
  const rawTemperatureReadings = readings.filter((r) => r.temperature != null);
  const halfSmoothingWindowMs = 90 * 60_000;
  let windowStart = 0, windowEnd = 0, windowTotal = 0;
  const temperatureSeries = rawTemperatureReadings.map((reading) => {
    while (rawTemperatureReadings[windowStart].recordedAt < reading.recordedAt - halfSmoothingWindowMs) {
      windowTotal -= rawTemperatureReadings[windowStart++].temperature;
    }
    while (windowEnd < rawTemperatureReadings.length && rawTemperatureReadings[windowEnd].recordedAt <= reading.recordedAt + halfSmoothingWindowMs) {
      windowTotal += rawTemperatureReadings[windowEnd++].temperature;
    }
    return { ...reading, chartTemperature: windowTotal / (windowEnd - windowStart) };
  });
  const chartTemperatureByTime = new Map(temperatureSeries.map((reading) => [reading.recordedAt, reading.chartTemperature]));
  const temperatures = temperatureSeries.map((reading) => state.american ? fahrenheit(reading.chartTemperature) : reading.chartTemperature);
  let minT = temperatures.length ? Math.min(...temperatures) : 0, maxT = temperatures.length ? Math.max(...temperatures) : 1;
  const tempPadding = Math.max((maxT - minT) * .15, .5); minT -= tempPadding; maxT += tempPadding;
  const niceScale = (minimum, maximum, intervals = 5) => {
    const rawStep = (maximum - minimum) / intervals;
    const magnitude = 10 ** Math.floor(Math.log10(rawStep));
    const fraction = rawStep / magnitude;
    const niceFraction = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10;
    const step = niceFraction * magnitude;
    return { min: Math.floor(minimum / step) * step, max: Math.ceil(maximum / step) * step, step };
  };
  let heightStep, temperatureStep;
  ({ min: minY, max: maxY, step: heightStep } = niceScale(minY, maxY));
  ({ min: minT, max: maxT, step: temperatureStep } = niceScale(minT, maxT));
  const x = (v) => margin.left + ((v - minX) / Math.max(maxX - minX, 1)) * (width - margin.left - margin.right);
  const y = (v) => margin.top + ((maxY - v) / (maxY - minY)) * (height - margin.top - margin.bottom);
  const temperatureY = (v) => margin.top + ((maxT - v) / (maxT - minT)) * (height - margin.top - margin.bottom);
  const ns = "http://www.w3.org/2000/svg";
  const add = (name, attrs, text) => { const el = document.createElementNS(ns, name); Object.entries(attrs).forEach(([k,v]) => el.setAttribute(k,v)); if (text) el.textContent = text; svg.append(el); return el; };

  const defs = add("defs", {}); const gradient = document.createElementNS(ns, "linearGradient"); gradient.id = "area-gradient"; gradient.setAttribute("x1", "0"); gradient.setAttribute("y1", "0"); gradient.setAttribute("x2", "0"); gradient.setAttribute("y2", "1");
  [["0%", ".28"], ["100%", "0"]].forEach(([offset, opacity]) => { const stop = document.createElementNS(ns, "stop"); stop.setAttribute("offset", offset); stop.setAttribute("stop-color", "#5de1c2"); stop.setAttribute("stop-opacity", opacity); gradient.append(stop); }); defs.append(gradient);
  const tickValues = (minimum, maximum, step) => Array.from({ length: Math.round((maximum - minimum) / step) + 1 }, (_, index) => minimum + index * step);
  const tickLabel = (value, step) => value.toFixed(step < 1 ? Math.max(1, Math.ceil(-Math.log10(step))) : 0);
  tickValues(minY, maxY, heightStep).forEach((value) => {
    const py = y(value);
    add("line", { x1: margin.left, y1: py, x2: width - margin.right, y2: py, class: "grid" });
    add("text", { x: margin.left - 10, y: py + 4, "text-anchor": "end", class: "axis-text" }, `${tickLabel(value, heightStep)} ${state.american ? "ft" : "m"}`);
  });
  if (temperatures.length) tickValues(minT, maxT, temperatureStep).forEach((value) => {
    add("text", { x: width - margin.right + 10, y: temperatureY(value) + 4, "text-anchor": "start", class: "axis-text" }, `${tickLabel(value, temperatureStep)}°${state.american ? "F" : "C"}`);
  });
  const chartTicks = () => {
    const ticks = [];
    const cursor = new Date(minX);
    if (state.hours <= 24) {
      const interval = state.hours === 6 ? 1 : 6;
      cursor.setMinutes(0, 0, 0);
      cursor.setHours(Math.ceil(cursor.getHours() / interval) * interval);
      while (cursor.getTime() <= maxX) {
        ticks.push(cursor.getTime());
        cursor.setHours(cursor.getHours() + interval);
      }
    } else {
      const interval = state.hours === 168 ? 1 : 5;
      cursor.setHours(0, 0, 0, 0);
      if (cursor.getTime() < minX) cursor.setDate(cursor.getDate() + 1);
      while (cursor.getTime() <= maxX) {
        ticks.push(cursor.getTime());
        cursor.setDate(cursor.getDate() + interval);
      }
    }
    return ticks;
  };
  const formatChartTime = (time) => state.hours > 24
    ? new Date(time).toLocaleDateString([], { month: "short", day: "numeric" })
    : new Date(time).toLocaleTimeString([], { hour: state.american ? "numeric" : "2-digit", minute: "2-digit", hour12: state.american });
  chartTicks().filter((time) => {
    const tickX = x(time);
    return tickX >= margin.left + 20 && tickX <= width - margin.right - 20;
  }).forEach((time) => {
    const tickX = x(time);
    add("line", { x1: tickX, y1: margin.top, x2: tickX, y2: height - margin.bottom, class: "vertical-grid" });
    add("text", { x: tickX, y: height - 7, "text-anchor": "middle", class: "axis-text" }, formatChartTime(time));
  });
  const points = heightSeries.map((reading) => `${x(reading.recordedAt).toFixed(1)},${y(reading.chartHeight).toFixed(1)}`).join(" ");
  add("path", { d: `M${points.split(" ").join(" L")} L${x(maxX)},${height-margin.bottom} L${x(minX)},${height-margin.bottom} Z`, class: "area" });
  add("polyline", { points, class: "plot" });
  const temperaturePoints = temperatureSeries.map((reading) => `${x(reading.recordedAt).toFixed(1)},${temperatureY(state.american ? fahrenheit(reading.chartTemperature) : reading.chartTemperature).toFixed(1)}`).join(" ");
  if (temperatures.length > 1) add("polyline", { points: temperaturePoints, class: "temperature-plot" });

  const crosshair = add("line", { class: "crosshair", visibility: "hidden" });
  const heightMarker = add("circle", { class: "hover-height", r: 4.5, visibility: "hidden" });
  const temperatureMarker = add("circle", { class: "hover-temperature", r: 4, visibility: "hidden" });
  const hideHover = () => {
    tooltip.hidden = true;
    [crosshair, heightMarker, temperatureMarker].forEach((element) => element.setAttribute("visibility", "hidden"));
  };
  svg.onpointerleave = hideHover;
  svg.onpointermove = (event) => {
    const rect = svg.getBoundingClientRect();
    const pointerX = (event.clientX - rect.left) / rect.width * width;
    const targetTime = minX + (Math.min(width - margin.right, Math.max(margin.left, pointerX)) - margin.left) / (width - margin.left - margin.right) * (maxX - minX);
    let low = 0, high = readings.length - 1;
    while (low < high) {
      const middle = Math.floor((low + high) / 2);
      if (readings[middle].recordedAt < targetTime) low = middle + 1;
      else high = middle;
    }
    const index = low > 0 && Math.abs(readings[low - 1].recordedAt - targetTime) < Math.abs(readings[low].recordedAt - targetTime) ? low - 1 : low;
    const reading = readings[index];
    const plottedHeight = state.american ? reading.heightFeet ?? feet(reading.height) : reading.height;
    const chartTemperature = chartTemperatureByTime.get(reading.recordedAt);
    const plottedTemperature = chartTemperature == null ? null : state.american ? fahrenheit(chartTemperature) : chartTemperature;
    const chartX = x(reading.recordedAt);
    crosshair.setAttribute("x1", chartX); crosshair.setAttribute("x2", chartX); crosshair.setAttribute("y1", margin.top); crosshair.setAttribute("y2", height - margin.bottom); crosshair.setAttribute("visibility", "visible");
    heightMarker.setAttribute("cx", chartX); heightMarker.setAttribute("cy", y(plottedHeight)); heightMarker.setAttribute("visibility", "visible");
    temperatureMarker.setAttribute("cx", chartX); temperatureMarker.setAttribute("cy", plottedTemperature == null ? 0 : temperatureY(plottedTemperature)); temperatureMarker.setAttribute("visibility", plottedTemperature == null ? "hidden" : "visible");
    $("#tooltip-time").textContent = new Date(reading.recordedAt).toLocaleString([], { month: "short", day: "numeric", hour: state.american ? "numeric" : "2-digit", minute: "2-digit", hour12: state.american });
    $("#tooltip-height").textContent = `Tide: ${plottedHeight.toFixed(2)} ${state.american ? "ft" : "m"}`;
    $("#tooltip-temperature").textContent = plottedTemperature == null ? "Water: —" : `Water: ${plottedTemperature.toFixed(1)} °${state.american ? "F" : "C"}`;
    tooltip.hidden = false;
    const tooltipX = Math.min(Math.max(event.clientX - rect.left + 14, 8), rect.width - tooltip.offsetWidth - 8);
    tooltip.style.left = `${tooltipX}px`;
    tooltip.style.top = "8px";
  };
}

async function refresh() {
  try {
    const [statusResponse, historyResponse] = await Promise.all([fetch("/api/status"), fetch(`/api/history?hours=${state.hours}`)]);
    if (!statusResponse.ok || !historyResponse.ok) throw new Error("API unavailable");
    const [status, history] = await Promise.all([statusResponse.json(), historyResponse.json()]);
    renderStatus(status); renderChart(history.readings);
  } catch {
    $("#status").className = "status error"; $("#status strong").textContent = "Server unavailable";
  }
}

document.querySelectorAll("[data-hours]").forEach((button) => button.addEventListener("click", () => {
  document.querySelectorAll("[data-hours]").forEach((item) => item.classList.remove("active"));
  button.classList.add("active"); state.hours = Number(button.dataset.hours); refresh();
}));
const batteryDialog = $("#battery-dialog");
$("#battery").addEventListener("click", async () => {
  batteryDialog.showModal();
  try {
    const response = await fetch("/api/history?hours=72");
    if (!response.ok) throw new Error("Battery history unavailable");
    const history = await response.json();
    renderBatteryChart(history.readings);
  } catch {
    renderBatteryChart([]);
  }
});

function renderBatteryChart(readings) {
  const svg = $("#battery-chart");
  const empty = $("#battery-empty");
  svg.replaceChildren();
  const data = readings.filter((reading) => reading.batteryVoltage != null).map((reading) => ({
    ...reading, percent: reading.batteryPercent ?? batteryPercentage(reading.batteryVoltage)
  }));
  empty.classList.toggle("hidden", data.length > 1);
  if (data.length < 2) return;
  const width = 650, height = 250, margin = { top: 12, right: 16, bottom: 32, left: 46 };
  const minTime = data[0].recordedAt, maxTime = data.at(-1).recordedAt;
  const x = (value) => margin.left + (value - minTime) / Math.max(maxTime - minTime, 1) * (width - margin.left - margin.right);
  const y = (value) => margin.top + (100 - value) / 100 * (height - margin.top - margin.bottom);
  const ns = "http://www.w3.org/2000/svg";
  const add = (name, attrs, text) => { const element = document.createElementNS(ns, name); Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value)); if (text) element.textContent = text; svg.append(element); return element; };
  for (let value = 0; value <= 100; value += 25) { const py = y(value); add("line", { x1: margin.left, y1: py, x2: width - margin.right, y2: py, class: "grid" }); add("text", { x: margin.left - 8, y: py + 4, "text-anchor": "end", class: "axis-text" }, `${value}%`); }
  for (let index = 0; index <= 3; index++) { const time = minTime + (maxTime - minTime) * index / 3; add("text", { x: x(time), y: height - 7, "text-anchor": index === 0 ? "start" : index === 3 ? "end" : "middle", class: "axis-text" }, new Date(time).toLocaleString([], { month: "short", day: "numeric", hour: "numeric" })); }
  const points = data.map((reading) => `${x(reading.recordedAt).toFixed(1)},${y(reading.percent).toFixed(1)}`).join(" ");
  add("polyline", { points, class: "plot" });
}
const unitToggle = $("#unit-toggle");
unitToggle.checked = state.american;
unitToggle.addEventListener("change", () => {
  state.american = unitToggle.checked;
  localStorage.setItem("tidegauge-units", state.american ? "american" : "metric");
  if (state.status) renderStatus(state.status);
  renderChart(state.readings);
});
refresh();
state.timer = setInterval(refresh, 30_000);
state.updatedTimer = setInterval(refreshUpdatedLabel, 1_000);
