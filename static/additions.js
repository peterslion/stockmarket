const els = {
  lede: document.getElementById("lede"),
  status: document.getElementById("status"),
  peakYear: document.getElementById("peak-year"),
  peakNote: document.getElementById("peak-note"),
  peakCount: document.getElementById("peak-count"),
  total: document.getElementById("total"),
  tableNote: document.getElementById("table-note"),
  rows: document.getElementById("rows"),
  refresh: document.getElementById("refresh"),
};

let chart = null;

function setStatus(message) {
  els.status.hidden = !message;
  els.status.textContent = message || "";
}

function renderChart(yearly, peakYear) {
  const ctx = document.getElementById("bars");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: yearly.map((row) => String(row.year)),
      datasets: [
        {
          data: yearly.map((row) => row.n_added),
          backgroundColor: yearly.map((row) => (row.year === peakYear ? "#1c6b45" : "#6a5f53")),
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          title: { display: true, text: "Current members added" },
          ticks: { precision: 0 },
          grid: { color: "#eadcc4" },
        },
        x: { grid: { display: false } },
      },
    },
  });
}

function render(payload) {
  const peak = payload.peak || {};
  els.peakYear.textContent = peak.year != null ? String(peak.year) : "n/a";
  els.peakCount.textContent = peak.n_added != null ? String(peak.n_added) : "n/a";
  els.total.textContent = String(payload.addition_count);
  els.peakNote.textContent = "Among current S&P 500 members with an add date of 2020 or later.";
  els.lede.textContent = `Highest additions since 2020: ${peak.year} (${peak.n_added} stocks). ${payload.addition_count} current members were added in 2020 or later.`;
  els.tableNote.textContent = `${payload.addition_count} names from the Wikipedia constituents table.`;
  renderChart(payload.yearly || [], peak.year);
  els.rows.innerHTML = (payload.additions || [])
    .map(
      (row) => `<tr>
        <td>${row.ticker}</td>
        <td>${row.name}</td>
        <td>${row.year}</td>
      </tr>`
    )
    .join("");
}

async function load({ refresh = false } = {}) {
  setStatus("");
  els.lede.textContent = "Loading the current S&P 500 constituents table from Wikipedia…";
  try {
    const response = await fetch(`/api/additions?refresh=${refresh ? "true" : "false"}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to load additions");
    render(data);
  } catch (error) {
    setStatus(error.message);
    els.lede.textContent = "The Wikipedia constituents table could not be loaded.";
  }
}

els.refresh.addEventListener("click", () => load({ refresh: true }));
load();
