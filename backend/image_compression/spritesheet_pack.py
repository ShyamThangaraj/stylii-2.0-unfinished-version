"""
spritesheet_pack.py
-------------------
Token/byte-optimized helpers to:
- Decode base64 -> PIL
- Downscale inputs (room + products)
- Pack product images into a contact sheet (spritesheet)
- Compress (room + spritesheet) to WebP under a target byte budget
- Build a single, concise Gemini 'contents' payload (one text + two images)

Usage (FastAPI example):
    from spritesheet_pack import prepare_contents_with_spritesheet, build_prompt

    contents, prompt_text, meta = prepare_contents_with_spritesheet(
        room_b64=request.room_image,
        product_b64s=request.product_images,
        cols=4,
        tile=256,
        padding=8,
        max_input_dim=1024,
        target_bytes=6*1024*1024,
        q_min=50,
        q_max=78,
        max_encode_dim=1024,
        prompt_override=build_prompt(style_prompt, custom_prompt)
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
# Decoding + pre-optimization
# ---------------------------
def _strip_data_url_prefix(image_base64: str) -> str:
    """Remove 'data:image/...;base64,' prefix if present."""
    if image_base64.startswith("data:image"):
        return image_base64.split(",", 1)[1]
    return image_base64

def decode_base64_image(image_base64: str) -> Image.Image:
    """Base64 -> PIL.Image (lazy decoded)."""
    raw = base64.b64decode(_strip_data_url_prefix(image_base64))
    img = Image.open(io.BytesIO(raw))
    return img

def _downscale(img: Image.Image, max_dim: int) -> Image.Image:
    """Cap long edge to max_dim; RGB; high-quality resample."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) <= max_dim:
        return img
    scale = float(max_dim) / float(max(w, h))
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return img.resize((nw, nh), Image.Resampling.LANCZOS)

def _sha256_bytes(img: Image.Image) -> str:
    """Content hash (post downscale) to dedupe identical product images."""
    bio = io.BytesIO()
    img.save(bio, format="PNG")  # stable bytes for hash; not sent to model
    return hashlib.sha256(bio.getvalue()).hexdigest()


# ---------------------------
# Packing (spritesheet)
# ---------------------------
def pack_contact_sheet(
    images: List[Image.Image],
    cols: int = 4,
    tile: int = 256,
    padding: int = 8,
    bg: Tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """
    Packs N images into a fixed-grid contact sheet. Images are downscaled
    to fit within (tile x tile). Returns an RGB PIL.Image.
    """
    if not images:
        raise ValueError("pack_contact_sheet: images list is empty")

    rows = math.ceil(len(images) / cols)
    w = cols * tile + (cols + 1) * padding
    h = rows * tile + (rows + 1) * padding
    sheet = Image.new("RGB", (w, h), bg)

    for i, img in enumerate(images):
        if img.mode != "RGB":
            img = img.convert("RGB")
        # preserve detail; don't upsample
        thumb = img.copy()
        thumb.thumbnail((tile, tile), Image.Resampling.LANCZOS)
        r, c = divmod(i, cols)
        x = padding + c * (tile + padding)
        y = padding + r * (tile + padding)
        sheet.paste(thumb, (x, y))

    return sheet


# ---------------------------
# Compression (WebP adaptive)
# ---------------------------
def _to_webp_bytes(img: Image.Image, max_dim: int, quality: int) -> bytes:
    """
    Convert to RGB, resize (encode-time) if needed to max_dim (long edge), encode as lossy WebP.
    """
    if img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > max_dim:
        scale = float(max_dim) / float(max(w, h))
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)

    bio = io.BytesIO()
    # WebP default is 4:2:0 chroma subsampling (good size/quality tradeoff)
    img.save(bio, format="WEBP", quality=quality, method=6)
    return bio.getvalue()

def compress_pair_adaptive_total(
    room_img: Image.Image,
    sheet_img: Image.Image,
    *,
    target_bytes: int = 6 * 1024 * 1024,  # 6 MB
    q_min: int = 50,
    q_max: int = 78,
    max_encode_dim: int = 1024,
) -> Tuple[bytes, bytes, int]:
    """
    Binary-search a single WebP quality applied to BOTH images so that the
    total bytes (room + sheet) <= target_bytes. Returns (room_bytes, sheet_bytes, used_quality).
    If cannot fit, returns at q_min.
    """
    best = None
    lo, hi = q_min, q_max

    while lo <= hi:
        q = (lo + hi) // 2
        rb = _to_webp_bytes(room_img, max_dim=max_encode_dim, quality=q)
        sb = _to_webp_bytes(sheet_img, max_dim=max_encode_dim, quality=q)
        total = len(rb) + len(sb)
        if total <= target_bytes:
            best = (rb, sb, q)
            lo = q + 1
        else:
            hi = q - 1

    if best:
        return best
    # fallback at min quality
    rb = _to_webp_bytes(room_img, max_dim=max_encode_dim, quality=q_min)
    sb = _to_webp_bytes(sheet_img, max_dim=max_encode_dim, quality=q_min)
    return rb, sb, q_min


