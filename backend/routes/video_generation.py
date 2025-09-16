from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import subprocess
import sys
import pathlib
from PIL import Image
import base64
import io

router = APIRouter(prefix="/api/video", tags=["video"])

class VideoGenerationRequest(BaseModel):
    """Request model for video generation"""
    room_image: str  # Base64 encoded image
    style: str
    prompt: Optional[str] = None

class VideoGenerationResponse(BaseModel):
    """Response model for video generation"""
    video_path: str
    video_url: str
    status: str = "success"
    message: str

@router.post("/generate-room-video", response_model=VideoGenerationResponse)
async def generate_room_video(request: VideoGenerationRequest):
    """
    Generate a video from a room image using the videogen/main.py script
    
    Args:
        request: VideoGenerationRequest containing room image and style
        
    Returns:
        VideoGenerationResponse with video path and URL
    """
    try:
        print(f"🎬 Starting video generation for style: {request.style}")
        
        # Get the backend directory path
        backend_dir = pathlib.Path(__file__).parent.parent
        videogen_dir = backend_dir / "videogen"
        
        # Create a temporary image file from base64
        image_data = base64.b64decode(request.room_image)
        temp_image_path = videogen_dir / "temp_room_image.jpg"
        
        # Save the image
        with open(temp_image_path, "wb") as f:
            f.write(image_data)
        
        print(f"📸 Saved temporary image: {temp_image_path}")
        
        # Call the video generation script
        script_path = videogen_dir / "main.py"
        
        # Run the video generation script
        result = subprocess.run(
            [sys.executable, str(script_path), str(temp_image_path)],
            cwd=str(videogen_dir),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            print(f"❌ Video generation failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Video generation failed: {result.stderr}"
            )
        
        print(f"✅ Video generation completed successfully")
        print(f"📝 Output: {result.stdout}")
        
        # Check if the output video exists
        output_video_path = videogen_dir / "final_with_audio_1080p.mp4"
        
        if not output_video_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Video file was not created successfully"
            )
        
        # Clean up temporary image
        if temp_image_path.exists():
            temp_image_path.unlink()
            print(f"🗑️ Cleaned up temporary image")
        
        # Create a URL for the video (served by FastAPI static files)
        video_url = f"/static/videos/{output_video_path.name}"
        
        return VideoGenerationResponse(
            video_path=str(output_video_path),
            video_url=video_url,
            status="success",
            message=f"Video generated successfully for {request.style} style"
        )
        
    except subprocess.TimeoutExpired:
        print("⏰ Video generation timed out")
        raise HTTPException(
            status_code=408,
            detail="Video generation timed out. Please try again."
        )
    except Exception as e:
        print(f"❌ Error in video generation: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Video generation failed: {str(e)}"
        )

@router.get("/health")
async def video_health_check():
    """Health check endpoint for video routes"""
    return {"status": "healthy", "service": "video-generation-api"}

