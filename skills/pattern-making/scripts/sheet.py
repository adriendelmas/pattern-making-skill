"""PNG pattern sheets from a pieces file (pieces_<size>.json written by `piece`, `block` or `garment`).
Optional: needs Pillow. Seam line black, cut line grey, notches, grain, fold in blue, internal lines dashed green,
buttons, 10 cm square. Pieces whose name contains "lining" go on a second sheet.

    python sheet.py out/pieces_38.json --title "Velvet coat" [--px 7] [--width 3200]
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pattern as P  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:                       # ponytail: PNG only with Pillow; SVG and DXF need nothing
    raise SystemExit("PNG sheets need Pillow (pip install pillow). The SVG and DXF files are already written.")

GREY, GREEN, BLUE = (110, 110, 110), (0, 130, 60), (30, 60, 200)


def font(size):
    for f in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def dashed(dr, pts, fill, width=2, dash=8.0):
    acc, on = 0.0, True
    for a, b in zip(pts, pts[1:]):
        l = P.dist(a, b)
        t = 0.0
        while t < l:
            step = min(dash - acc, l - t)
            if on:
                dr.line([(a[0] + (b[0] - a[0]) * t / l, a[1] + (b[1] - a[1]) * t / l),
                         (a[0] + (b[0] - a[0]) * (t + step) / l, a[1] + (b[1] - a[1]) * (t + step) / l)], fill=fill, width=width)
            t += step
            acc += step
            if acc >= dash - 1e-9:
                acc, on = 0.0, not on


def arrow(dr, a, b):
    dr.line([a, b], fill="black", width=3)
    for end, other in ((a, b), (b, a)):
        an = math.atan2(end[1] - other[1], end[0] - other[0])
        for s in (0.45, -0.45):
            dr.line([end, (end[0] - 16 * math.cos(an + s), end[1] - 16 * math.sin(an + s))], fill="black", width=3)


def draw_piece(dr, pc, T, px, fill):
    poly = P.outline(pc, 32)
    dr.polygon([T(q) for q in P.cut_line(pc)], fill=fill, outline=GREY)
    dr.line([T(q) for q in poly] + [T(poly[0])], fill="black", width=3)
    for layer, pts in P.construction_marks(pc):
        if layer in ("FOLD", "INTERNAL"):
            dashed(dr, [T(q) for q in pts], BLUE if layer == "FOLD" else GREEN, 2, 8)
        elif layer == "GRAIN":
            arrow(dr, T(pts[0]), T(pts[1]))
        else:
            dr.line([T(q) for q in pts], fill="black", width=2)


def sheet(pieces, title, path, width, px, fill):
    f_t, f_s = font(40), font(18)
    boxes = []
    for p in pieces:
        pts = P.cut_line(p)
        boxes.append((min(q[0] for q in pts), min(q[1] for q in pts), max(q[0] for q in pts), max(q[1] for q in pts)))
    x, y, rowh, pos = 40, 110, 0, []
    for p, bx in zip(pieces, boxes):
        w, h = (bx[2] - bx[0]) * px, (bx[3] - bx[1]) * px
        w = max(w, 10 * len(f"{p['name']} - cut {p.get('cut', '')}"))
        if x + w > width - 40:
            x, y, rowh = 40, y + rowh + 90, 0
        pos.append((x, y))
        x += w + 60
        rowh = max(rowh, h)
    im = Image.new("RGB", (width, int(y + rowh + 160)), "white")
    dr = ImageDraw.Draw(im)
    dr.text((30, 20), title, fill="black", font=f_t)
    dr.text((30, 70), "Seam line black, cut line grey, ticks: notches, blue: fold, green: internal lines. Print the SVG for 1:1.",
            fill=GREY, font=f_s)
    for p, bx, (ox, oy) in zip(pieces, boxes, pos):
        T = (lambda bx, ox, oy: (lambda q: (ox + (q[0] - bx[0]) * px, oy + 40 + (q[1] - bx[1]) * px)))(bx, ox, oy)
        draw_piece(dr, p, T, px, fill)
        dr.text((ox, oy), f"{p['name'].upper()} - cut {p.get('cut', '')}", fill="black", font=f_s)
    yb = y + rowh + 140
    dr.rectangle([width - 40 - 10 * px, yb - 10 * px - 20, width - 40, yb - 20], outline="black", width=3)
    dr.text((width - 40 - 10 * px + 4, yb - 10 * px - 16), "10 cm", fill="black", font=f_s)
    im.save(path)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pieces")
    ap.add_argument("--title", default="Pattern")
    ap.add_argument("--px", type=float, default=7.0, help="pixels per cm")
    ap.add_argument("--width", type=int, default=3200)
    a = ap.parse_args(argv)
    with open(a.pieces, encoding="utf-8") as f:
        data = json.load(f)
    pcs = data["pieces"] if isinstance(data, dict) else data
    base = os.path.splitext(a.pieces)[0]
    shell = [p for p in pcs if "lining" not in p["name"].lower()]
    lining = [p for p in pcs if "lining" in p["name"].lower()]
    print(sheet(shell, a.title, base + "_shell.png", a.width, a.px, (214, 214, 248)))
    if lining:
        print(sheet(lining, a.title + " - lining", base + "_lining.png", a.width, a.px, (236, 222, 200)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
