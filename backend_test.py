import requests
import unittest
import sys
from datetime import datetime

class SocialMediaVideoDownloaderAPITester:
    def __init__(self, base_url="https://74ccf6c4-3581-4467-be8a-0047827b1a10.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.headers.get('content-type') == 'application/json' else {}
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json().get('detail', 'No detail provided')
                    print(f"Error detail: {error_detail}")
                except:
                    print("Could not parse error response")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test the health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        return success

    def test_extract_info_youtube(self):
        """Test extracting info from a YouTube URL"""
        success, response = self.run_test(
            "Extract YouTube Video Info",
            "POST",
            "api/extract-info",
            200,
            data={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        )
        
        if success:
            print(f"Video Title: {response.get('title', 'Unknown')}")
            print(f"Platform: {response.get('platform', 'Unknown')}")
            print(f"Duration: {response.get('duration', 'Unknown')}")
            print(f"Formats available: {len(response.get('formats', []))}")
        
        return success, response

    def test_extract_info_invalid_url(self):
        """Test extracting info with an invalid URL"""
        success, _ = self.run_test(
            "Extract Info with Invalid URL",
            "POST",
            "api/extract-info",
            400,
            data={"url": "https://example.com/video"}
        )
        # For this test, we expect a 400 error, so success means we got the error
        return success

    def test_extract_info_facebook(self):
        """Test extracting info from a Facebook URL"""
        # Using a public Facebook video URL
        success, response = self.run_test(
            "Extract Facebook Video Info",
            "POST",
            "api/extract-info",
            200,
            data={"url": "https://www.facebook.com/facebook/videos/10153231379946729/"}
        )
        
        if success:
            print(f"Video Title: {response.get('title', 'Unknown')}")
            print(f"Platform: {response.get('platform', 'Unknown')}")
        
        return success

    def test_download_endpoint(self):
        """Test the download endpoint with a YouTube URL"""
        success, _ = self.run_test(
            "Download Video",
            "POST",
            "api/download",
            200,  # We expect a 200 but won't actually download the file
            data={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        )
        return success

    def test_get_downloads(self):
        """Test getting recent downloads"""
        success, response = self.run_test(
            "Get Recent Downloads",
            "GET",
            "api/downloads",
            200
        )
        
        if success and isinstance(response, list):
            print(f"Recent downloads count: {len(response)}")
            if len(response) > 0:
                print(f"Most recent download: {response[0].get('title', 'Unknown')}")
        
        return success

def main():
    # Get the backend URL from command line args or use default
    backend_url = "https://74ccf6c4-3581-4467-be8a-0047827b1a10.preview.emergentagent.com"
    
    print(f"🚀 Testing Social Media Video Downloader API at {backend_url}")
    tester = SocialMediaVideoDownloaderAPITester(backend_url)
    
    # Run tests
    health_check_success = tester.test_health_check()
    if not health_check_success:
        print("❌ Health check failed, stopping tests")
        return 1
    
    # Test extract info with YouTube URL
    youtube_info_success, youtube_info = tester.test_extract_info_youtube()
    
    # Test invalid URL
    tester.test_extract_info_invalid_url()
    
    # Test Facebook URL
    tester.test_extract_info_facebook()
    
    # Test download endpoint
    if youtube_info_success:
        tester.test_download_endpoint()
    
    # Test recent downloads
    tester.test_get_downloads()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())