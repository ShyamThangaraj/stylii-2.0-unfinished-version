"""
spritesheet_pack.py
-------------------
Helpers to:
- Decode base64 -> PIL
- Downscale inputs (room + products)
- Deduplicate identical products
- Stack room image on top, product grid below (one composite image)
- Compress to WebP under a fixed budget (single pass, no retries)
- Build a concise Gemini 'contents' payload (one text + one image)

Usage (FastAPI example):
    from spritesheet_pack import prepare_contents_single_image, build_single_image_prompt

    contents, prompt_text, meta = prepare_contents_single_image(
        room_b64=request.room_image,
        product_b64s=request.product_images,
        cols=4,
        tile=176,
        padding=6,
        gap=10,
        max_input_dim=864,
        room_long_edge_in_stack=720,
        out_max_long_edge=896,
        out_quality=52,
        prompt_override=build_single_image_prompt(style_prompt, custom_prompt)
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents=contents,
    )
"""

from typing import List, Tuple, Optional, Dict, Any
import base64
import io
import math
import hashlib
from PIL import Image

# ---------------------------
# Helpers: decode / resize / hash
# ---------------------------
def _strip_data_url_prefix(image_base64: str) -> str:
    """Remove 'data:image/...;base64,' prefix if present."""
    if image_base64.startswith("data:image"):
        return image_base64.split(",", 1)[1]
    return image_base64

def decode_base64_image(image_base64: str) -> Image.Image:
    """Base64 -> PIL.Image."""
    raw = base64.b64decode(_strip_data_url_prefix(image_base64))
    return Image.open(io.BytesIO(raw))

def _downscale(img: Image.Image, max_dim: int) -> Image.Image:
    """Cap long edge to max_dim; convert to RGB; LANCZOS resample."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) <= max_dim:
        return img
    s = max_dim / float(max(w, h))
    return img.resize((max(1, int(w*s)), max(1, int(h*s))), Image.Resampling.LANCZOS)

def _sha256_bytes(img: Image.Image) -> str:
    """Content hash (PNG-encoded) to dedupe identical product images."""
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return hashlib.sha256(bio.getvalue()).hexdigest()

# ---------------------------
# Build stacked composite (room + grid)
# ---------------------------
def build_stacked_sheet(
    room_img: Image.Image,
    products: List[Image.Image],
    *,
    cols: int = 4,
    tile: int = 176,
    pad: int = 6,
    gap: int = 10,
    bg=(255, 255, 255),
    room_long_edge: int = 720
) -> Image.Image:
    """Return one image: room on top, product grid below."""
    # resize room
    r = room_img.convert("RGB")
    rw, rh = r.size
    if max(rw, rh) > room_long_edge:
        s = room_long_edge / float(max(rw, rh))
        r = r.resize((max(1, int(rw*s)), max(1, int(rh*s))), Image.Resampling.LANCZOS)
        rw, rh = r.size

    # build product grid
    grid = None
    grid_w = grid_h = 0
    if products:
        rows = math.ceil(len(products) / cols)
        grid_w = cols * tile + (cols + 1) * pad
        grid_h = rows * tile + (rows + 1) * pad
        grid = Image.new("RGB", (grid_w, grid_h), bg)
        for i, img in enumerate(products):
            im = img.convert("RGB").copy()
            im.thumbnail((tile, tile), Image.Resampling.LANCZOS)
            r_i, c_i = divmod(i, cols)
            x = pad + c_i * (tile + pad)
            y = pad + r_i * (tile + pad)
            grid.paste(im, (x, y))
        # quantize grid for compression
        grid = grid.convert("P", palette=Image.ADAPTIVE, colors=144).convert("RGB")

    # final canvas
    W = max(rw + 2*pad, grid_w) if grid else rw + 2*pad
    H = rh + 2*pad + (gap if grid else 0) + (grid_h if grid else 0)
    canvas = Image.new("RGB", (W, H), bg)
    rx = (W - rw) // 2
    canvas.paste(r, (rx, pad))
    if grid:
        gx = (W - grid_w) // 2
        gy = pad + rh + gap
        canvas.paste(grid, (gx, gy))
    return canvas

# ---------------------------
# Encode single-pass WebP
# ---------------------------
def encode_singlepass_webp(img: Image.Image, *, max_long_edge: int = 896, q: int = 52) -> bytes:
    """Resize (if needed) and encode once to WebP."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > max_long_edge:
        s = max_long_edge / float(max(w, h))
        img = img.resize((max(1, int(w*s)), max(1, int(h*s))), Image.Resampling.LANCZOS)
    bio = io.BytesIO()
    img.save(bio, format="WEBP", quality=q, method=6, exact=False)
    return bio.getvalue()

# ---------------------------
# Prompt
# ---------------------------
def build_single_image_prompt(style_prompt: Optional[str] = None, custom_prompt: Optional[str] = None) -> str:
    parts = []
    if style_prompt: parts.append(f"Style: {style_prompt.strip()}")
    if custom_prompt: parts.append(custom_prompt.strip())
    parts.append(
        "Single image: Top is the room. Bottom is a contact sheet of ALL products (row-major). "
        "Place each product into the room once, matching perspective, scale, and lighting. "
        "Return a clean, photorealistic composite image of the room with the products placed naturally."
    )
    return " ".join(parts)

# ---------------------------
# Public entrypoint
# ---------------------------
def prepare_contents_single_image(
    room_b64: str,
    product_b64s: List[str],
    *,
    cols: int = 4,
    tile: int = 176,
    padding: int = 6,
    gap: int = 10,
    max_input_dim: int = 864,
    room_long_edge_in_stack: int = 720,
    out_max_long_edge: int = 896,
    out_quality: int = 52,
    prompt_override: Optional[str] = None,
    dedupe_products: bool = True,
) -> Tuple[List[dict], str, Dict[str, Any]]:
    """Return (contents, prompt_text, meta) with one WebP image."""
    if not room_b64: raise ValueError("room_b64 empty")
    if not product_b64s: raise ValueError("product_b64s empty")

    # decode + downscale
    room_img = _downscale(decode_base64_image(room_b64), max_input_dim)
    prods = [_downscale(decode_base64_image(b), max_input_dim) for b in product_b64s]

    # dedupe
    if dedupe_products:
        seen, uniq = set(), []
        for p in prods:
            h = _sha256_bytes(p)
            if h not in seen:
                seen.add(h); uniq.append(p)
        prods = uniq
    if not prods:
        raise ValueError("no valid (unique) product images")

    # build stacked canvas
    stacked = build_stacked_sheet(
        room_img, prods,
        cols=cols, tile=tile, pad=padding, gap=gap,
        room_long_edge=room_long_edge_in_stack
    )

    # single encode
    webp_bytes = encode_singlepass_webp(stacked, max_long_edge=out_max_long_edge, q=out_quality)

    # prompt
    prompt_text = (prompt_override.strip() if prompt_override else build_single_image_prompt())

    contents = [{
        "role": "user",
        "parts": [
            {"text": prompt_text},
            {"inline_data": {"mime_type": "image/webp", "data": webp_bytes}},
        ],
    }]

    meta = {
        "type": "single_image_stack",
        "cols": cols, "tile": tile, "padding": padding, "gap": gap,
        "room_long_edge_in_stack": room_long_edge_in_stack,
        "out_max_long_edge": out_max_long_edge, "out_quality": out_quality,
        "num_products_in": len(product_b64s), "num_products_used": len(prods),
        "bytes": len(webp_bytes),
        "final_size": stacked.size,
    }
    return contents, prompt_text, meta