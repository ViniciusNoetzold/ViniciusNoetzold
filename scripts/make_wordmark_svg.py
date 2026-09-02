#!/usr/bin/env python3
"""
Render 3D ASCII wordmark animated SVGs (SMIL / CSS).
Supports custom text, fonts, and modes (rock, spin, once, static).
"""
import argparse
import html
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

# Geometry / grid
DEFAULT_FONT = "C:\\Windows\\Fonts\\arialbd.ttf" if os.name == "nt" else "/System/Library/Fonts/Futura.ttc"
FONT_PATH = os.environ.get("WORDMARK_FONT", DEFAULT_FONT)
FONT_INDEX = int(os.environ.get("WORDMARK_FONT_INDEX", 0))

COLS = int(os.environ.get("WORDMARK_COLS", 52))
ROW_MARGIN = int(os.environ.get("WORDMARK_ROW_MARGIN", 4))
CELL_W = 9.0
CELL_H = 15.5

MASK_H = 260
TRACKING = 0.12
LINE_GAP = 1.15
DEPTH_FRAC = 0.32
TILT_DEG = float(os.environ.get("WORDMARK_TILT", 4.0))

CAM_DIST = 6.0
FOCAL = 4.15
FIT = 0.92

RAMP = " .`:-=+*csS#%@"
LIGHT = np.array([-0.15, -0.45, -1.00])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
AMBIENT = 0.22
FOG = 0.34
FOG_SPAN = 0.55

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"

PAD = 18
TITLEBAR_H = 28

def build_shell(text, font_path=FONT_PATH, font_index=FONT_INDEX, cols=COLS):
    probe = text.replace("\n", " ")
    font_size = MASK_H
    
    # Try loading font safely
    font = None
    for _ in range(40):
        try:
            if font_path.lower().endswith(".ttc"):
                font = ImageFont.truetype(font_path, font_size, index=font_index)
            else:
                font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
            break
        l, t, r, b = font.getbbox(probe)
        if b - t <= MASK_H:
            break
        font_size = int(font_size * 0.92)
        
    l, t, r, b = font.getbbox(probe)
    h = b - t
    track = int(round(TRACKING * font_size))
    lines = text.split("\n")
    line_h = int(round(h * LINE_GAP))

    def line_w(s):
        return sum(font.getlength(c) for c in s) + track * max(0, len(s) - 1)

    total_w = int(round(max(line_w(s) for s in lines))) + 16
    total_h = line_h * (len(lines) - 1) + h + 16
    img = Image.new("L", (total_w, total_h), 0)
    d = ImageDraw.Draw(img)
    for li, s in enumerate(lines):
        pen = 8.0 + (total_w - 16 - line_w(s)) / 2.0
        base = -t + 8 + li * line_h
        for ch in s:
            d.text((pen, base), ch, font=font, fill=255)
            pen += font.getlength(ch) + track
            
    mask = np.array(img) > 127
    xs_any = np.nonzero(mask.any(0))[0]
    ys_any = np.nonzero(mask.any(1))[0]
    if len(xs_any) == 0 or len(ys_any) == 0:
        mask = np.ones((100, 100), dtype=bool)
    else:
        mask = mask[ys_any[0]:ys_any[-1] + 1, xs_any[0]:xs_any[-1] + 1]

    H, W = mask.shape
    depth = max(4, int(round(H * DEPTH_FRAC)))

    pts, norms = [], []
    fy, fx = np.nonzero(mask)
    pts.append(np.column_stack([fx, fy, np.zeros_like(fx)]))
    norms.append(np.tile([0.0, 0.0, -1.0], (len(fx), 1)))

    pts.append(np.column_stack([fx, fy, np.full_like(fx, depth - 1)]))
    norms.append(np.tile([0.0, 0.0, 1.0], (len(fx), 1)))

    up = mask & ~np.pad(mask[:-1, :], ((1, 0), (0, 0)), constant_values=False)
    dn = mask & ~np.pad(mask[1:, :], ((0, 1), (0, 0)), constant_values=False)
    lf = mask & ~np.pad(mask[:, :-1], ((0, 0), (1, 0)), constant_values=False)
    rt = mask & ~np.pad(mask[:, 1:], ((0, 0), (0, 1)), constant_values=False)

    for z in range(depth):
        for cond, norm in [
            (up, [0.0, -1.0, 0.0]),
            (dn, [0.0, 1.0, 0.0]),
            (lf, [-1.0, 0.0, 0.0]),
            (rt, [1.0, 0.0, 0.0]),
        ]:
            cy, cx = np.nonzero(cond)
            if len(cx):
                pts.append(np.column_stack([cx, cy, np.full_like(cx, z)]))
                norms.append(np.tile(norm, (len(cx), 1)))

    P = np.vstack(pts).astype(np.float32)
    N = np.vstack(norms).astype(np.float32)

    P[:, 0] -= W / 2.0
    P[:, 1] -= H / 2.0
    P[:, 2] -= (depth - 1) / 2.0

    scale = 1.0 / W
    P *= scale

    tilt = math.radians(TILT_DEG)
    ct, st = math.cos(tilt), math.sin(tilt)
    Rx = np.array([[1, 0, 0], [0, ct, -st], [0, st, ct]], dtype=np.float32)
    P = P @ Rx.T
    N = N @ Rx.T

    return P, N

