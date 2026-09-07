const DEFAULT_TICKER = "AMZN";
const DEFAULT_WINDOW = "5y";

const els = {
  form: document.getElementById("ticker-form"),
  ticker: document.getElementById("ticker"),
  refresh: document.getElementById("refresh"),
  lede: document.getElementById("lede"),
  status: document.getElementById("status"),
  spearman: document.getElementById("spearman"),
  pearson: document.getElementById("pearson"),
  pearsonNote: document.getElementById("pearson-note"),
  beatMiss: document.getElementById("beat-miss"),
  beatMissNote: document.getElementById("beat-miss-note"),
  regimeGap: document.getElementById("regime-gap"),
  regimeNote: document.getElementById("regime-note"),
  scatterCopy: document.getElementById("scatter-copy"),
  tercileLegend: document.getElementById("tercile-legend"),
  bullMeta: document.getElementById("bull-meta"),
  bearMeta: document.getElementById("bear-meta"),
  bullTitle: document.getElementById("bull-title"),
  bearTitle: document.getElementById("bear-title"),
  meta: document.getElementById("meta"),
  rows: document.getElementById("rows"),
  tableTitle: document.getElementById("table-title"),
  tableNote: document.getElementById("table-note"),
};

let payload = null;
let activeWindow = DEFAULT_WINDOW;
let scatterChart = null;
let tercileChart = null;

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

function fillMeta(node, rows) {
  node.innerHTML = rows
    .map(([key, value]) => `<dt>${key}</dt><dd>${value ?? "n/a"}</dd>`)
    .join("");
}

function describeCorrelation(allS) {
  const spearman = allS.spearman_correlation;
  const pearson = allS.pearson_correlation;
  if (spearman === null || spearman === undefined) {
    return "There are not enough reported prints in this window to estimate a correlation.";
  }
  const strength =
    Math.abs(spearman) >= 0.5 ? "a clear rank relationship" : Math.abs(spearman) >= 0.3 ? "a moderate rank relationship" : "only a weak rank relationship";
  return `There is ${strength} between surprise magnitude and the 2-day return (Spearman ${formatNum(spearman)}). Raw Pearson is ${formatNum(pearson)}, pulled down by a few enormous Yahoo surprise percentages when the estimate is near zero; clipping those at the 5th/95th percentiles lifts Pearson to ${formatNum(allS.winsorized_pearson_correlation)}.`;
}

function describeRegimes(regimes) {
  const bullBeats = regimes.bull.beats?.event_count || 0;
  const bearBeats = regimes.bear.beats?.event_count || 0;
  const bullMed = regimes.bull.beats?.median_2day_return;
  const bearMed = regimes.bear.beats?.median_2day_return;
  if (!bearBeats) {
    return "This window has no S&P 500 bear-market prints, so a bull-versus-bear comparison is not possible here. Switch to all history to include 2008 and 2022.";
  }
  if (bearBeats < 8) {
    return `Beats during dated S&P 500 bears had a ${formatPct(bearMed)} median 2-day return versus ${formatPct(bullMed)} in bulls, but that bear sample is only ${bearBeats} print${bearBeats === 1 ? "" : "s"} — too small to treat as a stable regime effect.`;
  }
  const direction = (bearMed ?? 0) > (bullMed ?? 0) ? "larger" : "smaller";
  return `Beats during dated S&P 500 bears had a ${direction} median 2-day return (${formatPct(bearMed)}, n=${bearBeats}) than beats in bulls (${formatPct(bullMed)}, n=${bullBeats}). Spearman is ${formatNum(regimes.bear.spearman_correlation)} in bears versus ${formatNum(regimes.bull.spearman_correlation)} in bulls.`;
}

function renderMeta(windowData) {
  const allS = windowData.all_surprises;
  const regimes = windowData.regimes;
  fillMeta(els.meta, [
    ["Ticker", payload.ticker],
    ["Index for regimes", payload.market_index],
    ["Price history", `${payload.price_start} → ${payload.price_end}`],
    ["Reported prints", String(allS.event_count)],
    ["|Surprise| vs |return| Spearman", formatNum(allS.abs_spearman_correlation)],
    ["Below 200-day MA prints", String(regimes.below_200dma.event_count)],
    ["Below 200-day MA beat median", formatPct(regimes.below_200dma.beats?.median_2day_return)],
    ["Above 200-day MA beat median", formatPct(regimes.above_200dma.beats?.median_2day_return)],
    ["As of", payload.as_of],
  ]);
}

function renderRegimeCard(node, titleNode, label, block) {
  titleNode.textContent = `${label} · n=${block.event_count}`;
  fillMeta(node, [
    ["Spearman", formatNum(block.spearman_correlation)],
    ["Pearson", formatNum(block.pearson_correlation)],
    ["All-print median 2-day", formatPct(block.median_2day_return)],
    [`Beats (n=${block.beats?.event_count ?? 0})`, formatPct(block.beats?.median_2day_return)],
    [`Misses (n=${block.misses?.event_count ?? 0})`, formatPct(block.misses?.median_2day_return)],
  ]);
}

