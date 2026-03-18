async function getJson(url) {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`${url} failed with ${resp.status}`);
  }
  return resp.json();
}

function formatUsd(value) {
  if (typeof value !== "number") return "n/a";
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function renderPortfolio(data) {
  const el = document.getElementById("portfolio-content");
  if (!el) return;
  const rows = [
    ["Cash", formatUsd(data.cash)],
    ["Equity", formatUsd(data.equity)],
    ["Total Value", formatUsd(data.total_value)],
    ["Daily Trades", String(data.daily_trades_count ?? 0)],
    ["Exposure", `${((data.total_exposure_pct ?? 0) * 100).toFixed(2)}%`],
  ];
  el.innerHTML = rows
    .map(([label, value]) => `<div class="metric"><span class="dim">${label}</span><strong>${value}</strong></div>`)
    .join("");
}

function renderRuns(data) {
  const el = document.getElementById("runs-content");
  if (!el) return;
  if (!Array.isArray(data) || data.length === 0) {
    el.innerHTML = `<li class="list-row dim">No runs yet.</li>`;
    return;
  }
  el.innerHTML = data
    .slice(0, 8)
    .map((run) => {
      const cost = typeof run.total_cost_usd === "number" ? `$${run.total_cost_usd.toFixed(4)}` : "n/a";
      return `<li class="list-row"><strong>${run.run_id}</strong><br/><span class="dim">${run.status} | ${run.trigger} | ${cost}</span></li>`;
    })
    .join("");
}

function renderStrategies(data) {
  const el = document.getElementById("strategies-content");
  if (!el) return;
  if (!Array.isArray(data) || data.length === 0) {
    el.innerHTML = `<li class="list-row dim">No strategy performance snapshots yet.</li>`;
    return;
  }
  el.innerHTML = data
    .map(
      (row) =>
        `<li class="list-row"><strong>${row.strategy}</strong> <span class="dim">trades=${row.total_trades} win_rate=${(row.win_rate * 100).toFixed(1)}%</span></li>`,
    )
    .join("");
}

async function boot() {
  try {
    const [portfolio, runs, strategies] = await Promise.all([
      getJson("/api/portfolio"),
      getJson("/api/runs"),
      getJson("/api/strategies"),
    ]);
    renderPortfolio(portfolio || {});
    renderRuns(runs || []);
    renderStrategies(strategies || []);
  } catch (error) {
    const el = document.getElementById("portfolio-content");
    if (el) {
      el.innerHTML = `<div class="dim">Dashboard fetch error: ${String(error)}</div>`;
    }
  }
}

boot();
