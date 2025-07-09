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

class DownloadRequest(BaseModel):
    url: str
    format_id: str = None  # Optional: if not provided, use best quality

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
            'socket_timeout': 30,
            'retries': 3,
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
                        format_info = {
                            'format_id': fmt.get('format_id'),
                            'ext': fmt.get('ext'),
                            'resolution': fmt.get('resolution', 'Unknown'),
                            'height': fmt.get('height'),
                            'width': fmt.get('width'),
                            'fps': fmt.get('fps'),
                            'filesize': fmt.get('filesize'),
                            'filesize_approx': fmt.get('filesize_approx'),
                            'tbr': fmt.get('tbr'),  # Total bitrate
                            'vbr': fmt.get('vbr'),  # Video bitrate
                            'abr': fmt.get('abr'),  # Audio bitrate
                            'acodec': fmt.get('acodec'),
                            'vcodec': fmt.get('vcodec'),
                            'format_note': fmt.get('format_note', ''),
                            'quality': fmt.get('quality', 0)
                        }
                        
                        # Create a readable quality description
                        quality_desc = []
                        if format_info['height']:
                            quality_desc.append(f"{format_info['height']}p")
                        if format_info['fps']:
                            quality_desc.append(f"{format_info['fps']}fps")
                        if format_info['ext']:
                            quality_desc.append(format_info['ext'].upper())
                        
                        format_info['quality_desc'] = ' • '.join(quality_desc) if quality_desc else 'Unknown'
                        
                        # Calculate approximate file size in MB
                        if format_info['filesize']:
                            format_info['size_mb'] = round(format_info['filesize'] / (1024 * 1024), 1)
                        elif format_info['filesize_approx']:
                            format_info['size_mb'] = round(format_info['filesize_approx'] / (1024 * 1024), 1)
                        else:
                            format_info['size_mb'] = None
                        
                        formats.append(format_info)
            
            # Sort formats by height (resolution) descending, then by quality
            formats.sort(key=lambda x: (x.get('height', 0), x.get('quality', 0)), reverse=True)
            
            # Remove duplicates and limit to top 10 formats
            seen_resolutions = set()
            unique_formats = []
            for fmt in formats:
                resolution_key = (fmt.get('height'), fmt.get('ext'))
                if resolution_key not in seen_resolutions:
                    seen_resolutions.add(resolution_key)
                    unique_formats.append(fmt)
                    if len(unique_formats) >= 10:
                        break
            
            response_data = {
                'id': download_id,
                'url': url,
                'title': info.get('title', 'Unknown'),
                'platform': platform,
                'thumbnail': info.get('thumbnail', ''),
                'duration': str(info.get('duration', 0)),
                'formats': unique_formats,  # Top 10 unique formats
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
                'formats': unique_formats,
                'status': 'ready',
                'created_at': datetime.now(),
                'info': info
            })
            
            return response_data
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting video info: {str(e)}")

@app.post("/api/download")
async def download_video(request: DownloadRequest):
    """Download video and return download URL"""
    try:
        url = request.url.strip()
        
        # Validate URL
        if not validate_url(url):
            raise HTTPException(status_code=400, detail="Unsupported platform. Only YouTube, Facebook, and Instagram are supported.")
        
        # Create temporary directory for download
        temp_dir = tempfile.mkdtemp()
        
        # Determine format to use
        if request.format_id:
            # Use specific format if provided
            format_selector = request.format_id
        else:
            # Use default format if no specific format is requested
            format_selector = 'best[height<=720]'
        
        # Configure yt-dlp options for download
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'format': format_selector,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 3,
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