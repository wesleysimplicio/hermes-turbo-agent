#!/usr/bin/env python3
"""Generate Tota Agent benchmark battle cards as SVG and PNG assets."""

from __future__ import annotations

import argparse
import base64
import html
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs/assets/tota-benchmark/battles"
LOGO_PATH = ROOT / "docs/assets/tota-brand/tota-agent-founder-logo.jpg"


@dataclass(frozen=True)
class Competitor:
    name: str
    value: str
    numeric: float | None
    color: str
    accent: str


@dataclass(frozen=True)
class Battle:
    slug: str
    eyebrow: str
    title: str
    rule: str
    winner: str
    note: str
    competitors: tuple[Competitor, Competitor, Competitor]


HERMES = ("Hermes Agent", "#32B7FF", "#9ED8FF")
TOTA = ("Tota Agent", "#19D27F", "#FFE15A")
OPENCLAW = ("OpenClaw", "#FF4655", "#FFB3BD")


def c(agent: tuple[str, str, str], value: str, numeric: float | None) -> Competitor:
    return Competitor(agent[0], value, numeric, agent[1], agent[2])


BATTLES: tuple[Battle, ...] = (
    Battle(
        "00-scoreboard",
        "Benchmark Battle 00",
        "Final Scoreboard",
        "Higher score wins",
        "Tota Agent",
        "Tota wins the full measured report: 44 / 50.",
        (c(HERMES, "30 / 50", 30), c(TOTA, "44 / 50", 44), c(OPENCLAW, "36 / 50", 36)),
    ),
    Battle(
        "01-json-dumps-large",
        "Benchmark Battle 01",
        "Large JSON Dumps",
        "Lower latency wins",
        "Tota Agent",
        "Tota is 5.8x faster than Hermes on the large dump path.",
        (c(HERMES, "18.40 us", 18.40), c(TOTA, "3.20 us", 3.20), c(OPENCLAW, "5.80 us", 5.80)),
    ),
    Battle(
        "02-json-loads-large",
        "Benchmark Battle 02",
        "Large JSON Loads",
        "Lower latency wins",
        "Tota Agent",
        "Tota keeps the Python path fast with orjson.",
        (c(HERMES, "12.80 us", 12.80), c(TOTA, "2.80 us", 2.80), c(OPENCLAW, "5.20 us", 5.20)),
    ),
    Battle(
        "03-medium-message-pipeline",
        "Benchmark Battle 03",
        "Medium Message Pipeline",
        "Lower latency wins",
        "Tota Agent",
        "Tota cuts the Hermes-compatible message path to 2.20 us.",
        (c(HERMES, "7.50 us", 7.50), c(TOTA, "2.20 us", 2.20), c(OPENCLAW, "3.46 us", 3.46)),
    ),
    Battle(
        "04-medium-message-throughput",
        "Benchmark Battle 04",
        "Medium Message Throughput",
        "Higher throughput wins",
        "Tota Agent",
        "Tota pushes the medium pipeline to 454k msg/s.",
        (c(HERMES, "133k msg/s", 133), c(TOTA, "454k msg/s", 454), c(OPENCLAW, "289k msg/s", 289)),
    ),
    Battle(
        "05-tool-call-typed-parse",
        "Benchmark Battle 05",
        "Tool-Call Typed Parse",
        "Lower latency wins",
        "Tota Agent",
        "Tota owns the typed tool-call path; Hermes and OpenClaw do not expose the same measured typed path.",
        (c(HERMES, "Error / N/A", None), c(TOTA, "0.45 us", 0.45), c(OPENCLAW, "N/A", None)),
    ),
    Battle(
        "06-async-1000-tasks",
        "Benchmark Battle 06",
        "Async 1,000 Tasks",
        "Lower latency wins",
        "OpenClaw",
        "OpenClaw wins pure scheduler latency here; Tota still improves Hermes.",
        (c(HERMES, "2.50 ms", 2.50), c(TOTA, "1.40 ms", 1.40), c(OPENCLAW, "0.08 ms", 0.08)),
    ),
    Battle(
        "07-cold-start",
        "Benchmark Battle 07",
        "Cold Start",
        "Lower startup time wins",
        "Tota Agent",
        "Tota stays serverless-friendly at roughly 50 ms.",
        (c(HERMES, "~52 ms", 52), c(TOTA, "~50 ms", 50), c(OPENCLAW, "~280 ms", 280)),
    ),
    Battle(
        "08-rss-memory",
        "Benchmark Battle 08",
        "RSS Memory",
        "Lower memory wins",
        "Python variants",
        "Tota keeps Hermes-class memory while OpenClaw carries a larger Node footprint.",
        (c(HERMES, "~30 MB", 30), c(TOTA, "~30 MB", 30), c(OPENCLAW, "~97 MB", 97)),
    ),
)


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def logo_href() -> str:
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def bar_scores(battle: Battle) -> dict[str, float]:
    numeric = [item.numeric for item in battle.competitors if item.numeric is not None]
    if not numeric:
        return {item.name: 0 for item in battle.competitors}
    if "Lower" in battle.rule:
        best = min(numeric)
        return {
            item.name: (best / item.numeric if item.numeric else 0)
            for item in battle.competitors
        }
    worst = max(numeric)
    return {
        item.name: (item.numeric / worst if item.numeric else 0)
        for item in battle.competitors
    }


