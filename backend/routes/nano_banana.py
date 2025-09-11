from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
import base64
import hashlib
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from image_compression.spritesheet_pack import prepare_contents_single_image, build_single_image_prompt

router = APIRouter(prefix="/api/nano-banana", tags=["nano-banana"])

# Simple in-memory cache to avoid repeated model calls during rapid tests
_COMPOSITE_CACHE: dict[str, str] = {}
_CACHE_MAX_ENTRIES = 20

def _lru_put(cache: dict, key: str, value: str) -> None:
    """Add item to cache with LRU eviction"""
    cache[key] = value
    if len(cache) > _CACHE_MAX_ENTRIES:
        # Drop oldest entry (simple strategy)
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

def _generate_cache_key(request: ImageGenerationRequest) -> str:
    """Generate a cache key based on request content"""
    # Include prompt in cache key to differentiate between different styles/requests
    content = f"{request.room_image[:100]}{request.prompt or ''}{len(request.product_images or [])}{len(request.product_image_urls or [])}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]

def _convert_base64_to_pil_image(base64_string: str) -> Image.Image:
    """Convert base64 string to PIL Image"""
    # Remove data URL prefix if present
    if base64_string.startswith("data:image"):
        base64_string = base64_string.split(",", 1)[1]
    
    # Decode base64 to bytes
    image_bytes = base64.b64decode(base64_string)
    
    # Convert to PIL Image
    return Image.open(BytesIO(image_bytes))

def _generate_room_visualization(room_image: Image.Image, product_images: List[Image.Image], prompt: str, api_key: str) -> Image.Image:
    """Generate room visualization using Gemini 2.5 Flash Image Preview"""
    # Initialize GenAI client with API key
    client = genai.Client(api_key=api_key)
    
    # Create contents list with images and text prompt
    contents = [room_image] + product_images + [prompt]
    
    # Generate image using Gemini
    response = client.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents=contents,
    )
    
    # Extract generated image from response
    image_parts = [
        part.inline_data.data
        for part in response.candidates[0].content.parts
        if part.inline_data
    ]
    
    if not image_parts:
        raise HTTPException(status_code=500, detail="No image generated in response")
    
    # Convert to PIL Image
    generated_image = Image.open(BytesIO(image_parts[0]))
    return generated_image

def _pil_image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string"""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    return base64.b64encode(image_bytes).decode('utf-8')

@router.post("/generate-room-visualization", response_model=ImageGenerationResponse)
async def generate_room_visualization(request: ImageGenerationRequest):
    """
    Generate room visualization image using Google's Gemini 2.5 Flash Image Preview
    
    This endpoint takes a room image and product images to generate
    a visualization showing how the products would look in the room.
    """
    try:
        print(f"🎨 Generating room visualization")
        
        # Validate input
        if not request.room_image:
            raise HTTPException(status_code=400, detail="room_image is required (base64 string)")
        if (not request.product_images or len(request.product_images) == 0) and (not request.product_image_urls or len(request.product_image_urls) == 0):
            raise HTTPException(status_code=400, detail="Provide product_images (base64) or product_image_urls (URLs)")

        # Check cache first
        cache_key = _generate_cache_key(request)
        if cache_key in _COMPOSITE_CACHE:
            print("📦 Returning cached result")
            return ImageGenerationResponse(
                generated_image=_COMPOSITE_CACHE[cache_key],
                status="success",
                message="Composite generated (cached)"
            )

        # Get API key and initialize client
        api_key = os.getenv("GEMINI_API_KEY_2")
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY_2 not found in environment variables")

        # Convert room image to PIL
        try:
            room_image = _convert_base64_to_pil_image(request.room_image)
            print(f"✅ Room image loaded: {room_image.size}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process room image: {str(e)}")

        # Get product images
        product_images = []
        
        # If we have product URLs, fetch them
        if request.product_image_urls:
            print(f"🔄 Fetching {len(request.product_image_urls)} product images from URLs...")
            import requests
            for url in request.product_image_urls:
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    # Convert to PIL Image
                    product_image = Image.open(BytesIO(response.content))
                    product_images.append(product_image)
                    print(f"✅ Fetched product image: {product_image.size}")
                except Exception as e:
                    print(f"❌ Failed to fetch product image from {url}: {str(e)}")
                    continue
        
        # If we have base64 product images, convert them
        if request.product_images:
            for product_b64 in request.product_images:
                try:
                    product_image = _convert_base64_to_pil_image(product_b64)
                    product_images.append(product_image)
                    print(f"✅ Loaded product image: {product_image.size}")
                except Exception as e:
                    print(f"❌ Failed to process product image: {str(e)}")
                    continue

        if not product_images:
            raise HTTPException(status_code=400, detail="No valid product images available")

        # Build prompt
        style_prompt = "Scandinavian, light woods, linen, matte metals"
        custom_prompt = (request.prompt or "").strip() or "Prioritize symmetry; leave doorways clear."
        user_prompt = build_single_image_prompt(style_prompt=style_prompt, custom_prompt=custom_prompt)
        
        print(f"📝 Prompt: {user_prompt}")

        # Generate visualization
        try:
            generated_image = _generate_room_visualization(room_image, product_images, user_prompt, api_key)
            print(f"✅ Generated image: {generated_image.size}")
        except Exception as e:
            print(f"❌ Image generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

        # Convert to base64
        generated_b64 = _pil_image_to_base64(generated_image)
        
        # Cache the result
        _lru_put(_COMPOSITE_CACHE, cache_key, generated_b64)

        return ImageGenerationResponse(
            generated_image=generated_b64,
            status="success",
            message="Composite generated successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate room visualization: {str(e)}"
        )

@router.get("/health")
async def nano_banana_health_check():
    """Health check endpoint for Nano Banana routes"""
    return {"status": "healthy", "service": "nano-banana-api"}