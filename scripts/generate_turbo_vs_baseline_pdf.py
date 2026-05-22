#!/usr/bin/env python3
"""Render the Turbo vs Baseline benchmark JSON as a one-pager PDF.

Reads ``docs/perf/turbo-vs-baseline-baseline.json`` (or another path via
``--input``) and writes ``docs/perf/turbo-vs-baseline.pdf``. Uses
``reportlab`` (already a transitive dep via ``generate_tota_benchmark_report``)
with no extra packages.

Usage::

    python scripts/generate_turbo_vs_baseline_pdf.py
    python scripts/generate_turbo_vs_baseline_pdf.py \\
        --input docs/perf/turbo-vs-baseline-baseline.json \\
        --output docs/perf/turbo-vs-baseline.pdf
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import HorizontalBarChart

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "docs" / "perf" / "turbo-vs-baseline-baseline.json"
DEFAULT_OUTPUT = ROOT / "docs" / "perf" / "turbo-vs-baseline.pdf"

PAGE_W, PAGE_H = A4
MARGIN = 1.6 * cm
CONTENT_W = PAGE_W - 2 * MARGIN

GREEN = colors.HexColor("#19D27F")
BLUE = colors.HexColor("#32B7FF")
RED = colors.HexColor("#FF5D6C")
MUTED = colors.HexColor("#64748B")
INK = colors.HexColor("#0F172A")
PANEL = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#CBD5E1")


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=22, leading=26, textColor=INK, spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=11, leading=14, textColor=MUTED, spaceAfter=14,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=14, leading=18, textColor=INK, spaceBefore=10, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontName="Helvetica",
            fontSize=10, leading=14, textColor=INK,
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.5, leading=11, textColor=MUTED,
        ),
    }


def _speedup_chart(stages: Sequence[dict]) -> Drawing:
    """Horizontal bar chart of speedup ratios."""

    ranked = [s for s in stages if s.get("speedup_x") is not None]
    ranked.sort(key=lambda s: s["speedup_x"], reverse=True)

    chart_h = max(140, 22 * len(ranked) + 40)
    d = Drawing(CONTENT_W, chart_h)

    if not ranked:
        d.add(String(0, chart_h / 2, "no speedup data", fontName="Helvetica"))
        return d

    bar = HorizontalBarChart()
    bar.x = 170
    bar.y = 12
    bar.height = chart_h - 30
    bar.width = CONTENT_W - 200
    bar.data = [[s["speedup_x"] for s in ranked]]
    bar.categoryAxis.categoryNames = [s["name"] for s in ranked]
    bar.categoryAxis.labels.fontName = "Helvetica"
    bar.categoryAxis.labels.fontSize = 8
    bar.categoryAxis.labels.textAnchor = "end"
    bar.categoryAxis.labels.boxAnchor = "e"
    bar.categoryAxis.labels.dx = -4
    bar.valueAxis.valueMin = 0
    max_val = max(s["speedup_x"] for s in ranked)
    bar.valueAxis.valueMax = max_val * 1.1
    bar.valueAxis.valueStep = max(1, math.ceil(max_val / 6))
    bar.valueAxis.labels.fontName = "Helvetica"
    bar.valueAxis.labels.fontSize = 8
    bar.bars[0].fillColor = GREEN
    bar.bars.strokeColor = None
    bar.barLabelFormat = lambda v: f"{v:.2f}x"
    bar.barLabels.fontName = "Helvetica-Bold"
    bar.barLabels.fontSize = 8
    bar.barLabels.dx = 4
    bar.barLabels.boxAnchor = "w"
    bar.barLabels.nudge = 0
    bar.barLabels.fillColor = INK

    # Highlight the parity line (1x)
    one_x = bar.x + bar.width * (1.0 / bar.valueAxis.valueMax)
    d.add(Rect(one_x, bar.y, 1, bar.height, fillColor=RED, strokeColor=None))
    d.add(String(one_x + 3, bar.y + bar.height + 2, "1x parity",
                 fontName="Helvetica", fontSize=7, fillColor=RED))

    d.add(bar)
    return d


def _stage_table(stages: Sequence[dict]) -> Table:
    header = ["Stage", "p50 (µs)", "p95 (µs)", "Baseline (µs)", "Speedup"]
    rows = [header]
    for s in stages:
        sp = s.get("speedup_x")
        base = s.get("baseline_us")
        rows.append([
            s["name"],
            f"{s['median_us']:.1f}",
            f"{s['p95_us']:.1f}",
            f"{base:.1f}" if base is not None else "—",
            f"{sp:.2f}x" if sp is not None else "—",
        ])

    table = Table(
        rows,
        colWidths=[7.5 * cm, 2.1 * cm, 2.1 * cm, 2.4 * cm, 2.4 * cm],
        repeatRows=1,
    )
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL]),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
    # Colour the speedup cell green > 1, red < 1, muted = parity
    for i, s in enumerate(stages, start=1):
        sp = s.get("speedup_x")
        if sp is None:
            continue
        if sp >= 2:
            style.add("TEXTCOLOR", (4, i), (4, i), GREEN)
            style.add("FONTNAME", (4, i), (4, i), "Helvetica-Bold")
        elif sp < 1:
            style.add("TEXTCOLOR", (4, i), (4, i), RED)
        else:
            style.add("TEXTCOLOR", (4, i), (4, i), MUTED)
    table.setStyle(style)
    return table


def _summary_callouts(stages: Sequence[dict]) -> Table:
    ranked = [s for s in stages if s.get("speedup_x") is not None]
    ranked.sort(key=lambda s: s["speedup_x"], reverse=True)
    top = ranked[:2] if ranked else []
    cells: List[List] = []
    for s in top:
        cells.append([
            Paragraph(
                f"<b>{s['speedup_x']:.2f}×</b><br/>"
                f"<font size='8' color='#64748B'>{s['name']}</font>",
                _styles()["body"],
            ),
        ])
    if not cells:
        cells = [[Paragraph("no baseline data", _styles()["small"])]]
    while len(cells) < 2:
        cells.append([Paragraph("—", _styles()["small"])])

    callout = Table(
        [[cells[0][0], cells[1][0]]],
        colWidths=[CONTENT_W / 2 - 4, CONTENT_W / 2 - 4],
    )
    callout.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LINEBETWEEN", (0, 0), (-1, -1), 0.4, BORDER),
    ]))
    return callout


def build(report: dict, output: Path) -> Path:
    styles = _styles()
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title="Hermes Turbo vs Baseline Benchmark",
        author="hermes-turbo-agent",
    )

    iters = int(report.get("iters", 0))
    stages = report.get("stages", [])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    flow: List = []
    flow.append(Paragraph("Hermes Turbo vs Baseline", styles["title"]))
    flow.append(Paragraph(
        f"Generated {now} • {iters} iterations per stage • "
        "compares the runtime mechanisms added in the turbo fork "
        "(#81–#103 + P1–P7) against intentionally-naive baselines.",
        styles["subtitle"],
    ))

    flow.append(Paragraph("Headline wins", styles["h2"]))
    flow.append(_summary_callouts(stages))
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("Speedup per stage", styles["h2"]))
    flow.append(_speedup_chart(stages))
    flow.append(Spacer(1, 8))

    flow.append(Paragraph("Detailed results", styles["h2"]))
    flow.append(_stage_table(stages))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph(
        "<b>Reading the numbers.</b> Baselines are intentionally naïve "
        "(no validation, no disk, no contract enforcement). A speedup below "
        "1× reflects the <i>cost of correctness</i> — the turbo path holds "
        "invariants the baseline ignores. Real wins live where the turbo "
        "path replaces an LLM call (router) or a full tree walk "
        "(project_mapper).",
        styles["small"],
    ))
    flow.append(Spacer(1, 4))
    flow.append(Paragraph(
        "Source: <font face='Courier'>scripts/benchmark_turbo_vs_baseline.py</font> • "
        "Smoke mode runs in <font face='Courier'>.github/workflows/dod.yml</font> on "
        "every PR. The daily upstream-sync workflow regenerates the full "
        "report and attaches the JSON to the sync PR.",
        styles["small"],
    ))

    doc.build(flow)
    return output


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    if not args.input.exists():
        raise SystemExit(f"input not found: {args.input}")

    report = json.loads(args.input.read_text(encoding="utf-8"))
    out = build(report, args.output)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
