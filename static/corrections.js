const els = {
  lede: document.getElementById("lede"),
  status: document.getElementById("status"),
  median: document.getElementById("median"),
  count: document.getElementById("count"),
  countNote: document.getElementById("count-note"),
  toTrough: document.getElementById("to-trough"),
  toAth: document.getElementById("to-ath"),
  quantiles: document.getElementById("quantiles"),
  quantileNote: document.getElementById("quantile-note"),
  rows: document.getElementById("rows"),
  refresh: document.getElementById("refresh"),
};

function formatPct(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return `${value.toFixed(digits)}%`;
}

function formatDays(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return Math.round(value).toLocaleString();
}

function setStatus(message) {
  els.status.hidden = !message;
  els.status.textContent = message || "";
}

function render(payload) {
  const q = payload.quantiles || {};
  const medianDaysTrough = q["0.5"]?.days_peak_to_trough;
  const medianDaysAth = q["0.5"]?.days_peak_to_new_ath;
  els.median.textContent = formatPct(payload.median_drawdown_pct);
  els.count.textContent = String(payload.correction_count);
  els.countNote.textContent = `${payload.price_start} → ${payload.price_end}`;
  els.toTrough.textContent = formatDays(medianDaysTrough);
  els.toAth.textContent = formatDays(medianDaysAth);
  els.lede.textContent = `From ${payload.price_start} through ${payload.price_end}, the S&P 500 had ${payload.correction_count} corrections of at least 5% between all-time highs. The median peak-to-trough drawdown is ${formatPct(payload.median_drawdown_pct)}.`;
  els.quantileNote.textContent = "25th, 50th, and 75th percentiles across those corrections.";

  const order = ["0.25", "0.5", "0.75"];
  const labels = { "0.25": "25%", "0.5": "50%", "0.75": "75%" };
  els.quantiles.innerHTML = order
    .map((key) => {
      const row = q[key] || {};
      return `<tr>
        <td>${labels[key]}</td>
        <td>${formatPct(row.drawdown_pct)}</td>
        <td>${formatDays(row.days_peak_to_trough)}</td>
        <td>${formatDays(row.days_peak_to_new_ath)}</td>
      </tr>`;
    })
    .join("");

  const rows = [...(payload.corrections || [])].reverse();
  els.rows.innerHTML = rows
    .map(
      (row) => `<tr>
        <td>${row.peak_date}</td>
        <td>${row.trough_date}</td>
        <td>${row.recovery_date}</td>
        <td>${formatPct(row.drawdown_pct)}</td>
        <td>${row.days_peak_to_trough.toLocaleString()}</td>
        <td>${row.days_peak_to_new_ath.toLocaleString()}</td>
      </tr>`
    )
    .join("");
}

async function load({ refresh = false } = {}) {
  setStatus("");
  els.lede.textContent = "Loading daily S&P 500 closes…";
  try {
    const response = await fetch(`/api/corrections?refresh=${refresh ? "true" : "false"}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to load corrections");
    render(data);
  } catch (error) {
    setStatus(error.message);
    els.lede.textContent = "The S&P 500 series could not be loaded from Yahoo Finance.";
  }
}

els.refresh.addEventListener("click", () => load({ refresh: true }));
load();
