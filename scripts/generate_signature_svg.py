#!/usr/bin/env python3
"""
Generate ultra-crisp, legible, self-typing terminal ASCII/Braille SVGs from signatures and logos.
- Crops tight bounding box (no wasted empty black borders)
- Uses high-definition Braille matrix for smooth, legible curves
- Natural monospace metrics without letter-spacing distortion
- Animated line-by-line typing reveal with leading terminal cursor
"""
import html
import os
import subprocess
import sys
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
CONVERTER = os.path.join(HERE, "..", "ascii-image-converter.exe")

def crop_tight(image_path, out_cropped, threshold=30, pad=10):
    im = Image.open(image_path).convert("L")
    arr = np.array(im)
    if arr.mean() > 128:
        # Invert if light background
        arr = 255 - arr
        im = Image.fromarray(arr)
        
    mask = arr > threshold
    ys, xs = np.nonzero(mask)
    if len(ys) == 0 or len(xs) == 0:
        im.save(out_cropped)
        return
        
    y0 = max(0, ys.min() - pad)
    y1 = min(im.height, ys.max() + pad)
    x0 = max(0, xs.min() - pad)
    x1 = min(im.width, xs.max() + pad)
    cropped = im.crop((x0, y0, x1, y1))
    
    # Enhance sharpness for clean stroke thresholding
    cropped = ImageEnhance.Contrast(cropped).enhance(1.6)
    cropped = cropped.filter(ImageFilter.UnsharpMask(radius=1.5, percent=160, threshold=2))
    cropped.save(out_cropped)

