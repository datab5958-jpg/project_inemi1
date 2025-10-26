#!/usr/bin/env python3
import sys
sys.path.append('.')

from app import app
import json

def test_api():
    with app.app_context():
        client = app.test_client()
        
        print("Testing API endpoints...")
        
        # Test cursor endpoint
        response = client.get('/api/feed/videos/cursor?limit=3')
        print(f"Cursor API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            print(f"Success: {data.get('success')}")
            print(f"Data count: {len(data.get('data', []))}")
            
            if data.get('data'):
                first_video = data['data'][0]
                print(f"First video: {json.dumps(first_video, indent=2)}")
            else:
                print("No video data returned")
        else:
            print(f"Error: {response.get_data(as_text=True)}")
        
        # Test other endpoints
        endpoints = [
            '/api/feed/videos?page=1&per_page=3',
            '/api/videos?page=1&per_page=3',
            '/api/list_videos_db'
        ]
        
        for endpoint in endpoints:
            print(f"\nTesting {endpoint}...")
            response = client.get(endpoint)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                if isinstance(data, list):
                    print(f"Array response with {len(data)} items")
                else:
                    print(f"Success: {data.get('success', 'N/A')}")
                    print(f"Data count: {len(data.get('data', []))}")
            else:
                print(f"Error: {response.get_data(as_text=True)}")

if __name__ == "__main__":
    test_api()
