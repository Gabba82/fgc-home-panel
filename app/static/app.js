const senses = ["santboi-espanya", "espanya-santboi"];
const refreshButton = document.querySelector("#refresh");
const globalError = document.querySelector("#global-error");

const statusLabels = {
  on_time: "En hora",
  delayed: "Retraso",
  cancelled: "Cancelado",
  unknown_realtime: "Sin datos realtime",
  service_alert: "Incidencia"
};

function formatUpdatedAt(value) {
  if (!value) return "Sin actualizaciÃ³n";
  return new Intl.DateTimeFormat("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(new Date(value));
}

function statusText(train) {
  if (train.status === "delayed" && train.delay_minutes) {
    return `+${train.delay_minutes} min`;
  }
  return statusLabels[train.status] || train.status;
}

function safeColor(value, fallback) {
  if (!value) return fallback;
  return value.startsWith("#") ? value : `#${value}`;
}

function renderAlerts(container, alerts) {
  container.innerHTML = "";
  alerts.slice(0, 2).forEach((alert) => {
    const element = document.createElement("div");
    element.className = "alert";
    element.textContent = alert.description ? `${alert.title}: ${alert.description}` : alert.title;
    container.appendChild(element);
  });
}

function trainElement(train) {
  const element = document.createElement("div");
  element.className = "train";

  const badge = document.createElement("div");
  badge.className = "line-badge";
  badge.textContent = train.line || "?";
  badge.style.background = safeColor(train.route_color, "#475569");
  badge.style.color = safeColor(train.route_text_color, "#ffffff");

  const main = document.createElement("div");
  main.className = "train-main";

  const departure = train.estimated_departure || train.scheduled_departure;
  const arrival = train.estimated_arrival || train.scheduled_arrival;
  main.innerHTML = `
    <div class="times">
      <span class="time">${departure?.slice(0, 5) || "--:--"}</span>
      ${arrival ? `<span class="arrival">arriba ${arrival.slice(0, 5)}</span>` : ""}
    </div>
    <p class="train-sub">
      <span>${train.headsign || "Destino no informado"}</span>
      ${train.platform ? `<span class="platform">AndÃ©n ${train.platform}</span>` : ""}
    </p>
    <div class="status ${train.status}">${statusText(train)}</div>
  `;

  element.append(badge, main);
  return element;
}

function busElement(bus) {
  const element = document.createElement("div");
  element.className = "train bus";

  const badge = document.createElement("div");
  badge.className = "line-badge";
  badge.textContent = bus.line || "?";
  badge.style.background = safeColor(bus.route_color, "#ffaa00");
  badge.style.color = safeColor(bus.route_text_color, "#343434");

  const main = document.createElement("div");
  main.className = "train-main";
  const wait = bus.minutes !== null && bus.minutes !== undefined ? `${bus.minutes} min` : bus.wait_text;
  main.innerHTML = `
    <div class="times">
      <span class="time">${wait || "--"}</span>
      ${bus.scheduled_time ? `<span class="arrival">prog. ${bus.scheduled_time}</span>` : ""}
    </div>
    <p class="train-sub">
      <span>${bus.destination || "Destino no informado"}</span>
    </p>
  `;

  element.append(badge, main);
  return element;
}

function renderCard(sense, data) {
  const card = document.querySelector(`[data-sense="${sense}"]`);
  const meta = card.querySelector(".meta");
  const alerts = card.querySelector(".alerts");
  const trains = card.querySelector(".trains");

  meta.textContent = `Actualizado a las ${formatUpdatedAt(data.updated_at)}`;
  renderAlerts(alerts, data.alerts || []);
  trains.innerHTML = "";

  if (!data.trains?.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No se han encontrado prÃ³ximos trenes con la informaciÃ³n disponible.";
    trains.appendChild(empty);
    return;
  }

  data.trains.forEach((train) => trains.appendChild(trainElement(train)));
}

function renderBusStop(data) {
  const card = document.querySelector(`[data-bus-stop="${data.stop_id}"]`);
  const direction = card.querySelector(".direction");
  const meta = card.querySelector(".meta");
  const arrivals = card.querySelector(".bus-arrivals");

  direction.textContent = data.stop_name ? `Parada ${data.stop_id}` : `Parada ${data.stop_id}`;
  meta.textContent = `${data.stop_name || "Bus AMB"} Â· Actualizado a las ${formatUpdatedAt(data.updated_at)}`;
  arrivals.innerHTML = "";

  if (!data.arrivals?.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No se han encontrado prÃ³ximos buses con la informaciÃ³n disponible.";
    arrivals.appendChild(empty);
    return;
  }

  data.arrivals.forEach((bus) => arrivals.appendChild(busElement(bus)));
}

function renderBusError(message) {
  const card = document.querySelector("[data-bus-stop]");
  const meta = card.querySelector(".meta");
  const arrivals = card.querySelector(".bus-arrivals");

  meta.textContent = `No se han podido actualizar los buses Â· ${formatUpdatedAt(new Date().toISOString())}`;
  arrivals.innerHTML = "";

  const empty = document.createElement("div");
  empty.className = "empty";
  empty.textContent = message || "AMB no responde ahora mismo.";
  arrivals.appendChild(empty);
}

async function loadSense(sense) {
  const response = await fetch(`/api/next-trains?sense=${encodeURIComponent(sense)}`, {
    headers: { Accept: "application/json" }
  });
  if (!response.ok) {
    throw new Error(`FGC no responde correctamente (${response.status})`);
  }
  return response.json();
}

async function loadBusStop() {
  const response = await fetch("/api/bus-stop", {
    headers: { Accept: "application/json" }
  });
  if (!response.ok) {
    throw new Error(`AMB no responde correctamente (${response.status})`);
  }
  return response.json();
}

async function refresh() {
  refreshButton.disabled = true;
  globalError.classList.add("hidden");
  const [busStopResult, ...trainResults] = await Promise.allSettled([
    loadBusStop(),
    ...senses.map((sense) => loadSense(sense))
  ]);

  if (busStopResult.status === "fulfilled") {
    renderBusStop(busStopResult.value);
  } else {
    renderBusError(busStopResult.reason?.message);
  }

  const failedTrains = [];
  trainResults.forEach((result) => {
    if (result.status === "fulfilled") {
      renderCard(result.value.sense, result.value);
    } else {
      failedTrains.push(result.reason?.message || "FGC no responde");
    }
  });

  if (failedTrains.length) {
    globalError.textContent = `No se han podido actualizar algunos trenes. ${failedTrains.join(" ")}`;
    globalError.classList.remove("hidden");
  }
  refreshButton.disabled = false;
}

refreshButton.addEventListener("click", refresh);
refresh();
setInterval(refresh, 30000);
