from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Union
import os
import base64
import json
import re
from google import genai
from serpAPI import search_amazon_products
from serpAPI.product_picker import pick_products_with_budget

router = APIRouter(prefix="/api/gemini", tags=["gemini"])

# Gemini client will be initialized when needed


class DesignFormRequest(BaseModel):
    """Request model for design form data from frontend"""
    budget: int
    style: str
    notes: Optional[str] = None
    selectedProducts: List[str] = []
    images: List[str] = []  # Base64 encoded images

class DesignFormResponse(BaseModel):
    """Response model for design form processing"""
    amazon_search_queries: List[str]
    recommended_products: Optional[List[dict]] = None
    reasoning: Optional[str] = None
    status: str = "success"

@router.post("/generate-design-queries", response_model=DesignFormResponse)
async def process_design_form(request: DesignFormRequest):
    """
    Process design form data and generate search queries using Gemini 2.5 Flash-Lite
    
    This endpoint receives the form data from the frontend design page and:
    1. Processes the budget, style, notes, and selected products
    2. Calls Gemini API to generate relevant search queries
    3. Returns optimized search queries for product discovery
    
    Args:
        request: DesignFormRequest containing budget, style, notes, and selectedProducts
        
    Returns:
        DesignFormResponse with generated search queries and reasoning
    """
    try:
        print(f"🔍 Received request: budget={request.budget}, style={request.style}, images={len(request.images)}")
        
        # Validate request data
        if not request.budget or request.budget <= 0:
            raise HTTPException(status_code=400, detail="Budget must be greater than 0")
        
        if not request.style:
            raise HTTPException(status_code=400, detail="Style is required")
        
        print(f"✅ Request validation passed")
        # Initialize Gemini client
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY not found in environment variables"
            )
        client = genai.Client(api_key=api_key)
        
        # Create comprehensive prompt for Gemini
        products_text = ", ".join(request.selectedProducts) if request.selectedProducts else "general home decor"
        notes_text = f"Additional notes: {request.notes}" if request.notes else "No additional notes provided"
        images_text = f"Room images provided: {len(request.images)} photos" if request.images else "No room images provided"
        
        prompt = f"""
You are a professional interior designer. Analyze provided room images and design parameters to recommend Amazon product searches.

DESIGN BRIEF:
- Budget: ${request.budget:,}
- Style: {request.style}
- Focus Areas: {products_text}
- Notes: {notes_text}
- Images: {images_text}

ANALYSIS:
1. Existing Items: identify current furniture, decor, and built-in features.  
2. Room Characteristics: layout, size, color palette, lighting, flooring, architectural features.  
3. Opportunities: empty areas, enhancements, missing complements, or inconsistencies.

RECOMMENDATION RULES:
- Do NOT suggest items already in the room.  
- DO suggest complementary products (e.g., bed → bedding, lamps, nightstands).  
- Respect style ({request.style}), focus areas ({products_text}), and budget (${request.budget:,}).  
- Generate exactly 5–6 optimized Amazon queries.  
- Ensure total cost stays within budget.  
- Include price ranges and make queries specific enough for Amazon.  

FORMAT:
- Return only 5–6 query strings, one per line (no bullets/URLs).  
- Example:  
  modern nightstand with USB charging under $150  
  contemporary area rug 8x10 neutral under $300  
  scandinavian throw pillows set of 4 neutral colors  

DO NOT return full URLs or Amazon parameters, only the plain search query text.  
"""
        
        # Prepare contents for Gemini (text + images)
        contents = []
        
        # Add text content
        contents.append(prompt)
        
        # Add images if provided (compress to reduce token usage)
        if request.images:
            import base64
            from PIL import Image
            import io
            
            # Only use the first image to reduce token consumption
            image_base64 = request.images[0]
            # Remove data URL prefix if present
            if image_base64.startswith('data:image'):
                image_base64 = image_base64.split(',')[1]
            
            try:
                # Decode base64 image
                image_data = base64.b64decode(image_base64)
                image = Image.open(io.BytesIO(image_data))
                
                # Compress image: resize to max 512x512 and reduce quality
                max_size = 512
                if image.width > max_size or image.height > max_size:
                    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to RGB if necessary (remove alpha channel)
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                
                # Save with compression
                output = io.BytesIO()
                image.save(output, format='JPEG', quality=70, optimize=True)
                compressed_data = output.getvalue()
                
                # Save debug image for inspection
                debug_path = os.path.join(os.path.dirname(__file__), "..", "image_compression", "gemini_compressed_debug.jpg")
                with open(debug_path, "wb") as f:
                    f.write(compressed_data)
                print(f"🔍 Saved gemini compressed image: {debug_path}")
                
                # Convert back to base64
                compressed_base64 = base64.b64encode(compressed_data).decode('utf-8')
                contents.append(compressed_base64)
                
                print(f"📸 Compressed image: {image.width}x{image.height}, quality=70% (out of {len(request.images)} provided)")
                
            except Exception as e:
                print(f"⚠️ Image compression failed: {e}, using original image")
                contents.append(image_base64)
        
        # Call Gemini 2.5 Flash-Lite
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=contents,
            config={
                "temperature": 0.8,
                "max_output_tokens": 800,
            }
        )
        
        # Parse the response
        search_queries = [query.strip() for query in response.text.strip().split('\n') if query.strip()]
        
        # Print the generated queries to console
        print("\n" + "="*60)
        print("🔍 GEMINI GENERATED SERPAPI QUERIES:")
        print("="*60)
        for i, query in enumerate(search_queries, 1):
            print(f"{i}. {query}")
        print("="*60)
        print(f"📊 Total queries generated: {len(search_queries)}")
        print(f"💰 Budget: ${request.budget:,}")
        print(f"🎨 Style: {request.style}")
        print(f"🛍️  Products: {products_text}")
        print("="*60 + "\n")
        
        # Use real SerpAPI for production
        try:
            print(f"🔍 Calling SerpAPI with {len(search_queries)} queries...")
            serpapi_results = []
            
            for query in search_queries:
                try:
                    result = search_amazon_products(query)
                    serpapi_results.append({
                        "query": query,
                        "success": True,
                        "raw_data": result
                    })
                    print(f"✅ SerpAPI success for: {query}")
                except Exception as query_error:
                    print(f"⚠️ SerpAPI failed for query '{query}': {query_error}")
                    serpapi_results.append({
                        "query": query,
                        "success": False,
                        "raw_data": None
                    })
            
            print(f"📋 SerpAPI completed: {len([r for r in serpapi_results if r['success']])} successful, {len([r for r in serpapi_results if not r['success']])} failed")
            
        except Exception as serpapi_error:
            print(f"❌ SerpAPI error: {serpapi_error}")
            import traceback
            traceback.print_exc()
            serpapi_results = None
        
        picked_products = pick_products_with_budget(
            query_results=serpapi_results,
            budget=request.budget,
            style=request.style,
            selected_products=request.selectedProducts,
            notes=request.notes
        )

        return DesignFormResponse(
            amazon_search_queries=search_queries,
            recommended_products=picked_products,
            reasoning=f"Generated {len(search_queries)} Amazon search queries for {request.style} style with ${request.budget:,} budget",
            status="success"
        )
        
    except Exception as e:
        print(f"❌ Error in process_design_form: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process design form: {str(e)}"
        )

@router.get("/health")
async def gemini_health_check():
    """Health check endpoint for Gemini routes"""
    return {"status": "healthy", "service": "gemini-api"}
