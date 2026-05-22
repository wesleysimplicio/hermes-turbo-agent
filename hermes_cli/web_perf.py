"""Performance dashboard endpoints for ``hermes dashboard`` (issue #137).

Adds three JSON endpoints and one HTML page that turn the existing CLI
telemetry into an interactive web view:

    GET /api/perf/stage_summary?group_by=stage  →  per-stage percentile rows
    GET /api/perf/token_savings?since=7d        →  weekly token savings report
    GET /api/perf/turbo_score                   →  Turbo Score payload
    GET /perf                                   →  static HTML view that polls the JSON

The module is intentionally framework-agnostic: it exposes the route handlers
as plain async functions and a ``register(app)`` helper that wires them into a
FastAPI app. This keeps the handlers unit-testable without spinning up
uvicorn.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional


def _json_response(payload: Any, status: int = 200):
    """Return a Starlette/FastAPI JSONResponse if available, else dict.

    The fallback dict path is used by tests that bypass FastAPI entirely.
    """
    try:
        from fastapi.responses import JSONResponse
        return JSONResponse(content=payload, status_code=status)
    except Exception:
        return payload


def _html_response(body: str):
    try:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=body)
    except Exception:
        return body


# ---------------------------------------------------------------------------
# Handlers — return plain dicts that ``register(app)`` will wrap in JSONResponse.
# ---------------------------------------------------------------------------

VALID_GROUPS = ("stage", "provider", "model", "tool")


def stage_summary(group_by: str = "stage") -> dict[str, Any]:
    if group_by not in VALID_GROUPS:
        return {"error": f"group_by must be one of {VALID_GROUPS}",
                "rows": [], "events": 0}
    try:
        from agent.telemetry.dashboard import summarize
        from agent.telemetry.stage_timer import get_log_path
    except Exception as exc:
        return {"error": f"stage_timer unavailable: {exc}",
                "rows": [], "events": 0}
    log_path = get_log_path()
    if not log_path.exists():
        return {"error": None, "rows": [], "events": 0, "log_path": str(log_path)}
    rows = summarize(log_path, group_by=group_by)
    return {
        "rows": rows,
        "events": sum(r["count"] for r in rows),
        "group_by": group_by,
        "log_path": str(log_path),
    }


def token_savings(since: str = "7d", prices_json: Optional[str] = None) -> dict[str, Any]:
    try:
        from agent.telemetry.savings_report import build_report, parse_since
        from agent.telemetry.token_savings import default_log_path, iter_records
    except Exception as exc:
        return {"error": f"savings_report unavailable: {exc}"}
    try:
        window = parse_since(since)
    except ValueError as exc:
        return {"error": str(exc)}
    prices: dict[str, float] = {}
    if prices_json:
        try:
            prices = json.loads(prices_json)
        except json.JSONDecodeError:
            prices = {}
    log = default_log_path()
    records = list(iter_records(log))
    return build_report(records, since=window, prices=prices)


def turbo_score() -> dict[str, Any]:
    try:
        scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        import turbo_score as _ts  # type: ignore
    except Exception as exc:
        return {"error": f"turbo_score unavailable: {exc}"}
    report = _ts._load_report(_ts.DEFAULT_REPORT)
    baselines = _ts._load_baselines(_ts.DEFAULT_BASELINES)
    savings = _ts._load_token_savings_pct()
    try:
        result = _ts.compute(report, baselines, savings)
        return _ts.to_payload(result)
    except Exception as exc:
        return {"error": f"turbo_score compute failed: {exc}"}


# ---------------------------------------------------------------------------
# Static HTML view — uses fetch() against the JSON endpoints above. Keeps
# us free of any frontend build step (per issue #137 "lightweight").
# ---------------------------------------------------------------------------

_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Hermes Turbo — Performance Dashboard</title>
<style>
  :root { color-scheme: dark; }
  body { font: 14px/1.45 -apple-system, system-ui, "Segoe UI", Roboto, sans-serif;
         background:#0b1220; color:#e2e8f0; margin:0; padding:24px; }
  h1 { margin-top:0; font-size:24px; color:#19D27F; }
  h2 { font-size:18px; color:#9ed8ff; margin:24px 0 8px; }
  .grid { display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); }
  .card { background:#071522; border:1px solid #1c3450; border-radius:12px;
          padding:16px 18px; }
  .score { font-size:36px; font-weight:900; color:#FFE15A; }
  .pill { display:inline-block; font-size:11px; padding:2px 8px; border-radius:999px;
          background:#19D27F22; color:#19D27F; margin-left:8px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th, td { padding:6px 8px; border-bottom:1px solid #1c3450; text-align:left; }
  th { color:#9ed8ff; font-weight:700; }
  td.num { text-align:right; font-variant-numeric:tabular-nums; }
  .muted { color:#7f93ad; }
  .row { display:flex; gap:8px; flex-wrap:wrap; align-items:baseline; }
  button, select { background:#0e1e33; border:1px solid #25406a; color:#e2e8f0;
                   padding:6px 10px; border-radius:6px; font:inherit; cursor:pointer; }
  button:hover { background:#1a3050; }
  code { background:#0e1e33; padding:1px 6px; border-radius:4px; font-size:12px; }
  .err { color:#FF5D6C; }
</style>
</head>
<body>
  <h1>Hermes Turbo — Performance Dashboard
    <span class="pill" id="freshness">loading…</span></h1>
  <div class="muted">Per-stage runtime telemetry, token-savings, and Turbo Score —
    all rendered from your local <code>~/.hermes/telemetry/*.jsonl</code>.</div>

  <div class="grid">
    <div class="card">
      <h2>Turbo Score</h2>
      <div class="score" id="score">—</div>
      <table><tbody id="families"></tbody></table>
    </div>

    <div class="card">
      <h2>Token Savings
        <select id="since">
          <option value="24h">24h</option>
          <option value="7d" selected>7d</option>
          <option value="30d">30d</option>
        </select>
      </h2>
      <div id="totals" class="muted">—</div>
      <h2 style="font-size:14px">By adapter</h2>
      <table><thead><tr><th>Adapter</th><th class="num">Saved</th>
                        <th class="num">USD</th></tr></thead>
        <tbody id="by-adapter"></tbody></table>
    </div>

    <div class="card">
      <h2>Stage timings
        <select id="group-by">
          <option value="stage" selected>stage</option>
          <option value="provider">provider</option>
          <option value="model">model</option>
          <option value="tool">tool</option>
        </select>
      </h2>
      <table>
        <thead><tr><th id="key-header">stage</th><th class="num">count</th>
                   <th class="num">p50 (ms)</th><th class="num">p95 (ms)</th>
                   <th class="num">p99 (ms)</th></tr></thead>
        <tbody id="stages"></tbody>
      </table>
    </div>
  </div>

  <div class="row" style="margin-top:24px">
    <button onclick="refresh()">↻ Refresh</button>
    <span class="muted">Polls auto-refresh every 15s.</span>
  </div>

<script>
const sessionToken = window.HERMES_SESSION_TOKEN || "";
const headers = sessionToken ? { "X-Hermes-Session-Token": sessionToken } : {};

async function getJson(path) {
  const r = await fetch(path, { headers });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

function fmt(n, d=2) {
  if (n === null || n === undefined) return "—";
  return Number(n).toFixed(d);
}

async function loadScore() {
  try {
    const data = await getJson("/api/perf/turbo_score");
    if (data.error) {
      document.getElementById("score").textContent = "n/a";
      document.getElementById("families").innerHTML =
        `<tr><td colspan="4" class="err">${data.error}</td></tr>`;
      return;
    }
    document.getElementById("score").textContent = fmt(data.score, 1) + " / 100";
    document.getElementById("families").innerHTML = (data.families || []).map(f =>
      `<tr><td>${f.name}</td><td class="num">${f.weight}</td>
            <td class="num">${fmt(f.raw_score, 2)}</td>
            <td class="num">${fmt(f.weighted, 2)}</td></tr>`).join("");
  } catch (e) {
    document.getElementById("score").textContent = "error";
  }
}

async function loadSavings() {
  const since = document.getElementById("since").value;
  try {
    const data = await getJson(`/api/perf/token_savings?since=${encodeURIComponent(since)}`);
    if (data.error) {
      document.getElementById("totals").innerHTML =
        `<span class="err">${data.error}</span>`;
      return;
    }
    const t = data.totals || {};
    document.getElementById("totals").innerHTML =
      `Saved <b>${(t.saved_tokens ?? 0).toLocaleString()}</b> tokens · ` +
      `<b>${fmt(t.overall_savings_pct, 1)}%</b> · ` +
      `<b>$${fmt(t.estimated_usd_saved, 4)}</b>`;
    const adapters = Object.entries(data.by_adapter || {})
      .sort((a, b) => (b[1].saved||0) - (a[1].saved||0));
    document.getElementById("by-adapter").innerHTML = adapters.map(([k, v]) =>
      `<tr><td>${k}</td><td class="num">${(v.saved||0).toLocaleString()}</td>
            <td class="num">$${fmt(v.usd, 4)}</td></tr>`).join("") ||
      `<tr><td colspan="3" class="muted">no records yet</td></tr>`;
  } catch (e) {
    document.getElementById("totals").innerHTML = `<span class="err">${e}</span>`;
  }
}

async function loadStages() {
  const groupBy = document.getElementById("group-by").value;
  document.getElementById("key-header").textContent = groupBy;
  try {
    const data = await getJson(`/api/perf/stage_summary?group_by=${encodeURIComponent(groupBy)}`);
    if (data.error) {
      document.getElementById("stages").innerHTML =
        `<tr><td colspan="5" class="err">${data.error}</td></tr>`;
      return;
    }
    document.getElementById("stages").innerHTML = (data.rows || []).map(r =>
      `<tr><td>${r.key}</td><td class="num">${r.count}</td>
            <td class="num">${fmt(r.p50_ms)}</td>
            <td class="num">${fmt(r.p95_ms)}</td>
            <td class="num">${fmt(r.p99_ms)}</td></tr>`).join("") ||
      `<tr><td colspan="5" class="muted">no stage events yet</td></tr>`;
  } catch (e) {
    document.getElementById("stages").innerHTML =
      `<tr><td colspan="5" class="err">${e}</td></tr>`;
  }
}

async function refresh() {
  document.getElementById("freshness").textContent = "refreshing…";
  await Promise.all([loadScore(), loadSavings(), loadStages()]);
  document.getElementById("freshness").textContent = "live";
}

document.getElementById("since").addEventListener("change", loadSavings);
document.getElementById("group-by").addEventListener("change", loadStages);
refresh();
setInterval(refresh, 15000);
</script>
</body>
</html>
"""