def build_braille_svg(cropped_img, out_svg, title, width_cols=64, canvas_w=560, canvas_h=385, titlebar_h=32, pad_x=24, accent_color="#58a6ff"):
    # Run ascii-image-converter with Braille (-b)
    cmd = [CONVERTER, cropped_img, "-W", str(width_cols), "-b"]
    raw_output = subprocess.check_output(cmd, encoding="utf-8")
    all_lines = raw_output.splitlines()
    
    # Trim leading and trailing blank rows
    trimmed = []
    for l in all_lines:
        if l.strip("⠀ \t"):
            trimmed.append(l)
            
    if not trimmed:
        print("Warning: no characters generated!")
        return

    # Trim leading/trailing blank columns
    min_col = min(len(l) - len(l.lstrip("⠀ ")) for l in trimmed)
    max_col = max(len(l.rstrip("⠀ ")) for l in trimmed)
    lines = [l[min_col:max_col] for l in trimmed]
    
    num_rows = len(lines)
    num_cols = max(len(l) for l in lines)
    
    # Calculate font size and positions to fill the canvas nicely without distortion
    avail_w = canvas_w - pad_x * 2
    avail_h = canvas_h - titlebar_h - 32
    
    # For Braille, aspect ratio of character cell is ~ 0.5 (width / height)
    cell_w = avail_w / num_cols
    cell_h = avail_h / num_rows
    
    # Ensure uniform scaling so characters don't stretch
    # Braille chars are roughly 0.6em wide, 1.2em tall
    font_size = min(cell_w * 1.6, cell_h * 0.95)
    line_spacing = avail_h / num_rows
    
    start_y = titlebar_h + 20 + line_spacing * 0.7
    
    BG = "#0d1117"
    BG2 = "#111722"
    FRAME = "#30363d"
    TITLE_TEXT = "#7d8590"
    INK = "#f0f6fc"
    CURSOR = accent_color
    
    ROW_DUR = 0.08
    STAGGER = 0.07
    
    clip_prefix = os.path.basename(out_svg).replace("-", "_").replace(".", "_")
    
    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {canvas_w} {canvas_h}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
    )
    parts.append(
        '<defs>'
        f'<linearGradient id="bg_{clip_prefix}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
        '</linearGradient></defs>'
    )
    parts.append(f'<rect width="{canvas_w}" height="{canvas_h}" rx="12" fill="url(#bg_{clip_prefix})"/>')
    parts.append(f'<rect x="0.5" y="0.5" width="{canvas_w-1}" height="{canvas_h-1}" rx="12" fill="none" stroke="{FRAME}" stroke-width="1"/>')
    parts.append(f'<line x1="0" y1="{titlebar_h}" x2="{canvas_w}" y2="{titlebar_h}" stroke="{FRAME}"/>')
    
    # macOS window traffic light dots
    for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{18 + i*16}" cy="{titlebar_h/2}" r="5" fill="{dotcol}"/>')
        
    parts.append(
        f'<text x="{canvas_w/2}" y="{titlebar_h/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
        f'text-anchor="middle">{html.escape(title)}</text>'
    )
    
    # Render animated lines
    for ry, line in enumerate(lines):
        y = start_y + ry * line_spacing
        row_top = y - line_spacing * 0.7
        delay = ry * STAGGER
        safe_line = html.escape(line)
        
        # Center the text row horizontally
        text = (
            f'<text xml:space="preserve" x="{canvas_w/2}" y="{y:.1f}" fill="{INK}" '
            f'font-size="{font_size:.1f}" text-anchor="middle">{safe_line}</text>'
        )
        
        clip_id = f"clp_{clip_prefix}_{ry}"
        parts.append(
            f'<clipPath id="{clip_id}"><rect x="0" y="{row_top:.1f}" height="{line_spacing*1.2:.1f}" width="0">'
            f'<animate attributeName="width" from="0" to="{canvas_w}" begin="{delay:.3f}s" dur="{ROW_DUR:.2f}s" fill="freeze"/>'
            f'</rect></clipPath>'
        )
        parts.append(f'<g clip-path="url(#{clip_id})">{text}</g>')
        
        # Cursor wipe
        parts.append(
            f'<rect y="{row_top+2:.1f}" width="9" height="{line_spacing-2:.1f}" fill="{CURSOR}" opacity="0">'
            f'<animate attributeName="x" from="{pad_x}" to="{canvas_w-pad_x}" begin="{delay:.3f}s" dur="{ROW_DUR:.2f}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
            f'<set attributeName="opacity" to="0" begin="{delay+ROW_DUR:.3f}s"/></rect>'
        )
        
    parts.append("</svg>")
    svg = "".join(parts)
    with open(out_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out_svg} ({len(svg)} bytes; {canvas_w}x{canvas_h}; {num_rows} rows x {num_cols} cols; font {font_size:.1f}px)")

if __name__ == "__main__":
    vini_src = r"C:/Users/Ana/.gemini/antigravity/brain/e2dc2eaa-d1c6-4110-8515-84c283278f07/.user_uploaded/media_1788372551171.jpg"
    mezz_src = r"C:/Users/Ana/.gemini/antigravity/brain/e2dc2eaa-d1c6-4110-8515-84c283278f07/.user_uploaded/media_1788372602059.png"
    
    crop_tight(vini_src, "vini_cropped.png", threshold=35, pad=8)
    crop_tight(mezz_src, "mezz_cropped.png", threshold=35, pad=8)
    
    # 1. Vinícius Noetzold signature (beside portrait in whoami)
    # 560 x 385 -> fits 100% proportionally next to Vini2-ascii.svg (370 x 385.4px)
    build_braille_svg(
        "vini_cropped.png",
        "vinicius-wordmark.svg",
        title="vinicius@github: ~$ ./signature.sh",
        width_cols=58,
        canvas_w=560,
        canvas_h=385,
        accent_color="#58a6ff"
    )
    
    # 2. Mezzold Studios logo (bottom banner)
    # 860 x 420 -> full width banner matching contribution heatmap
    build_braille_svg(
        "mezz_cropped.png",
        "mezzold-studios.svg",
        title="mezzold@studios: ~$ ./mezzold_studios.sh",
        width_cols=76,
        canvas_w=860,
        canvas_h=420,
        accent_color="#bc8cff"
    )
