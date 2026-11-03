#!/usr/bin/env python3
"""Render a captured terminal 'screen' text file to a PNG (for README images).

Each line's first two characters pick the colour; the rest is printed as-is:
  "$ " command (blue)   "+ " good result (green)   "! " refused/error (red)
  "? " note (yellow)    "~ " dim (grey)            anything else: plain
Usage: python3 scripts/render_screen.py screen.txt out.png "Window title"
Needs Pillow. Falls back to Pillow's default font if Menlo isn't installed.
"""
import sys
from PIL import Image, ImageDraw, ImageFont

COLOURS = {"$ ": (122, 184, 255), "+ ": (126, 211, 133), "! ": (255, 107, 107),
           "? ": (240, 200, 100), "~ ": (150, 150, 160)}
PLAIN, BG, BAR = (225, 225, 230), (24, 26, 32), (38, 40, 48)


def load_font(size):
    for path in ("/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def parse(text):
    rows = []
    for line in text.splitlines():
        key = line[:2]
        if key in COLOURS:
            rows.append((line if key == "$ " else line[2:], COLOURS[key]))
        else:
            rows.append((line, PLAIN))
    return rows


def render(rows, title, size=22, pad=28):
    font = load_font(size)
    line_h = int(size * 1.45)
    char_w = font.getlength("M")
    width = int(max([len(t) for t, _ in rows] + [len(title) + 10]) * char_w + pad * 2)
    height = 46 + pad + line_h * len(rows) + pad
    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, 46], fill=BAR)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([20 + i * 30, 15, 36 + i * 30, 31], fill=c)
    d.text(((width - font.getlength(title)) / 2, 11), title, font=font, fill=(160, 160, 170))
    y = 46 + pad
    for text, colour in rows:
        d.text((pad, y), text, font=font, fill=colour)
        y += line_h
    return img


if __name__ == "__main__":
    src, out, title = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(src, encoding="utf-8") as fh:
        render(parse(fh.read()), title).save(out)
    print(f"wrote {out}")