function renderScatter(windowData) {
  const events = windowData.all_events || [];
  const bull = events.filter((event) => event.regime !== "bear");
  const bear = events.filter((event) => event.regime === "bear");
  const toPoints = (rows) =>
    rows.map((event) => ({
      x: event.surprise_pct,
      y: event.two_day_return * 100,
    }));
  const ctx = document.getElementById("scatter");
  if (scatterChart) scatterChart.destroy();
  scatterChart = new Chart(ctx, {
    type: "scatter",
    data: {
      datasets: [
        {
          label: "Bull",
          data: toPoints(bull),
          backgroundColor: "#1c6b45",
          borderColor: "#1c1712",
          pointRadius: 5,
        },
        {
          label: "Bear",
          data: toPoints(bear),
          backgroundColor: "#9b2c2c",
          borderColor: "#1c1712",
          pointRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, labels: { boxWidth: 12 } },
        tooltip: {
          callbacks: {
            label(item) {
              return `${item.dataset.label}: surprise ${item.parsed.x.toFixed(1)}% · 2-day ${item.parsed.y.toFixed(2)}%`;
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

function renderTerciles(windowData) {
  const terciles = windowData.all_surprises.terciles || [];
  const ctx = document.getElementById("terciles");
  if (tercileChart) tercileChart.destroy();
  tercileChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: terciles.map((row) => row.label.replace(" surprise third", "")),
      datasets: [
        {
          data: terciles.map((row) => row.median_2day_return * 100),
          backgroundColor: terciles.map((row) => (row.median_2day_return >= 0 ? "#1c6b45" : "#9b2c2c")),
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          title: { display: true, text: "Median 2-day return (%)" },
          grid: { color: "#eadcc4" },
        },
        x: { grid: { display: false } },
      },
    },
  });
  els.tercileLegend.innerHTML = terciles
    .map(
      (row) =>
        `<li>${row.label}: n=${row.event_count}, median surprise ${row.median_surprise.toFixed(1)}%, median 2-day ${formatPct(row.median_2day_return)}</li>`
    )
    .join("");
}

function renderTable(windowData) {
  const events = windowData.all_events || [];
  els.tableTitle.textContent = `${payload.ticker} reported prints · ${windowData.label.toLowerCase()}`;
  els.tableNote.textContent = events.length
    ? `${events.length} prints with a mapped 2-day return`
    : "No reported surprises in this window.";
  if (!events.length) {
    els.rows.innerHTML = `<tr><td colspan="6">No reported earnings surprises in this lookback.</td></tr>`;
    return;
  }
  els.rows.innerHTML = events
    .map((event) => {
      const cls = signedClass(event.two_day_return);
      const regime = event.regime === "bear" ? "Bear" : event.regime === "bull" ? "Bull" : "—";
      return `<tr>
        <td>${event.earnings_date}</td>
        <td>${regime}</td>
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
  const allS = windowData.all_surprises;
  const regimes = windowData.regimes;

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.classList.toggle("is-active", chip.dataset.window === windowData.key);
  });

  els.spearman.textContent = formatNum(allS.spearman_correlation);
  els.spearman.className = `metric-value ${signedClass(allS.spearman_correlation)}`;
  els.pearson.textContent = `${formatNum(allS.pearson_correlation)} / ${formatNum(allS.winsorized_pearson_correlation)}`;
  els.beatMiss.textContent = `${formatPct(allS.beats?.median_2day_return)} / ${formatPct(allS.misses?.median_2day_return)}`;
  els.beatMissNote.textContent = `${allS.beats?.event_count ?? 0} beats, ${allS.misses?.event_count ?? 0} misses`;
  const bearBeats = regimes.bear.beats?.median_2day_return;
  const bullBeats = regimes.bull.beats?.median_2day_return;
  els.regimeGap.textContent = `${formatPct(bearBeats)} / ${formatPct(bullBeats)}`;
  els.regimeNote.textContent = `Bear beats n=${regimes.bear.beats?.event_count ?? 0}; bull beats n=${regimes.bull.beats?.event_count ?? 0}`;
  els.lede.textContent = `${describeCorrelation(allS)} ${describeRegimes(regimes)}`;
  els.scatterCopy.textContent = `Green points are prints during S&P 500 bulls; rust points are bears. ${windowData.label} includes ${allS.event_count} reported surprises.`;

  renderRegimeCard(els.bullMeta, els.bullTitle, "Bull markets", regimes.bull);
  renderRegimeCard(els.bearMeta, els.bearTitle, "Bear markets", regimes.bear);
  renderMeta(windowData);
  renderScatter(windowData);
  renderTerciles(windowData);
  renderTable(windowData);
}

async function loadAnalysis({ refresh = false } = {}) {
  const ticker = (els.ticker.value || DEFAULT_TICKER).trim().toUpperCase();
  els.ticker.value = ticker;
  setStatus("");
  els.lede.textContent = `Loading ${ticker} earnings dates, daily closes, and S&P 500 regimes…`;
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