def project(P, N, yaw_rad):
    cy, sy = math.cos(yaw_rad), math.sin(yaw_rad)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float32)
    p = P @ Ry.T
    n = N @ Ry.T

    z = p[:, 2] + CAM_DIST
    inv = FOCAL / z
    sx = p[:, 0] * inv
    sy = p[:, 1] * inv

    diff = np.maximum(0.0, np.sum(n * -LIGHT, axis=1))
    fog = np.clip((p[:, 2] - (-FOG_SPAN / 2.0)) / FOG_SPAN, 0.0, 1.0)
    shade = np.clip((AMBIENT + (1.0 - AMBIENT) * diff) * (1.0 - FOG * fog), 0.0, 1.0)

    vis = n[:, 2] < 0.05
    return np.column_stack([sx[vis], sy[vis], z[vis], shade[vis]])

def fit(projections, cols=COLS):
    xs = np.concatenate([q[:, 0] for q in projections])
    ys = np.concatenate([q[:, 1] for q in projections])
    w = xs.max() - xs.min()
    h = ys.max() - ys.min()

    scale_x = (cols * FIT) / w
    scale_y = scale_x * (CELL_W / CELL_H)

    cx = (xs.max() + xs.min()) / 2.0
    cy = (ys.max() + ys.min()) / 2.0
    return (scale_x, scale_y), cx, cy

def rasterize(q, scale, cx, cy, cols=COLS, row_margin=ROW_MARGIN):
    (sx, sy) = scale
    gx = np.round((q[:, 0] - cx) * sx + (cols - 1) / 2.0).astype(int)
    sy_screen = (q[:, 1] - cy) * sy
    gy = np.round(sy_screen - sy_screen.min()).astype(int)

    rows = gy.max() + 1
    zbuf = np.full((rows, cols), np.inf, dtype=np.float32)
    sbuf = np.zeros((rows, cols), dtype=np.float32)

    order = np.argsort(-q[:, 2])
    for idx in order:
        x, y = gx[idx], gy[idx]
        if 0 <= x < cols and 0 <= y < rows:
            zv = q[idx, 2]
            if zv < zbuf[y, x]:
                zbuf[y, x] = zv
                sbuf[y, x] = q[idx, 3]

    out = []
    for _ in range(row_margin):
        out.append(" " * cols)
    for y in range(rows):
        chars = []
        for x in range(cols):
            if np.isinf(zbuf[y, x]):
                chars.append(" ")
            else:
                idx = int(sbuf[y, x] * (len(RAMP) - 1) + 0.5)
                idx = max(1, min(len(RAMP) - 1, idx))
                chars.append(RAMP[idx])
        out.append("".join(chars))
    for _ in range(row_margin):
        out.append(" " * cols)
    return out

