"""`cdm chart`: a static SVG line chart of the monthly mart, for the README.

Pure Python, no plotting library: one SVG file that GitHub renders as an image. The three
series share one unit (percent), so they share one axis. Colours are the first three slots of
a palette validated for colour-blind readers; the legend names every line, so identity never
depends on colour alone. The SVG switches to dark colours with the viewer's system setting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import duckdb

QUERY = """
SELECT month_start, policy_rate_end_of_month, cpi_ontario_yoy_pct, unemployment_rate_ontario
FROM marts.mart_monthly_indicators
ORDER BY month_start
"""


@dataclass(frozen=True)
class Line:
    key: str  # CSS class suffix
    label: str
    points: list[tuple[date, float | None]]


WIDTH, HEIGHT = 800, 396
LEFT, RIGHT, TOP, BOTTOM = 48, 24, 92, 68

STYLE = """
.bg { fill: #fcfcfb; }
.title { fill: #0b0b0b; font: 600 16px system-ui, -apple-system, 'Segoe UI', sans-serif; }
.text { fill: #52514e; font: 12px system-ui, -apple-system, 'Segoe UI', sans-serif; }
.grid { stroke: #e6e5e0; stroke-width: 1; }
.axis { stroke: #c3c2b7; stroke-width: 1; }
.line { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.dot { stroke: #fcfcfb; stroke-width: 2; }
.s1 { stroke: #2a78d6; } .f1 { fill: #2a78d6; }
.s2 { stroke: #eb6834; } .f2 { fill: #eb6834; }
.s3 { stroke: #1baf7a; } .f3 { fill: #1baf7a; }
@media (prefers-color-scheme: dark) {
  .bg { fill: #1a1a19; }
  .title { fill: #f0efec; }
  .text { fill: #c3c2b7; }
  .grid { stroke: #2e2e2c; }
  .axis { stroke: #52514e; }
  .dot { stroke: #1a1a19; }
  .s1 { stroke: #3987e5; } .f1 { fill: #3987e5; }
  .s2 { stroke: #d95926; } .f2 { fill: #d95926; }
  .s3 { stroke: #199e70; } .f3 { fill: #199e70; }
}
"""


def load_lines(con: duckdb.DuckDBPyConnection) -> list[Line]:
    rows = con.execute(QUERY).fetchall()
    as_float = lambda v: None if v is None else float(v)  # noqa: E731
    return [
        Line("1", "Policy rate, Bank of Canada",
             [(r[0], as_float(r[1])) for r in rows]),
        Line("2", "Inflation, Ontario (CPI y/y)",
             [(r[0], as_float(r[2])) for r in rows]),
        Line("3", "Unemployment, Ontario", [(r[0], as_float(r[3])) for r in rows]),
    ]  # fmt: skip


def render(lines: list[Line], as_of: date) -> str:
    months = sorted({d for line in lines for d, _ in line.points})
    values = [v for line in lines for _, v in line.points if v is not None]
    if not months or not values:
        raise ValueError("The mart is empty; run `uv run cdm run` first.")
    y_min = min(0.0, math.floor(min(values) / 2) * 2)
    y_max = math.ceil(max(values) / 2) * 2
    plot_w, plot_h = WIDTH - LEFT - RIGHT, HEIGHT - TOP - BOTTOM
    index = {m: i for i, m in enumerate(months)}
    x = lambda m: LEFT + plot_w * index[m] / max(1, len(months) - 1)  # noqa: E731
    y = lambda v: TOP + plot_h * (y_max - v) / (y_max - y_min)  # noqa: E731

    first, last = months[0], months[-1]
    title = f"Ontario inflation, unemployment and the policy rate, {first.year}-{last.year} (%)"
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'width="{WIDTH}" height="{HEIGHT}" role="img" aria-labelledby="t d">',
        f'<title id="t">{escape(title)}</title>',
        f'<desc id="d">Monthly values from {first:%Y-%m} to {last:%Y-%m}, '
        f"from marts.mart_monthly_indicators, generated on {as_of.isoformat()}.</desc>",
        f"<style>{STYLE}</style>",
        f'<rect class="bg" width="{WIDTH}" height="{HEIGHT}" rx="8"/>',
        f'<text class="title" x="{LEFT}" y="30">{escape(title)}</text>',
    ]
    # Legend: one row under the title, a short line-key per series.
    lx = LEFT
    for line in lines:
        out.append(
            f'<line class="line s{line.key}" x1="{lx:.0f}" y1="56" x2="{lx + 18:.0f}" y2="56"/>'
            f'<text class="text" x="{lx + 24:.0f}" y="60">{escape(line.label)}</text>'
        )
        lx += 24 + 6.6 * len(line.label) + 32
    # Horizontal gridlines with percent labels.
    for tick in range(int(y_min), int(y_max) + 1, 2):
        ty = y(tick)
        cls = "axis" if tick == 0 else "grid"
        out.append(f'<line class="{cls}" x1="{LEFT}" y1="{ty:.1f}" x2="{WIDTH - RIGHT}" '
                   f'y2="{ty:.1f}"/>')  # fmt: skip
        out.append(f'<text class="text" x="{LEFT - 8}" y="{ty + 4:.1f}" '
                   f'text-anchor="end">{tick}</text>')  # fmt: skip
    # Year labels on January.
    for m in months:
        if m.month == 1:
            out.append(f'<text class="text" x="{x(m):.1f}" y="{HEIGHT - BOTTOM + 20}" '
                       f'text-anchor="middle">{m.year}</text>')  # fmt: skip
    # Lines, broken where a value is missing; an end dot on the last value.
    for line in lines:
        segments, current = [], []
        for m, v in line.points:
            if v is None:
                if current:
                    segments.append(current)
                current = []
            else:
                current.append(f"{x(m):.1f},{y(v):.1f}")
        if current:
            segments.append(current)
        for seg in segments:
            out.append(f'<polyline class="line s{line.key}" points="{" ".join(seg)}"/>')
        known = [(m, v) for m, v in line.points if v is not None]
        if known:
            m, v = known[-1]
            out.append(f'<circle class="dot f{line.key}" cx="{x(m):.1f}" cy="{y(v):.1f}" r="4"/>')
    out.append(
        f'<text class="text" x="{LEFT}" y="{HEIGHT - 28}">Sources: Bank of Canada (Valet API); '
        "Statistics Canada, tables 18-10-0004-01 and 14-10-0287-01.</text>"
        f'<text class="text" x="{LEFT}" y="{HEIGHT - 12}">Generated by this pipeline on '
        f"{as_of.isoformat()} with uv run cdm chart.</text>"
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def write(con: duckdb.DuckDBPyConnection, path: Path, as_of: date) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(load_lines(con), as_of), encoding="utf-8")
    return path
