#!/usr/bin/env python3
"""
Generate clean, self-typing terminal ASCII SVGs from black-and-white signature/logo images.
- Background (black) -> spaces
- Strokes (white) -> smooth ASCII density ramp
- macOS terminal titlebar with traffic light dots
- Self-typing horizontal clip animation with leading block cursor
"""
import html
import os
import sys
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

def create_logo_svg(image_path, out_path, title, canvas_w=560, canvas_h=440, cols=80, rows=26, pad=18, titlebar_h=30, accent_color="#58a6ff"):
    im = Image.open(image_path).convert("L")
    
    # Invert if the image was white background with black text
    # Here the uploaded images are black background with white text (mean brightness < 128)
    arr = np.array(im)
    if arr.mean() > 128:
        im = ImageOps.invert(im)
        
    im = ImageEnhance.Contrast(im).enhance(1.4)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=150, threshold=2))
    
    # Calculate crop around bounding box of the strokes to make it fill nicely
    mask = np.array(im) > 30
    ys, xs = np.nonzero(mask)
    if len(ys) and len(xs):
        # crop with a small border
        y0, y1 = max(0, ys.min() - 8), min(im.height, ys.max() + 8)
        x0, x1 = max(0, xs.min() - 8), min(im.width, xs.max() + 8)
        im = im.crop((x0, y0, x1, y1))
        
    im = im.resize((cols, rows), Image.LANCZOS)
    px = np.array(im)
    
    # Fine density ramp
    RAMP = " .:-=+*sS#%@"
    
    lines = []
    for y in range(rows):
        chars = []
        for x in range(cols):
            v = px[y, x]
            if v < 40:
                chars.append(" ")
            else:
                idx = int((v - 40) / (255 - 40) * (len(RAMP) - 1))
                idx = max(0, min(len(RAMP) - 1, idx))
                chars.append(RAMP[idx])
        lines.append("".join(chars))
        
    # Sizing
    art_w = canvas_w - pad * 2
    art_h = canvas_h - titlebar_h - pad * 1.5
    cell_h = art_h / rows
    font_size = cell_h * 0.92
    art_top = titlebar_h + pad * 0.6
    
    BG = "#0d1117"
    BG2 = "#111722"
    FRAME = "#30363d"
    TITLE_TEXT = "#7d8590"
    INK = "#c9d1d9"
    CURSOR = accent_color
    
    ROW_DUR = 0.08
    STAGGER = 0.08
    
    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {canvas_w} {canvas_h}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
    )
    parts.append(
        '<defs>'
        f'<linearGradient id="bg_{os.path.basename(out_path)[:6]}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
        '</linearGradient></defs>'
    )
    parts.append(f'<rect width="{canvas_w}" height="{canvas_h}" rx="12" fill="url(#bg_{os.path.basename(out_path)[:6]})"/>')
    parts.append(f'<rect x="0.5" y="0.5" width="{canvas_w-1}" height="{canvas_h-1}" rx="12" fill="none" stroke="{FRAME}" stroke-width="1"/>')
    parts.append(f'<line x1="0" y1="{titlebar_h}" x2="{canvas_w}" y2="{titlebar_h}" stroke="{FRAME}"/>')
    
    for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{pad + i*16}" cy="{titlebar_h/2}" r="5" fill="{dotcol}"/>')
        
    parts.append(
        f'<text x="{canvas_w/2}" y="{titlebar_h/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
        f'text-anchor="middle">{html.escape(title)}</text>'
    )
    
    # Animated rows
    for ry, line in enumerate(lines):
        y = art_top + ry * cell_h + cell_h * 0.78
        row_y = art_top + ry * cell_h
        delay = ry * STAGGER
        safe = html.escape(line)
        text = (
            f'<text xml:space="preserve" x="{pad}" y="{y:.1f}" fill="{INK}" '
            f'font-size="{font_size:.1f}" textLength="{art_w}" lengthAdjust="spacing">{safe}</text>'
        )
        clip_id = f"clp_{os.path.basename(out_path)[:4]}_{ry}"
        parts.append(
            f'<clipPath id="{clip_id}"><rect x="{pad}" y="{row_y:.1f}" height="{cell_h:.1f}" width="0">'
            f'<animate attributeName="width" from="0" to="{art_w}" begin="{delay:.3f}s" dur="{ROW_DUR:.2f}s" fill="freeze"/>'
            f'</rect></clipPath>'
        )
        parts.append(f'<g clip-path="url(#{clip_id})">{text}</g>')
        parts.append(
            f'<rect y="{row_y+1:.1f}" width="9" height="{cell_h-2:.1f}" fill="{CURSOR}" opacity="0">'
            f'<animate attributeName="x" from="{pad}" to="{pad+art_w}" begin="{delay:.3f}s" dur="{ROW_DUR:.2f}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
            f'<set attributeName="opacity" to="0" begin="{delay+ROW_DUR:.3f}s"/></rect>'
        )
        
    parts.append("</svg>")
    svg = "".join(parts)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out_path} ({len(svg)} bytes; {canvas_w}x{canvas_h})")

if __name__ == "__main__":
    vini_img = r"C:/Users/Ana/.gemini/antigravity/brain/e2dc2eaa-d1c6-4110-8515-84c283278f07/.user_uploaded/media_1788372551171.jpg"
    mezz_img = r"C:/Users/Ana/.gemini/antigravity/brain/e2dc2eaa-d1c6-4110-8515-84c283278f07/.user_uploaded/media_1788372602059.png"
    
    # 1. Vinícius Noetzold signature (beside portrait in whoami)
    # Size 560x440 -> displays at width="490", height="385px" (exact match to Vini2-ascii.svg!)
    create_logo_svg(
        vini_img,
        "vinicius-wordmark.svg",
        title="vinicius@github: ~$ ./signature.sh",
        canvas_w=560,
        canvas_h=440,
        cols=78,
        rows=26,
        accent_color="#58a6ff"
    )
    
    # 2. Mezzold Studios logo (bottom banner)
    # Size 860x420 -> displays at width="860" (full width, matching the heatmap!)
    create_logo_svg(
        mezz_img,
        "mezzold-studios.svg",
        title="mezzold@studios: ~$ ./mezzold_studios.sh",
        canvas_w=860,
        canvas_h=420,
        cols=96,
        rows=32,
        accent_color="#bc8cff"
    )
