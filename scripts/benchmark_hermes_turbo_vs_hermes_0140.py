#!/usr/bin/env python3
"""Benchmark Tota Agent against upstream Hermes Agent 0.14.0.

This script provisions a temporary upstream checkout at tag ``v2026.5.16``
(``version = "0.14.0"``), creates an isolated venv for the stock baseline,
and measures the benchmark rows needed by issue #38 where the local host has
enough machinery.

The browser-console row is intentionally conservative: this host needs a local
Chrome/Chromium binary, and the repo currently only ships a Tota-side browser
eval harness, not a stock/Tota parity harness. When either prerequisite is
missing, the row is emitted as blocked instead of fabricating a comparison.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import statistics
import subprocess
import tempfile
import textwrap
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCAL_PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
DEFAULT_OUTPUT_JSON = ROOT / "docs" / "tota-benchmark-hermes-0.14.0.json"
DEFAULT_OUTPUT_MD = ROOT / "docs" / "tota-benchmark-hermes-0.14.0.md"
UPSTREAM_REMOTE = "https://github.com/NousResearch/hermes-agent.git"
UPSTREAM_REF = "v2026.5.16"
EXPECTED_STOCK_VERSION = "0.14.0"


def _venv_python(venv_root: Path) -> Path:
    return venv_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=merged_env,
        text=True,
        capture_output=True,
        check=check,
    )


def _run_json(
    python_exec: Path,
    code: str,
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    proc = _run([str(python_exec), "-c", code], cwd=cwd, env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "python -c failed")
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("python -c returned no JSON payload")
    return json.loads(lines[-1])


def _median(values: list[float]) -> float:
    return statistics.median(values)


def _find_browser_binary() -> str | None:
    explicit = os.environ.get("CHROME_BIN")
    if explicit and os.path.isfile(explicit) and os.access(explicit, os.X_OK):
        return explicit
    for name in ("google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    for app_path in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ):
        if os.path.isfile(app_path) and os.access(app_path, os.X_OK):
            return app_path
    return None


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * q) - 1))
    return ordered[index]


def _start_headless_chrome(browser_binary: str, port: int) -> tuple[subprocess.Popen[str], Path, str]:
    profile = Path(tempfile.mkdtemp(prefix="tota-browser-bench-"))
    stdout_log = (profile / "chrome.stdout.log").open("w", encoding="utf-8")
    stderr_log = (profile / "chrome.stderr.log").open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            browser_binary,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--headless=new",
            "--disable-gpu",
        ],
        stdout=stdout_log,
        stderr=stderr_log,
        text=True,
    )
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return proc, profile, payload["webSocketDebuggerUrl"]
        except Exception:
            time.sleep(0.25)
    stderr_text = (profile / "chrome.stderr.log").read_text(encoding="utf-8", errors="replace")
    for line in stderr_text.splitlines():
        marker = "DevTools listening on "
        if marker in line:
            return proc, profile, line.split(marker, 1)[1].strip()
    proc.terminate()
    raise RuntimeError(
        "Chrome did not expose a CDP endpoint in time. "
        f"stderr: {stderr_text[:400]}"
    )


def _stock_version(repo_root: Path) -> str:
    with (repo_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    return str(data["project"]["version"])


def _bootstrap_stock_checkout(temp_root: Path, local_python: Path) -> tuple[Path, Path]:
    stock_repo = temp_root / "hermes-stock"
    stock_venv = temp_root / "stock-venv"
    _run(["git", "clone", "--depth", "1", "--branch", UPSTREAM_REF, UPSTREAM_REMOTE, str(stock_repo)])
    version = _stock_version(stock_repo)
    if version != EXPECTED_STOCK_VERSION:
        raise RuntimeError(
            f"upstream ref {UPSTREAM_REF} resolved to version {version}, expected {EXPECTED_STOCK_VERSION}"
        )
    _run([str(local_python), "-m", "venv", str(stock_venv)])
    stock_python = _venv_python(stock_venv)
    _run([str(stock_python), "-m", "pip", "install", "--upgrade", "pip"])
    _run([str(stock_python), "-m", "pip", "install", "-e", str(stock_repo)])
    _run([str(stock_python), "-m", "pip", "install", "websockets", "aiohttp"])
    return stock_repo, stock_python


def _microbench_code(kind: str) -> str:
    local = {
        "json": """
            import json, statistics, time
            from agent._fastjson import dumps
            payload = {"message": "hello world", "numbers": [1, 2, 3], "meta": {"lang": "en", "ok": True}}
            def fn():
                return dumps(payload)
            samples = []
            for _ in range(7):
                start = time.perf_counter()
                for _ in range(30000):
                    fn()
                samples.append((time.perf_counter() - start) / 30000 * 1e6)
            print(json.dumps({"metric": "json_dumps_short_us", "value": statistics.median(samples)}))
        """,
        "tool": """
            import json, statistics, time
            from agent._hermes_fast import HAVE_RUST, parse_tool_call_delta
            blob = '{"id":"toolu_123","type":"function","function":{"name":"search","arguments":"{\\\\\\"q\\\\\\":\\\\\\"benchmark\\\\\\"}"}}'
            samples = []
            for _ in range(7):
                start = time.perf_counter()
                for _ in range(30000):
                    parse_tool_call_delta(blob)
                samples.append((time.perf_counter() - start) / 30000 * 1e6)
            print(json.dumps({"metric": "tool_call_parse_us", "value": statistics.median(samples), "have_rust": HAVE_RUST}))
        """,
        "tokens": """
            import json, statistics, time
            from agent._hermes_fast import HAVE_RUST, estimate_messages_tokens
            messages = [{"role": "system", "content": "Benchmark harness"}, {"role": "user", "content": "hello" * 20}, {"role": "assistant", "content": "world" * 20}] * 40
            samples = []
            for _ in range(7):
                start = time.perf_counter()
                for _ in range(3000):
                    estimate_messages_tokens(messages)
                samples.append((time.perf_counter() - start) / 3000 * 1e6)
            print(json.dumps({"metric": "token_estimate_batch_us", "value": statistics.median(samples), "have_rust": HAVE_RUST}))
        """,
        "async": """
            import asyncio, json, statistics, time
            from agent.uvloop_utils import install_uvloop_policy
            install_uvloop_policy()
            async def churn():
                async def unit():
                    for _ in range(1000):
                        await asyncio.sleep(0)
                await asyncio.gather(*[unit() for _ in range(50)])
            samples = []
            for _ in range(7):
                start = time.perf_counter()
                asyncio.run(churn())
                samples.append((time.perf_counter() - start) * 1000)
            print(json.dumps({"metric": "async_1000_task_ms", "value": statistics.median(samples), "uvloop_requested": True}))
        """,
        "cold": """
            import json, time
            start = time.perf_counter()
            import model_tools  # noqa: F401
            elapsed = (time.perf_counter() - start) * 1000
            print(json.dumps({"metric": "cold_start_ms", "value": elapsed}))
        """,
        "integrations": """
            import json
            from pathlib import Path
            root = Path.cwd() / "gateway" / "platforms"
            count = sum(1 for path in root.glob("*.py") if path.name != "__init__.py")
            print(json.dumps({"metric": "integration_breadth", "value": count}))
        """,
    }
    stock = {
        "json": """
            import json, statistics, time
            payload = {"message": "hello world", "numbers": [1, 2, 3], "meta": {"lang": "en", "ok": True}}
            samples = []
            for _ in range(7):
                start = time.perf_counter()
                for _ in range(30000):
                    json.dumps(payload)
                samples.append((time.perf_counter() - start) / 30000 * 1e6)
            print(json.dumps({"metric": "json_dumps_short_us", "value": statistics.median(samples)}))
        """,
        "tool": """
            import json, statistics, time
            decoder = json.JSONDecoder()
            blob = '{"id":"toolu_123","type":"function","function":{"name":"search","arguments":"{\\\\\\"q\\\\\\":\\\\\\"benchmark\\\\\\"}"}}'
            samples = []
            for _ in range(7):
                start = time.perf_counter()
                for _ in range(30000):
                    decoder.raw_decode(blob)
                samples.append((time.perf_counter() - start) / 30000 * 1e6)
            print(json.dumps({"metric": "tool_call_parse_us", "value": statistics.median(samples)}))
        """,
        "tokens": """
            import json, statistics, time
            from agent.model_metadata import estimate_messages_tokens_rough
            messages = [{"role": "system", "content": "Benchmark harness"}, {"role": "user", "content": "hello" * 20}, {"role": "assistant", "content": "world" * 20}] * 40
            samples = []
            for _ in range(7):
                start = time.perf_counter()
                for _ in range(3000):
                    estimate_messages_tokens_rough(messages)
                samples.append((time.perf_counter() - start) / 3000 * 1e6)
            print(json.dumps({"metric": "token_estimate_batch_us", "value": statistics.median(samples)}))
        """,
        "async": """
            import asyncio, json, statistics, time
            async def churn():
                async def unit():
                    for _ in range(1000):
                        await asyncio.sleep(0)
                await asyncio.gather(*[unit() for _ in range(50)])
            samples = []
            for _ in range(7):
                start = time.perf_counter()
                asyncio.run(churn())
                samples.append((time.perf_counter() - start) * 1000)
            print(json.dumps({"metric": "async_1000_task_ms", "value": statistics.median(samples), "uvloop_requested": False}))
        """,
        "cold": local["cold"],
        "integrations": local["integrations"],
    }
    return textwrap.dedent((local if kind.startswith("local:") else stock)[kind.split(":", 1)[1]])


def _browser_bench_code(cdp_url: str, iterations: int) -> str:
    return textwrap.dedent(
        f"""
        import json
        import math
        import statistics
        import time

        from tools.browser_supervisor import SUPERVISOR_REGISTRY
        from tools.browser_tool import browser_console

        task_id = "bench-browser-0140"
        cdp_url = {cdp_url!r}
        iterations = {iterations}

        supervisor = SUPERVISOR_REGISTRY.get_or_start(task_id=task_id, cdp_url=cdp_url)
        time.sleep(1.0)

        warm = json.loads(browser_console(expression="1+1", task_id=task_id))
        if not warm.get("success") or warm.get("result") != 2:
            raise RuntimeError(f"browser warmup failed: {{warm}}")

        samples = []
        for _ in range(iterations):
            start = time.perf_counter()
            out = json.loads(browser_console(expression="1+1", task_id=task_id))
            elapsed_ms = (time.perf_counter() - start) * 1000
            if not out.get("success") or out.get("result") != 2:
                raise RuntimeError(f"browser iteration failed: {{out}}")
            samples.append(elapsed_ms)

        SUPERVISOR_REGISTRY.stop_all()

        ordered = sorted(samples)
        p99_index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * 0.99) - 1))
        print(json.dumps({{
            "metric": "browser_console_p99_ms",
            "value": ordered[p99_index],
            "median": statistics.median(samples),
            "min": min(samples),
            "max": max(samples),
            "iterations": iterations,
        }}))
        """
    )


@dataclass
class MetricRow:
    key: str
    label: str
    unit: str
    lower_is_better: bool = True


ROWS = [
    MetricRow("cold_start_ms", "Cold start (import_model_tools proxy)", "ms"),
    MetricRow("json_dumps_short_us", "JSON dumps short payload", "us"),
    MetricRow("tool_call_parse_us", "Tool-call parse", "us"),
    MetricRow("token_estimate_batch_us", "Token estimate batch", "us"),
    MetricRow("async_1000_task_ms", "Async 1,000-task scheduler", "ms"),
    MetricRow("browser_console_p99_ms", "browser_console p99", "ms"),
    MetricRow("integration_breadth", "Integration breadth", "platforms", lower_is_better=False),
]


def _collect_metric(
    key: str,
    *,
    local_python: Path,
    stock_python: Path,
    stock_repo: Path,
) -> dict[str, Any]:
    if key == "cold_start_ms":
        local_samples = []
        stock_samples = []
        for _ in range(5):
            local_payload = _run_json(local_python, _microbench_code("local:cold"), cwd=ROOT)
            stock_payload = _run_json(stock_python, _microbench_code("stock:cold"), cwd=stock_repo)
            local_samples.append(float(local_payload["value"]))
            stock_samples.append(float(stock_payload["value"]))
        return {"local": _median(local_samples), "stock": _median(stock_samples)}
    local_payload = _run_json(local_python, _microbench_code(f"local:{key.replace('_ms', '').replace('_us', '').replace('integration_breadth', 'integrations')}"), cwd=ROOT)
    stock_payload = _run_json(stock_python, _microbench_code(f"stock:{key.replace('_ms', '').replace('_us', '').replace('integration_breadth', 'integrations')}"), cwd=stock_repo)
    return {
        "local": float(local_payload["value"]),
        "stock": float(stock_payload["value"]),
        "local_meta": {k: v for k, v in local_payload.items() if k not in {"metric", "value"}},
        "stock_meta": {k: v for k, v in stock_payload.items() if k not in {"metric", "value"}},
    }


def _metric_alias(key: str) -> str:
    return {
        "json_dumps_short_us": "json",
        "tool_call_parse_us": "tool",
        "token_estimate_batch_us": "tokens",
        "async_1000_task_ms": "async",
        "integration_breadth": "integrations",
    }[key]


def _winner(row: MetricRow, local_value: float, stock_value: float) -> str:
    if abs(local_value - stock_value) < 1e-12:
        return "Tie"
    if row.lower_is_better:
        return "Tota Agent" if local_value < stock_value else "Hermes 0.14.0"
    return "Tota Agent" if local_value > stock_value else "Hermes 0.14.0"


def _speedup(row: MetricRow, local_value: float, stock_value: float) -> float:
    if row.lower_is_better:
        return stock_value / local_value
    return local_value / stock_value


def _format_value(value: float, unit: str) -> str:
    if unit == "platforms":
        return str(int(value))
    if unit == "ms":
        return f"{value:.2f} ms"
    return f"{value:.3f} us"


def _build_markdown(report: dict[str, Any]) -> str:
    wins = sum(1 for metric in report["metrics"].values() if metric["winner"] == "Tota Agent")
    losses = sum(1 for metric in report["metrics"].values() if metric["winner"] == "Hermes 0.14.0")
    ties = sum(1 for metric in report["metrics"].values() if metric["winner"] == "Tie")
    blocked = sum(1 for metric in report["metrics"].values() if metric["winner"] == "Blocked")
    lines = [
        "# Tota Agent vs Hermes 0.14.0",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Stock ref: `{report['stock_ref']}` (`version = {report['stock_version']}`)",
        f"- Local Python: `{report['local_python']}`",
        f"- Stock Python: `{report['stock_python']}`",
        f"- Browser benchmark: **{report['browser_console']['status']}**",
        f"- Measured rows: **{wins} wins / {losses} losses / {ties} ties / {blocked} blocked** for Tota Agent on this host",
        "",
        "## Side-by-side rows",
        "",
        "| Row | Hermes 0.14.0 | Tota Agent | Winner | Delta | Notes |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in ROWS:
        metric = report["metrics"][row.key]
        stock_value = "blocked" if metric["stock"] is None else _format_value(metric["stock"], row.unit)
        local_value = "blocked" if metric["local"] is None else _format_value(metric["local"], row.unit)
        delta_value = "-" if metric["speedup"] is None else f"{metric['speedup']:.2f}x"
        lines.append(
            "| {label} | {stock} | {local} | {winner} | {delta} | {notes} |".format(
                label=row.label,
                stock=stock_value,
                local=local_value,
                winner=metric["winner"],
                delta=delta_value,
                notes=metric["notes"],
            )
        )
    lines.extend([""])
    if report["browser_console"]["status"] != "measured":
        lines.extend(
            [
                "## Blocker",
                "",
                report["browser_console"]["reason"],
                "",
                "Because the browser row is still blocked and the measurable rows on this host land below the acceptance target, this pass does not regenerate `tota_agent_benchmark_report.pdf`.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## Status",
                "",
                report["browser_console"]["reason"],
                "",
            ]
        )
    lines.extend(
        [
            "## Commands",
            "",
            "```bash",
            f"{report['local_python']} scripts/benchmark_tota_vs_hermes_0140.py --output-json {report['json_path']} --output-md {report['md_path']}",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-python", default=str(DEFAULT_LOCAL_PYTHON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    parser.add_argument("--browser-iterations", type=int, default=50)
    args = parser.parse_args()

    local_python = Path(args.local_python).expanduser()
    if not local_python.is_absolute():
        local_python = (ROOT / local_python)
    if not local_python.exists():
        raise SystemExit(f"local python not found: {local_python}")

    temp_root = Path(tempfile.mkdtemp(prefix="tota-vs-hermes-0140-"))
    try:
        stock_repo, stock_python = _bootstrap_stock_checkout(temp_root, local_python)

        metrics: dict[str, Any] = {}
        browser_binary = _find_browser_binary()
        browser_status = {"status": "blocked", "binary": browser_binary, "reason": ""}
        chrome_proc = None
        chrome_profile: Path | None = None
        chrome_cdp_url: str | None = None
        if browser_binary is not None:
            try:
                chrome_proc, chrome_profile, chrome_cdp_url = _start_headless_chrome(browser_binary, port=9336)
            except Exception as exc:
                browser_status["reason"] = f"Chrome binary was found at `{browser_binary}`, but startup failed: {exc}"

        for row in ROWS:
            key = row.key
            if key == "browser_console_p99_ms":
                if chrome_cdp_url is None:
                    metrics[key] = {
                        "local": None,
                        "stock": None,
                        "winner": "Blocked",
                        "speedup": None,
                        "notes": "Benchmark blocked on local Chrome startup.",
                    }
                    continue
                local_payload = _run_json(
                    local_python,
                    _browser_bench_code(chrome_cdp_url, args.browser_iterations),
                    cwd=ROOT,
                )
                stock_payload = _run_json(
                    stock_python,
                    _browser_bench_code(chrome_cdp_url, args.browser_iterations),
                    cwd=stock_repo,
                )
                local_value = float(local_payload["value"])
                stock_value = float(stock_payload["value"])
                metrics[key] = {
                    "local": local_value,
                    "stock": stock_value,
                    "winner": _winner(row, local_value, stock_value),
                    "speedup": _speedup(row, local_value, stock_value),
                    "notes": "Measures browser_console(expression) p99 over a shared headless Chrome CDP session.",
                    "local_meta": {k: v for k, v in local_payload.items() if k not in {"metric", "value"}},
                    "stock_meta": {k: v for k, v in stock_payload.items() if k not in {"metric", "value"}},
                }
                browser_status = {
                    "status": "measured",
                    "binary": browser_binary,
                    "reason": "Measured against a shared local headless Chrome instance via CDP.",
                }
            elif key not in {"cold_start_ms", "integration_breadth"}:
                alias = _metric_alias(key)
                local_payload = _run_json(local_python, _microbench_code(f"local:{alias}"), cwd=ROOT)
                stock_payload = _run_json(stock_python, _microbench_code(f"stock:{alias}"), cwd=stock_repo)
                local_value = float(local_payload["value"])
                stock_value = float(stock_payload["value"])
                metrics[key] = {
                    "local": local_value,
                    "stock": stock_value,
                    "winner": _winner(row, local_value, stock_value),
                    "speedup": _speedup(row, local_value, stock_value),
                    "notes": "",
                    "local_meta": {k: v for k, v in local_payload.items() if k not in {"metric", "value"}},
                    "stock_meta": {k: v for k, v in stock_payload.items() if k not in {"metric", "value"}},
                }
                if key == "tool_call_parse_us" and local_payload.get("have_rust"):
                    metrics[key]["notes"] = "Tota path uses the Rust parser."
                elif key == "async_1000_task_ms":
                    metrics[key]["notes"] = "Tota run requested uvloop; stock stayed on default asyncio."
                elif key == "token_estimate_batch_us":
                    metrics[key]["notes"] = "Tota uses estimate_messages_tokens; stock uses estimate_messages_tokens_rough."
            elif key == "cold_start_ms":
                local_samples = []
                stock_samples = []
                for _ in range(5):
                    local_samples.append(
                        float(_run_json(local_python, _microbench_code("local:cold"), cwd=ROOT)["value"])
                    )
                    stock_samples.append(
                        float(_run_json(stock_python, _microbench_code("stock:cold"), cwd=stock_repo)["value"])
                    )
                local_value = _median(local_samples)
                stock_value = _median(stock_samples)
                metrics[key] = {
                    "local": local_value,
                    "stock": stock_value,
                    "winner": _winner(row, local_value, stock_value),
                    "speedup": _speedup(row, local_value, stock_value),
                    "notes": "Fresh subprocess import of model_tools as a cold-start proxy.",
                }
            else:
                local_value = float(_run_json(local_python, _microbench_code("local:integrations"), cwd=ROOT)["value"])
                stock_value = float(_run_json(stock_python, _microbench_code("stock:integrations"), cwd=stock_repo)["value"])
                metrics[key] = {
                    "local": local_value,
                    "stock": stock_value,
                    "winner": _winner(row, local_value, stock_value),
                    "speedup": _speedup(row, local_value, stock_value),
                    "notes": "Counts Python gateway platform modules excluding __init__.py.",
                }
        if browser_status["status"] == "blocked" and not browser_status["reason"]:
            browser_status["reason"] = (
                "No local Chrome/Chromium binary is available on this host, so the browser_console p99 row cannot run."
            )

        report = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
            "stock_ref": UPSTREAM_REF,
            "stock_version": EXPECTED_STOCK_VERSION,
            "local_python": str(local_python),
            "stock_python": str(_venv_python(Path("temporary stock venv"))),
            "metrics": metrics,
            "browser_console": browser_status,
            "json_path": str(Path(args.output_json).resolve()),
            "md_path": str(Path(args.output_md).resolve()),
        }

        output_json = Path(args.output_json).resolve()
        output_md = Path(args.output_md).resolve()
        output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output_md.write_text(_build_markdown(report), encoding="utf-8")
        print(json.dumps({"json": str(output_json), "markdown": str(output_md)}, indent=2))
        return 0
    finally:
        if 'chrome_proc' in locals() and chrome_proc is not None:
            chrome_proc.terminate()
            try:
                chrome_proc.wait(timeout=3)
            except Exception:
                chrome_proc.kill()
        if 'chrome_profile' in locals() and chrome_profile is not None:
            shutil.rmtree(chrome_profile, ignore_errors=True)
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
