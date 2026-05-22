#!/usr/bin/env python3
"""Render the full Hermes Turbo vs upstream benchmark as a multi-page PDF.

Reads ``docs/perf/turbo-full-segments.json`` (or another file via ``--input``)
and writes ``docs/perf/turbo-full-segments.pdf``. One page per segment plus a
cover page with the headline and the segment summary table.

Usage::

    python scripts/generate_turbo_full_pdf.py
    python scripts/generate_turbo_full_pdf.py --input <json> --output <pdf>
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "docs" / "perf" / "turbo-full-segments.json"
DEFAULT_OUTPUT = ROOT / "docs" / "perf" / "turbo-full-segments.pdf"

PAGE_W, PAGE_H = A4
MARGIN = 1.55 * cm
CONTENT_W = PAGE_W - 2 * MARGIN

GREEN = colors.HexColor("#19D27F")
BLUE = colors.HexColor("#32B7FF")
YELLOW = colors.HexColor("#FFE15A")
RED = colors.HexColor("#FF5D6C")
MUTED = colors.HexColor("#64748B")
INK = colors.HexColor("#0F172A")
PANEL = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#CBD5E1")

SEGMENT_PRETTY = {
    "project_mapping": "1. Project Mapping (survivor, P1)",
    "routing":         "2. Deterministic Routing (survivor, #99)",
    "receipts":        "3. Receipts (survivor, P7)",
    "tool_replay":     "4. Tool-Call Replay (NEW — Proposta A)",
    "cost_router":     "5. Cost-Aware Multi-Tier Router (NEW — Proposta B)",
    "async_dag":       "6. Async DAG Tool Executor (NEW — Proposta C)",
    "tracing":         "7. OTel-Compatible Tracing (NEW — Proposta D)",
    "provider_chain":  "8. Provider Fallback Chain (NEW — Proposta E)",
}

SEGMENT_BLURB = {
    "project_mapping":
        "Deterministic stack/workspace fingerprint via top-level manifests. "
        "Survived the post-mortem cleanup with a 33–39× win over a naïve "
        "tree walk.",
    "routing":
        "Deterministic regex router skips LLM round-trips on trivial "
        "intents. The original headline win of the fork — 129–185× vs an "
        "LLM proxy stand-in.",
    "receipts":
        "Append-only `.receipts/<sha>.json` content-addressable ledger. "
        "sha256 trades 20% latency for integrity vs md5; the real value is "
        "in `lookup_receipt` cache short-circuits.",
    "tool_replay":
        "Tool-call replay primitive built on top of receipts. Canonical "
        "key over (name, args), stored as `.receipts/tool/<sha>.json`. "
        "12× over a 500 µs tool stand-in on cache hit. Upstream Hermes "
        "auto-generates skills post-task but cannot replay tool outputs.",
    "cost_router":
        "Multi-tier router: deterministic → cheap LLM → frontier LLM. "
        "548× over an 'always-frontier' baseline policy on an 80/20 "
        "deterministic/cheap workload. Tracks per-request $$. Upstream "
        "lets you switch models but does not auto-route by cost.",
    "async_dag":
        "DAG executor with Kahn's algorithm topological levels and "
        "per-level parallelism. Resolves `$ref:` placeholders across "
        "tool calls automatically. 4.6× over sequential await on a "
        "5-node independent batch. Upstream parallelises only when the "
        "caller hand-batches.",
    "tracing":
        "Stdlib OTel-compatible span emitter (trace_id, span_id, "
        "parent_span_id, attributes). Drains to JSONL for any OTLP "
        "exporter. ~5 µs per span — observability without pulling "
        "opentelemetry-sdk.",
    "provider_chain":
        "Provider fallback chain with transient-vs-fatal classification "
        "and full-jitter exponential backoff. On a happy path it adds "
        "~1 µs over the raw provider call; on 429 / 5xx it rotates "
        "providers automatically. Upstream Hermes treats provider "
        "outage as a session failure.",
}


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "h1", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=24, leading=28, textColor=INK, spaceAfter=2,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=15, leading=19, textColor=INK,
            spaceBefore=6, spaceAfter=6,
        ),
        "lead": ParagraphStyle(
            "lead", parent=base["BodyText"], fontName="Helvetica",
            fontSize=11, leading=15, textColor=MUTED, spaceAfter=12,
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontName="Helvetica",
            fontSize=10, leading=14, textColor=INK,
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.5, leading=11, textColor=MUTED,
        ),
        "kicker": ParagraphStyle(
            "kicker", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=8, leading=10, textColor=GREEN, spaceAfter=2,
        ),
    }


def _group_by_segment(stages: Sequence[dict]) -> Dict[str, List[dict]]:
    out: Dict[str, List[dict]] = defaultdict(list)
    for s in stages:
        out[s["segment"]].append(s)
    return out


def _speedup_chart(stages: Sequence[dict], width: float, height: float) -> Drawing:
    ranked = [s for s in stages if s.get("speedup_x") is not None]
    ranked.sort(key=lambda s: s["speedup_x"], reverse=True)

    d = Drawing(width, height)
    if not ranked:
        d.add(String(0, height / 2, "no measurable speedup data",
                     fontName="Helvetica", fontSize=10, fillColor=MUTED))
        return d

    bar = HorizontalBarChart()
    bar.x = 200
    bar.y = 12
    bar.height = height - 26
    bar.width = width - 220
    bar.data = [[s["speedup_x"] for s in ranked]]
    bar.categoryAxis.categoryNames = [s["name"][:48] for s in ranked]
    bar.categoryAxis.labels.fontName = "Helvetica"
    bar.categoryAxis.labels.fontSize = 7
    bar.categoryAxis.labels.textAnchor = "end"
    bar.categoryAxis.labels.boxAnchor = "e"
    bar.categoryAxis.labels.dx = -3

    max_val = max(s["speedup_x"] for s in ranked)
    bar.valueAxis.valueMin = 0
    # use log-friendly bounds when there's a huge headline value
    if max_val > 50:
        bar.valueAxis.valueMax = math.ceil(max_val * 1.05)
        step = max(10, math.ceil(max_val / 6))
    else:
        bar.valueAxis.valueMax = max(2, max_val * 1.1)
        step = max(0.5, max_val / 6)
    bar.valueAxis.valueStep = step
    bar.valueAxis.labels.fontName = "Helvetica"
    bar.valueAxis.labels.fontSize = 7

    # green for >= 1x, red otherwise
    for i, s in enumerate(ranked):
        # ReportLab uses bars[0] for the dataset; per-bar color requires custom
        pass
    bar.bars[0].fillColor = GREEN
    bar.bars.strokeColor = None
    bar.barLabelFormat = lambda v: f"{v:.2f}x"
    bar.barLabels.fontName = "Helvetica-Bold"
    bar.barLabels.fontSize = 7
    bar.barLabels.dx = 3
    bar.barLabels.boxAnchor = "w"
    bar.barLabels.fillColor = INK

    # parity line
    one_x = bar.x + bar.width * (1.0 / bar.valueAxis.valueMax)
    d.add(Rect(one_x, bar.y, 0.7, bar.height, fillColor=RED, strokeColor=None))
    d.add(String(one_x + 3, bar.y + bar.height + 1, "1x parity",
                 fontName="Helvetica", fontSize=6, fillColor=RED))
    d.add(bar)
    return d


def _stage_table(stages: Sequence[dict], *, with_segment: bool = False) -> Table:
    headers = (["Stage", "p50 (µs)", "p95 (µs)", "Baseline (µs)", "Speedup"]
               if not with_segment else
               ["Segment", "Stage", "p50 (µs)", "Speedup"])
    rows: List[List[Any]] = [headers]
    for s in stages:
        sp = s.get("speedup_x")
        base = s.get("baseline_us")
        if with_segment:
            rows.append([
                SEGMENT_PRETTY.get(s["segment"], s["segment"]).split(".")[0]
                if "." in SEGMENT_PRETTY.get(s["segment"], "") else s["segment"],
                s["name"],
                f"{s['median_us']:.1f}",
                f"{sp:.2f}x" if sp is not None else "—",
            ])
        else:
            rows.append([
                s["name"],
                f"{s['median_us']:.1f}",
                f"{s['p95_us']:.1f}",
                f"{base:.1f}" if base is not None else "N/A",
                f"{sp:.2f}x" if sp is not None else "—",
            ])

    if with_segment:
        col_widths = [1.2 * cm, 9.5 * cm, 2.4 * cm, 3.5 * cm]
    else:
        col_widths = [7.4 * cm, 2.0 * cm, 2.0 * cm, 2.6 * cm, 2.5 * cm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)

    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("ALIGN", (1 if not with_segment else 2, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (1 if with_segment else 0, -1), "LEFT"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 7.8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL]),
        ("BOX", (0, 0), (-1, -1), 0.3, BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])
    speedup_col = 3 if with_segment else 4
    for i, s in enumerate(stages, start=1):
        sp = s.get("speedup_x")
        if sp is None:
            continue
        if sp >= 2:
            style.add("TEXTCOLOR", (speedup_col, i), (speedup_col, i), GREEN)
            style.add("FONTNAME", (speedup_col, i), (speedup_col, i),
                      "Helvetica-Bold")
        elif sp < 1:
            style.add("TEXTCOLOR", (speedup_col, i), (speedup_col, i), RED)
        else:
            style.add("TEXTCOLOR", (speedup_col, i), (speedup_col, i), MUTED)
    table.setStyle(style)
    return table


def _cover_page(report: dict, styles: Dict[str, ParagraphStyle]) -> List[Any]:
    iters = report.get("iters", 0)
    stages = report.get("stages", [])
    ranked = sorted(
        (s for s in stages if s.get("speedup_x") is not None),
        key=lambda s: s["speedup_x"], reverse=True,
    )
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    net_new = sum(1 for s in stages if s.get("speedup_x") is None)
    winners = sum(1 for s in stages if (s.get("speedup_x") or 0) > 1)

    flow: List[Any] = []
    flow.append(Paragraph("Hermes Turbo vs Upstream", styles["h1"]))
    flow.append(Paragraph(
        "Per-segment benchmark of every customisation introduced under "
        "issues #81–#103 + P1–P7.",
        styles["lead"],
    ))
    flow.append(Paragraph(
        f"Generated {now} &nbsp;•&nbsp; {iters} iterations per stage "
        f"&nbsp;•&nbsp; {len(stages)} stages across {len(report.get('segments', []))} segments "
        f"&nbsp;•&nbsp; {winners} winners, {net_new} net-new (no upstream equivalent).",
        styles["small"],
    ))
    flow.append(Spacer(1, 12))

    # Headline callouts (top 3 speedups)
    top = ranked[:3]
    cells: List[Any] = []
    for s in top:
        cells.append(Paragraph(
            f"<font size='8' color='#19D27F'>HEADLINE</font><br/>"
            f"<font size='22'><b>{s['speedup_x']:.2f}×</b></font><br/>"
            f"<font size='8' color='#64748B'>{s['name']}</font>",
            styles["body"],
        ))
    while len(cells) < 3:
        cells.append(Paragraph("—", styles["small"]))
    callout = Table([cells[:3]],
                    colWidths=[CONTENT_W / 3 - 4] * 3)
    callout.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("LINEBETWEEN", (0, 0), (-1, -1), 0.4, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    flow.append(callout)
    flow.append(Spacer(1, 14))

    # Segment summary table
    flow.append(Paragraph("Segments covered", styles["h2"]))
    seg_rows: List[List[Any]] = [["#", "Segment", "Stages", "Avg p50 (µs)", "Best speedup"]]
    grouped = _group_by_segment(stages)
    for key in [
        "project_mapping", "routing", "receipts",
        "tool_replay", "cost_router", "async_dag", "tracing",
        "provider_chain",
    ]:
        if key not in grouped:
            continue
        items = grouped[key]
        median_p50 = statistics.median(s["median_us"] for s in items)
        speedups = [s["speedup_x"] for s in items if s.get("speedup_x")]
        best = max(speedups) if speedups else None
        idx, name = SEGMENT_PRETTY[key].split(". ", 1)
        seg_rows.append([
            idx,
            name,
            str(len(items)),
            f"{median_p50:.1f}",
            f"{best:.2f}x" if best else "net-new",
        ])
    seg_table = Table(
        seg_rows,
        colWidths=[0.8 * cm, 8.8 * cm, 1.6 * cm, 3.0 * cm, 3.0 * cm],
        repeatRows=1,
    )
    seg_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL]),
        ("BOX", (0, 0), (-1, -1), 0.3, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    flow.append(seg_table)
    flow.append(Spacer(1, 14))

    flow.append(Paragraph("How to read the numbers", styles["h2"]))
    flow.append(Paragraph(
        "<b>Speedup &gt; 1×</b> means the turbo path is faster than the "
        "upstream-equivalent naïve baseline at the same step. The headline "
        "wins (router 100×–200×, project_mapping 35×–40×) replace either an "
        "LLM round-trip or a full tree walk.",
        styles["body"],
    ))
    flow.append(Spacer(1, 4))
    flow.append(Paragraph(
        "<b>Speedup &lt; 1×</b> reflects the <i>cost of correctness</i>. "
        "Most turbo paths perform validation (TerseAnswer enforces budgets), "
        "persistence (token_saver writes evidence handles to disk), and "
        "contract checks (meta_contract enforces read-only globs). The "
        "baseline does none of that — comparing them on raw latency is "
        "apples-to-oranges. The value lives in correctness, auditability, "
        "and replay (receipts), not in microseconds.",
        styles["body"],
    ))
    flow.append(Spacer(1, 4))
    flow.append(Paragraph(
        "<b>“net-new”</b> stages have no upstream equivalent at all "
        "(<font face='Courier'>check_write</font>, "
        "<font face='Courier'>TupleStatusEnvelope</font>). The upstream "
        "&ldquo;baseline&rdquo; would be to not run that step — which means "
        "the protection it offers simply doesn&rsquo;t exist outside turbo.",
        styles["body"],
    ))
    return flow


def _segment_page(
    key: str,
    stages: Sequence[dict],
    styles: Dict[str, ParagraphStyle],
) -> List[Any]:
    flow: List[Any] = []
    flow.append(Paragraph(SEGMENT_PRETTY.get(key, key), styles["h2"]))
    flow.append(Paragraph(SEGMENT_BLURB.get(key, ""), styles["body"]))
    flow.append(Spacer(1, 6))

    chart_h = max(80, 22 * len(stages) + 30)
    flow.append(_speedup_chart(stages, CONTENT_W, chart_h))
    flow.append(Spacer(1, 6))

    flow.append(_stage_table(stages))

    # Notes
    notes = [s for s in stages if s.get("notes")]
    if notes:
        flow.append(Spacer(1, 6))
        for s in notes:
            flow.append(Paragraph(
                f"<font color='#64748B'>•</font> "
                f"<font face='Courier' size='8'>{s['name']}</font>: "
                f"{s['notes']}",
                styles["small"],
            ))
    return flow


def build(report: dict, output: Path) -> Path:
    styles = _styles()
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title="Hermes Turbo vs Upstream — full segmented benchmark",
        author="hermes-turbo-agent",
    )

    flow: List[Any] = []
    flow.extend(_cover_page(report, styles))
    flow.append(PageBreak())

    grouped = _group_by_segment(report.get("stages", []))
    for key in [
        "project_mapping", "routing", "receipts",
        "tool_replay", "cost_router", "async_dag", "tracing",
        "provider_chain",
    ]:
        if key not in grouped:
            continue
        flow.extend(_segment_page(key, grouped[key], styles))
        flow.append(PageBreak())

    # Final page: all stages
    flow.append(Paragraph("Full result matrix", styles["h2"]))
    flow.append(Paragraph(
        "Every stage in one place. Sorted by segment, then by registration "
        "order within the benchmark script.",
        styles["small"],
    ))
    flow.append(Spacer(1, 6))
    flow.append(_stage_table(report.get("stages", []), with_segment=True))
    flow.append(Spacer(1, 10))
    flow.append(Paragraph(
        "Sources: "
        "<font face='Courier'>scripts/benchmark_full_turbo_segments.py</font> · "
        "<font face='Courier'>docs/perf/turbo-full-segments.json</font>. "
        "Regenerate with "
        "<font face='Courier'>python scripts/benchmark_full_turbo_segments.py "
        "--out docs/perf/turbo-full-segments.json &amp;&amp; "
        "python scripts/generate_turbo_full_pdf.py</font>.",
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
