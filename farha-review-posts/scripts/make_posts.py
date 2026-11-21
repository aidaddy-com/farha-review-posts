#!/usr/bin/env python3
"""Make Instagram review posts (1080x1350 PNG) + captions + approval sheet.

Works for any business. Needs only Python 3 and Pillow (`pip install pillow`).
Default fonts are bundled in ./fonts; the brand's own fonts go in <business folder>/fonts/.

  python3 make_posts.py --folder "<business folder>" reviews.json [--template auto|split|market|bubble|hero|solid]
                        [--carousel off|long-only|always] [--location <slug>] [--job commercial|residential|multifamily]
                        [--include-seen]
  python3 make_posts.py --folder "<business folder>" --preview [reviews.json]
      -> <business folder>/setup-previews/: one sample post per layout, to pick a look during setup

<business folder> holds settings.json, the logo file, photos/ and (optional) fonts/.
reviews.json is a list of:
  {"location": "wichita", "source": "Google", "name": "Sam P.", "date": "Jul 2026",
   "job": "optional: commercial | residential | multifamily (leave out to detect it from the review)",
   "quote": "full review, word for word",
   "hook": "the one line that grabs attention, word for word, 12 words or fewer (the big quote on the image)",
   "excerpt": "optional, older batches: best sentences, word for word (used when there is no hook)",
   "hl": "optional: short phrase to highlight, word for word",
   "edits": [{"from": "REMOVED and REMOVED", "to": "Two reps"}],   # only for names the site blurred (BBB)
   "caption": "post caption",
   "photo": "optional: photo the reviewer posted with the review (path inside the business folder);
             used as this post's background instead of the rotation"}
Output: <business folder>/posts/<date>/ with PNGs, captions.md, approval.csv
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
except ImportError:
    sys.exit("Pillow is missing. Run: pip install pillow")

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
W, H = 1080, 1350
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_COLORS = {"dark": "#0c3455", "darker": "#071f35", "accent": "#cb972b", "accent_light": "#e2b04a"}


# ---------------------------------------------------------------- fonts
# Roles -> bundled default. settings.json "fonts" can point any role at a file in <business folder>/fonts/.
DEFAULT_FONTS = {"head": "PlayfairDisplay.ttf", "head_italic": "PlayfairDisplay-Italic.ttf",
                 "body": "Poppins-Regular.ttf", "body_bold": "Poppins-SemiBold.ttf",
                 "body_light": "Poppins-Light.ttf", "label": "Raleway.ttf"}
FALLBACK_ROLE = {"head_italic": "head", "body_bold": "body", "body_light": "body", "label": "body_bold"}
FONT_FILES: dict[str, Path] = {k: FONTS / v for k, v in DEFAULT_FONTS.items()}
_cache: dict = {}


def set_fonts(folder: Path, chosen: dict) -> None:
    for role, name in (chosen or {}).items():
        for cand in (folder / "fonts" / name, folder / name, FONTS / name):
            if name and cand.is_file():
                FONT_FILES[role] = cand
                break
        else:
            print(f"NOTE: font '{name}' for {role} not found, using the default.")
    for role, parent in FALLBACK_ROLE.items():  # brand gave a head/body font but no italic/bold: reuse it
        if role not in (chosen or {}) and parent in (chosen or {}):
            FONT_FILES[role] = FONT_FILES[parent]


def font(role: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    key = (role, size, weight)
    if key in _cache:
        return _cache[key]
    f = ImageFont.truetype(str(FONT_FILES[role]), size)
    if weight is not None:  # variable fonts: set the weight axis, leave other axes at default
        try:
            axes = f.get_variation_axes()
            f.set_variation_by_axes([max(a["minimum"], min(a["maximum"], weight)) if str(a.get("name", "")).strip("b'").lower() in ("weight", "wght") else a["default"] for a in axes])
        except Exception:
            pass
    _cache[key] = f
    return f


HEAD_WEIGHT = [400]  # settings.json "head_weight": 700 for bold sans brands (Montserrat)


def serif(size, italic=False, weight=None):
    return font("head_italic" if italic else "head", size, weight or HEAD_WEIGHT[0])


def sans(size, style="Regular"):
    return font({"Regular": "body", "SemiBold": "body_bold", "Light": "body_light"}[style], size,
                {"Regular": 400, "SemiBold": 600, "Light": 300}[style])


def label_font(size, weight=700):
    return font("label", size, weight)


# ---------------------------------------------------------------- helpers
def rgb(hex_: str, a: int = 255):
    h = hex_.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def words(s: str) -> int:
    return len(s.split())


def cover(photo: Path, focus: str) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(photo)).convert("RGB")
    fx, fy = (float(v.strip().rstrip("%")) / 100 for v in (focus or "50% 50%").split()[:2])
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = round((img.width - W) * fx), round((img.height - H) * fy)
    return img.crop((left, top, left + W, top + H)).convert("RGBA")


def vgradient(stops: list[tuple[float, int]], color: str) -> Image.Image:
    """Vertical overlay; stops = [(y fraction 0..1 from top, alpha 0..255)]."""
    col = Image.new("L", (1, H))
    px = col.load()
    for y in range(H):
        t = y / (H - 1)
        for (t0, a0), (t1, a1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                px[0, y] = round(a0 + (a1 - a0) * ((t - t0) / (t1 - t0) if t1 > t0 else 0))
                break
        else:
            px[0, y] = stops[0][1] if t < stops[0][0] else stops[-1][1]
    over = Image.new("RGBA", (W, H), rgb(color))
    over.putalpha(col.resize((W, H)))
    return over


def logo_on_dark(path: Path, style: str = "white") -> Image.Image:
    """Logo for dark backgrounds. "white" (default) = all-white version, works with transparent or
    white-background logos. "original" = full color, only for logos that already read well on dark."""
    img = Image.open(path).convert("RGBA")
    if style == "original":
        bbox = img.getchannel("A").getbbox()
        return img.crop(bbox) if bbox else img
    alpha = img.getchannel("A")
    if alpha.getextrema() == (255, 255):  # no transparency: treat light pixels as background
        lum = img.convert("L")
        alpha = lum.point(lambda v: 0 if v > 235 else min(255, (235 - v) * 3))
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    white.putalpha(alpha)
    bbox = alpha.getbbox()
    return white.crop(bbox) if bbox else white


def paste_h(base: Image.Image, img: Image.Image, height: int, xy: tuple[int, int], anchor="lt", max_w: int = 560):
    scale = min(height / img.height, max_w / img.width)
    im = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    x, y = xy
    if anchor[0] == "m":
        x -= im.width // 2
    if anchor[0] == "r":
        x -= im.width
    base.alpha_composite(im, (x, y))
    return im.width


def star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill):
    import math
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=fill)


def stars(draw, x, y, size, fill, gap=6):
    for i in range(5):
        star(draw, x + size / 2 + i * (size + gap), y + size / 2, size / 2, fill)
    return 5 * size + 4 * gap


def _digit_font(fnt):
    """Some fonts (Raleway, Georgia...) have old-style digits: the 5 drops below the line. Swap in body digits."""
    if fnt.getbbox("5")[3] > fnt.getbbox("H")[3] + fnt.size * 0.06:
        return sans(round(fnt.size * 0.98), "SemiBold")
    return fnt


def spaced(draw, xy, text, fnt, fill, spacing):
    x, y = xy
    dfont = _digit_font(fnt)
    base = y + fnt.getbbox("H")[3]  # align digit baseline with letters
    for ch in text:
        if ch.isdigit() and dfont is not fnt:
            draw.text((x, base), ch, font=dfont, fill=fill, anchor="ls")
            x += dfont.getlength(ch) + spacing
        else:
            draw.text((x, y), ch, font=fnt, fill=fill)
            x += fnt.getlength(ch) + spacing
    return x - xy[0] - spacing


def spaced_len(text, fnt, spacing):
    dfont = _digit_font(fnt)
    return sum((dfont if c.isdigit() else fnt).getlength(c) for c in text) + spacing * (len(text) - 1)


# ---------------------------------------------------------------- rich text (one highlighted phrase)
def tokens(text: str, hl: str):
    """[(piece, is_highlight, joins_previous)]. A word half inside the highlight is split
    into two pieces with no space between, so 'cleanup.' stays together on one line."""
    start = text.find(hl) if hl else -1
    end = start + len(hl) if start >= 0 else -1
    out = []
    for m in re.finditer(r"\S+", text):
        a, b = m.start(), m.end()
        if start < 0 or b <= start or a >= end:
            out.append((m.group(), False, False))
            continue
        cuts = sorted({a, b, max(a, start), min(b, end)})
        first = True
        for x, y in zip(cuts, cuts[1:]):
            out.append((text[x:y], start <= x < end, not first))
            first = False
    return out


def layout_lines(toks, fonts, width):
    """Wrap; pieces that join the previous one move with it."""
    groups, cur = [], []
    for tok in toks:
        if cur and not tok[2]:
            groups.append(cur)
            cur = []
        cur.append(tok)
    if cur:
        groups.append(cur)
    lines, line, lw = [], [], 0.0
    for g in groups:
        gw = sum(fonts[f].getlength(w_) for w_, f, _ in g)
        sp = fonts[g[0][1]].getlength(" ") if line else 0
        if line and lw + sp + gw > width:
            lines.append(line)
            line, lw, sp = [], 0.0, 0
        line.extend(g)
        lw += sp + gw
    if line:
        lines.append(line)
    return lines


def ellipsize(s: str) -> str:
    return re.sub(r"\.+$", "…", s) if s.endswith(".") else s + " …"


def fit_text(text, hl, make_fonts, width, max_h, size_max, size_min, lh):
    """Shrink until it fits; at the minimum size keep whole sentences + ellipsis."""
    for size in range(size_max, size_min - 1, -1):
        fonts = make_fonts(size)
        lines = layout_lines(tokens(text, hl), fonts, width)
        if len(lines) * size * lh <= max_h:
            return lines, fonts, size
    sents = re.findall(r"[^.!?]+[.!?]+[\"')\]]*\s*|[^.!?]+$", text) or [text]
    kept = ""
    fonts = make_fonts(size_min)
    best = layout_lines(tokens(ellipsize(sents[0].strip()), hl), fonts, width)
    for s in sents:
        trial = ellipsize((kept + s).strip())
        lines = layout_lines(tokens(trial, hl), fonts, width)
        if len(lines) * size_min * lh > max_h:
            break
        kept += s
        best = lines
    return best, fonts, size_min


def draw_lines(draw, lines, fonts, x, y, size, lh, colors, align="left", width=0):
    for line in lines:
        lx = x
        for i, (w_, f, join) in enumerate(line):
            if i and not join:
                lx += fonts[f].getlength(" ")
            draw.text((lx, y), w_, font=fonts[f], fill=colors[f])
            lx += fonts[f].getlength(w_)
        y += size * lh
    return y


# ---------------------------------------------------------------- layouts
def hero(bg, logo_white, c, r, swipe=""):
    img = bg.copy()
    img.alpha_composite(vgradient([(0, 0), (0.24, 0), (0.38, 89), (0.66, 240), (1, 255)], c["darker"]))
    img.alpha_composite(vgradient([(0, 190), (0.26, 0), (1, 0)], c["darker"]))
    if logo_white is not None:
        paste_h(img, logo_white, 140, (W // 2, 64), "mt")
    d = ImageDraw.Draw(img)
    side = 104
    lines, fonts, size = fit_text(r["quote"], r.get("hl", ""), lambda s: {False: serif(s), True: serif(s, italic=True)},
                                  W - 2 * side, 360, 60, 40, 1.22)
    block_h = len(lines) * size * 1.22
    top = 780 + (360 - block_h) / 2
    sw = stars(d, side, top - 70, 30, rgb(c["accent_light"]))
    spaced(d, (side + sw + 20, top - 70 + 3), f"{r.get('source', 'Google')} Review".upper(), label_font(23), rgb(c["accent_light"]), 5)
    draw_lines(d, lines, fonts, side, top, size, 1.22, {False: (255, 255, 255, 255), True: rgb(c["accent_light"])})
    d.rectangle((side, 1180, side + 90, 1183), fill=rgb(c["accent"]))
    spaced(d, (side, 1205), (r.get("name") or r["_fallback"]).upper(), label_font(26), (255, 255, 255, 255), 4)
    d.text((side, 1245), r["_srcline"], font=sans(22, "Light"), fill=(255, 255, 255, 190))
    if swipe:
        t = swipe.upper()
        f = label_font(21, 600)
        col = rgb(c["accent_light"])
        x_end = W - side
        spaced(d, (x_end - 44 - spaced_len(t, f, 3), 1212), t, f, col, 3)
        ay = 1224  # drawn arrow (fonts may lack the arrow glyph)
        d.line((x_end - 30, ay, x_end - 4, ay), fill=col, width=3)
        d.polygon([(x_end + 2, ay), (x_end - 10, ay - 8), (x_end - 10, ay + 8)], fill=col)
    return img


def bubble(bg, logo_white, c, r, title):
    img = bg.copy()
    img.alpha_composite(vgradient([(0, 0), (0.38, 0), (0.62, 140), (0.86, 245), (1, 255)], c["darker"]))
    side, pad = 110, 60
    inner_w = W - 2 * side - 2 * pad
    lines, fonts, size = fit_text(r["quote"], r.get("hl", ""), lambda s: {False: sans(s), True: sans(s, "SemiBold")},
                                  inner_w, 470, 34, 27, 1.5)
    text_h = len(lines) * size * 1.5
    box_top, box_h = 110, 56 + 84 + 30 + text_h + 56
    box = (side, box_top, W - side, box_top + box_h)
    # shadow
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((box[0], box[1] + 24, box[2], box[3] + 24), 8, fill=rgb(c["darker"], 110))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(28)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, 6, fill=(255, 255, 255, 255))
    d.polygon([(side + 90, box[3] - 1), (side + 186, box[3] - 1), (side + 90, box[3] + 78)], fill=(255, 255, 255, 255))
    ax, ay = side + pad, box_top + 56
    d.ellipse((ax, ay, ax + 84, ay + 84), fill=rgb(c["dark"]))
    name = r.get("name") or r["_fallback"]
    d.text((ax + 42, ay + 44), name.strip()[0].upper(), font=sans(40, "SemiBold"), fill=rgb(c["accent_light"]), anchor="mm")
    nx = ax + 84 + 24
    d.text((nx, ay + 2), name, font=sans(30, "SemiBold"), fill=(29, 39, 51, 255))
    sw = stars(d, nx, ay + 46, 30, rgb(c["accent"]), 5)
    d.text((nx + sw + 16, ay + 49), r["_srcline"], font=sans(20), fill=(74, 85, 99, 255))
    draw_lines(d, lines, fonts, ax, ay + 84 + 30, size, 1.5, {False: (29, 39, 51, 255), True: rgb(c["dark"])})
    spaced(d, (side, 1150), f"5-star {r.get('source', 'Google')} review".upper(), label_font(25), rgb(c["accent_light"]), 5)
    d.text((side, 1190), title, font=serif(64, weight=500), fill=(255, 255, 255, 255))
    if logo_white is not None:
        paste_h(img, logo_white, 140, (W - 100, H - 80 - 140), "rt", max_w=300)
    return img


def solid(bg, logo_white, c, r, title):
    """No photo: brand color background, big quote mark. Good when there are no usable photos."""
    img = Image.new("RGBA", (W, H), rgb(c["dark"]))
    img.alpha_composite(vgradient([(0, 0), (1, 255)], c["darker"]))
    d = ImageDraw.Draw(img)
    side = 110
    d.text((side - 10, 120), "\u201c", font=serif(300), fill=rgb(c["accent"], 235))
    lines, fonts, size = fit_text(r["quote"], r.get("hl", ""), lambda s: {False: serif(s), True: serif(s, italic=True)},
                                  W - 2 * side, 560, 58, 34, 1.3)
    block_h = len(lines) * size * 1.3
    top = 400 + (560 - block_h) / 2
    draw_lines(d, lines, fonts, side, top, size, 1.3, {False: (255, 255, 255, 255), True: rgb(c["accent_light"])})
    y = 1040
    sw = stars(d, side, y, 30, rgb(c["accent_light"]))
    spaced(d, (side + sw + 20, y + 3), f"{r.get('source', 'Google')} Review".upper(), label_font(23), rgb(c["accent_light"]), 5)
    d.rectangle((side, y + 70, side + 90, y + 73), fill=rgb(c["accent"]))
    spaced(d, (side, y + 95), (r.get("name") or r["_fallback"]).upper(), label_font(26), (255, 255, 255, 255), 4)
    d.text((side, y + 135), r["_srcline"], font=sans(22, "Light"), fill=(255, 255, 255, 190))
    if logo_white is not None:
        paste_h(img, logo_white, 120, (W - side, y + 60), "rt", max_w=300)
    return img


def cover_box(photo_img: Image.Image, w: int, h: int) -> Image.Image:
    """Re-crop an already 4:5 covered photo to a w x h band, keeping the middle."""
    scale = max(w / photo_img.width, h / photo_img.height)
    im = photo_img.resize((round(photo_img.width * scale), round(photo_img.height * scale)), Image.LANCZOS)
    left, top = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))


def tag(d, x, y, text, fnt, bg, fg=(255, 255, 255, 255), padx=18, pady=10):
    """Small filled label, like 'From Our Wichita Market:'. Returns its bottom y."""
    tw = fnt.getlength(text)
    asc = fnt.getbbox("Hg")[3]
    d.rectangle((x, y, x + tw + 2 * padx, y + asc + 2 * pady), fill=bg)
    d.text((x + padx, y + pady), text, font=fnt, fill=fg)
    return y + asc + 2 * pady


def market(bg, logo_white, c, r, title):
    """The brand's own testimonial look: accent strip with logo, title, location tag,
    the best line in a dark box, then the full review."""
    INK = rgb(c["dark"])
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    strip_w = 250
    grad = Image.new("RGBA", (strip_w, H))
    a, b = rgb(c["accent"]), rgb(c["accent_light"])
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        t = y / (H - 1)
        gd.line((0, y, strip_w, y), fill=tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,))
    img.alpha_composite(grad)
    d = ImageDraw.Draw(img)
    if logo_white is not None:
        paste_h(img, logo_white, 110, (strip_w // 2, H - 90 - 110), "mt", max_w=190)
    x0, right = 320, W - 70
    y = 92
    full = r["quote"]
    best = r.get("_hook") or r.get("_best") or full
    show_full = words(full) > words(best) + 2
    tsize = 64 if show_full else 76
    tf = serif(tsize, weight=800)
    for line in layout_lines(tokens(title, ""), {False: tf}, right - x0):
        d.text((x0, y), " ".join(w_ for w_, _, _ in line), font=tf, fill=INK)
        y += tsize * 1.1
    y += 10
    if r.get("_loctag"):
        tf_ = sans(26, "SemiBold")
        ty = y
        y = tag(d, x0, y, r["_loctag"], tf_, rgb(c["accent_light"]))
        if r.get("_jobtag"):
            jx = x0 + tf_.getlength(r["_loctag"]) + 36 + 10
            if jx + tf_.getlength(r["_jobtag"]) + 36 > right:
                y = tag(d, x0, y + 8, r["_jobtag"], tf_, INK)
            else:
                tag(d, jx, ty, r["_jobtag"], tf_, INK)
        y += 44
    else:
        y += 30
    # dark box with the hook, bleeding over the strip (left out on a carousel's 2nd slide: slide 1 already shows it)
    bx0, bx1, pad = 200, W - 70, 44
    nobox = r.get("_nobox") and show_full
    if nobox:
        y += 10
    lines, fonts, size = ([], {}, 0) if nobox else fit_text("“" + best + "”", r.get("hl", ""), lambda s_: {False: serif(s_, weight=700), True: serif(s_, weight=800)},
                                  bx1 - bx0 - 2 * pad, (250 if show_full and words(full) > 70 else 330), 66 if words(best) > 6 else 84, 40, 1.18)
    if not nobox:
        bh = len(lines) * size * 1.18 + 2 * pad - size * 0.18
        d.rectangle((bx0, y, bx1, y + bh), fill=INK)
        draw_lines(d, lines, fonts, bx0 + pad, y + pad - size * 0.08, size, 1.18, {False: (255, 255, 255, 255), True: rgb(c["accent_light"])})
        y += bh + 44
    bottom = H - 140
    if show_full:
        y = tag(d, x0, y, r.get("_subtag", "In their words"), sans(24, "SemiBold"), rgb(c["accent_light"])) + 26
        body = "“" + full + "”"
        bx = x0
        lines, fonts, size = fit_text(body, r.get("hl", "") if nobox else "", lambda s_: {False: sans(s_), True: sans(s_, "SemiBold")}, right - bx, bottom - y - 10, 40 if nobox else 34, 19, 1.42)
        y = draw_lines(d, lines, fonts, bx, y, size, 1.42, {False: (51, 60, 74, 255), True: rgb(c["accent"])}) + 14
    sy = max(y + 6, bottom - 6) if not show_full else bottom
    sw = stars(d, x0, sy, 28, rgb(c["accent"]), 5)
    d.text((x0 + sw + 18, sy - 2), "— " + (r.get("name") or r["_fallback"]), font=sans(28, "SemiBold"), fill=INK)
    d.text((x0, sy + 46), r["_srcline"], font=sans(21), fill=(96, 106, 120, 255))
    return img


def split(bg, logo_white, c, r, title):
    """Job photo on top, white panel below with location tag, stars, quote and name."""
    INK = rgb(c["dark"])
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    ph = 690
    img.alpha_composite(cover_box(bg, W, ph))
    img.alpha_composite(vgradient([(0, 120), (0.16, 0), (1, 0)], c["darker"]).crop((0, 0, W, ph)))
    if logo_white is not None:
        paste_h(img, logo_white, 96, (64, 50), "lt", max_w=240)
    d = ImageDraw.Draw(img)
    side = 80
    y = ph - 30
    label = r.get("_loctag") or f"5-Star {r.get('source', 'Google')} Review"
    tf_ = sans(26, "SemiBold")
    ty = y
    y = tag(d, side, y, label, tf_, rgb(c["accent_light"]), padx=20, pady=12)
    if r.get("_jobtag"):
        jx = side + tf_.getlength(label) + 40 + 12
        if jx + tf_.getlength(r["_jobtag"]) + 40 > W - side:  # no room: second line
            y = tag(d, side, y + 8, r["_jobtag"], tf_, INK, padx=20, pady=12)
        else:
            tag(d, jx, ty, r["_jobtag"], tf_, INK, padx=20, pady=12)
    y += 40
    stars(d, side, y, 34, rgb(c["accent"]), 7)
    y += 34 + 34
    bottom = H - 165
    lines, fonts, size = fit_text("“" + r["quote"] + "”", r.get("hl", ""), lambda s_: {False: serif(s_, weight=700), True: serif(s_, weight=800)},
                                  W - 2 * side, bottom - y, 76, 30, 1.18)
    block = len(lines) * size * 1.18
    draw_lines(d, lines, fonts, side, y + max(0, (bottom - y - block) / 2 - 10), size, 1.18, {False: INK, True: rgb(c["accent"])})
    d.rectangle((side, H - 140, side + 80, H - 136), fill=rgb(c["accent"]))
    d.text((side, H - 118), r.get("name") or r["_fallback"], font=sans(30, "SemiBold"), fill=INK)
    d.text((side, H - 76), r["_srcline"], font=sans(22), fill=(96, 106, 120, 255))
    return img


LAYOUT_FN = {"hero": lambda bg, lw, c, r, t: hero(bg, lw, c, r), "bubble": bubble, "solid": solid,
             "market": market, "split": split}


# ---------------------------------------------------------------- batch
def review_key(r):
    text = re.sub(r"\s+", " ", r["quote"].strip())[:80]
    base = f"{r.get('source', '')}|{r.get('name', '')}|{text}"
    return hashlib.sha1(base.lower().encode()).hexdigest()[:16]


def apply_edits(r):
    edits = r.get("edits") or []
    for e in edits:
        if (not e["to"].strip() and re.search(r"[A-Za-z]", e["from"])) or re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", e["to"]):
            sys.exit(f"Edit '{e['to']}': use a plain role word (e.g. 'Two reps', 'The crew lead'), never a guessed name.")
        if e["from"] not in r["quote"]:
            sys.exit(f"'{e['from']}' is not in the review text.")
    r = dict(r)
    for fld in ("quote", "excerpt", "hl"):
        if r.get(fld):
            for e in edits:
                r[fld] = r[fld].replace(e["from"], e["to"].strip())
            r[fld] = re.sub(r"\s+([,.!?])", r"\1", re.sub(r"\s{2,}", " ", r[fld])).strip()
    return r


def mix_order(paths):
    """Spread similar photos apart: alternate between name groups (city-..., dji-...) instead of A-Z."""
    groups = {}
    for p in sorted(paths):
        key = p.stem.split("-")[0]
        groups.setdefault(key, []).append(p)
    out, queues = [], [g for _, g in sorted(groups.items())]
    while any(queues):
        for q in queues:
            if q:
                out.append(q.pop(0))
    return out


def first_sentences(text, limit):
    sents = re.findall(r"[^.!?]+[.!?]+[\"')\]]*\s*|[^.!?]+$", text) or [text]
    out = ""
    for s in sents:
        if out and words(out + s) > limit:
            break
        out += s
    return out.strip()



# ---------------------------------------------------------------- job type (commercial / residential / multifamily)
JOB_WORDS = {
    "commercial": r"\b(building|buildings|office|offices|warehouse|church|school|college|campus|store|retail|restaurant|hotel|"
                  r"(?:our|my|their) business|business owners?|vendors?|facility|facilities|plant|tenants?|property manager|building manager|commercial|"
                  r"tpo|epdm|pvc|membrane|flat roof|modified bitumen|coating|medical|clinic|hospital|sq ?ft|square feet|stor(e)?y)\b",
    "multifamily": r"\b(hoa|homeowners? association|apartments?|apartment complex|condo(minium)?s?|complex|townhomes?|townhouses?|"
                   r"units|residents|multi-?family|property management)\b",
    "residential": r"\b(my house|our house|my home|our home|house|home|homeowner|shingles?|gutters?|garage|my roof|our roof|"
                   r"family|neighbor|neighbors|closing|attic|chimney|insurance)\b",
}


def detect_job(text: str) -> tuple[str, str]:
    """Best guess from the review's own words. Returns (job, the words that decided it)."""
    t = text.lower()
    hits = {k: re.findall(rx, t) for k, rx in JOB_WORDS.items()}
    flat = lambda k: sorted({h if isinstance(h, str) else h[0] for h in hits[k]})
    score = {k: len(v) for k, v in hits.items()}
    score["commercial"] *= 1.5   # strong words: one 'TPO' or 'office building' beats a stray 'home'
    score["multifamily"] *= 1.5
    strong_mf = re.findall(r"\b(hoa|homeowners? association|apartments?|condo(?:minium)?s?|townhomes?|townhouses?|multi-?family)\b", t)
    house = re.search(r"\b(my|our) (house|home)\b", t)
    if strong_mf and house and set(strong_mf) <= {"hoa", "homeowners association", "homeowner association"}:
        return "residential", f"{house.group(0)} (a house in an HOA)"
    if strong_mf:  # an HOA or condo job is multifamily even when the review says 'building' or 'TPO'
        return "multifamily", ", ".join(sorted(set(strong_mf)))
    best = max(score, key=score.get)
    if score[best] == 0:
        return "residential", "no clues; most reviews are homes"
    return best, ", ".join(flat(best))


