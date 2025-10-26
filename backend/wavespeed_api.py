import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

class WaveSpeedAPI:
    def __init__(self):
        self.api_key = os.getenv("WAVESPEED_API_KEY")
        if not self.api_key:
            raise ValueError("WAVESPEED_API_KEY not found in environment variables")
    
    def edit_image(self, image_url, prompt, fusion_image=None, size="2227*3183"):
        """
        Edit image using ByteDance Seedream v4 model via WaveSpeed AI
        
        Args:
            image_url (str): URL of the image to edit
            prompt (str): Edit instruction
            fusion_image (str, optional): Base64 encoded fusion image
            size (str): Output size, default "2227*3183"
        
        Returns:
            dict: Result containing success status and image URL
        """
        url = "https://api.wavespeed.ai/api/v3/bytedance/seedream-v4/edit"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        # Prepare images array
        images = [image_url]
        if fusion_image:
            images.append(fusion_image)
        
        payload = {
            "enable_base64_output": False,
            "enable_sync_mode": False,
            "images": images,
            "prompt": prompt,
            "size": size
        }
        
        print(f"Making request to ByteDance Seedream v4 via WaveSpeed AI")
        print(f"Image URL: {image_url}")
        print(f"Prompt: {prompt}")
        print(f"Size: {size}")
        if fusion_image:
            print(f"Fusion image provided: {len(fusion_image)} characters")
        
        begin = time.time()
        
        try:
            # Submit task
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            
            if response.status_code == 200:
                result = response.json()["data"]
                request_id = result["id"]
                print(f"Task submitted successfully. Request ID: {request_id}")
            else:
                print(f"Error: {response.status_code}, {response.text}")
                return {
                    "success": False,
                    "error": f"Failed to submit task: {response.text}"
                }
            
            # Poll for results
            result_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
            result_headers = {"Authorization": f"Bearer {self.api_key}"}
            
            while True:
                response = requests.get(result_url, headers=result_headers, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()["data"]
                    status = result["status"]
                    
                    if status == "completed":
                        end = time.time()
                        print(f"Task completed in {end - begin} seconds.")
                        image_url = result["outputs"][0]
                        print(f"Task completed. URL: {image_url}")
                        
                        return {
                            "success": True,
                            "image_url": image_url,
                            "processing_time": end - begin
                        }
                    elif status == "failed":
                        error_msg = result.get('error', 'Unknown error')
                        print(f"Task failed: {error_msg}")
                        return {
                            "success": False,
                            "error": f"Task failed: {error_msg}"
                        }
                    else:
                        print(f"Task still processing. Status: {status}")
                else:
                    print(f"Error: {response.status_code}, {response.text}")
                    return {
                        "success": False,
                        "error": f"Error checking result: {response.text}"
                    }
                
                time.sleep(2)  # Wait 2 seconds before checking again
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout. Please try again."
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "success": False,
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

def main():
    """Test function - same as the original code you provided"""
    print("Hello from WaveSpeedAI!")
    API_KEY = os.getenv("WAVESPEED_API_KEY")
    print(f"API_KEY: {API_KEY}")

    url = "https://api.wavespeed.ai/api/v3/bytedance/seedream-v4/edit"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "enable_base64_output": False,
        "enable_sync_mode": False,
        "images": [
                "https://d1q70pf5vjeyhc.cloudfront.net/media/92d2d4ca66f84793adcb20742b15d262/images/1757414555847323990_Si8cqCBF.jpeg"
        ],
        "prompt": "Turn this photo into a characterfigure. Behind it, place a box withthe character's image printed on it,and a computer showing the Blendermodeling process on its screen. In frontof the box, add a round plastic basewith the character figure standing on it .set the scene indoors if possible.",
        "size": "2227*3183"
    }

    begin = time.time()
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        result = response.json()["data"]
        request_id = result["id"]
        print(f"Task submitted successfully. Request ID: {request_id}")
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return

    url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    # Poll for results
    while True:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            result = response.json()["data"]
            status = result["status"]

            if status == "completed":
                end = time.time()
                print(f"Task completed in {end - begin} seconds.")
                url = result["outputs"][0]
                print(f"Task completed. URL: {url}")
                break
            elif status == "failed":
                print(f"Task failed: {result.get('error')}")
                break
            else:
                print(f"Task still processing. Status: {status}")
        else:
            print(f"Error: {response.status_code}, {response.text}")
            break

        time.sleep(0.1)

if __name__ == "__main__":
    main()
