#!/usr/bin/env python3
"""
Test script untuk memverifikasi perbaikan current_app error
"""

import os
import sys
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def test_import():
    """Test import Generate_video_avatar module"""
    try:
        from Generate_video_avatar import generate_video_avatar_bp
        print("✅ Import Generate_video_avatar successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        return False

def test_blueprint_creation():
    """Test blueprint creation"""
    try:
        from Generate_video_avatar import generate_video_avatar_bp
        print(f"✅ Blueprint created: {generate_video_avatar_bp.name}")
        return True
    except Exception as e:
        print(f"❌ Blueprint creation failed: {str(e)}")
        return False

def test_function_signatures():
    """Test function signatures"""
    try:
        from Generate_video_avatar import generate_tts_audio, generate_avatar_video, download_and_save_file
        
        # Check if functions are callable
        if callable(generate_tts_audio):
            print("✅ generate_tts_audio is callable")
        else:
            print("❌ generate_tts_audio is not callable")
            return False
            
        if callable(generate_avatar_video):
            print("✅ generate_avatar_video is callable")
        else:
            print("❌ generate_avatar_video is not callable")
            return False
            
        if callable(download_and_save_file):
            print("✅ download_and_save_file is callable")
        else:
            print("❌ download_and_save_file is not callable")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Function signature test failed: {str(e)}")
        return False

def main():
    print("🔧 Testing current_app Fix")
    print("=" * 40)
    
    tests = [
        ("Import Module", test_import),
        ("Blueprint Creation", test_blueprint_creation),
        ("Function Signatures", test_function_signatures),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 20)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
            results.append((test_name, False))
    
    print("\n" + "=" * 40)
    print("📊 Test Results Summary")
    print("=" * 40)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All tests passed! The current_app fix should work.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    return all_passed

if __name__ == "__main__":
    main()