def photos_for(pdir: Path, job: str, L, fallbacks: dict):
    """Background pool for this post: photos/<location>/ (filtered by job prefix) and photos/<job>/,
    falling back along `fallbacks` and finally to any photo at the top of photos/."""
    def imgs(d):
        return sorted(p for p in d.glob("*") if p.suffix.lower() in PHOTO_EXT) if d.is_dir() else []
    loc = []
    if L:
        loc_all = imgs(pdir / L["slug"])
        loc = [p for p in loc_all if not job or p.stem.startswith(job) or not any(p.stem.startswith(j) for j in JOB_WORDS)]
    pool = []
    for j in ([job] if job else []) + fallbacks.get(job, []):
        pool = imgs(pdir / j)
        if pool:
            break
    if not pool:
        pool = mix_order(imgs(pdir)) or mix_order(sum((imgs(pdir / j) for j in JOB_WORDS), []))
    return loc, pool


def _loc_of(cfg, r):
    k = str(r.get("location", "")).lower()
    return next((L for L in cfg.get("locations", []) if k and k in (L.get("slug", "").lower(), L.get("name", "").lower())), None)


EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B50\u2B55\uFE0F\u200D]")


def _decorate(r, L, cfg):
    """Fill the text bits every layout uses: source line, location tag, best line."""
    r.setdefault("_orig", r["quote"])  # the sheet and captions keep the review exactly as written
    for f in ("quote", "excerpt", "hl", "hook"):  # the fonts have no emoji: drop them from the image text only
        if r.get(f):
            r[f] = re.sub(r"[ \t]{2,}", " ", EMOJI.sub("", r[f])).strip()
    src = r.get("source", "Google")
    r["_srcline"] = f"{src} review \u00b7 {L['name']}" if L else "Posted on " + src  # date stays in the sheet, not on the image
    r["_loctag"] = (L.get("tag") or cfg.get("location_tag", "{name}").format(name=L["name"])) if L else ""
    r["_subtag"] = cfg.get("subtag", "In their words")
    r["_best"] = r.get("excerpt") or (r["quote"] if words(r["quote"]) <= 32 else first_sentences(r["quote"], 28))
    r["_hook"] = make_hook(r, cfg.get("hook_max_words", 12))
    return r


