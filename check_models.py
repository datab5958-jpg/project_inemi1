import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def check_models():
    print("=== Checking Available Models ===")
    API_KEY = os.getenv("WAVESPEED_API_KEY")
    print(f"API_KEY: {API_KEY[:10]}..." if API_KEY else "API_KEY not found")
    
    if not API_KEY:
        print("ERROR: WAVESPEED_API_KEY not found")
        return
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    
    # Test payload untuk face swap
    face_swap_payload = {
        "enable_base64_output": False,
        "enable_safety_checker": True,
        "enable_sync_mode": False,
        "face_image": "https://d1q70pf5vjeyhc.wavespeed.ai/media/images/1752546643736831648_IVfDAxtq.jpeg",
        "image": "https://d1q70pf5vjeyhc.wavespeed.ai/media/images/1752546604367620589_qF0WTQOJ.jpeg",
        "output_format": "jpeg",
        "target_index": 0
    }
    
    # Test payload untuk generate image
    generate_payload = {
        "prompt": "test",
        "num_images": 1
    }
    
    # Test beberapa kemungkinan model
    models_to_test = [
        ("wavespeed-ai/imagen4", generate_payload, "Generate Image"),
        ("wavespeed-ai/image-face-swap", face_swap_payload, "Face Swap (Correct)"),
        ("wavespeed-ai/image_face_swap", face_swap_payload, "Face Swap (Underscore)"),
        ("wavespeed-ai/face-swap", face_swap_payload, "Face Swap Alt 1"),
        ("wavespeed-ai/face_swap", face_swap_payload, "Face Swap Alt 2"),
        ("wavespeed-ai/face-swap-ai", face_swap_payload, "Face Swap AI"),
        ("wavespeed-ai/face-swap-model", face_swap_payload, "Face Swap Model"),
        ("wavespeed-ai/flux-kontext-dev/multi-ultra-fast", generate_payload, "Fusigaya")
    ]
    
    print("\n=== Testing Models ===")
    available_models = []
    
    for model, payload, description in models_to_test:
        url = f"https://api.wavespeed.ai/api/v3/wavespeed-ai/{model}"
        print(f"\nTesting: {model} ({description})")
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✅ AVAILABLE: {model}")
                available_models.append((model, description))
            elif response.status_code == 400:
                error_text = response.text
                if "product not found" in error_text:
                    print(f"  ❌ NOT AVAILABLE: {model} (product not found)")
                else:
                    print(f"  ⚠️  ERROR: {model} - {error_text}")
            else:
                print(f"  ❌ ERROR: {model} - {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"  ❌ EXCEPTION: {model} - {str(e)}")
    
    print(f"\n=== SUMMARY ===")
    print(f"Available models: {len(available_models)}")
    for model, description in available_models:
        print(f"  ✅ {model} ({description})")
    
    # Cek apakah ada model face swap yang tersedia
    face_swap_models = [m for m, d in available_models if "face" in m.lower() or "swap" in m.lower()]
    if face_swap_models:
        print(f"\n🎉 Face swap models available: {face_swap_models}")
    else:
        print(f"\n❌ No face swap models available!")
        print("You may need to:")
        print("1. Upgrade your WavespeedAI plan")
        print("2. Subscribe to face swap feature")
        print("3. Check if face swap is available in your region")

if __name__ == "__main__":
    check_models() 