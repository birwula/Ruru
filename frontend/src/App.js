import React, { useState, useEffect } from 'react';
import './App.css';

const App = () => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [videoInfo, setVideoInfo] = useState(null);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [recentDownloads, setRecentDownloads] = useState([]);
  const [selectedFormat, setSelectedFormat] = useState(null);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  useEffect(() => {
    fetchRecentDownloads();
  }, []);

  const fetchRecentDownloads = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/downloads`);
      if (response.ok) {
        const downloads = await response.json();
        setRecentDownloads(downloads);
      }
    } catch (err) {
      console.error('Error fetching recent downloads:', err);
    }
  };

  const detectPlatform = (url) => {
    if (url.includes('youtube.com') || url.includes('youtu.be')) {
      return 'YouTube';
    } else if (url.includes('facebook.com') || url.includes('fb.watch')) {
      return 'Facebook';
    } else if (url.includes('instagram.com')) {
      return 'Instagram';
    }
    return 'Unknown';
  };

  const getPlatformIcon = (platform) => {
    switch (platform) {
      case 'YouTube':
        return '🎬';
      case 'Facebook':
        return '📘';
      case 'Instagram':
        return '📸';
      default:
        return '🎥';
    }
  };

  const handleExtractInfo = async () => {
    if (!url.trim()) {
      setError('Please enter a valid URL');
      return;
    }

    setLoading(true);
    setError('');
    setVideoInfo(null);

    try {
      const response = await fetch(`${backendUrl}/api/extract-info`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (response.ok) {
        const data = await response.json();
        setVideoInfo(data);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to extract video information');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!url.trim()) {
      setError('Please enter a valid URL');
      return;
    }

    setDownloading(true);
    setError('');

    try {
      const response = await fetch(`${backendUrl}/api/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (response.ok) {
        // Get the filename from the response headers
        const contentDisposition = response.headers.get('content-disposition');
        let filename = 'video.mp4';
        
        if (contentDisposition) {
          const matches = contentDisposition.match(/filename\*?=['"]?([^'";]+)['"]?/);
          if (matches) {
            filename = decodeURIComponent(matches[1]);
          }
        }

        const blob = await response.blob();
        
        // Create download link
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);

        // Refresh recent downloads
        fetchRecentDownloads();
        
        // Show success message
        setError('');
        
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to download video');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0">
          <img 
            src="https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7" 
            alt="Social Media"
            className="w-full h-full object-cover opacity-20"
          />
        </div>
        
        <div className="relative max-w-7xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
              Social Media Video Downloader
            </h1>
            <p className="text-xl md:text-2xl text-gray-300 mb-8">
              Download videos from YouTube, Facebook, and Instagram with ease
            </p>
            
            {/* Supported Platforms */}
            <div className="flex justify-center items-center space-x-8 mb-12">
              <div className="flex items-center space-x-2 text-white">
                <span className="text-2xl">🎬</span>
                <span className="text-lg font-semibold">YouTube</span>
              </div>
              <div className="flex items-center space-x-2 text-white">
                <span className="text-2xl">📘</span>
                <span className="text-lg font-semibold">Facebook</span>
              </div>
              <div className="flex items-center space-x-2 text-white">
                <span className="text-2xl">📸</span>
                <span className="text-lg font-semibold">Instagram</span>
              </div>
            </div>
            
            {/* URL Input */}
            <div className="max-w-2xl mx-auto">
              <div className="flex flex-col sm:flex-row gap-4">
                <input
                  type="url"
                  placeholder="Paste your video URL here..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="flex-1 px-6 py-4 rounded-lg text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-lg"
                />
                <button
                  onClick={handleExtractInfo}
                  disabled={loading}
                  className="px-8 py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg font-semibold text-lg transition-colors duration-200"
                >
                  {loading ? 'Analyzing...' : 'Get Video Info'}
                </button>
              </div>
              
              {error && (
                <div className="mt-4 p-4 bg-red-500/20 border border-red-500 rounded-lg">
                  <p className="text-red-200">{error}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Video Info Section */}
      {videoInfo && (
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
            <div className="flex flex-col md:flex-row gap-6">
              {/* Thumbnail */}
              <div className="md:w-1/3">
                {videoInfo.thumbnail && (
                  <img 
                    src={videoInfo.thumbnail} 
                    alt={videoInfo.title}
                    className="w-full rounded-lg shadow-lg"
                  />
                )}
              </div>
              
              {/* Video Details */}
              <div className="md:w-2/3">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl">{getPlatformIcon(videoInfo.platform)}</span>
                  <span className="text-sm font-semibold text-blue-300 bg-blue-900/30 px-3 py-1 rounded-full">
                    {videoInfo.platform}
                  </span>
                </div>
                
                <h2 className="text-2xl font-bold text-white mb-4">{videoInfo.title}</h2>
                
                <div className="flex items-center gap-4 mb-6 text-gray-300">
                  <span>⏱️ {formatDuration(parseInt(videoInfo.duration))}</span>
                  <span>📹 {videoInfo.formats.length} formats available</span>
                </div>
                
                <button
                  onClick={handleDownload}
                  disabled={downloading}
                  className="w-full md:w-auto px-8 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white rounded-lg font-semibold text-lg transition-colors duration-200 flex items-center justify-center gap-2"
                >
                  {downloading ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      Downloading...
                    </>
                  ) : (
                    <>
                      📥 Download Video
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recent Downloads */}
      {recentDownloads.length > 0 && (
        <div className="max-w-4xl mx-auto px-4 py-8">
          <h3 className="text-2xl font-bold text-white mb-6">Recent Downloads</h3>
          <div className="grid gap-4">
            {recentDownloads.map((download) => (
              <div key={download.id} className="bg-white/10 backdrop-blur-md rounded-lg p-4 border border-white/20">
                <div className="flex items-center gap-4">
                  {download.thumbnail && (
                    <img 
                      src={download.thumbnail} 
                      alt={download.title}
                      className="w-16 h-16 rounded-lg object-cover"
                    />
                  )}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-lg">{getPlatformIcon(download.platform)}</span>
                      <span className="text-sm text-blue-300">{download.platform}</span>
                    </div>
                    <h4 className="text-white font-semibold truncate">{download.title}</h4>
                    <p className="text-gray-300 text-sm">Duration: {formatDuration(download.duration)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="text-center py-8 text-gray-400">
        <p>© 2025 Social Media Video Downloader. Built with React & FastAPI.</p>
      </footer>
    </div>
  );
};

export default App;