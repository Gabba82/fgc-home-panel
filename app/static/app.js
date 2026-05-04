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

async function loadSense(sense) {
  const response = await fetch(`/api/next-trains?sense=${encodeURIComponent(sense)}`, {
    headers: { Accept: "application/json" }
  });
  if (!response.ok) {
    throw new Error(`FGC no responde correctamente (${response.status})`);
  }
  return response.json();
}

async function refresh() {
  refreshButton.disabled = true;
  globalError.classList.add("hidden");
  try {
    const results = await Promise.all(senses.map((sense) => loadSense(sense)));
    results.forEach((data) => renderCard(data.sense, data));
  } catch (error) {
    globalError.textContent = `No se han podido actualizar los datos. ${error.message}`;
    globalError.classList.remove("hidden");
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener("click", refresh);
refresh();
setInterval(refresh, 30000);
