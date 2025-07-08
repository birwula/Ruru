from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
import os
import asyncio
import uvicorn
from pymongo import MongoClient
from datetime import datetime
import uuid
import yt_dlp
import tempfile
import json
import re
from typing import Dict, Any

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URL)
db = client.social_video_downloader
downloads_collection = db.downloads

class URLRequest(BaseModel):
    url: str

class DownloadResponse(BaseModel):
    id: str
    url: str
    title: str
    platform: str
    thumbnail: str
    duration: str
    formats: list
    status: str

def detect_platform(url: str) -> str:
    """Detect the platform from URL"""
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'YouTube'
    elif 'facebook.com' in url or 'fb.watch' in url:
        return 'Facebook'
    elif 'instagram.com' in url:
        return 'Instagram'
    else:
        return 'Unknown'

def validate_url(url: str) -> bool:
    """Validate if URL is from supported platforms"""
    supported_patterns = [
        r'https?://(www\.)?(youtube\.com|youtu\.be)/',
        r'https?://(www\.)?(facebook\.com|fb\.watch)/',
        r'https?://(www\.)?instagram\.com/',
    ]
    
    for pattern in supported_patterns:
        if re.match(pattern, url):
            return True
    return False

@app.get("/")
async def root():
    return {"message": "Social Media Video Downloader API"}

@app.post("/api/extract-info")
async def extract_video_info(request: URLRequest):
    """Extract video information without downloading"""
    try:
        url = request.url.strip()
        
        # Validate URL
        if not validate_url(url):
            raise HTTPException(status_code=400, detail="Unsupported platform. Only YouTube, Facebook, and Instagram are supported.")
        
        platform = detect_platform(url)
        
        # Configure yt-dlp options
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
        }
        
        # Extract video info
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Create download record
            download_id = str(uuid.uuid4())
            
            # Format the response
            formats = []
            if 'formats' in info:
                for fmt in info['formats']:
                    if fmt.get('vcodec') != 'none':  # Only video formats
                        formats.append({
                            'format_id': fmt.get('format_id'),
                            'ext': fmt.get('ext'),
                            'quality': fmt.get('quality', 'Unknown'),
                            'filesize': fmt.get('filesize'),
                            'url': fmt.get('url')
                        })
            
            # Sort formats by quality (highest first)
            formats.sort(key=lambda x: x.get('quality', 0), reverse=True)
            
            response_data = {
                'id': download_id,
                'url': url,
                'title': info.get('title', 'Unknown'),
                'platform': platform,
                'thumbnail': info.get('thumbnail', ''),
                'duration': str(info.get('duration', 0)),
                'formats': formats[:5],  # Top 5 formats
                'status': 'ready'
            }
            
            # Store in database
            downloads_collection.insert_one({
                'id': download_id,
                'url': url,
                'title': info.get('title', 'Unknown'),
                'platform': platform,
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'formats': formats,
                'status': 'ready',
                'created_at': datetime.now(),
                'info': info
            })
            
            return response_data
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting video info: {str(e)}")

@app.post("/api/download")
async def download_video(request: URLRequest):
    """Download video and return download URL"""
    try:
        url = request.url.strip()
        
        # Validate URL
        if not validate_url(url):
            raise HTTPException(status_code=400, detail="Unsupported platform. Only YouTube, Facebook, and Instagram are supported.")
        
        # Create temporary directory for download
        temp_dir = tempfile.mkdtemp()
        
        # Configure yt-dlp options for download
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'format': 'best[height<=720]',  # Download best quality up to 720p
            'quiet': True,
            'no_warnings': True,
        }
        
        # Download video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Find the downloaded file
            downloaded_file = None
            for file in os.listdir(temp_dir):
                if file.endswith(('.mp4', '.webm', '.mkv', '.avi')):
                    downloaded_file = os.path.join(temp_dir, file)
                    break
            
            if not downloaded_file:
                raise HTTPException(status_code=500, detail="Failed to download video")
            
            # Return file response
            return FileResponse(
                downloaded_file,
                media_type='video/mp4',
                filename=f"{info.get('title', 'video')}.mp4"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading video: {str(e)}")

@app.get("/api/downloads")
async def get_downloads():
    """Get recent downloads"""
    try:
        downloads = list(downloads_collection.find(
            {},
            {'_id': 0, 'info': 0}
        ).sort('created_at', -1).limit(10))
        
        return downloads
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching downloads: {str(e)}")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)