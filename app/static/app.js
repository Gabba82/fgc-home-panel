const senses = ["santboi-espanya", "espanya-santboi"];
const cardsContainer = document.querySelector(".cards");
const refreshButton = document.querySelector("#refresh");
const globalError = document.querySelector("#global-error");
const panelTitle = document.querySelector("#panel-title");
const panelSubtitle = document.querySelector("#panel-subtitle");

const statusLabels = {
  on_time: "En hora",
  delayed: "Retraso",
  cancelled: "Cancelado",
  unknown_realtime: "Sin datos en tiempo real",
  service_alert: "Incidencia"
};

function formatUpdatedAt(value) {
  if (!value) return "Sin actualización";
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

async function loadPanelConfig() {
  const response = await fetch("/api/panel-config", {
    headers: { Accept: "application/json" }
  });
  if (!response.ok) return;

  const config = await response.json();
  const title = config.title?.trim();
  const subtitle = config.subtitle?.trim();

  if (title) {
    panelTitle.textContent = title;
    document.title = title;
  }

  if (subtitle) {
    panelSubtitle.textContent = subtitle;
    panelSubtitle.classList.remove("hidden");
  } else {
    panelSubtitle.textContent = "";
    panelSubtitle.classList.add("hidden");
  }
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
      ${train.platform ? `<span class="platform">Andén ${train.platform}</span>` : ""}
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
    empty.textContent = "No se han encontrado próximos trenes con la información disponible.";
    trains.appendChild(empty);
    return;
  }

  data.trains.forEach((train) => trains.appendChild(trainElement(train)));
}

function ensureBusCard(stopId) {
  let card = document.querySelector(`[data-bus-stop="${stopId}"]`);
  if (card) return card;

  card = document.createElement("article");
  card.className = "route-card bus-card";
  card.dataset.busStop = stopId;
  card.innerHTML = `
    <div class="card-head">
      <div>
        <p class="direction">Parada ${stopId}</p>
        <h2>Bus AMB</h2>
      </div>
      <div class="pulse" title="Actualización automática cada 30 segundos"></div>
    </div>
    <div class="meta">Carregant...</div>
    <div class="trains bus-arrivals"></div>
  `;
  cardsContainer.appendChild(card);
  return card;
}

function renderBusStop(data) {
  const card = ensureBusCard(data.stop_id);
  const direction = card.querySelector(".direction");
  const meta = card.querySelector(".meta");
  const arrivals = card.querySelector(".bus-arrivals");

  direction.textContent = `Parada ${data.stop_id}`;
  meta.textContent = `${data.stop_name || "Bus AMB"} · Actualizado a las ${formatUpdatedAt(data.updated_at)}`;
  arrivals.innerHTML = "";

  if (!data.arrivals?.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No se han encontrado próximos buses con la información disponible.";
    arrivals.appendChild(empty);
    return;
  }

  data.arrivals.forEach((bus) => arrivals.appendChild(busElement(bus)));
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

async function loadBusStops() {
  const response = await fetch("/api/bus-stops", {
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
  const [busStopsResult, ...trainResults] = await Promise.allSettled([
    loadBusStops(),
    ...senses.map((sense) => loadSense(sense))
  ]);

  if (busStopsResult.status === "fulfilled") {
    busStopsResult.value.forEach((busStop) => renderBusStop(busStop));
  } else {
    globalError.textContent = `No se han podido actualizar los buses. ${busStopsResult.reason?.message || ""}`;
    globalError.classList.remove("hidden");
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

document.addEventListener("keydown", (event) => {
  if (event.key === "r" && !event.ctrlKey && !event.metaKey && !event.altKey && document.activeElement === document.body) {
    refresh();
  }
});

refresh();
loadPanelConfig();
setInterval(refresh, 30000);
