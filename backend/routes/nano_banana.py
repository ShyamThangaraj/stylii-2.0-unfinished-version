from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
import base64
import time
import hashlib
from google import genai
from image_compression.spritesheet_pack import prepare_contents_with_spritesheet, build_prompt

router = APIRouter(prefix="/api/nano-banana", tags=["nano-banana"])

# Simple in-memory cache to avoid repeated model calls during rapid tests
_COMPOSITE_CACHE: dict[str, str] = {}
_CACHE_MAX_ENTRIES = 20

def _lru_put(cache: dict, key: str, value: str) -> None:
    cache[key] = value
    if len(cache) > _CACHE_MAX_ENTRIES:
        # drop an arbitrary/oldest entry (simple strategy)
        cache.pop(next(iter(cache)))

class ImageGenerationRequest(BaseModel):
    """Request model for Nano Banana image generation"""
    room_image: str  # Base64 encoded room image
    product_images: Optional[List[str]] = None  # List of base64 encoded product images
    product_image_urls: Optional[List[str]] = None  # List of image URLs (server will fetch)
    prompt: Optional[str] = None  # Optional additional instructions

class ImageGenerationResponse(BaseModel):
    """Response model for generated image"""
    generated_image: str  # Base64 encoded generated image
    status: str = "success"
    message: Optional[str] = None

@router.post("/generate-room-visualization", response_model=ImageGenerationResponse)
async def generate_room_visualization(request: ImageGenerationRequest):
    """
    Generate room visualization image using Google's Nano Banana
    
    This endpoint takes a room image and product images to generate
    a visualization showing how the products would look in the room.
    
    Args:
        request: ImageGenerationRequest containing room image and product images
        
    Returns:
        ImageGenerationResponse with generated visualization image
    """
    try:
        print(f"🎨 Generating room visualization")
        try:
            num_b64 = len(request.product_images) if request.product_images else 0
            num_urls = len(request.product_image_urls) if request.product_image_urls else 0
            print(f"🧾 Request inputs → room_image: {'yes' if bool(request.room_image) else 'no'}, product_images(b64): {num_b64}, product_image_urls: {num_urls}")
        except Exception:
            pass
        
        # Validate input
        if not request.room_image:
            raise HTTPException(status_code=400, detail="room_image is required (base64 string)")
        if (not request.product_images or len(request.product_images) == 0) and (not request.product_image_urls or len(request.product_image_urls) == 0):
            raise HTTPException(status_code=400, detail="Provide product_images (base64) or product_image_urls (URLs)")

        # Read API key
        api_key = os.getenv("GEMINI_API_KEY_2")
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not found in environment variables")

        client = genai.Client(api_key=api_key)

        # Construct prompt using spritesheet helper (single source of truth)
        style_prompt = ""  # Optional: wire a style string from request if available
        custom_prompt = (request.prompt or "").strip() or None
        user_prompt = build_prompt(style_prompt=style_prompt, custom_prompt=custom_prompt)

        # Build spritesheet contents first to reduce token/byte usage
        try:
            # If URLs were provided, fetch them and convert to base64 first
            product_b64s: List[str]
            if request.product_image_urls and len(request.product_image_urls) > 0:
                import urllib.request
                import urllib.error
                fetched: List[str] = []
                for idx, url in enumerate(request.product_image_urls):
                    try:
                        with urllib.request.urlopen(url, timeout=15) as resp:
                            img_bytes = resp.read()
                            fetched.append(base64.b64encode(img_bytes).decode('utf-8'))
                    except Exception as fetch_err:
                        print(f"⚠️ Failed to fetch product image URL at index {idx}: {url} -> {fetch_err}")
                if not fetched:
                    raise HTTPException(status_code=400, detail="Failed to fetch any product images from URLs")
                product_b64s = fetched
            else:
                product_b64s = request.product_images or []

            # Use all provided products (no cap)

            # Cache key (room + product hashes + prompt)
            def _sha(s: str) -> str:
                return hashlib.sha256(s.encode('utf-8')).hexdigest()
            cache_key = _sha(request.room_image[:2000]) + "|" + _sha(";".join(p[:2000] for p in product_b64s)) + "|" + _sha(user_prompt or "")
            if cache_key in _COMPOSITE_CACHE:
                print("🟢 Cache hit for composite")
                return ImageGenerationResponse(generated_image=_COMPOSITE_CACHE[cache_key], status="success", message="Composite from cache")

            contents, prompt_text, meta = prepare_contents_with_spritesheet(
                room_b64=request.room_image,
                product_b64s=product_b64s,
                cols=4,
                tile=192,
                padding=4,
                max_input_dim=768,
                target_bytes=2*1024*1024,
                q_min=45,
                q_max=72,
                max_encode_dim=768,
                prompt_override=user_prompt,
                dedupe_products=True,
            )

            print("DEBUG prompt:", prompt_text)
            print("DEBUG meta info:", meta)
        except Exception as prep_error:
            import traceback
            print("❌ Spritesheet preparation failed:", str(prep_error))
            print(traceback.format_exc())
            raise HTTPException(status_code=400, detail=f"Failed to prepare images: {str(prep_error)}")

        # Send spritesheet contents to Gemini
        try:
            max_attempts = 3
            attempt = 0
            last_err: Optional[Exception] = None
            while attempt < max_attempts:
                attempt += 1
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash-image-preview",
                        contents=contents,
                    )
                    break
                except Exception as model_error:
                    err_str = str(model_error)
                    last_err = model_error
                    if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                        backoff = 12 * attempt
                        print(f"⏳ Quota backoff attempt {attempt}/{max_attempts} → sleeping {backoff}s")
                        time.sleep(backoff)
                        continue
                    raise
            else:
                raise last_err or Exception("Model call failed after retries")
        except Exception as model_error:
            import traceback
            print("❌ Model call failed:", str(model_error))
            print("❌ Error type:", type(model_error).__name__)
            print("❌ Traceback:")
            print(traceback.format_exc())
            raise

        # Extract base64 image directly from response
        image_parts = [
            part.inline_data.data
            for part in response.candidates[0].content.parts
            if getattr(part, 'inline_data', None)
        ]

        if not image_parts:
            raise HTTPException(status_code=502, detail="Model did not return an image")

        # image_parts[0] are raw bytes; encode to base64 string for response
        generated_bytes = image_parts[0]
        generated_b64 = base64.b64encode(generated_bytes).decode('utf-8')

        _lru_put(_COMPOSITE_CACHE, cache_key, generated_b64)

        return ImageGenerationResponse(
            generated_image=generated_b64,
            status="success",
            message="Composite generated"
        )
        
    except Exception as e:
        import traceback
        print("❌ Unhandled error in generate_room_visualization:", str(e))
        print("❌ Error type:", type(e).__name__)
        print("❌ Traceback:")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate room visualization: {str(e)}"
        )

@router.get("/health")
async def nano_banana_health_check():
    """Health check endpoint for Nano Banana routes"""
    return {"status": "healthy", "service": "nano-banana-api"}
