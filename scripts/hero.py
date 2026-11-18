"""Compose the README's hero image — one research document, growing a topic at a time.

Not shipped code. Writes docs/hero.svg, then rasterises it to docs/hero.png with a
headless Chromium (the README shows the PNG: GitHub's `<img>` view of an SVG loads
no fonts). Needs the Inter and DejaVu Sans Mono fonts and Pillow (to crop).

Same drafting-sheet family as the author's other repos, built around the
package's own logo (the book-and-magnifier mark is cropped from
src/research_buddy/images/research-buddy.png and embedded). The sheet carries no
tool version or counts, so nothing on it goes stale on a release.

Usage, from the repository root:

    make hero
"""

from __future__ import annotations

import base64
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image  # type: ignore[import-not-found, unused-ignore]

ROOT = Path(__file__).resolve().parent.parent
LOGO_PNG = ROOT / "src" / "research_buddy" / "images" / "research-buddy.png"
OUT_SVG = ROOT / "docs" / "hero.svg"
OUT_PNG = ROOT / "docs" / "hero.png"

#: The GitHub social-preview size, which the README shows scaled to its column.
W, H = 1280, 640

GROUND = "#f5f7fb"
GRID = "#e3e9f2"
INK = "#14284a"
SOFT = "#3a4d6b"
DIM = "#6b7a92"
FRAME = "#9aa7bd"
CARD = "#ffffff"
NAVY = "#00376f"  # the logo's
ORANGE = "#ff8d0c"  # the logo's
SANS = "Inter, 'DejaVu Sans', sans-serif"
DISPLAY = "'Inter Display', Inter, sans-serif"
MONO = "'DejaVu Sans Mono', monospace"


def text(
    x: float,
    y: float,
    s: str,
    *,
    size: float,
    fill: str = INK,
    family: str = SANS,
    weight: int = 400,
    anchor: str = "start",
    spacing: float = 0,
    italic: bool = False,
) -> str:
    style = ' font-style="italic"' if italic else ""
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
        f'letter-spacing="{spacing}"{style} xml:space="preserve">{escape(s)}</text>'
    )


def sheet() -> list[str]:
    """Grid, border with zone marks, registration marks — the family's drafting sheet."""
    out = [f'<rect width="{W}" height="{H}" fill="{GROUND}"/>']
    for gx in range(0, W, 20):
        width = 0.9 if gx % 100 == 0 else 0.4
        out.append(
            f'<line x1="{gx}" y1="0" x2="{gx}" y2="{H}" stroke="{GRID}" stroke-width="{width}"/>'
        )
    for gy in range(0, H, 20):
        width = 0.9 if gy % 100 == 0 else 0.4
        out.append(
            f'<line x1="0" y1="{gy}" x2="{W}" y2="{gy}" stroke="{GRID}" stroke-width="{width}"/>'
        )
    out.append(
        f'<rect x="16" y="16" width="{W - 32}" height="{H - 32}" fill="none" stroke="{GRID}"/>'
    )
    out.append(
        f'<rect x="30" y="30" width="{W - 60}" height="{H - 60}" fill="none" '
        f'stroke="{FRAME}" stroke-width="1.5"/>'
    )
    zw = (W - 60) / 8
    for i in range(8):
        x = 30 + zw * i
        if i:
            out.append(f'<line x1="{x}" y1="16" x2="{x}" y2="30" stroke="{FRAME}"/>')
            out.append(f'<line x1="{x}" y1="{H - 30}" x2="{x}" y2="{H - 16}" stroke="{FRAME}"/>')
        for ty in (27, H - 19):
            out.append(
                text(x + zw / 2, ty, str(8 - i), size=9, fill=DIM, family=MONO, anchor="middle")
            )
    zh = (H - 60) / 4
    for i in range(4):
        y = 30 + zh * i
        if i:
            out.append(f'<line x1="16" y1="{y}" x2="30" y2="{y}" stroke="{FRAME}"/>')
            out.append(f'<line x1="{W - 30}" y1="{y}" x2="{W - 16}" y2="{y}" stroke="{FRAME}"/>')
        for x in (23, W - 23):
            out.append(
                text(x, y + zh / 2 + 3, "ABCD"[i], size=9, fill=DIM, family=MONO, anchor="middle")
            )
    for cx, cy in ((48, 48), (48, H - 48)):
        out += [
            f'<circle cx="{cx}" cy="{cy}" r="7" fill="none" stroke="{ORANGE}"/>',
            f'<line x1="{cx - 11}" y1="{cy}" x2="{cx + 11}" y2="{cy}" stroke="{ORANGE}"/>',
            f'<line x1="{cx}" y1="{cy - 11}" x2="{cx}" y2="{cy + 11}" stroke="{ORANGE}"/>',
        ]
    return out