def agent_icon(item: Competitor, idx: int, logo_data: str) -> str:
    x = 120 + idx * 450
    if item.name == "Tota Agent":
        return f"""
        <g transform="translate({x} 244)">
          <circle cx="80" cy="80" r="78" fill="#0b1220" stroke="url(#totaGlow)" stroke-width="8"/>
          <clipPath id="totaClip"><circle cx="80" cy="80" r="68"/></clipPath>
          <image href="{logo_data}" x="12" y="12" width="136" height="136" preserveAspectRatio="xMidYMid slice" clip-path="url(#totaClip)"/>
          <circle cx="80" cy="80" r="68" fill="none" stroke="#FFE15A" stroke-width="3" opacity="0.8"/>
        </g>
        """
    if item.name == "Hermes Agent":
        return f"""
        <g transform="translate({x} 244)">
          <circle cx="80" cy="80" r="74" fill="#071522" stroke="#32B7FF" stroke-width="6"/>
          <path d="M40 96 C66 48 111 43 128 82 C103 73 85 84 74 119 C63 109 52 101 40 96 Z" fill="#9ED8FF"/>
          <text x="80" y="96" text-anchor="middle" fill="#ffffff" font-family="Helvetica" font-size="72" font-weight="900">H</text>
        </g>
        """
    return f"""
    <g transform="translate({x} 244)">
      <circle cx="80" cy="80" r="74" fill="#1a0710" stroke="#FF4655" stroke-width="6"/>
      <path d="M42 42 L118 118 M118 42 L42 118" stroke="#FF4655" stroke-width="16" stroke-linecap="round"/>
      <path d="M54 126 C88 100 106 100 132 126" fill="none" stroke="#FFB3BD" stroke-width="8" stroke-linecap="round"/>
    </g>
    """


