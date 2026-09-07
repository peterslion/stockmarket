const DEFAULT_TICKER = "AMZN";
const DEFAULT_WINDOW = "5y";

const els = {
  form: document.getElementById("ticker-form"),
  ticker: document.getElementById("ticker"),
  refresh: document.getElementById("refresh"),
  lede: document.getElementById("lede"),
  status: document.getElementById("status"),
  median: document.getElementById("median"),
  medianNote: document.getElementById("median-note"),
  pearson: document.getElementById("pearson"),
  count: document.getElementById("count"),
  countNote: document.getElementById("count-note"),
  upShare: document.getElementById("up-share"),
  scatterCopy: document.getElementById("scatter-copy"),
  meta: document.getElementById("meta"),
  rows: document.getElementById("rows"),
  tableTitle: document.getElementById("table-title"),
  tableNote: document.getElementById("table-note"),
};

let payload = null;
let activeWindow = DEFAULT_WINDOW;
let chart = null;

function formatPct(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(digits)}%`;
}

function formatNum(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return value.toFixed(digits);
}

function formatSurprise(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function signedClass(value) {
  if (value === null || value === undefined) return "";
  if (value > 0) return "is-up";
  if (value < 0) return "is-down";
  return "";
}

function currentWindow() {
  return (payload?.windows || []).find((item) => item.key === activeWindow) || payload?.windows?.[0];
}

function setStatus(message) {
  els.status.hidden = !message;
  els.status.textContent = message || "";
}

function renderMeta() {
  const windowData = currentWindow();
  const rows = [
    ["Ticker", payload.ticker],
    ["Price history", `${payload.price_start} → ${payload.price_end}`],
    ["Sessions", String(payload.price_sessions)],
    ["Reported prints", String(payload.reported_earnings)],
    ["Baseline median 2-day", formatPct(payload.baseline_median_2day_return)],
    ["Spearman corr", formatNum(windowData?.spearman_correlation)],
    ["Mean 2-day return", formatPct(windowData?.mean_2day_return)],
    ["As of", payload.as_of],
  ];
  els.meta.innerHTML = rows
    .map(([key, value]) => `<dt>${key}</dt><dd>${value ?? "n/a"}</dd>`)
    .join("");
}

function renderScatter(windowData) {
  const points = (windowData.events || []).map((event) => ({
    x: event.surprise_pct,
    y: event.two_day_return * 100,
  }));
  const ctx = document.getElementById("scatter");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "scatter",
    data: {
      datasets: [
        {
          data: points,
          backgroundColor: "#1c6b45",
          borderColor: "#1c1712",
          pointRadius: 5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label(item) {
              return `Surprise ${item.parsed.x.toFixed(1)}% · 2-day ${item.parsed.y.toFixed(2)}%`;
            },
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "Earnings surprise (%)" },
          grid: { color: "#eadcc4" },
        },
        y: {
          title: { display: true, text: "2-day return (%)" },
          grid: { color: "#eadcc4" },
        },
      },
    },
  });
}

function renderTable(windowData) {
  const events = windowData.events || [];
  els.tableTitle.textContent = `${payload.ticker} positive surprises · ${windowData.label.toLowerCase()}`;
  els.tableNote.textContent = events.length
    ? `${events.length} prints with a mapped 2-day return`
    : "No positive surprises in this window.";
  if (!events.length) {
    els.rows.innerHTML = `<tr><td colspan="5">No positive earnings surprises in this lookback.</td></tr>`;
    return;
  }
  els.rows.innerHTML = events
    .map((event) => {
      const cls = signedClass(event.two_day_return);
      return `<tr>
        <td>${event.earnings_date}</td>
        <td>${event.eps_estimate == null ? "—" : event.eps_estimate.toFixed(2)}</td>
        <td>${event.reported_eps == null ? "—" : event.reported_eps.toFixed(2)}</td>
        <td>${formatSurprise(event.surprise_pct)}</td>
        <td class="${cls}">${formatPct(event.two_day_return)}</td>
      </tr>`;
    })
    .join("");
}

function render() {
  const windowData = currentWindow();
  if (!payload || !windowData) return;

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.classList.toggle("is-active", chip.dataset.window === windowData.key);
  });

  els.median.textContent = formatPct(windowData.median_2day_return);
  els.median.className = `metric-value ${signedClass(windowData.median_2day_return)}`;
  els.pearson.textContent = formatNum(windowData.pearson_correlation);
  els.count.textContent = String(windowData.event_count);
  els.upShare.textContent = formatPct(windowData.positive_return_share, 0);
  els.lede.textContent = `${payload.ticker} beat estimates on ${windowData.event_count} reported prints in ${windowData.label.toLowerCase()}. The median 2-day move after those beats is ${formatPct(windowData.median_2day_return)}, versus a ${formatPct(payload.baseline_median_2day_return)} median 2-day move across every session in the price history.`;
  els.scatterCopy.textContent = `Pearson correlation between surprise size and the 2-day return is ${formatNum(windowData.pearson_correlation)}. Spearman rank correlation is ${formatNum(windowData.spearman_correlation)}.`;
  renderMeta();
  renderScatter(windowData);
  renderTable(windowData);
}

async function loadAnalysis({ refresh = false } = {}) {
  const ticker = (els.ticker.value || DEFAULT_TICKER).trim().toUpperCase();
  els.ticker.value = ticker;
  setStatus("");
  els.lede.textContent = `Loading ${ticker} earnings dates and daily closes from Yahoo Finance…`;
  try {
    const response = await fetch(`/api/analysis?ticker=${encodeURIComponent(ticker)}&refresh=${refresh ? "true" : "false"}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Failed to load analysis");
    }
    payload = data;
    render();
  } catch (error) {
    setStatus(error.message);
    els.lede.textContent = "The analysis could not be loaded. Yahoo Finance may be rate-limiting requests.";
  }
}

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  loadAnalysis();
});

els.refresh.addEventListener("click", () => loadAnalysis({ refresh: true }));

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    activeWindow = chip.dataset.window;
    render();
  });
});

loadAnalysis();