def make_hook(r, max_w=12):
    """The single attention-grabbing line shown big. Uses the review's 'hook' when given;
    otherwise the whole review if it is short, else the short sentence holding the highlight."""
    if r.get("hook"):
        h = r["hook"].strip()
        return h[0].upper() + h[1:]
    q = r["quote"].strip()
    if words(q) <= max_w:
        return q
    sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", q) if 3 <= words(x) <= max_w]
    hl = r.get("hl", "")
    for x in sents:
        if hl and hl in x:
            return x
    if sents:
        return sents[0]
    return hl or " ".join(q.split()[:max_w]) + "…"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reviews", nargs="?")
    ap.add_argument("--folder", required=True, help="business folder with settings.json, logo and photos/")
    ap.add_argument("--template", choices=["auto", "bubble", "hero", "solid", "market", "split"])
    ap.add_argument("--job", choices=["commercial", "residential", "multifamily"], help="force this job type for the whole batch")
    ap.add_argument("--location", help="only this location (slug or name from settings.json \"locations\")")
    ap.add_argument("--preview", action="store_true", help="one sample post per layout, for setup")
    ap.add_argument("--carousel", choices=["off", "long-only", "always"])
    ap.add_argument("--include-seen", action="store_true")
    a = ap.parse_args()

    folder = Path(a.folder).expanduser()
    cfg = json.loads((folder / "settings.json").read_text())
    set_fonts(folder, cfg.get("fonts", {}))
    HEAD_WEIGHT[0] = int(cfg.get("head_weight", 400))
    c = {**DEFAULT_COLORS, **cfg.get("colors", {})}
    template = a.template or cfg.get("template", "auto")
    carousel = a.carousel or cfg.get("carousel", "long-only")
    short = int(cfg.get("short_quote_words", 32))
    hook_max = int(cfg.get("hook_max_words", 12))
    long_words = int(cfg.get("carousel_min_words", 70))  # only really long reviews become 2-slide carousels
    brand = cfg.get("business_name", "")

    logo_path = folder / cfg.get("logo", "logo.png")
    logo_white = logo_on_dark(logo_path, cfg.get("logo_style", "white")) if logo_path.is_file() else None
    pdir = folder / cfg.get("photos_folder", "photos")
    photos = mix_order(p for p in pdir.glob("*") if p.suffix.lower() in PHOTO_EXT) if pdir.exists() else []  # top level only; review photos live in photos/from-reviews/
    focus = cfg.get("photo_focus", {})
    locs = {}
    for L in cfg.get("locations", []):
        for k in (L.get("slug", ""), L.get("name", "")):
            if k:
                locs[k.lower()] = L
    auto = {"short": "hero", "long": "bubble", **cfg.get("auto", {})}
    car_slides = cfg.get("carousel_slides", ["hero", "bubble"])
    loc_count: dict = {}
    rot_file, seen_file = folder / ".photo-rotation", folder / "seen.json"
    try:
        rot = json.loads(rot_file.read_text()) if rot_file.exists() else {}
        rot = rot if isinstance(rot, dict) else {"all": int(rot)}
    except ValueError:
        rot = {}
    jobs_on = bool(cfg.get("job_types"))
    job_labels = {k: v.get("label", k.title()) for k, v in (cfg.get("job_types") or {}).items()}
    fallbacks = {k: v.get("fallback", []) for k, v in (cfg.get("job_types") or {}).items()}
    seen = json.loads(seen_file.read_text()) if seen_file.exists() else {}
    if a.preview:
        return preview(folder, cfg, c, brand, logo_white, photos, focus, a.reviews)
    if not a.reviews:
        sys.exit("Give the reviews file, or use --preview.")

    only = locs.get((a.location or "").lower()) if a.location else None
    if a.location and not only:
        sys.exit(f"Unknown location '{a.location}'. Known: " + ", ".join(L.get("slug", "") for L in cfg.get("locations", [])))
    out = folder / "posts" / (dt.date.today().isoformat() + (f"-{only['slug']}" if only else ""))
    out.mkdir(parents=True, exist_ok=True)
    rows, md, skipped, n = [], [f"# {brand} review posts, {dt.date.today():%d %b %Y}\n"], [], 0

    for raw in json.loads(Path(a.reviews).read_text()):
        key = review_key(raw)
        if key in seen and not a.include_seen:
            skipped.append(raw.get("name") or "a review")
            continue
        for fld in ("excerpt", "hl", "hook"):
            v = raw.get(fld) or ""
            if v and v not in raw["quote"] and (v[:1].lower() + v[1:]) not in raw["quote"]:
                sys.exit(f"{raw.get('name')}: '{fld}' must be copied word for word from the review.")
        if words(raw.get("hook") or "") > hook_max + 2:
            sys.exit(f"{raw.get('name')}: the hook has {words(raw['hook'])} words; keep it to {hook_max} or fewer.")
        r = apply_edits(raw)
        edit_note = "; ".join(f"'{e['from']}' -> '{e['to']}'" for e in raw.get("edits") or [])
        r["_fallback"] = f"{brand} customer" if brand else "Happy customer"
        L = locs.get(str(r.get("location", "")).lower())
        if r.get("location") and locs and not L:
            sys.exit(f"{raw.get('name')}: unknown location '{r['location']}'.")
        if only and L is not only:
            continue
        _decorate(r, L, cfg)
        n += 1
        own = folder / r["photo"] if r.get("photo") else None
        job, job_why = "", ""
        if jobs_on:
            if a.job:
                job, job_why = a.job, "set for this batch"
            elif r.get("job"):
                job, job_why = r["job"], "set by hand"
            else:
                job, job_why = detect_job(r["quote"])
                job_why = "auto: " + job_why
            if job not in JOB_WORDS:
                sys.exit(f"{raw.get('name')}: job must be commercial, residential or multifamily, not '{job}'.")
            r["_jobtag"] = job_labels.get(job, "")
        lphotos, pool = photos_for(pdir, job, L, fallbacks) if jobs_on else ([], photos)
        lp_key = f"loc:{L['slug']}:{job}" if L else ""
        if own and own.is_file():  # the reviewer's own photo of the job beats any rotation
            bg = cover(own, r.get("photo_focus", "50% 50%"))
            src_photo = r["photo"]
        elif lphotos and (rot.get(lp_key + ":turn", 0) % 2 == 0 or not pool):  # this location's own photos, every other post
            p = lphotos[rot.get(lp_key, 0) % len(lphotos)]
            rot[lp_key] = rot.get(lp_key, 0) + 1
            rot[lp_key + ":turn"] = rot.get(lp_key + ":turn", 0) + 1
            bg, src_photo = cover(p, focus.get(p.name, "50% 50%")), p.relative_to(pdir).as_posix()
        elif pool:
            if lp_key:
                rot[lp_key + ":turn"] = rot.get(lp_key + ":turn", 0) + 1
            p = pool[rot.get(job or "all", 0) % len(pool)]
            rot[job or "all"] = rot.get(job or "all", 0) + 1
            bg, src_photo = cover(p, focus.get(p.name, "50% 50%")), p.relative_to(pdir).as_posix()
        else:  # no photos yet: plain brand background
            bg = Image.new("RGBA", (W, H), rgb(c["dark"]))
            src_photo = ""
        slug = re.sub(r"[^a-z0-9]+", "-", (r.get("name") or f"review-{n}").lower()).strip("-")
        is_long = words(r["quote"]) > long_words
        shown = r.get("excerpt") or r["quote"]
        slides = []
        if carousel == "always" or (carousel == "long-only" and is_long):
            teaser = r["_hook"]
            r1 = {**r, "quote": teaser, "hl": r.get("hl", "") if r.get("hl", "") in teaser else ""}
            if car_slides[0] == "hero":
                slides.append(hero(bg, logo_white, c, r1, cfg.get("swipe_text", "")))
            else:
                slides.append(LAYOUT_FN[car_slides[0]](bg, logo_white, c, r1, cfg.get("bubble_title", "Client Review")))
            slides.append(LAYOUT_FN[car_slides[1]](bg, logo_white, c, {**r, "_nobox": True}, cfg.get("bubble_title", "Client Review")))
        else:
            if template != "auto":
                pick = template
            elif auto["long"] == "market":  # market shows the best line AND the full review, so judge by the full text
                pick = auto["short"] if words(r["quote"]) <= short else "market"
            else:
                pick = auto["short"] if words(shown) <= short else auto["long"]
            if pick == "market":
                rr = r
            elif pick == "bubble":
                rr = {**r, "quote": shown}
            else:  # big-quote layouts show only the hook
                rr = {**r, "quote": r["_hook"], "hl": r.get("hl", "") if r.get("hl", "") in r["_hook"] else ""}
            slides.append(LAYOUT_FN[pick](bg, logo_white, c, rr, cfg.get("bubble_title", "Client Review")))
        files = []
        for i, im in enumerate(slides, 1):
            name = f"{n:02d}-{slug}{'-' + str(i) if len(slides) > 1 else ''}.png"
            im.convert("RGB").save(out / name, optimize=True)
            files.append(name)
            print(out / name)
        kind = "Carousel" if len(files) > 1 else "Single image"
        cap = r.get("caption", "").strip()
        md.append(f"## {n:02d}. {r.get('name') or 'Customer'} ({(L['name'] + ', ') if L else ''}{(job + ', ') if job else ''}{r.get('source', 'Google')}{', ' + r['date'] if r.get('date') else ''})\n"
                  f"{kind}: {', '.join(files)}\n\n" + (f"**Edited:** {edit_note} (the review site hid these names)\n\n" if edit_note else "") + f"**Caption**\n\n{cap or '(no caption yet)'}\n\n**Full review**\n\n> {r['_orig']}\n")
        rows.append({"post": n, "files": " ".join(files), "type": kind, "location": L.get("name", "") if L else "", "job type": f"{job} ({job_why})" if job else "", "background": src_photo, "source": r.get("source", "Google"),
                     "reviewer": r.get("name", ""), "date": r.get("date", ""), "review": r["_orig"], "caption": cap,
                     "edits (blurred names replaced)": edit_note, "approve (Y/N)": "", "posted (date)": ""})
        seen[key] = {"name": r.get("name", ""), "source": r.get("source", ""), "made": dt.date.today().isoformat()}

    rot_file.write_text(json.dumps(rot))
    seen_file.write_text(json.dumps(seen, indent=2) + "\n")
    if rows:
        (out / "captions.md").write_text("\n".join(md))
        with (out / "approval.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(f"\nDONE: {len(rows)} post(s) in {out}")
    if skipped:
        print(f"Skipped {len(skipped)} already made before: {', '.join(skipped)}")
    if rows and not any(x["background"] for x in rows) and template != "solid":
        print("NOTE: no photos found, so a plain brand background was used. Add photos to the photos folder, or use --template solid.")
    if logo_white is None:
        print("NOTE: no logo found. Add the logo file and set its name in settings.json.")


SAMPLE = {"source": "Google", "name": "Sam P.",
          "quote": "They showed up on time, explained every step, and left the place spotless. Best experience we have had with any company.",
          "hl": "left the place spotless"}
SAMPLE_LONG = {"source": "Google", "name": "Jordan K.",
               "quote": ("From the first call to the final walkthrough, the whole team was professional and easy to work with. "
                         "They gave us a clear quote with no surprises, finished a day early, and cleaned up so well you would never know they had been here. "
                         "When we had a small question a week later, they came back the same day. We have already recommended them to three neighbors."),
               "hl": "finished a day early"}


def preview(folder, cfg, c, brand, logo_white, photos, focus, reviews_file):
    """Setup helper: the same sample review in every layout, with this brand's logo, colors, fonts and photos."""
    out = folder / "setup-previews"
    out.mkdir(exist_ok=True)
    real = json.loads(Path(reviews_file).read_text()) if reviews_file else []
    short_r = next((x for x in real if words(x["quote"]) <= 32), SAMPLE)
    long_r = next((x for x in real if words(x["quote"]) > 70), SAMPLE_LONG)
    fb = {"_fallback": f"{brand} customer" if brand else "Happy customer"}
    title = cfg.get("bubble_title", "Client Review")

    def bg_for(i, rv=None):
        if cfg.get("job_types") and rv is not None:
            L = _loc_of(cfg, rv)
            job = rv.get("job") or detect_job(rv["quote"])[0]
            loc, pool = photos_for(folder / cfg.get("photos_folder", "photos"), job, L, {k: v.get("fallback", []) for k, v in cfg["job_types"].items()})
            cands = loc + pool
            if cands:
                p = cands[i % len(cands)]
                return cover(p, focus.get(p.name, "50% 50%"))
        if not photos:
            return Image.new("RGBA", (W, H), rgb(c["dark"]))
        p = photos[i % len(photos)]
        return cover(p, focus.get(p.name, "50% 50%"))

    jobs = [("1-big-quote-on-photo", "hero", short_r, 0), ("2-review-card-on-photo", "bubble", long_r, 1),
            ("3-no-photo-brand-color", "solid", short_r, 0)]
    if cfg.get("locations"):  # brand-style layouts are worth showing when the brand has markets
        jobs += [("5-photo-and-quote", "split", short_r, 3), ("6-testimonial-card", "market", long_r, 4)]
    L0 = (cfg.get("locations") or [None])[0]
    for name, lay, rv, i in jobs:
        r = _decorate({**apply_edits(rv), **fb}, _loc_of(cfg, rv) or L0, cfg)
        if lay not in ("bubble", "market"):
            r["quote"], r["hl"] = r["_hook"], (r.get("hl", "") if r.get("hl", "") in r["_hook"] else "")
        if cfg.get("job_types"):
            r["_jobtag"] = cfg["job_types"].get(rv.get("job") or detect_job(rv["quote"])[0], {}).get("label", "")
        LAYOUT_FN[lay](bg_for(i, rv), logo_white, c, r, title).convert("RGB").save(out / f"{name}.png", optimize=True)
        print(out / f"{name}.png")
    r = _decorate({**apply_edits(long_r), **fb}, _loc_of(cfg, long_r) or L0, cfg)
    teaser = r["_hook"]
    if cfg.get("job_types"):
        r["_jobtag"] = cfg["job_types"].get(long_r.get("job") or detect_job(long_r["quote"])[0], {}).get("label", "")
    hero(bg_for(2, long_r), logo_white, c, {**r, "quote": teaser, "hl": r["hl"] if r.get("hl", "") in teaser else ""}).convert("RGB").save(out / "4-carousel-slide-1.png", optimize=True)
    bubble(bg_for(2, long_r), logo_white, c, r, title).convert("RGB").save(out / "4-carousel-slide-2.png", optimize=True)
    print(out / "4-carousel-slide-1.png", out / "4-carousel-slide-2.png", sep="\n")
    print(f"\nPREVIEWS in {out}")


if __name__ == "__main__":
    main()
