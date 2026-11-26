#!/usr/bin/env python3
"""Витягти кольорову палітру буклета з титульної ілюстрації.

Пише JSON з ролями кольорів: page_bg, panel_bg, ink, heading, rule, frame, muted.
Залежності: лише stdlib + системний `sips` (macOS) для зменшення зображення.

    python3 palette.py cover.png > palette.json
    python3 palette.py cover.png --out palette.json
"""

import argparse
import colorsys
import json
import os
import struct
import subprocess
import sys
import tempfile
import zlib

THUMB = 64
K = 6
ITERS = 24


# ---------------------------------------------------------------- PNG reading

def _sips_thumb(path, size=THUMB):
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    subprocess.run(
        ["sips", "-s", "format", "png", "-z", str(size), str(size), path, "--out", tmp],
        check=True, capture_output=True,
    )
    return tmp


def _read_png(path):
    """Мінімальний декодер PNG -> (width, height, [(r,g,b,a), ...])."""
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("не PNG: %s" % path)
    pos, idat = 8, bytearray()
    w = h = depth = ctype = interlace = None
    palette = None
    trns = None
    while pos + 8 <= len(data):
        (ln,) = struct.unpack(">I", data[pos:pos + 4])
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if typ == b"IHDR":
            w, h, depth, ctype, _comp, _filt, interlace = struct.unpack(">IIBBBBB", chunk)
        elif typ == b"PLTE":
            palette = chunk
        elif typ == b"tRNS":
            trns = chunk
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
    if depth != 8 or interlace:
        raise ValueError("підтримується лише 8-біт, без interlace (отримано depth=%s)" % depth)

    nch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(bytes(idat))
    stride = w * nch
    out = bytearray(h * stride)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        ftype = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        if ftype == 1:
            for i in range(nch, stride):
                line[i] = (line[i] + line[i - nch]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                b = prev[i]
                c = prev[i - nch] if i >= nch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line

    px = []
    for i in range(0, len(out), nch):
        s = out[i:i + nch]
        if ctype == 2:
            px.append((s[0], s[1], s[2], 255))
        elif ctype == 6:
            px.append((s[0], s[1], s[2], s[3]))
        elif ctype == 0:
            px.append((s[0], s[0], s[0], 255))
        elif ctype == 4:
            px.append((s[0], s[0], s[0], s[1]))
        elif ctype == 3:
            j = s[0] * 3
            a = trns[s[0]] if trns and s[0] < len(trns) else 255
            px.append((palette[j], palette[j + 1], palette[j + 2], a))
    return w, h, px


# ------------------------------------------------------------------ кластери

def _lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _sat(c):
    return colorsys.rgb_to_hls(c[0] / 255, c[1] / 255, c[2] / 255)[2]


def _kmeans(pixels, k=K, iters=ITERS):
    """Детермінований k-means: центроїди засіяні рівномірно за яскравістю."""
    ordered = sorted(pixels, key=_lum)
    step = max(1, len(ordered) // k)
    cents = [ordered[min(len(ordered) - 1, i * step + step // 2)][:3] for i in range(k)]
    clusters = [[c, 0] for c in cents]
    for _ in range(iters):
        acc = [[0, 0, 0, 0] for _ in range(k)]
        for p in pixels:
            best, bd = 0, 1e18
            for i, (c, _n) in enumerate(clusters):
                d = (p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2
                if d < bd:
                    best, bd = i, d
            a = acc[best]
            a[0] += p[0]; a[1] += p[1]; a[2] += p[2]; a[3] += 1
        moved = False
        for i, a in enumerate(acc):
            if a[3] == 0:
                continue
            new = (a[0] // a[3], a[1] // a[3], a[2] // a[3])
            if new != clusters[i][0]:
                moved = True
            clusters[i] = [new, a[3]]
        if not moved:
            break
    return sorted([c for c in clusters if c[1] > 0], key=lambda c: -c[1])


# -------------------------------------------------------------- ролі кольорів

def _hex(c):
    return "#%02x%02x%02x" % (max(0, min(255, int(c[0]))),
                              max(0, min(255, int(c[1]))),
                              max(0, min(255, int(c[2]))))


def _shift(rgb, light=None, sat_mul=1.0, sat=None):
    """Змінити світлоту/насиченість, зберігши відтінок."""
    h, l, s = colorsys.rgb_to_hls(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
    if light is not None:
        l = light
    s = s * sat_mul if sat is None else sat
    s = max(0.0, min(1.0, s))
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), s)
    return (r * 255, g * 255, b * 255)


def build_palette(image, force_mode=None):
    thumb = _sips_thumb(image)
    try:
        _w, _h, px = _read_png(thumb)
    finally:
        os.unlink(thumb)
    px = [p for p in px if p[3] > 128]
    if not px:
        raise ValueError("порожнє зображення")

    clusters = _kmeans(px)
    weights = sum(n for _c, n in clusters)
    mean_l = sum(_lum(p) for p in px) / len(px)
    mode = force_mode or ("dark" if mean_l < 108 else "light")

    # акцент — найнасиченіший кластер із помітною вагою
    accent = max(clusters, key=lambda cn: _sat(cn[0]) * (cn[1] / weights) ** 0.35)[0]
    # характерний тон — найважчий кластер у середньому діапазоні
    mids = [c for c, n in clusters if 35 < _lum(c) < 205] or [c for c, _ in clusters]
    base = mids[0]

    if mode == "dark":
        pal = {
            "mode": "dark",
            "page_bg":  _hex(_shift(base,   light=0.055, sat_mul=0.55)),
            "panel_bg": _hex(_shift(base,   light=0.115, sat_mul=0.45)),
            "ink":      _hex(_shift(base,   light=0.86,  sat=0.10)),
            "heading":  _hex(_shift(accent, light=0.80,  sat_mul=0.55)),
            "rule":     _hex(_shift(accent, light=0.45,  sat_mul=1.0)),
            "frame":    _hex(_shift(accent, light=0.42,  sat_mul=1.1)),
            "muted":    _hex(_shift(base,   light=0.62,  sat=0.12)),
        }
    else:
        pal = {
            "mode": "light",
            "page_bg":  _hex(_shift(base,   light=0.42,  sat_mul=0.95)),
            "panel_bg": _hex(_shift(base,   light=0.93,  sat_mul=0.22)),
            "ink":      _hex(_shift(base,   light=0.17,  sat_mul=0.70)),
            "heading":  _hex(_shift(base,   light=0.22,  sat_mul=0.85)),
            "rule":     _hex(_shift(accent, light=0.40,  sat_mul=0.90)),
            "frame":    _hex(_shift(accent, light=0.38,  sat_mul=1.0)),
            "muted":    _hex(_shift(base,   light=0.40,  sat=0.15)),
        }

    pal["source"] = os.path.abspath(image)
    pal["swatches"] = [{"hex": _hex(c), "weight": round(n / weights, 4)} for c, n in clusters]
    return pal


CHRISTIAN = {
    "mode": "light",
    "page_bg": "#ffffff",       # поля завжди білі
    "panel_bg": "#ebe6dc",      # RGB(235,230,220)
    "ink": "#2b2620",
    "heading": "#1f1a14",
    "rule": "#8c7f6a",
    "frame": "#ffffff",
    "muted": "#6b6154",
    "swatches": [],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--mode", choices=["light", "dark"])
    ap.add_argument("--christian", action="store_true",
                    help="фіксована палітра християнських сюжетів (ігнорує зображення)")
    a = ap.parse_args()

    if a.christian:
        pal = dict(CHRISTIAN)
    else:
        if not a.image:
            ap.error("потрібен шлях до зображення або --christian")
        pal = build_palette(a.image, a.mode)

    text = json.dumps(pal, ensure_ascii=False, indent=2)
    if a.out:
        open(a.out, "w").write(text + "\n")
        print(a.out, file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