# ---------------------------
# Prompt (short + expressive)
# ---------------------------
def build_prompt(style_prompt: Optional[str] = None, custom_prompt: Optional[str] = None) -> str:
    """
    Produces a single concise instruction block to cut tokens.
    You can pass this as `prompt_override` to prepare_contents_with_spritesheet().
    """
    parts = []
    if style_prompt:
        parts.append(f"Style: {style_prompt.strip()}")
    if custom_prompt:
        parts.append(custom_prompt.strip())

    # Core spritesheet instruction keeps it deterministic and short.
    parts.append(
        "Second image is a contact sheet of ALL products (row-major from (1,1)). "
        "Place every product into the room exactly once, matching perspective, scale, and lighting; avoid overlaps. "
        "Return one photorealistic composite."
    )
    return " ".join(parts)


# ---------------------------
# Public: prepare payload
# ---------------------------
def prepare_contents_with_spritesheet(
    room_b64: str,
    product_b64s: List[str],
    *,
    # montage/layout
    cols: int = 4,
    tile: int = 256,
    padding: int = 8,
    # input downscale
    max_input_dim: int = 1024,
    # encoding/compression
    target_bytes: int = 6 * 1024 * 1024,
    q_min: int = 50,
    q_max: int = 78,
    max_encode_dim: int = 1024,
    # prompt
    prompt_override: Optional[str] = None,
    # dedupe identical products (saves bytes, still "uses all unique products")
    dedupe_products: bool = True,
) -> Tuple[List[dict], str, Dict[str, Any]]:
    """
    High-level helper:
      - decodes base64 inputs,
      - **downscales** room + products to max_input_dim,
      - optionally **dedupes** identical product images,
      - creates product spritesheet,
      - adaptively compresses room & sheet to WebP under target_bytes,
      - returns (contents, prompt_text, meta).

    'contents' is ready for google.genai client.models.generate_content(..., contents=contents).
    """
    if not room_b64:
        raise ValueError("prepare_contents_with_spritesheet: room_b64 is empty")
    if not product_b64s:
        raise ValueError("prepare_contents_with_spritesheet: product_b64s is empty")

    # Decode + downscale
    room_img_raw = decode_base64_image(room_b64)
    room_img = _downscale(room_img_raw, max_input_dim)

    decoded_products = [_downscale(decode_base64_image(b64), max_input_dim) for b64 in product_b64s]

    # Optional dedupe (helps when duplicates slip in)
    if dedupe_products:
        seen = {}
        unique_products = []
        for img in decoded_products:
            h = _sha256_bytes(img)
            if h not in seen:
                seen[h] = True
                unique_products.append(img)
        products = unique_products
    else:
        products = decoded_products

    if not products:
        raise ValueError("prepare_contents_with_spritesheet: no valid (unique) product images")

    sheet = pack_contact_sheet(products, cols=cols, tile=tile, padding=padding)

    # Encode under byte budget
    room_bytes, sheet_bytes, used_q = compress_pair_adaptive_total(
        room_img, sheet,
        target_bytes=target_bytes,
        q_min=q_min,
        q_max=q_max,
        max_encode_dim=max_encode_dim,
    )

    # Prompt
    prompt_text = (prompt_override.strip() if prompt_override else build_prompt())

    # Build Gemini 'contents' with minimal parts: [text, room, sheet]
    contents = [
        {
            "role": "user",
            "parts": [
                {"text": prompt_text},
                {"inline_data": {"mime_type": "image/webp", "data": room_bytes}},
                {"inline_data": {"mime_type": "image/webp", "data": sheet_bytes}},
            ],
        }
    ]

    meta: Dict[str, Any] = {
        "used_quality": used_q,
        "room_bytes": len(room_bytes),
        "sheet_bytes": len(sheet_bytes),
        "total_bytes": len(room_bytes) + len(sheet_bytes),
        "num_products_in": len(product_b64s),
        "num_products_used": len(products),
        "deduped": dedupe_products,
        "cols": cols,
        "tile": tile,
        "padding": padding,
        "max_input_dim": max_input_dim,
        "max_encode_dim": max_encode_dim,
        "target_bytes": target_bytes,
    }
    return contents, prompt_text, meta