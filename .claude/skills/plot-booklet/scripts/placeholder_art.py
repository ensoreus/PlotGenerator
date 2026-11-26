#!/usr/bin/env python3
"""Тимчасова заглушка замість ілюстрації — щоб верстку можна було зібрати
й перевірити ще до того, як прийде картинка з Midjourney.

    python3 placeholder_art.py cover.png --ar 2:3 --seed "проклаття ящірки" \
        --colors "#2b6a68,#c8b48a,#1a3a38"

Пише PNG (лише stdlib: zlib + struct). Не для фінального буклета —
у фінал іде справжня ілюстрація.
"""

import argparse
import math
import struct
import zlib


def png_write(path, w, h, rows):
    raw = bytearray()
    for row in rows:
        raw.append(0)
        raw.extend(row)

    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw), 6)))
        f.write(chunk(b"IEND", b""))


def hex2rgb(s):
    s = s.strip().lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--ar", default="2:3")
    ap.add_argument("--width", type=int, default=600)
    ap.add_argument("--seed", default="")
    ap.add_argument("--colors", default="#2b6a68,#c8b48a,#1a2f2e")
    a = ap.parse_args()

    aw, ah = (int(x) for x in a.ar.split(":"))
    w = a.width
    h = int(round(w * ah / aw))
    cols = [hex2rgb(c) for c in a.colors.split(",")]
    while len(cols) < 3:
        cols.append(cols[-1])
    s = sum(ord(c) for c in a.seed) or 7

    rows = []
    for y in range(h):
        row = bytearray()
        for x in range(w):
            u, v = x / w, y / h
            t = 0.5 + 0.5 * math.sin((u * 3.1 + s * 0.11) * 2.4 + math.cos(v * 4.7 + s * 0.07) * 1.6)
            k = 0.5 + 0.5 * math.sin(v * 3.0 + s * 0.03)
            c0, c1, c2 = cols[0], cols[1], cols[2]
            for i in range(3):
                mid = c0[i] * (1 - t) + c1[i] * t
                row.append(int(max(0, min(255, mid * (1 - k * 0.55) + c2[i] * k * 0.55))))
        rows.append(row)

    png_write(a.out, w, h, rows)
    print(a.out)


if __name__ == "__main__":
    main()
