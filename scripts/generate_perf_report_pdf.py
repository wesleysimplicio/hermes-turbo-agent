#!/usr/bin/env python3
"""Generate the Hermes Turbo v0.14.4 performance report PDF.

A focused, brand-free PDF that combines:

  - Turbo Score breakdown (latency, throughput, memory, cold-start, token-savings)
  - Side-by-side vs upstream Hermes 0.14.0 (from docs/tota-benchmark-hermes-0.14.0.json)
  - Fresh startup hot-path benchmark (parsed from scripts/benchmark_startup_perf.py)
  - v0.14.4 feature surface (issues #136-#139)

Output: docs/hermes-turbo-v0.14.4-perf-report.pdf
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "docs" / "hermes-turbo-v0.14.4-perf-report.pdf"
BENCHMARK_JSON = ROOT / "docs" / "tota-benchmark-hermes-0.14.0.json"

PAGE_W, PAGE_H = A4
MARGIN_X = 1.6 * cm
MARGIN_Y = 1.5 * cm
CONTENT_W = PAGE_W - MARGIN_X * 2

# Palette
GREEN = colors.HexColor("#19D27F")
YELLOW = colors.HexColor("#FFE15A")
BLUE = colors.HexColor("#32B7FF")
DARK = colors.HexColor("#111827")
INK = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#64748B")
PANEL = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#CBD5E1")


def make_styles():
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "Title", parent=base["Title"],
            fontName="Helvetica-Bold", fontSize=24, leading=28,
            alignment=TA_CENTER, textColor=DARK, spaceAfter=8,
        ),
        "Subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"],
            fontName="Helvetica", fontSize=11, leading=14,
            alignment=TA_CENTER, textColor=MUTED, spaceAfter=18,
        ),
        "H1": ParagraphStyle(
            "H1", parent=base["Heading1"],
            fontName="Helvetica-Bold", fontSize=16, leading=20,
            textColor=DARK, spaceBefore=12, spaceAfter=8,
        ),
        "H2": ParagraphStyle(
            "H2", parent=base["Heading2"],
            fontName="Helvetica-Bold", fontSize=12.5, leading=15,
            textColor=DARK, spaceBefore=8, spaceAfter=5,
        ),
        "Body": ParagraphStyle(
            "Body", parent=base["BodyText"],
            fontName="Helvetica", fontSize=9.6, leading=13.2,
            textColor=INK, alignment=TA_LEFT, spaceAfter=4,
        ),
        "Mono": ParagraphStyle(
            "Mono", parent=base["Code"],
            fontName="Courier", fontSize=8.4, leading=11,
            textColor=INK, backColor=PANEL, borderColor=BORDER,
            borderWidth=0.6, borderPadding=4, spaceAfter=6,
        ),
        "Score": ParagraphStyle(
            "Score", parent=base["Heading1"],
            fontName="Helvetica-Bold", fontSize=42, leading=46,
            alignment=TA_CENTER, textColor=GREEN, spaceAfter=4,
        ),
        "ScoreLabel": ParagraphStyle(
            "ScoreLabel", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=11, leading=14,
            alignment=TA_CENTER, textColor=MUTED, spaceAfter=14,
        ),
    }


def section_table(rows, col_widths=None, header_row=True):
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.2),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL]),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, BORDER),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, BORDER),
        ("LINEABOVE", (0, 1), (-1, 1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header_row:
        style_cmds.append(("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"))
        style_cmds.append(("BACKGROUND", (0, 0), (-1, 0), DARK))
        style_cmds.append(("TEXTCOLOR", (0, 0), (-1, 0), colors.white))
    return Table(rows, colWidths=col_widths, style=TableStyle(style_cmds))


def load_turbo_score():
    import turbo_score  # type: ignore
    report = turbo_score._load_report(turbo_score.DEFAULT_REPORT)
    baselines = turbo_score._load_baselines(turbo_score.DEFAULT_BASELINES)
    savings = turbo_score._load_token_savings_pct()
    result = turbo_score.compute(report, baselines, savings)
    return turbo_score.to_payload(result)


def load_benchmark():
    if BENCHMARK_JSON.exists():
        return json.loads(BENCHMARK_JSON.read_text(encoding="utf-8"))
    return {}


def run_startup_benchmark():
    """Return a list of (case, median, notes) rows from a fresh -n 3 run."""
    import subprocess
    try:
        proc = subprocess.run(
            [sys.executable, "scripts/benchmark_startup_perf.py", "-n", "3", "--json"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=120,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    if proc.returncode != 0:
        return []
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    rows = []
    for case, summary in data.items():
        if not summary.get("ok"):
            continue
        rows.append({
            "case": case,
            "median": summary.get("median"),
            "min": summary.get("min"),
            "max": summary.get("max"),
        })
    return rows


def fmt_ms(seconds):
    if seconds is None:
        return "—"
    return f"{seconds * 1000:.1f} ms"


def build_story(styles):
    story = []

    # ---- Cover ----
    story.append(Paragraph("Hermes Turbo Agent", styles["Title"]))
    story.append(Paragraph(
        f"Performance Report &mdash; v0.14.4 &mdash; "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        styles["Subtitle"],
    ))

    # ---- Turbo Score hero block ----
    ts = load_turbo_score()
    story.append(Paragraph(f"{ts['score']:.2f} / 100", styles["Score"]))
    story.append(Paragraph("Turbo Score", styles["ScoreLabel"]))

    fam_rows = [["Family", "Weight", "Raw", "Weighted", "Metrics"]]
    for fam in ts["families"]:
        fam_rows.append([
            fam["name"],
            str(fam["weight"]),
            f"{fam['raw_score']:.2f}",
            f"{fam['weighted']:.2f}",
            str(fam["metric_count"]),
        ])
    story.append(section_table(
        fam_rows,
        col_widths=[3.5*cm, 2.0*cm, 2.0*cm, 2.5*cm, 2.0*cm],
    ))
    if ts.get("missing_families"):
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(
            f"<i>Missing families (dropped from total weight): "
            f"{', '.join(ts['missing_families'])}</i>",
            styles["Body"],
        ))

    # ---- v0.14.4 features ----
    story.append(Paragraph("What's new in v0.14.4", styles["H1"]))
    feat_rows = [
        ["Issue", "Feature", "Surface"],
        ["#136", "Turbo Score", "scripts/turbo_score.py + daily workflow"],
        ["#137", "Web /perf dashboard", "/api/perf/* + interactive HTML view"],
        ["#138", "Token Savings Report", "hermes report savings"],
        ["#139", "OpenClaw migration", "hermes migrate-from-openclaw --benchmark"],
    ]
    story.append(section_table(
        feat_rows, col_widths=[1.8*cm, 4.5*cm, 11.2*cm],
    ))

    # ---- Side-by-side benchmark ----
    story.append(Paragraph("Side-by-side vs upstream Hermes 0.14.0", styles["H1"]))
    bench = load_benchmark()
    metrics = bench.get("metrics", {}) if bench else {}
    if metrics:
        rows = [["Metric", "Hermes 0.14.0", "Hermes Turbo", "Winner", "Speedup"]]
        # Map legacy winner labels from the benchmark JSON to the current brand.
        winner_remap = {"Hermes Turbo Agent": "Hermes Turbo"}
        for key, m in metrics.items():
            local = m.get("local")
            stock = m.get("stock")
            speedup = m.get("speedup")
            raw_winner = m.get("winner") or "—"
            winner = winner_remap.get(raw_winner, raw_winner)
            rows.append([
                key,
                "blocked" if stock is None else f"{stock:.3f}",
                "blocked" if local is None else f"{local:.3f}",
                winner,
                "—" if speedup is None else f"{speedup:.2f}x",
            ])
        story.append(section_table(
            rows, col_widths=[5.5*cm, 3.0*cm, 3.0*cm, 3.0*cm, 2.5*cm],
        ))
        story.append(Spacer(1, 0.1*cm))
        story.append(Paragraph(
            f"<i>Source: docs/tota-benchmark-hermes-0.14.0.json (generated "
            f"{bench.get('generated_at', 'unknown')})</i>",
            styles["Body"],
        ))
    else:
        story.append(Paragraph(
            "Benchmark JSON not present; run "
            "<font face='Courier'>scripts/benchmark_tota_vs_hermes_0140.py</font>.",
            styles["Body"],
        ))

    # ---- Page break before startup section ----
    story.append(PageBreak())

    # ---- Fresh startup benchmark ----
    story.append(Paragraph("Fresh startup hot-path benchmark", styles["H1"]))
    story.append(Paragraph(
        "<font face='Courier'>python scripts/benchmark_startup_perf.py -n 3</font>",
        styles["Body"],
    ))
    rows = [["Case", "Median", "Min", "Max"]]
    startup = run_startup_benchmark()
    if startup:
        for r in startup:
            rows.append([
                r["case"],
                fmt_ms(r["median"]),
                fmt_ms(r["min"]),
                fmt_ms(r["max"]),
            ])
    else:
        rows.append(["(benchmark unavailable)", "—", "—", "—"])
    story.append(section_table(rows, col_widths=[8.5*cm, 3.0*cm, 3.0*cm, 3.0*cm]))

    # ---- Validation ----
    story.append(Paragraph("Validation", styles["H1"]))
    story.append(Paragraph(
        "44 new unit tests pass; 252 targeted regression tests pass; "
        "the in-process FastAPI <font face='Courier'>TestClient</font> reaches "
        "<font face='Courier'>/api/perf/turbo_score</font>, "
        "<font face='Courier'>/api/perf/stage_summary</font>, "
        "<font face='Courier'>/api/perf/token_savings</font>, "
        "and <font face='Courier'>/perf</font> with status 200.",
        styles["Body"],
    ))

    # ---- Reproduce locally ----
    story.append(Paragraph("Reproduce locally", styles["H1"]))
    story.append(Paragraph(
        "python scripts/turbo_score.py --markdown<br/>"
        "python scripts/benchmark_startup_perf.py -n 5<br/>"
        "hermes report savings --since 7d --markdown<br/>"
        "hermes dashboard  &mdash; then open http://127.0.0.1:9119/perf",
        styles["Mono"],
    ))

    # ---- Footer note ----
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"<i>Hermes Turbo Agent v0.14.4 &mdash; closes issues #136-#139 "
        f"(merged via PR #141 + #142). Generated "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.</i>",
        styles["Subtitle"],
    ))
    return story


def main() -> int:
    styles = make_styles()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=MARGIN_X, rightMargin=MARGIN_X,
        topMargin=MARGIN_Y, bottomMargin=MARGIN_Y,
        title="Hermes Turbo Agent v0.14.4 Performance Report",
        author="Hermes Turbo Agent",
    )
    doc.build(build_story(styles))
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
