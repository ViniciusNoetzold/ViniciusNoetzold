#!/usr/bin/env python3
"""
Generate an animated Neofetch-style terminal info card SVG.
Matches the aesthetic and proportions of the ASCII portrait window.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "info-card.svg")

STATIC = bool(os.environ.get("STATIC"))

# Canvas sizing to match the portrait aspect ratio when displayed at 490px wide
CANVAS_W = 620
CANVAS_H = 460

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"

# Colors
C_USER = "#58a6ff"
C_AT = "#8b949e"
C_HOST = "#bc8cff"
C_KEY = "#79c0ff"
C_SEP = "#8b949e"
C_VAL = "#c9d1d9"
C_ACCENT = "#56d364"
C_GOLD = "#e3b341"
C_CYAN = "#39c5cf"
C_PINK = "#f0883e"

# Terminal color blocks (neofetch style)
PALETTE_COLORS = [
    "#484f58", "#ff7b72", "#3fb950", "#d29922",
    "#58a6ff", "#bc8cff", "#39c5cf", "#f0f6fc"
]

INFO_ROWS = [
    ("Title", "Vinícius de Almeida Noetzold", C_GOLD),
    ("Role", "Tech Support Analyst @ Hansen Software", C_VAL),
    ("Education", "B.S. in Computer Science (Student)", C_VAL),
    ("Focus", "Systems, APIs, Automation, QA & AI", C_CYAN),
    ("Languages", "Python, Java, TypeScript, JavaScript, SQL", C_ACCENT),
    ("Backend", "Spring Boot, Fastify, Node.js, REST APIs", C_VAL),
    ("Data & Tools", "PostgreSQL, Redis, SQLite, Docker, Git", C_VAL),
    ("Highlights", "Mezzold Connect, YouTube Trend, QuotePRO, EduSystem", C_PINK),
    ("Status", "Connecting Support, Dev and Quality", C_ACCENT),
]

def build_svg():
    parts = []
    
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
        f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
    )
    
    # Styles and animations
    css = """
    @keyframes lineIn {
      0%   { opacity: 0; transform: translateY(4px); }
      100% { opacity: 1; transform: translateY(0); }
    }
    .line {
      animation: lineIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) both;
    }
    """
    if STATIC:
        css = ".line { opacity: 1; }"
        
    parts.append(f'<style>{css}</style>')
    
    # Gradient definition
    parts.append(
        '<defs>'
        f'<linearGradient id="card-bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/>'
        f'<stop offset="1" stop-color="{BG}"/>'
        '</linearGradient>'
        '</defs>'
    )
    
    # Background & Frame
    parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#card-bg)"/>')
    parts.append(f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" fill="none" stroke="{FRAME}" stroke-width="1"/>')
    
    # Title bar
    TITLEBAR_H = 34
    parts.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>')
    for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{20 + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
    parts.append(
        f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
        f'text-anchor="middle">vinicius@github: ~/neofetch</text>'
    )
    
    # Content starting coordinates
    start_y = 66
    line_h = 24
    
    # Header: user@host
    delay = 0.05
    parts.append(
        f'<g class="line" style="animation-delay: {delay:.2f}s;">'
        f'<text x="24" y="{start_y}" font-size="14" font-weight="700">'
        f'<tspan fill="{C_USER}">vinicius</tspan>'
        f'<tspan fill="{C_AT}">@</tspan>'
        f'<tspan fill="{C_HOST}">github</tspan>'
        f'</text>'
        '</g>'
    )
    
    delay += 0.06
    # Divider rule
    parts.append(
        f'<g class="line" style="animation-delay: {delay:.2f}s;">'
        f'<text x="24" y="{start_y + 14}" fill="{TITLE_TEXT}" font-size="12">'
        f'------------------------------------------------</text>'
        '</g>'
    )
    
    curr_y = start_y + 36
    
    import html
    for key, val, val_color in INFO_ROWS:
        delay += 0.07
        safe_key = html.escape(key)
        safe_val = html.escape(val)
        parts.append(
            f'<g class="line" style="animation-delay: {delay:.2f}s;">'
            f'<text x="24" y="{curr_y}" font-size="12.5">'
            f'<tspan fill="{C_KEY}" font-weight="600">{safe_key:12}</tspan>'
            f'<tspan fill="{C_SEP}">: </tspan>'
            f'<tspan fill="{val_color}">{safe_val}</tspan>'
            f'</text>'
            f'</g>'
        )
        curr_y += line_h
        
    # Extra decorative section (Terminal colors)
    curr_y += 18
    delay += 0.08
    parts.append(
        f'<g class="line" style="animation-delay: {delay:.2f}s;">'
        f'<text x="24" y="{curr_y}" fill="{TITLE_TEXT}" font-size="12">'
        f'------------------------------------------------</text>'
        '</g>'
    )
    
    curr_y += 24
    delay += 0.08
    # Color palette chips
    parts.append(f'<g class="line" style="animation-delay: {delay:.2f}s;">')
    chip_w = 26
    chip_h = 14
    chip_gap = 6
    for i, col in enumerate(PALETTE_COLORS):
        cx = 24 + i * (chip_w + chip_gap)
        parts.append(f'<rect x="{cx}" y="{curr_y}" width="{chip_w}" height="{chip_h}" rx="3" fill="{col}"/>')
    parts.append('</g>')
    
    # Row 2 of chips (bright)
    curr_y += chip_h + 5
    delay += 0.05
    parts.append(f'<g class="line" style="animation-delay: {delay:.2f}s;">')
    for i, col in enumerate(PALETTE_COLORS):
        cx = 24 + i * (chip_w + chip_gap)
        parts.append(f'<rect x="{cx}" y="{curr_y}" width="{chip_w}" height="{chip_h}" rx="3" fill="{col}" opacity="0.6"/>')
    parts.append('</g>')
    
    # Status prompt with blinking cursor at the bottom
    curr_y += 42
    parts.append(f'<line x1="0" y1="{curr_y-16}" x2="{CANVAS_W}" y2="{curr_y-16}" stroke="{FRAME}" stroke-opacity="0.6"/>')
    parts.append(
        f'<text x="24" y="{curr_y + 4}" fill="{TITLE_TEXT}" font-size="12">'
        f'vinicius@github:~$ <tspan fill="{C_ACCENT}">uptime --pretty</tspan> '
        f'<tspan fill="{C_VAL}">up and coding</tspan>'
        f'<tspan fill="{C_VAL}"> █<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></tspan>'
        f'</text>'
    )
    
    parts.append('</svg>')
    return "".join(parts)

if __name__ == "__main__":
    svg = build_svg()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg)} bytes; {CANVAS_W}x{CANVAS_H})")
