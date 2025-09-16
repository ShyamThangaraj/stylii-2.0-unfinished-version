from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from routes.gemini import router as gemini_router
from routes.nano_banana import router as nano_banana_router
from routes.video_generation import router as video_router

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Stylii Backend API", version="1.0.0")

# Add CORS middleware to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(gemini_router)
app.include_router(nano_banana_router)
app.include_router(video_router)

# Mount static files for serving generated videos
import pathlib
videogen_dir = pathlib.Path(__file__).parent / "videogen"
app.mount("/static/videos", StaticFiles(directory=str(videogen_dir)), name="videos")

@app.get("/")
async def root():
    return {"message": "Welcome to Stylii Backend API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Backend is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

