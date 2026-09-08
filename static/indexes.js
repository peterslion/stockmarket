const els = {
  lede: document.getElementById("lede"),
  status: document.getElementById("status"),
  leader: document.getElementById("leader"),
  leaderNote: document.getElementById("leader-note"),
  laggard: document.getElementById("laggard"),
  laggardNote: document.getElementById("laggard-note"),
  count: document.getElementById("count"),
  countNote: document.getElementById("count-note"),
  rows: document.getElementById("rows"),
  refresh: document.getElementById("refresh"),
};

let chart = null;

function formatPct(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

function formatNum(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function signedClass(value) {
  if (value === null || value === undefined) return "";
  if (value > 0) return "is-up";
  if (value < 0) return "is-down";
  return "";
}

function setStatus(message) {
  els.status.hidden = !message;
  els.status.textContent = message || "";
}

function renderChart(rows) {
  const available = rows.filter((row) => row.return !== null);
  const ctx = document.getElementById("bars");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: available.map((row) => row.country),
      datasets: [
        {
          data: available.map((row) => row.return * 100),
          backgroundColor: available.map((row) => (row.return >= 0 ? "#1c6b45" : "#9b2c2c")),
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          title: { display: true, text: "YTD return (%)" },
          grid: { color: "#eadcc4" },
        },
        y: { grid: { display: false } },
      },
    },
  });
}

function render(payload) {
  const rows = payload.rows || [];
  els.count.textContent = `${payload.available_count}/${payload.index_count}`;
  els.countNote.textContent = `${payload.start} → ${payload.end}`;
  if (payload.leader) {
    els.leader.textContent = formatPct(payload.leader.return);
    els.leader.className = `metric-value ${signedClass(payload.leader.return)}`;
    els.leaderNote.textContent = `${payload.leader.country} · ${payload.leader.index}`;
  }
  if (payload.laggard) {
    els.laggard.textContent = formatPct(payload.laggard.return);
    els.laggard.className = `metric-value ${signedClass(payload.laggard.return)}`;
    els.laggardNote.textContent = `${payload.laggard.country} · ${payload.laggard.index}`;
  }
  els.lede.textContent = `From ${payload.start} through ${payload.end}, ${payload.leader?.index || "the leader"} is ahead at ${formatPct(payload.leader?.return)} and ${payload.laggard?.index || "the laggard"} is last at ${formatPct(payload.laggard?.return)}.`;

  const sorted = [...rows].sort((a, b) => (b.return ?? -Infinity) - (a.return ?? -Infinity));
  els.rows.innerHTML = sorted
    .map((row) => {
      const cls = signedClass(row.return);
      return `<tr>
        <td>${row.country}</td>
        <td>${row.index}</td>
        <td>${row.ticker}</td>
        <td>${row.start_date || "—"}</td>
        <td>${formatNum(row.start_close)}</td>
        <td>${row.end_date || "—"}</td>
        <td>${formatNum(row.end_close)}</td>
        <td class="${cls}">${formatPct(row.return)}</td>
      </tr>`;
    })
    .join("");
  renderChart(sorted);
}

async function load({ refresh = false } = {}) {
  setStatus("");
  els.lede.textContent = "Loading major equity indexes…";
  try {
    const response = await fetch(`/api/indexes-ytd?refresh=${refresh ? "true" : "false"}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to load index returns");
    render(data);
  } catch (error) {
    setStatus(error.message);
    els.lede.textContent = "Index prices could not be loaded from Yahoo Finance.";
  }
}

els.refresh.addEventListener("click", () => load({ refresh: true }));
load();
