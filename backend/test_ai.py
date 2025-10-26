#!/usr/bin/env python3
"""
Test script untuk memeriksa AI analysis
"""

import os
import sys
import base64

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    print("🔍 Testing AI Analysis...")
    
    # Test import
    from chat import gemini_service
    print("✅ Successfully imported gemini_service")
    print(f"🔍 gemini_service type: {type(gemini_service)}")
    
    # Test with dummy base64 image data
    dummy_image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    print("🔍 Testing analyze_image_for_music...")
    result = gemini_service.analyze_image_for_music(dummy_image_data)
    print(f"🔍 Result: {result}")
    
    if result and result.get('success'):
        analysis_text = result.get('analysis', '')
        print("✅ AI Analysis successful!")
        print("📝 Analysis text:")
        print("=" * 50)
        print(analysis_text)
        print("=" * 50)
    else:
        print("❌ AI Analysis failed!")
        print(f"Error: {result}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()



