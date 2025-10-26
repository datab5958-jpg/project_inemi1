#!/usr/bin/env python3
"""
Test script untuk memverifikasi perbaikan Generate Video Avatar
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def test_api_connectivity():
    """Test konektivitas ke API WaveSpeed"""
    print("Testing API connectivity...")
    
    API_KEY = os.getenv("WAVESPEED_API_KEY")
    if not API_KEY:
        print("❌ WAVESPEED_API_KEY not found in environment")
        return False
    
    print(f"✅ API Key found: {API_KEY[:10]}...")
    
    # Test TTS API
    try:
        url = "https://api.wavespeed.ai/api/v3/minimax/speech-2.5-turbo-preview"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }
        payload = {
            "emotion": "surprised",
            "enable_sync_mode": False,
            "english_normalization": False,
            "language_boost": "Indonesian",
            "pitch": 0,
            "speed": 1,
            "text": "Test",
            "voice_id": "Indonesian_ReservedYoungMan",
            "volume": 1
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        if response.status_code == 200:
            print("✅ TTS API accessible")
            return True
        else:
            print(f"❌ TTS API error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ TTS API error: {str(e)}")
        return False

def test_avatar_api():
    """Test konektivitas ke Avatar API"""
    print("Testing Avatar API...")
    
    API_KEY = os.getenv("WAVESPEED_API_KEY")
    if not API_KEY:
        print("❌ WAVESPEED_API_KEY not found")
        return False
    
    try:
        url = "https://api.wavespeed.ai/api/v3/bytedance/avatar-omni-human-1.5"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }
        payload = {
            "audio": "https://example.com/test.mp3",
            "image": "https://example.com/test.jpg",
            "enable_base64_output": False
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        if response.status_code == 200:
            print("✅ Avatar API accessible")
            return True
        else:
            print(f"❌ Avatar API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Avatar API error: {str(e)}")
        return False

def test_file_structure():
    """Test struktur file yang diperlukan"""
    print("Testing file structure...")
    
    required_files = [
        "Generate_video_avatar.py",
        "templates/Generate_video_avatar.html",
        "static/outputs/.gitkeep",
        "static/uploads"
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing")
            all_exist = False
    
    return all_exist

def main():
    print("🔧 Testing Generate Video Avatar Fixes")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("TTS API Connectivity", test_api_connectivity),
        ("Avatar API Connectivity", test_avatar_api),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! The fixes should work correctly.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    return all_passed

if __name__ == "__main__":
    main()