def emit(frames, mode, out, dur=5.0, reveal=1.6, title="vinicius@github: ~$ ./wordmark.sh --3d", cols=COLS):
    n = len(frames)
    rows = len(frames[0])

    art_w = cols * CELL_W
    art_h = rows * CELL_H
    canvas_w = art_w + PAD * 2
    canvas_h = TITLEBAR_H + art_h + PAD

    art_top = TITLEBAR_H + PAD * 0.3
    fs = CELL_H * 0.95

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w:.0f}" height="{canvas_h:.0f}" '
        f'viewBox="0 0 {canvas_w:.0f} {canvas_h:.0f}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
        '<defs>'
        f'<linearGradient id="wbg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
        '</linearGradient></defs>',
        f'<rect width="{canvas_w:.0f}" height="{canvas_h:.0f}" rx="12" fill="url(#wbg)"/>',
        f'<rect x="0.5" y="0.5" width="{canvas_w-1:.0f}" height="{canvas_h-1:.0f}" rx="12" '
        f'fill="none" stroke="{FRAME}" stroke-width="1"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{canvas_w:.0f}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
    ]
    for i, dot in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        p.append(f'<circle cx="{PAD + i*15}" cy="{TITLEBAR_H/2}" r="4.5" fill="{dot}"/>')
    p.append(
        f'<text x="{canvas_w/2:.0f}" y="{TITLEBAR_H/2 + 4:.0f}" fill="{TITLE_TEXT}" '
        f'font-size="11.5" text-anchor="middle">{title}</text>'
    )

    def frame_g(rows, extra=""):
        out_rows = []
        for ry, line in enumerate(rows):
            s = line.rstrip()
            if not s.strip():
                continue
            lead = len(s) - len(s.lstrip(" "))
            body = s[lead:]
            x = PAD + lead * CELL_W
            y = art_top + ry * CELL_H + CELL_H * 0.78
            out_rows.append(
                f'<text xml:space="preserve" x="{x:.1f}" y="{y:.1f}" font-size="{fs:.1f}" '
                f'textLength="{len(body)*CELL_W:.1f}" lengthAdjust="spacing">{html.escape(body)}</text>'
            )
        return f'<g fill="{INK}"{extra}>' + "".join(out_rows) + "</g>"

    if mode == "static":
        p.append(frame_g(frames[0]))
        p.append("</svg>")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("".join(p))
        print("wrote", out)
        return

    p.append(
        f'<clipPath id="wipe"><rect x="{PAD}" y="{art_top:.1f}" height="{art_h:.1f}" width="0">'
        f'<animate attributeName="width" from="0" to="{art_w:.0f}" begin="0s" dur="{reveal:.2f}s" fill="freeze"/>'
        f'</rect></clipPath>'
    )
    p.append(f'<g clip-path="url(#wipe)">{frame_g(frames[0])}'
             f'<set attributeName="opacity" to="0" begin="{reveal:.2f}s"/></g>')
    p.append(
        f'<rect x="{PAD}" y="{art_top+2:.1f}" width="{CELL_W*1.6:.1f}" height="{art_h-4:.1f}" fill="{INK}" opacity="0.16">'
        f'<animate attributeName="x" from="{PAD}" to="{PAD+art_w:.0f}" begin="0s" dur="{reveal:.2f}s" fill="freeze"/>'
        f'<set attributeName="opacity" to="0" begin="{reveal:.2f}s"/></rect>'
    )

    if mode == "once":
        step = dur / n
        for i, rows in enumerate(frames):
            begin = reveal + i * step
            sets = f'<set attributeName="opacity" to="1" begin="{begin:.3f}s"/>'
            if i != n - 1:
                sets += f'<set attributeName="opacity" to="0" begin="{begin+step:.3f}s"/>'
            p.append(frame_g(rows, ' opacity="0"').replace("</g>", sets + "</g>"))
    else:
        for i, rows in enumerate(frames):
            if i == 0:
                vals, kt = "1;0", f"0;{1/n:.5f}"
            else:
                vals, kt = "0;1;0", f"0;{i/n:.5f};{(i+1)/n:.5f}"
            anim = (
                f'<animate attributeName="opacity" calcMode="discrete" values="{vals}" '
                f'keyTimes="{kt}" dur="{dur:.2f}s" begin="{reveal:.2f}s" repeatCount="indefinite"/>'
            )
    p.append("</svg>")
    svg = "".join(p)
    out_dir = os.path.dirname(os.path.abspath(out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote {out} ({len(svg)/1024:.1f} KB; {n} frames; {canvas_w:.0f}x{canvas_h:.0f})")

def generate_wordmark(text, out_path, mode="rock", cols=52, font_path=DEFAULT_FONT, title=None):
    if title is None:
        title = "vinicius@github: ~$ ./wordmark.sh --3d"
    P, N = build_shell(text, font_path=font_path, cols=cols)
    rest = math.radians(-13)
    if mode == "spin":
        nf = 36
        yaws = [rest + 2 * math.pi * i / nf for i in range(nf)]
        dur = 7.0
    elif mode == "once":
        nf = 32
        yaws = [rest + 2 * math.pi * i / nf for i in range(nf)] + [rest]
        dur = 3.6
    else:
        nf = 20
        amp = math.radians(11)
        yaws = [rest + amp * math.sin(2 * math.pi * i / nf) for i in range(nf)]
        dur = 5.0

    proj = [project(P, N, y) for y in yaws]
    scale, cx, cy = fit(proj, cols=cols)
    frames = [rasterize(q, scale, cx, cy, cols=cols) for q in proj]
    emit(frames, mode, out_path, dur=dur, reveal=1.6, title=title, cols=cols)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="MEZZOLD")
    parser.add_argument("--out", default=os.path.join(HERE, "..", "wordmark.svg"))
    parser.add_argument("--mode", default="rock")
    parser.add_argument("--cols", type=int, default=52)
    parser.add_argument("--font", default=DEFAULT_FONT)
    parser.add_argument("--title", default=None)
    args = parser.parse_args()

    generate_wordmark(args.text, args.out, mode=args.mode, cols=args.cols, font_path=args.font, title=args.title)
