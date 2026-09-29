"""ReviewFlow Vision - renders social quote cards from 5-star reviews.
Pipeline: procedural aurora background (NumPy) -> convolutional layout analysis (OpenCV) ->
frosted-glass card + typography (Pillow).

The 'CNN' stage is a fixed-kernel convolutional feature extractor (Sobel/Laplacian/Gaussian filter bank ->
ReLU -> max-pool -> global average), i.e. the forward pass of a conv net with hand-set weights. It decides
where the text band goes (lowest visual energy) and whether text is light or dark. Swap `analyze_layout`
for a trained saliency model later without touching the rest of the service.
Designed & developed by NIKHIL CHARY SRIRAMOJU."""
import math
import os
import textwrap
import uuid

import cv2
import numpy as np
from fastapi import FastAPI
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

OUT = os.getenv("ASSET_OUTPUT_DIR", "/data/assets")
os.makedirs(OUT, exist_ok=True)
app = FastAPI(title="ReviewFlow Vision")

THEMES = {
    "aurora": [(12, 16, 40), (91, 33, 182), (6, 182, 212), (244, 114, 182)],
    "sunset": [(30, 12, 40), (190, 40, 90), (251, 146, 60), (253, 224, 71)],
    "forest": [(6, 24, 20), (16, 120, 90), (132, 204, 22), (250, 250, 210)],
    "paper": [(250, 246, 238), (240, 220, 200), (214, 190, 170), (255, 255, 255)],
}
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


class RenderIn(BaseModel):
    quote: str = Field(min_length=3, max_length=280)
    author: str = "Happy customer"
    business_name: str
    rating: int = Field(default=5, ge=1, le=5)
    theme: str = "aurora"
    width: int = Field(default=1080, ge=512, le=2160)
    height: int = Field(default=1080, ge=512, le=2160)
    asset_id: str | None = None


def font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def make_background(theme: str, w: int, h: int) -> np.ndarray:
    pal = np.array(THEMES.get(theme, THEMES["aurora"]), dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = np.clip((xx / w * 0.55 + yy / h * 0.75) / 1.3, 0, 1)
    seg = t * (len(pal) - 1)
    i = np.clip(seg.astype(int), 0, len(pal) - 2)
    f = (seg - i)[..., None]
    img = pal[i] * (1 - f) + pal[i + 1] * f
    rng = np.random.default_rng(abs(hash(theme)) % 2**32)
    for _ in range(5):  # soft glowing orbs
        cx, cy, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.18, 0.4) * w
        col = pal[rng.integers(1, len(pal))]
        g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (r / 2) ** 2)))[..., None]
        img = img + g * col * 0.55
    img += rng.normal(0, 4, img.shape).astype(np.float32)  # film grain
    return np.clip(img, 0, 255).astype(np.uint8)


def analyze_layout(bg: np.ndarray) -> dict:
    """Conv filter bank -> ReLU -> max-pool -> energy per horizontal band; picks calmest band + text colour."""
    gray = cv2.cvtColor(bg, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    kernels = [
        np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float32),      # Sobel-x
        np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], np.float32),      # Sobel-y
        np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], np.float32),        # Laplacian
    ]
    x = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
    maps = [np.maximum(cv2.filter2D(x, -1, k), 0) for k in kernels]      # conv + ReLU
    energy = sum(maps)
    for _ in range(3):                                                    # 3x (2x2 max-pool)
        h, w = energy.shape
        energy = energy[: h // 2 * 2, : w // 2 * 2].reshape(h // 2, 2, w // 2, 2).max(axis=(1, 3))
    bands = np.array_split(energy, 3, axis=0)
    scores = [float(b.mean()) for b in bands]
    band = int(np.argmin(scores))
    centre = bg[bg.shape[0] // 4: 3 * bg.shape[0] // 4].mean()
    return {"band": ["top", "middle", "bottom"][band], "band_index": band,
            "text_color": "dark" if centre > 150 else "light", "energy": [round(s, 4) for s in scores]}


def frosted(bg_rgb: np.ndarray, box, radius: int) -> Image.Image:
    x0, y0, x1, y1 = box
    region = cv2.GaussianBlur(bg_rgb[y0:y1, x0:x1], (0, 0), 22)
    tile = Image.fromarray(region).convert("RGBA")
    mask = Image.new("L", tile.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, tile.size[0] - 1, tile.size[1] - 1), radius, fill=255)
    tile.putalpha(mask)
    return tile


def star(draw: ImageDraw.ImageDraw, cx, cy, r, fill):
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rad = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=fill)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/render")
def render(req: RenderIn):
    w, h = req.width, req.height
    bg = make_background(req.theme, w, h)
    layout = analyze_layout(bg)
    light = layout["text_color"] == "light"
    ink, sub = ((255, 255, 255), (220, 226, 240)) if light else ((24, 24, 40), (70, 70, 90))

    card_w, card_h = int(w * 0.84), int(h * 0.56)
    x0 = (w - card_w) // 2
    y0 = {0: int(h * 0.08), 1: (h - card_h) // 2, 2: int(h * 0.92) - card_h}[layout["band_index"]]
    box = (x0, y0, x0 + card_w, y0 + card_h)

    canvas = Image.fromarray(bg).convert("RGBA")
    canvas.alpha_composite(frosted(bg, box, 48), (x0, y0))
    alpha = 34 if light else 110
    mask = Image.new("L", (card_w, card_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, card_w - 1, card_h - 1), 48, fill=255)
    tint = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 0))
    tint.putalpha(mask.point(lambda v: v * alpha // 255))
    canvas.alpha_composite(tint, (x0, y0))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle(box, 48, outline=(255, 255, 255, 110), width=3)

    pad = int(card_w * 0.08)
    for i in range(5):
        star(d, x0 + pad + 26 + i * 62, y0 + pad + 26, 26, (251, 191, 36) if i < req.rating else (255, 255, 255, 60))

    size = 64
    quote = f"“{req.quote.strip()}”"
    while size > 30:
        f = font(SERIF, size)
        chars = max(10, int((card_w - 2 * pad) / (size * 0.58)))
        lines = textwrap.wrap(quote, chars)
        if len(lines) * size * 1.28 <= card_h - 2 * pad - 150:
            break
        size -= 4
    ty = y0 + pad + 80
    for ln in lines:
        d.text((x0 + pad, ty), ln, font=f, fill=ink)
        ty += int(size * 1.28)

    d.text((x0 + pad, y0 + card_h - pad - 68), f"— {req.author}", font=font(SANS_B, 34), fill=ink)
    d.text((x0 + pad, y0 + card_h - pad - 26), req.business_name, font=font(SANS, 26), fill=sub)
    d.text((w - 40, h - 36), "Made with ReviewFlow AI", font=font(SANS, 22), fill=(255, 255, 255, 190), anchor="rs")

    name = f"{req.asset_id or uuid.uuid4()}.png"
    canvas.convert("RGB").save(os.path.join(OUT, name), optimize=True)
    return {"filename": name, "url": f"/assets/{name}", "width": w, "height": h, "layout": layout}
