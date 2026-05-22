#!/usr/bin/env python3
"""Generate the Tota Agent benchmark and launch report PDF."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "tota_agent_benchmark_report.pdf"
HERMES_0140_REPORT = ROOT / "docs" / "tota-benchmark-hermes-0.14.0.json"
LOGO = ROOT / "docs/assets/tota-brand/tota-agent-logo.png"
OG = ROOT / "docs/assets/tota-brand/tota-agent-og.png"
CHART_DIR = ROOT / "docs/assets/tota-benchmark/generated"

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 1.45 * cm
MARGIN_Y = 1.35 * cm
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN_X * 2)

GREEN = colors.HexColor("#19D27F")
YELLOW = colors.HexColor("#FFE15A")
BLUE = colors.HexColor("#32B7FF")
RED = colors.HexColor("#FF5D6C")
DARK = colors.HexColor("#111827")
INK = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#64748B")
PANEL = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#CBD5E1")

HERMES_0140_LABELS = {
    "cold_start_ms": ("Cold start", "ms"),
    "json_dumps_short_us": ("JSON dumps short payload", "us"),
    "tool_call_parse_us": ("Tool-call parse", "us"),
    "token_estimate_batch_us": ("Token estimate batch", "us"),
    "async_1000_task_ms": ("Async 1,000-task scheduler", "ms"),
    "browser_console_p99_ms": ("browser_console p99", "ms"),
    "integration_breadth": ("Integration breadth", "platforms"),
}


def load_hermes_0140_report() -> dict | None:
    if not HERMES_0140_REPORT.exists():
        return None
    return json.loads(HERMES_0140_REPORT.read_text(encoding="utf-8"))


def format_metric_value(value, unit: str) -> str:
    if value is None:
        return "blocked"
    if unit == "platforms":
        return str(int(value))
    if unit == "ms":
        return f"{float(value):.2f} ms"
    return f"{float(value):.3f} us"


def hermes_0140_summary(report: dict | None) -> tuple[int, int, int, int]:
    if not report:
        return (0, 0, 0, 0)
    metrics = report.get("metrics", {}).values()
    wins = sum(1 for metric in metrics if metric.get("winner") == "Tota Agent")
    losses = sum(1 for metric in metrics if metric.get("winner") == "Hermes 0.14.0")
    ties = sum(1 for metric in metrics if metric.get("winner") == "Tie")
    blocked = sum(1 for metric in metrics if metric.get("winner") == "Blocked")
    return wins, losses, ties, blocked


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle(
            "TotaTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            alignment=TA_CENTER,
            textColor=DARK,
            spaceAfter=10,
        ),
        "Subtitle": ParagraphStyle(
            "TotaSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11.5,
            leading=16,
            alignment=TA_CENTER,
            textColor=MUTED,
            spaceAfter=14,
        ),
        "H1": ParagraphStyle(
            "TotaH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=DARK,
            spaceBefore=10,
            spaceAfter=8,
        ),
        "H2": ParagraphStyle(
            "TotaH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13.5,
            leading=17,
            textColor=DARK,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "Body": ParagraphStyle(
            "TotaBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=13.2,
            textColor=INK,
            spaceAfter=6,
        ),
        "Small": ParagraphStyle(
            "TotaSmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10.4,
            textColor=MUTED,
        ),
        "Cell": ParagraphStyle(
            "TotaCell",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.4,
            leading=9.4,
            textColor=INK,
        ),
        "CellBold": ParagraphStyle(
            "TotaCellBold",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.4,
            leading=9.4,
            textColor=DARK,
        ),
        "Callout": ParagraphStyle(
            "TotaCallout",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=DARK,
            alignment=TA_LEFT,
        ),
    }
    return styles


STYLES = make_styles()


def para_table(data: list[list[str]], widths: list[float] | None = None) -> Table:
    rows = []
    for i, row in enumerate(data):
        style = STYLES["CellBold"] if i == 0 else STYLES["Cell"]
        rows.append([p(str(value), style) for value in row])
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def metric_cards(cards: list[tuple[str, str, str, str]]) -> Table:
    data = []
    for title, value, label, color in cards:
        data.append(
            [
                p(
                    f"<font color='{color}'>{title}</font><br/><font size='17'><b>{value}</b></font><br/>{label}",
                    STYLES["Callout"],
                )
            ]
        )
    table = Table([data], colWidths=[CONTENT_WIDTH / len(cards)] * len(cards))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def chart(name: str, caption: str) -> KeepTogether:
    path = CHART_DIR / name
    img = Image(str(path), width=CONTENT_WIDTH, height=CONTENT_WIDTH * 864 / 1536)
    return KeepTogether([img, p(caption, STYLES["Small"]), Spacer(1, 8)])


def branded_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DARK)
    canvas.rect(0, PAGE_HEIGHT - 0.45 * cm, PAGE_WIDTH, 0.45 * cm, stroke=0, fill=1)
    canvas.setFillColor(GREEN)
    canvas.rect(0, PAGE_HEIGHT - 0.45 * cm, PAGE_WIDTH * 0.37, 0.45 * cm, stroke=0, fill=1)
    canvas.setFillColor(YELLOW)
    canvas.rect(PAGE_WIDTH * 0.37, PAGE_HEIGHT - 0.45 * cm, PAGE_WIDTH * 0.22, 0.45 * cm, stroke=0, fill=1)
    canvas.setFillColor(BLUE)
    canvas.rect(PAGE_WIDTH * 0.59, PAGE_HEIGHT - 0.45 * cm, PAGE_WIDTH * 0.22, 0.45 * cm, stroke=0, fill=1)
    canvas.setFillColor(RED)
    canvas.rect(PAGE_WIDTH * 0.81, PAGE_HEIGHT - 0.45 * cm, PAGE_WIDTH * 0.19, 0.45 * cm, stroke=0, fill=1)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN_X, 0.72 * cm, "Tota Agent Benchmark Report - updated launch edition")
    canvas.drawRightString(PAGE_WIDTH - MARGIN_X, 0.72 * cm, f"Page {doc.page}")
    canvas.restoreState()


def story() -> list:
    s: list = []
    hermes_0140_report = load_hermes_0140_report()
    hermes_0140_wins, hermes_0140_losses, hermes_0140_ties, hermes_0140_blocked = hermes_0140_summary(
        hermes_0140_report
    )

    s.append(Spacer(1, 0.7 * cm))
    s.append(Image(str(LOGO), width=CONTENT_WIDTH, height=CONTENT_WIDTH / 3))
    s.append(Spacer(1, 0.45 * cm))
    s.append(p("Tota Agent Benchmark Report", STYLES["Title"]))
    s.append(
        p(
            "Hermes Original vs Tota Agent vs OpenClaw - updated after the Tota Agent launch package",
            STYLES["Subtitle"],
        )
    )
    s.append(
        metric_cards(
            [
                ("Hermes 0.14.0", f"{hermes_0140_wins} / 7", "Measured rows won by Tota Agent", "#19D27F"),
                ("JSON encode", "7.1x", "Current .venv vs stdlib", "#FFE15A"),
                ("Session batch", "5.3x", "180-message append speedup", "#32B7FF"),
                ("Rust path", "ON", "HAVE_RUST=True", "#FF5D6C"),
            ]
        )
    )
    s.append(Spacer(1, 0.35 * cm))
    s.append(
        p(
            "Generated May 17, 2026 on Apple Silicon ARM. This edition keeps the original benchmark comparison and adds the new Tota Agent brand system, GPT-image-2 visual chart pack, standalone HTML site, README launch story, and current-checkout validation from the local .venv.",
            STYLES["Body"],
        )
    )
    if hermes_0140_report:
        s.append(
            p(
                "Hermes 0.14.0 refresh: "
                f"{hermes_0140_wins} wins / {hermes_0140_losses} losses / "
                f"{hermes_0140_ties} ties / {hermes_0140_blocked} blocked. "
                f"Generated {hermes_0140_report.get('generated_at')} from "
                f"{HERMES_0140_REPORT.relative_to(ROOT)}.",
                STYLES["Body"],
            )
        )
    s.append(
        p(
            "Repository: github.com/wesleysimplicio/tota-agent | Upstream: NousResearch/hermes-agent | Site: tota-agent.html",
            STYLES["Small"],
        )
    )
    s.append(PageBreak())

    s.append(p("Table of Contents", STYLES["H1"]))
    toc = [
        ["1", "Executive Summary"],
        ["2", "Launch Update: What Changed"],
        ["3", "System Overview"],
        ["4", "Current Checkout Validation"],
        ["5", "Benchmark Comparison"],
        ["6", "Benchmark Visuals"],
        ["7", "Runtime Smoke Snapshot"],
        ["8", "Install and Verification"],
        ["9", "Recommendations and Conclusion"],
        ["10", "Methodology and Limitations"],
    ]
    s.append(para_table(toc, [1.2 * cm, CONTENT_WIDTH - 1.2 * cm]))
    s.append(PageBreak())

    s.append(p("1. Executive Summary", STYLES["H1"]))
    s.append(
        p(
            "Tota Agent is a branded and performance-oriented fork of Hermes Agent. The original benchmark already showed Tota Agent leading the practical scorecard against Hermes Original and OpenClaw: stronger JSON performance, lower memory footprint than Node/V8, higher message throughput, faster startup, and a Python-native operating model.",
            STYLES["Body"],
        )
    )
    s.append(
        p(
            "This new report adds the launch layer requested for the project: a Tota Agent logo, a standalone HTML site, updated README positioning, benchmark images generated with GPT-image-2, and a fresh validation pass from the active local .venv. The current environment confirms that the fast path is installed: orjson, msgspec, uvloop, and the Rust extension are all available.",
            STYLES["Body"],
        )
    )
    s.append(
        para_table(
            [
                ["Decision area", "Result"],
                ["Best practical agent fork", "Tota Agent: 44 / 50 consolidated benchmark score."],
                ["Best raw async scheduler", "OpenClaw still wins synthetic libuv scheduling."],
                ["Best low-memory deployment", "Tota Agent / Hermes Python line: about 30 MB RSS in the original comparison."],
                ["Best launch package", "Tota Agent now has logo, site, README story, PDF and visual benchmark deck."],
                ["Current local fast path", "orjson, msgspec, uvloop and Rust extension active in .venv."],
            ],
            [4.3 * cm, CONTENT_WIDTH - 4.3 * cm],
        )
    )
    s.append(PageBreak())

    s.append(p("2. Launch Update: What Changed", STYLES["H1"]))
    s.append(
        para_table(
            [
                ["Area", "New artifact", "Impact"],
                ["Brand", "docs/assets/tota-brand/tota-agent-logo.png and .svg", "Gives the fork a distinct Tota Agent identity while preserving Hermes attribution."],
                ["Visual identity", "GPT-image-2 emblem plus deterministic typography", "Brazil-to-US streaming energy without using a portrait or implying official endorsement."],
                ["Website", "tota-agent.html", "Standalone site with install flow, benchmark story, report links, and full comparison tables."],
                ["README", "README.md", "Repositioned as Tota Agent by Hermes Agent with install, performance extras, assets and usage guidance."],
                ["Charts", "8 generated PNG benchmark visuals", "Readable image set for README and site: JSON, memory, throughput, tools, tokens, async, startup, scorecard."],
                ["Report", "tota_agent_benchmark_report.pdf", "This updated PDF packages the benchmark and launch changes in one artifact."],
            ],
            [3.2 * cm, 6.4 * cm, CONTENT_WIDTH - 9.6 * cm],
        )
    )
    s.append(Spacer(1, 0.2 * cm))
    s.append(Image(str(OG), width=CONTENT_WIDTH, height=CONTENT_WIDTH * 9 / 16))
    s.append(p("Open graph launch image for the Tota Agent site and README ecosystem.", STYLES["Small"]))
    s.append(PageBreak())

    s.append(p("3. System Overview", STYLES["H1"]))
    s.append(
        para_table(
            [
                ["Attribute", "Hermes Original", "Tota Agent", "OpenClaw"],
                ["Language", "Python 3.14", "Python 3.11.14", "TypeScript / Node.js 22"],
                ["JSON engine", "stdlib json", "orjson plus fast shim", "V8 built-in JSON"],
                ["Event loop", "asyncio", "uvloop when fast extra is installed", "libuv"],
                ["Struct decode", "None", "msgspec", "None"],
                ["Native extension", "None", "Rust / PyO3 active in local .venv", "None"],
                ["Main category", "AI Agent", "Optimized Python AI Agent", "Multi-channel AI Gateway"],
                ["Brand layer", "Hermes Agent", "Tota Agent by Hermes Agent", "OpenClaw"],
            ],
            [3.2 * cm, 4.3 * cm, 4.8 * cm, CONTENT_WIDTH - 12.3 * cm],
        )
    )
    s.append(
        p(
            "Tota Agent keeps the Hermes operating model and adds a sharper performance and product story. OpenClaw remains the strongest comparison point for pure Node/libuv scheduling and multi-channel breadth, while Tota Agent has the best balance of Python ergonomics, footprint, startup and hot-path speed.",
            STYLES["Body"],
        )
    )
    s.append(PageBreak())

    s.append(p("4. Current Checkout Validation", STYLES["H1"]))
    s.append(
        p(
            "The following values were collected from the active .venv in this checkout on May 17, 2026. They validate the current installed fast path rather than replacing every historical cross-project benchmark row.",
            STYLES["Body"],
        )
    )
    s.append(
        para_table(
            [
                ["Metric", "Current .venv result", "Interpretation"],
                ["Python", "3.11.14 arm64", "Matches the benchmarked Tota Agent runtime family."],
                ["orjson loads", "1.708 us vs stdlib 4.000 us", "2.3x faster decode on realistic message payload."],
                ["orjson dumps", "0.833 us vs stdlib 5.917 us", "7.1x faster encode on realistic message payload."],
                ["_fast_loads shim", "1.750 us", "Transparent fast-json wrapper keeps orjson-class decode speed."],
                ["estimate_tokens", "0.125 us, HAVE_RUST=True", "Rust extension is active in this checkout."],
                ["uvloop", "0.22.1 available", "Fast event loop is installed for CLI/gateway policy."],
                ["msgspec", "0.21.1 available", "Typed decode dependency is installed."],
            ],
            [4.0 * cm, 5.0 * cm, CONTENT_WIDTH - 9.0 * cm],
        )
    )
    s.append(Spacer(1, 0.2 * cm))
    s.append(
        para_table(
            [
                ["Smoke benchmark", "Median", "Notes"],
                ["import_model_tools", "0.2769 s", "69 tool names discovered."],
                ["discover_plugins_fast", "0.1214 s", "17 plugins without platform load."],
                ["discover_plugins_full", "0.1619 s", "22 plugins with platform load."],
                ["resolve_toolset_cached", "0.0049 s cold / 0.000001 s warm", "70 tools; cache is effectively instant once warm."],
                ["session_append_messages_batch", "0.0068 s batch vs 0.0363 s loop", "5.3x faster append path for 180 messages."],
            ],
            [5.2 * cm, 4.0 * cm, CONTENT_WIDTH - 9.2 * cm],
        )
    )
    s.append(PageBreak())

    s.append(p("5. Benchmark Comparison", STYLES["H1"]))
    if hermes_0140_report:
        rows = [["Metric", "Hermes 0.14.0", "Tota Agent", "Winner", "Delta"]]
        for key, (label, unit) in HERMES_0140_LABELS.items():
            metric = hermes_0140_report["metrics"][key]
            rows.append(
                [
                    label,
                    format_metric_value(metric.get("stock"), unit),
                    format_metric_value(metric.get("local"), unit),
                    metric.get("winner", "-"),
                    "-" if metric.get("speedup") is None else f"{metric['speedup']:.2f}x",
                ]
            )
        s.append(
            p(
                "Current side-by-side refresh against upstream Hermes 0.14.0. "
                f"Browser status: {hermes_0140_report.get('browser_console', {}).get('status', 'unknown')}.",
                STYLES["Body"],
            )
        )
        s.append(
            para_table(
                rows,
                [4.5 * cm, 3.2 * cm, 3.2 * cm, 3.3 * cm, CONTENT_WIDTH - 14.2 * cm],
            )
        )
        s.append(Spacer(1, 0.25 * cm))
    s.append(
        para_table(
            [
                ["Metric", "Hermes Original", "Tota Agent", "OpenClaw", "Winner"],
                ["Total score", "30 / 50", "44 / 50", "36 / 50", "Tota Agent"],
                ["JSON dumps, large payload", "18.40 us", "3.20 us", "5.80 us", "Tota Agent"],
                ["JSON loads, large payload", "12.80 us", "2.80 us", "5.20 us", "Tota Agent"],
                ["Medium message pipeline", "7.50 us", "2.20 us", "3.46 us", "Tota Agent"],
                ["Medium throughput", "133k msg/s", "454k msg/s", "289k msg/s", "Tota Agent"],
                ["Tool-call typed parse", "Error / N/A", "0.45 us", "N/A", "Tota Agent"],
                ["Async 1,000 tasks", "2.50 ms", "1.40 ms", "0.08 ms", "OpenClaw"],
                ["Cold start", "~52 ms", "~50 ms", "~280 ms", "Tota Agent"],
                ["RSS memory", "~30 MB", "~30 MB", "~97 MB", "Python line"],
            ],
            [4.5 * cm, 3.2 * cm, 3.1 * cm, 3.1 * cm, CONTENT_WIDTH - 13.9 * cm],
        )
    )
    s.append(
        p(
            "The comparison still says the same thing after the launch update: Tota Agent is the strongest practical fork for Python-based AI agent deployments. OpenClaw wins pure scheduler microbenchmarks, but Tota Agent wins the mixed operational score.",
            STYLES["Body"],
        )
    )
    s.append(PageBreak())

    s.append(p("6. Benchmark Visuals", STYLES["H1"]))
    for file_name, caption in [
        ("gpt-image-2-tota-benchmark-json-latency.png", "Figure 1 - JSON serialization latency. Lower is better."),
        ("gpt-image-2-tota-benchmark-memory-footprint.png", "Figure 2 - Memory and footprint comparison."),
        ("gpt-image-2-tota-benchmark-message-throughput.png", "Figure 3 - Message throughput and pipeline latency."),
        ("gpt-image-2-tota-benchmark-tool-call-parsing.png", "Figure 4 - Tool-call parsing fast path."),
        ("gpt-image-2-tota-benchmark-token-counting.png", "Figure 5 - Token counting benchmark."),
        ("gpt-image-2-tota-benchmark-concurrency-async.png", "Figure 6 - Concurrency and async scheduling."),
        ("gpt-image-2-tota-benchmark-startup-time.png", "Figure 7 - Startup time and cold-start behavior."),
        ("gpt-image-2-tota-benchmark-ecosystem-scorecard.png", "Figure 8 - Consolidated category scorecard."),
    ]:
        s.append(chart(file_name, caption))
        if file_name in {
            "gpt-image-2-tota-benchmark-message-throughput.png",
            "gpt-image-2-tota-benchmark-token-counting.png",
            "gpt-image-2-tota-benchmark-startup-time.png",
        }:
            s.append(PageBreak())

    s.append(PageBreak())
    s.append(p("7. Runtime Smoke Snapshot", STYLES["H1"]))
    s.append(
        para_table(
            [
                ["Runtime surface", "Observed value", "Why it matters"],
                ["AIAgent init with default tools", "3.30 s median, 27 valid tools", "Shows full agent construction path in the local checkout."],
                ["AIAgent init file/terminal subset", "3.37 s median, 8 valid tools", "Focused toolset construction remains comparable."],
                ["Delegate child build", "2.85 s median", "Measures subagent construction without model API calls."],
                ["Tool dispatch noop", "0.048-0.050 ms per call", "Dispatch overhead is small relative to LLM latency."],
                ["OpenRouter metadata cache", "0.745-0.758 ms per lookup", "Disk cache lookup remains sub-millisecond class."],
                ["Session batch append", "3.9x to 5.3x faster than loop append", "Batching materially improves transcript persistence."],
            ],
            [4.7 * cm, 4.5 * cm, CONTENT_WIDTH - 9.2 * cm],
        )
    )
    s.append(
        p(
            "One synthetic parallel-tool benchmark case was excluded from the score because its stub lacked an internal method and the environment missed the optional websockets dependency. The rest of the report uses successful benchmark cases and existing cross-project comparison data.",
            STYLES["Small"],
        )
    )
    s.append(PageBreak())

    s.append(p("8. Install and Verification", STYLES["H1"]))
    s.append(
        para_table(
            [
                ["Step", "Command"],
                ["Clone", "git clone https://github.com/wesleysimplicio/tota-agent.git"],
                ["Create env", "uv venv .venv --python 3.11 && source .venv/bin/activate"],
                ["Install", "uv pip install -e \".[all,dev]\""],
                ["Fast extra", "uv pip install -e \".[fast]\""],
                ["Rust extension", "PATH=\"$HOME/.cargo/bin:$PATH\" bash scripts/install-rust.sh"],
                ["Verify Rust", "python -c \"from agent._hermes_fast import HAVE_RUST; print(HAVE_RUST)\""],
                ["Run app", "./hermes"],
                ["Validate repo", "taskflow run ."],
            ],
            [4.2 * cm, CONTENT_WIDTH - 4.2 * cm],
        )
    )
    s.append(
        p(
            "The fast extra remains optional. Base installs stay smaller, while performance installs activate orjson, msgspec, uvloop and the Rust extension when the platform supports them.",
            STYLES["Body"],
        )
    )
    s.append(PageBreak())

    s.append(p("9. Recommendations and Conclusion", STYLES["H1"]))
    s.append(
        para_table(
            [
                ["Scenario", "Recommended", "Reason"],
                ["WhatsApp / HTTP AI agent", "Tota Agent", "Hermes-compatible Python model with materially faster JSON hot paths."],
                ["Serverless / cold-start sensitive", "Tota Agent", "Original comparison shows about 50 ms cold start vs about 280 ms for OpenClaw."],
                ["Low memory density", "Tota Agent", "Python line keeps RSS far lower than the Node/V8 comparison point."],
                ["Pure scheduler stress", "OpenClaw", "Native libuv wins synthetic async scheduling."],
                ["Upstream contribution baseline", "Hermes Agent", "Canonical upstream architecture and community."],
                ["Public fork launch", "Tota Agent", "Now has brand identity, site, README, visuals and updated PDF."],
            ],
            [4.2 * cm, 3.1 * cm, CONTENT_WIDTH - 7.3 * cm],
        )
    )
    s.append(
        p(
            "Final conclusion: Tota Agent is now more than a fast fork. It has a complete launch package and a benchmark narrative that is legible to both engineers and product readers. The next highest-impact technical work is to keep the Rust path active in release builds, expand measured integration scoring to the full current gateway adapter surface, and rerun OpenClaw/Hermes comparisons under the same host whenever a release candidate is cut.",
            STYLES["Body"],
        )
    )
    s.append(PageBreak())

    s.append(p("10. Methodology and Limitations", STYLES["H1"]))
    s.append(
        para_table(
            [
                ["Topic", "Detail"],
                ["Original comparison", "Based on the May 2026 benchmark PDF comparing Hermes Original, Tota Agent and OpenClaw across 8 dimensions."],
                ["Current validation", "Collected from the local .venv on May 17, 2026 with Python 3.11.14 on Apple Silicon ARM."],
                ["Brand update", "Assets were generated for the launch package; logo typography was composed deterministically for exact text."],
                ["Images", "Benchmark visuals are PNG assets generated with GPT-image-2 and overlaid with deterministic benchmark data."],
                ["Microbenchmarks", "Numbers isolate hot paths and do not include LLM network latency, provider variance or external API queues."],
                ["Cross-runtime caveat", "Python and Node.js runtimes optimize different workloads; real deployment fit still depends on workload mix."],
            ],
            [4.2 * cm, CONTENT_WIDTH - 4.2 * cm],
        )
    )
    s.append(
        p(
            "Primary local artifacts: README.md, tota-agent.html, docs/assets/tota-brand/*, docs/assets/tota-benchmark/generated/*, docs/tota-benchmark-win-plan.md, benchmark-report.md and this PDF.",
            STYLES["Small"],
        )
    )
    return s


def main() -> int:
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=MARGIN_X,
        leftMargin=MARGIN_X,
        topMargin=MARGIN_Y,
        bottomMargin=MARGIN_Y,
        title="Tota Agent Benchmark Report - Updated Launch Edition",
        author="Wesley Simplicio",
        subject="AI Agent Framework Performance Comparison",
    )
    doc.build(story(), onFirstPage=branded_page, onLaterPages=branded_page)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