def logo_mark() -> str:
    """The book-and-magnifier mark, cropped from the logo (its wordmark is set as text)."""
    with Image.open(LOGO_PNG) as im:
        mark = im.convert("RGBA").crop((50, 41, 150, 129))
        buf = io.BytesIO()
        mark.save(buf, format="PNG")
    data = base64.b64encode(buf.getvalue()).decode()
    return f'<image x="56" y="48" width="100" height="88" href="data:image/png;base64,{data}"/>'


def wordmark() -> list[str]:
    return [
        logo_mark(),
        f'<text x="168" y="118" font-family="{DISPLAY}" font-size="68" font-weight="800" '
        f'letter-spacing="-1.5"><tspan fill="{NAVY}">Research </tspan>'
        f'<tspan fill="{ORANGE}">Buddy</tspan></text>',
        text(66, 178, "A structured AI research collaborator, for any domain.", size=25, fill=SOFT),
        text(
            66,
            206,
            "One versioned document carries the project, the rules and every "
            "finding, session after session.",
            size=15,
            fill=DIM,
        ),
    ]


def title_block() -> list[str]:
    x, y, w, h = 842, 62, 376, 64
    half = w / 2 - 20
    cells = [(0.0, "INSTALL", "pip install research-buddy"), (half + 40, "LICENSE", "MIT")]
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{GROUND}" stroke="{FRAME}" '
        f'stroke-width="1.2"/>',
        f'<line x1="{x}" y1="{y + h / 2 + 4}" x2="{x + w}" y2="{y + h / 2 + 4}" stroke="{FRAME}"/>',
        f'<line x1="{x + half + 40}" y1="{y + h / 2 + 4}" x2="{x + half + 40}" y2="{y + h}" '
        f'stroke="{FRAME}"/>',
        text(x + 10, y + 14, "PROJECT", size=8, fill=DIM, family=MONO, spacing=1.5),
        text(x + 10, y + 30, "research-buddy", size=14, weight=700, family=MONO),
    ]
    for cx, label, value in cells:
        out.append(text(x + cx + 10, y + 47, label, size=8, fill=DIM, family=MONO, spacing=1.5))
        out.append(
            text(x + cx + 10, y + 61, value, size=11, family=MONO, fill=NAVY if cx else ORANGE)
        )
    return out


def caption(x: float, y: float, s: str) -> str:
    return text(x, y, s, size=10, fill=ORANGE, family=MONO, spacing=2, weight=700)


def card(x: float, y: float, w: float, h: float) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{CARD}" stroke="{FRAME}"/>'


#: The source file: frontmatter plus the anchors the validator protects.
SOURCE = [
    ("---", DIM),
    ("title: Heat pumps for an old house", INK),
    ("doc_format_version: 2", INK),
    ("language: en", INK),
    ("---", DIM),
    ("## Open Research Queue", NAVY),
    ("| Q-004 | Ground vs air source |", INK),
    ("<!-- @rule: R-SRC-1 -->", ORANGE),
    ("<!-- @da: DA-002 -->", ORANGE),
    ("## Research Tracker", NAVY),
]


def source() -> list[str]:
    x, y, w, h = 64, 262, 336, 252
    out = [caption(x, y - 12, "THE SOURCE OF TRUTH"), card(x, y, w, h)]
    out.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="6" fill="{NAVY}"/>'
        f'<rect x="{x}" y="{y + 16}" width="{w}" height="10" fill="{NAVY}"/>'
    )
    out.append(
        text(x + 12, y + 17, "project_v1.3-source.md", size=11.5, family=MONO, fill="#ffffff")
    )
    for i, (line, colour) in enumerate(SOURCE):
        out.append(text(x + 14, y + 48 + i * 20, line, size=11.5, family=MONO, fill=colour))
    return out


def turns() -> list[str]:
    """One queue topic per session, in exactly two turns."""
    x, w = 452, 330
    out = [caption(x, 250, "ONE TOPIC PER SESSION · TWO TURNS")]
    boxes = [
        ("TURN 1", "brief, discovery, then stop", "Tier-1 sources · hypotheses pre-registered"),
        ("TURN 2", "write the next version", "queue → tracker · append-only, validated"),
    ]
    for i, (label, head, sub) in enumerate(boxes):
        y = 262 + i * 128
        out += [
            card(x, y, w, 96),
            f'<rect x="{x}" y="{y}" width="5" height="96" rx="2" fill="{ORANGE}"/>',
            text(
                x + 20, y + 26, label, size=10.5, weight=700, family=MONO, fill=ORANGE, spacing=1.5
            ),
            text(x + 20, y + 52, head, size=17, weight=700, fill=INK),
            text(x + 20, y + 76, sub, size=12.5, fill=DIM),
        ]
    # Turn 1 → you bring results → Turn 2.
    out += [
        f'<line x1="{x + 40}" y1="358" x2="{x + 40}" y2="386" stroke="{NAVY}" stroke-width="1.6"/>',
        f'<path d="M{x + 34},380 L{x + 40},388 L{x + 46},380" fill="none" stroke="{NAVY}" '
        f'stroke-width="1.6"/>',
        text(x + 56, 377, "you bring the results back", size=12, fill=NAVY, italic=True),
    ]
    return out