def perf_html(session_token: str = "") -> str:
    """Return the dashboard HTML with the session token injected for fetch()."""
    if not session_token:
        return _HTML
    # Inject the token before any other <script> so fetch() can pick it up.
    return _HTML.replace(
        "<script>",
        f"<script>window.HERMES_SESSION_TOKEN={json.dumps(session_token)};</script>\n<script>",
        1,
    )


# ---------------------------------------------------------------------------
# FastAPI registration helper. Called by web_server.py at import time.
# ---------------------------------------------------------------------------

def register(app, public_paths: set | None = None,
             session_token_getter=None) -> None:
    """Mount perf endpoints onto an existing FastAPI app.

    ``public_paths`` is mutated to whitelist the perf endpoints so they
    don't require the dashboard session token. ``session_token_getter`` is
    a callable returning the live session token for HTML injection.
    """
    try:
        from fastapi import Query
    except Exception:  # pragma: no cover
        return

    @app.get("/api/perf/stage_summary")
    async def _stage_summary(group_by: str = Query("stage")):
        return _json_response(stage_summary(group_by=group_by))

    @app.get("/api/perf/token_savings")
    async def _token_savings(since: str = Query("7d")):
        return _json_response(token_savings(since=since))

    @app.get("/api/perf/turbo_score")
    async def _turbo_score():
        return _json_response(turbo_score())

    @app.get("/perf")
    async def _perf_page():
        token = ""
        if session_token_getter is not None:
            try:
                token = session_token_getter() or ""
            except Exception:
                token = ""
        return _html_response(perf_html(session_token=token))

    if public_paths is not None:
        # Read-only telemetry is safe to expose without the session token —
        # the dashboard binds to localhost only and the data is in the user's
        # own ~/.hermes/ directory.
        public_paths.update({
            "/api/perf/stage_summary",
            "/api/perf/token_savings",
            "/api/perf/turbo_score",
        })


__all__ = [
    "perf_html",
    "register",
    "stage_summary",
    "token_savings",
    "turbo_score",
]
