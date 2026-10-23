"""Grade the raw Unreal HDR captures into the final beauty still (run with any Python 3 + numpy + Pillow).

Exposure, ACES-style filmic tone mapping, bloom, the violet studio backdrop (the capture has no backdrop, so empty pixels are
exactly zero and make the mask),
vignette and a 2x supersampling downsample all happen here, so the look is deterministic.
"""
import os
import re
import sys

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
BEAUTY = os.path.join(HERE, '..', 'Export', 'Beauty')


def read_hdr(path):
    data = open(path, 'rb').read()
    pos = 0
    while True:  # header ends with an empty line
        end = data.index(b'\n', pos)
        line = data[pos:end]
        pos = end + 1
        if line.strip() == b'':
            break
    end = data.index(b'\n', pos)
    m = re.match(rb'-Y (\d+) \+X (\d+)', data[pos:end])
    h, w = int(m.group(1)), int(m.group(2))
    pos = end + 1
    body = np.frombuffer(data, dtype=np.uint8, offset=pos)
    if body.size == w * h * 4 and not (body[0] == 2 and body[1] == 2):
        rgbe = body.reshape(h, w, 4)
    else:  # new-style run-length encoded scanlines
        rgbe = np.zeros((h, w, 4), np.uint8)
        i = 0
        for y in range(h):
            i += 4  # 2, 2, width hi, width lo
            for c in range(4):
                x = 0
                while x < w:
                    n = body[i]; i += 1
                    if n > 128:
                        n -= 128
                        rgbe[y, x:x + n, c] = body[i]; i += 1
                    else:
                        rgbe[y, x:x + n, c] = body[i:i + n]; i += n
                    x += n
    e = rgbe[..., 3].astype(np.int32)
    scale = np.where(e > 0, np.ldexp(1.0, e - 136), 0.0).astype(np.float32)
    return rgbe[..., :3].astype(np.float32) * scale[..., None]


def aces(x):
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)


def to_srgb(x):
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.maximum(x, 1e-8), 1 / 2.4) - 0.055)


def grade(tag, exposure=None, out_name=None, mid=0.13, bloom_threshold=1.6, bloom_strength=0.35):
    col = read_hdr(os.path.join(BEAUTY, f'{tag}.hdr'))
    h, w, _ = col.shape
    lum = col @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    fg = lum > 1e-6  # nothing behind the character, so the background is exactly black
    if exposure is None:  # meter on the character (the frame above the plinth), letting chrome highlights roll off
        top = lum[: int(h * 0.66)]
        exposure = mid / max(1e-6, float(np.median(top[top > 1e-6])))
    img = col * exposure
    # violet studio backdrop with a soft glow behind the character
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = yy / h
    bg = (np.array([0.010, 0.004, 0.028]) * v[..., None] + np.array([0.11, 0.045, 0.24]) * (1 - v[..., None]) ** 1.6)
    glow = np.exp(-(((xx - w * 0.5) / (w * 0.32)) ** 2 + ((yy - h * 0.42) / (h * 0.30)) ** 2))
    bg = bg + np.array([0.20, 0.08, 0.42]) * 0.55 * glow[..., None]
    img = np.where(fg[..., None], img, bg.astype(np.float32))
    # bloom from the bright parts (blade, rim, highlights)
    bright = np.clip(img - bloom_threshold, 0, None)
    small = Image.fromarray(np.clip(bright / 4.0 * 255, 0, 255).astype(np.uint8)).resize((w // 8, h // 8), Image.BILINEAR)
    blur = sum(np.asarray(small.filter(ImageFilter.GaussianBlur(r)).resize((w, h), Image.BILINEAR), np.float32) / 255 * 4.0 * wgt
               for r, wgt in ((2, 0.5), (6, 0.35), (16, 0.25)))
    img = img + blur * bloom_strength
    # vignette, filmic curve, sRGB
    vig = 1 - 0.38 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) ** 1.4
    img = to_srgb(aces(img * vig[..., None]))
    out = Image.fromarray(np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8)).resize((w // 2, h // 2), Image.LANCZOS)
    path = os.path.join(BEAUTY, out_name or f'{tag}_graded.png')
    out.save(path)
    return path, exposure, float(fg.mean())


def contact_sheet(prefix):
    """Grade the preview frames of one character (step3 with -Preview) side by side, labelled, for picking a pose."""
    from PIL import ImageDraw
    tags = sorted(f[:-4] for f in os.listdir(BEAUTY) if f.startswith(f'preview_{prefix}_') and f.endswith('.hdr'))
    tiles = []
    for tag in tags:
        path, _, _ = grade(tag)
        tile = Image.open(path).convert('RGB')
        ImageDraw.Draw(tile).text((8, 8), tag[len(f'preview_{prefix}_'):], fill=(255, 255, 255))
        tiles.append(tile)
        os.remove(path)
    w, h = tiles[0].size
    cols = 3
    sheet = Image.new('RGB', (w * cols, h * ((len(tiles) + cols - 1) // cols)))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % cols) * w, (i // cols) * h))
    out = os.path.join(BEAUTY, f'preview_{prefix}_sheet.png')
    sheet.save(out)
    return out


if __name__ == '__main__':
    if sys.argv[1:2] == ['--preview']:
        for prefix in sys.argv[2:]:
            print(contact_sheet(prefix))
        sys.exit()
    # <character>_beauty.hdr from step3 -> <character>_beauty_final.png (the site's assets/<character>-ue-render.webp,
    # resized to 800 x 1000)
    for f in sorted(os.listdir(BEAUTY)):
        if f.endswith('_beauty.hdr') and not f.startswith('preview_'):
            print(grade(f[:-4], out_name=f[:-4] + '_final.png'))
    # the knight's still from the first, knight-only version of step3
    if os.path.exists(os.path.join(BEAUTY, 'beauty_right.hdr')) and not os.path.exists(os.path.join(BEAUTY, 'knight_beauty.hdr')):
        print(grade('beauty_right', out_name='knight_beauty_final.png'))