TABS = ["Overview", "Queue", "Tracker", "References"]


def rendered() -> list[str]:
    """The built single-file HTML: one tab per top-level section."""
    x, y, w, h = 834, 262, 384, 252
    out = [caption(x, y - 12, "RENDERED · ONE HTML FILE"), card(x, y, w, h)]
    tx: float = x + 12
    for i, tab in enumerate(TABS):
        tw = len(tab) * 7.2 + 20
        active = i == 2
        out += [
            f'<rect x="{tx}" y="{y + 12}" width="{tw}" height="24" rx="12" '
            f'fill="{NAVY if active else GROUND}" stroke="{NAVY if active else FRAME}"/>',
            text(
                tx + tw / 2,
                y + 28.5,
                tab,
                size=11.5,
                anchor="middle",
                fill="#ffffff" if active else SOFT,
            ),
        ]
        tx += tw + 8
    rows = [
        ("Q-001", "Insulation first?", "settled"),
        ("Q-002", "Radiator sizing", "settled"),
        ("Q-003", "Grants available", "settled"),
        ("Q-004", "Ground vs air source", "in progress"),
    ]
    for i, (qid, topic, state) in enumerate(rows):
        ry = y + 64 + i * 40
        done = state == "settled"
        out += [
            f'<line x1="{x + 12}" y1="{ry + 16}" x2="{x + w - 12}" y2="{ry + 16}" '
            f'stroke="{GRID}"/>',
            text(x + 16, ry + 4, qid, size=11.5, family=MONO, fill=DIM),
            text(x + 76, ry + 4, topic, size=13, fill=INK),
            f'<rect x="{x + w - 104}" y="{ry - 10}" width="88" height="20" rx="10" '
            f'fill="{"#e6f2ea" if done else "#fff1df"}"/>',
            text(
                x + w - 60,
                ry + 4,
                state,
                size=11,
                anchor="middle",
                fill="#2f7d4f" if done else "#b55f00",
            ),
        ]
    out.append(text(x + 16, y + h - 18, "↗ every claim cited, sources tiered", size=11.5, fill=DIM))
    return out


def arrows() -> list[str]:
    out = []
    for x1, x2 in ((404, 446), (786, 828)):
        out += [
            f'<line x1="{x1}" y1="388" x2="{x2 - 6}" y2="388" stroke="{ORANGE}" '
            f'stroke-width="1.6" stroke-dasharray="5 3"/>',
            f'<path d="M{x2 - 9},382 L{x2},388 L{x2 - 9},394" fill="none" stroke="{ORANGE}" '
            f'stroke-width="1.6"/>',
        ]
    return out


def strip() -> list[str]:
    items = [
        ("any domain", "the agent proposes the structure"),
        ("any chatbot", "upload one file, no setup"),
        ("never loses work", "validate --prior checks it"),
    ]
    x0, y, w, h, gap = 64, 548, 376, 40, 9
    out = []
    for i, (name, sub) in enumerate(items):
        x = x0 + i * (w + gap)
        out += [
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{CARD}" '
            f'stroke="{FRAME}" stroke-width="0.8"/>',
            f'<rect x="{x}" y="{y}" width="4" height="{h}" rx="2" fill="{NAVY}"/>',
            text(x + 16, y + 25, name, size=12.5, weight=700, family=MONO, fill=NAVY),
            text(x + 16 + len(name) * 7.6 + 10, y + 25, sub, size=12, fill=SOFT),
        ]
    return out


def svg() -> str:
    parts = sheet() + wordmark() + title_block() + source() + turns() + rendered()
    parts += arrows() + strip()
    body = "\n  ".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">\n  {body}\n</svg>\n'
    )


def chromium() -> str:
    for candidate in (
        os.environ.get("CHROMIUM"),
        "/opt/pw-browsers/chromium",
        shutil.which("chromium"),
        shutil.which("google-chrome"),
    ):
        if candidate and Path(candidate).exists():
            return candidate
    sys.exit("hero: no Chromium found; set CHROMIUM=/path/to/chrome")


def main() -> None:
    OUT_SVG.write_text(svg())
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "hero.html"
        page.write_text(f'<html><body style="margin:0;overflow:hidden">{svg()}</body></html>')
        subprocess.run(
            [
                chromium(),
                "--headless=new",
                "--no-sandbox",
                "--hide-scrollbars",
                "--force-device-scale-factor=2",
                f"--window-size={W},{H + 200}",
                f"--screenshot={OUT_PNG}",
                page.as_uri(),
            ],
            check=True,
            capture_output=True,
        )
    # Headless Chromium's viewport is shorter than its window: shoot tall, then crop.

    with Image.open(OUT_PNG) as shot:
        shot.crop((0, 0, W * 2, H * 2)).save(OUT_PNG, optimize=True)
    print(f"wrote {OUT_SVG.relative_to(ROOT)} and {OUT_PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