def render_svg(battle: Battle) -> str:
    scores = bar_scores(battle)
    logo_data = logo_href()
    note_lines = textwrap.wrap(battle.note, width=54)[:2]
    note_svg = "".join(
        f'<text x="936" y="{770 + i * 22}" fill="#c6d8ef" font-family="Helvetica" font-size="20" font-weight="800">{esc(line)}</text>'
        for i, line in enumerate(note_lines)
    )
    cards = []
    for idx, item in enumerate(battle.competitors):
        x = 90 + idx * 450
        score = max(0.06, min(scores[item.name], 1.0))
        bar_width = 310 * score
        is_winner = item.name == battle.winner or (battle.winner == "Python variants" and item.name in {"Hermes Agent", "Tota Agent"})
        badge = (
            f'<rect x="224" y="30" width="116" height="34" rx="17" fill="{item.color}" opacity="0.22" stroke="{item.color}" stroke-width="2"/>'
            f'<text x="282" y="53" text-anchor="middle" fill="{item.accent}" font-family="Helvetica" font-size="17" font-weight="900">WINNER</text>'
            if is_winner
            else ""
        )
        cards.append(
            f"""
            <g transform="translate({x} 438)">
              <rect x="0" y="0" width="370" height="238" rx="26" fill="#071522" stroke="{item.color}" stroke-width="3" opacity="0.96"/>
              <text x="30" y="58" fill="{item.accent}" font-family="Helvetica" font-size="24" font-weight="900" letter-spacing="2">{esc(item.name.upper())}</text>
              <text x="30" y="124" fill="#ffffff" font-family="Helvetica" font-size="44" font-weight="900">{esc(item.value)}</text>
              <rect x="30" y="158" width="310" height="18" rx="9" fill="#17314e"/>
              <rect x="30" y="158" width="{bar_width:.1f}" height="18" rx="9" fill="{item.color}"/>
              <text x="30" y="210" fill="#b9c8dc" font-family="Helvetica" font-size="18" font-weight="700">Measured report value</text>
              {badge}
            </g>
            {agent_icon(item, idx, logo_data)}
            """
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img" aria-labelledby="title desc">
  <title id="title">{esc(battle.title)} comparison battle card</title>
  <desc id="desc">Tota Agent, Hermes Agent, and OpenClaw comparison card generated from the Tota Agent benchmark report.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#030712"/>
      <stop offset="0.5" stop-color="#07111f"/>
      <stop offset="1" stop-color="#130514"/>
    </linearGradient>
    <linearGradient id="totaGlow" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#19D27F"/>
      <stop offset="0.45" stop-color="#FFE15A"/>
      <stop offset="1" stop-color="#32B7FF"/>
    </linearGradient>
    <pattern id="grid" width="72" height="72" patternUnits="userSpaceOnUse">
      <path d="M72 0H0V72" fill="none" stroke="#1a2c44" stroke-width="1" opacity="0.45"/>
    </pattern>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">
      <feDropShadow dx="0" dy="20" stdDeviation="20" flood-color="#000000" flood-opacity="0.55"/>
    </filter>
  </defs>
  <rect width="1600" height="900" fill="url(#bg)"/>
  <rect width="1600" height="900" fill="url(#grid)" opacity="0.75"/>
  <path d="M-70 690 C250 526 438 790 704 594 C960 405 1120 474 1680 194 L1680 900 L-70 900 Z" fill="#0b1b33" opacity="0.72"/>
  <path d="M0 670 C284 548 430 722 684 584 C950 438 1076 470 1600 280" fill="none" stroke="url(#totaGlow)" stroke-width="7" opacity="0.72"/>

  <g filter="url(#shadow)">
    <rect x="72" y="66" width="1456" height="128" rx="34" fill="#06101d" stroke="#243f5b" stroke-width="3"/>
    <text x="112" y="116" fill="#FFE15A" font-family="Helvetica" font-size="27" font-weight="900" letter-spacing="4">{esc(battle.eyebrow.upper())}</text>
    <text x="112" y="165" fill="#ffffff" font-family="Helvetica" font-size="46" font-weight="900">{esc(battle.title)}</text>
    <text x="1062" y="115" fill="#d7fff2" font-family="Helvetica" font-size="26" font-weight="900" letter-spacing="3">TOTA AGENT</text>
    <text x="1064" y="154" fill="#FFE15A" font-family="Helvetica" font-size="19" font-weight="900" letter-spacing="3">BY HERMES AGENT</text>
  </g>

  <g>
    <rect x="72" y="706" width="1456" height="88" rx="28" fill="#071522" stroke="#23415f" stroke-width="2"/>
    <text x="112" y="742" fill="#9ed8ff" font-family="Helvetica" font-size="19" font-weight="900" letter-spacing="2">RULE</text>
    <text x="112" y="774" fill="#ffffff" font-family="Helvetica" font-size="28" font-weight="900">{esc(battle.rule)}</text>
    <text x="524" y="742" fill="#19D27F" font-family="Helvetica" font-size="19" font-weight="900" letter-spacing="2">BATTLE RESULT</text>
    <text x="524" y="774" fill="#ffffff" font-family="Helvetica" font-size="28" font-weight="900">{esc(battle.winner)} wins</text>
    <text x="936" y="742" fill="#FFE15A" font-family="Helvetica" font-size="19" font-weight="900" letter-spacing="2">NOTE</text>
    {note_svg}
  </g>

  <g filter="url(#shadow)">
    {''.join(cards)}
  </g>

  <text x="80" y="838" fill="#7f93ad" font-family="Helvetica" font-size="16" font-weight="700">Source: Tota Agent benchmark report linked in README, May 17 2026.</text>
  <text x="80" y="866" fill="#7f93ad" font-family="Helvetica" font-size="16" font-weight="700">Runtime caveat: Hermes CPython 3.14, Tota CPython 3.11.14, OpenClaw Node.js 22. Once you're Tota, you'll never be OpenClaw.</text>
</svg>
"""


def write_cards() -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for battle in BATTLES:
        path = OUT_DIR / f"{battle.slug}.svg"
        svg = "\n".join(line.rstrip() for line in render_svg(battle).splitlines()) + "\n"
        path.write_text(svg, encoding="utf-8")
        paths.append(path)
    return paths


def render_pngs(svg_paths: list[Path]) -> None:
    for path in svg_paths:
        png_path = path.with_suffix(".png")
        subprocess.run(
            [
                "npx",
                "-y",
                "@resvg/resvg-js-cli",
                "--fit-width",
                "1600",
                "--text-rendering",
                "1",
                "--shape-rendering",
                "2",
                str(path),
                str(png_path),
            ],
            cwd=ROOT,
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true", help="Render PNG files with resvg-js.")
    args = parser.parse_args()
    paths = write_cards()
    if args.render:
        render_pngs(paths)
    print(f"Generated {len(paths)} SVG battle cards in {OUT_DIR}")


if __name__ == "__main__":
    main()
