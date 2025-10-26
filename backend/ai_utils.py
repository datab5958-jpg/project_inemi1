import google.generativeai as genai
from PIL import Image
import io
import base64
import re
from typing import Dict, List, Optional

class AIUtils:
    """Utility class for AI operations"""
    
    def __init__(self, api_key: str):
        """Initialize AI utilities with API key"""
        genai.configure(api_key=api_key)
        self.text_model = genai.GenerativeModel('gemini-2.0-flash')
        # Note: Vision analysis now uses REST API directly, no need for vision_model
    
    def generate_prompt_from_form(self, form_data: Dict) -> Dict:
        """
        Generate AI prompt from form data
        form_data should contain: subject, action, expression, location, time, camera_angle, camera_movement, lighting
        """
        try:
            # Build the prompt from form data
            prompt_parts = []
            
            if form_data.get('subject'):
                prompt_parts.append(f"Subjek: {form_data['subject']}")
            
            if form_data.get('action'):
                prompt_parts.append(f"Aksi: {form_data['action']}")
            
            if form_data.get('expression'):
                prompt_parts.append(f"Ekspresi: {form_data['expression']}")
            
            if form_data.get('location'):
                prompt_parts.append(f"Lokasi: {form_data['location']}")
            
            if form_data.get('time'):
                prompt_parts.append(f"Waktu: {form_data['time']}")
            
            if form_data.get('camera_angle'):
                prompt_parts.append(f"Sudut Kamera: {form_data['camera_angle']}")
            
            if form_data.get('camera_movement'):
                prompt_parts.append(f"Pergerakan Kamera: {form_data['camera_movement']}")
            
            if form_data.get('lighting'):
                prompt_parts.append(f"Pencahayaan: {form_data['lighting']}")
            
            # Create the base prompt
            base_prompt = ", ".join(prompt_parts)
            
            # Create AI instruction
            ai_instruction = f"""
            Berdasarkan informasi berikut, buatlah prompt yang detail dan kreatif untuk AI image generator:
            
            {base_prompt}
            
            Buatlah prompt yang:
            1. Menggabungkan semua elemen dengan harmonis
            2. Menambahkan detail visual yang menarik
            3. Menggunakan bahasa yang deskriptif dan artistik
            4. Cocok untuk AI image generator seperti DALL-E, Midjourney, atau Stable Diffusion
            5. Maksimal 200 kata
            
            Berikan juga saran untuk meningkatkan prompt ini.
            """
            
            # Generate AI response
            ai_response = self.generate_text_response(ai_instruction)
            
            return {
                'success': True,
                'generated_prompt': ai_response,
                'base_prompt': base_prompt,
                'form_data': form_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'generated_prompt': None,
                'base_prompt': None,
                'form_data': form_data
            }
    
    def generate_text_response(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate text response using Gemini"""
        try:
            response = self.text_model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def analyze_image(self, image_data: str, prompt: str = "Describe this image in detail") -> str:
        """Analyze image using Gemini Vision API (same approach as chat.py)"""
        try:
            from config import Config
            import requests
            
            # Clean base64 data
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Use same approach as chat.py
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_data
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 10000,
                }
            }
            
            headers = {
                "Content-Type": "application/json",
            }
            
            url = f"{Config.GEMINI_API_URL}?key={Config.GEMINI_API_KEY}"
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    return result['candidates'][0]['content']['parts'][0]['text']
                else:
                    return "Error: No candidates in Gemini response"
            else:
                return f"Error: Gemini API error {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error analyzing image: {str(e)}"
    
    def create_chat_session(self, history: List[Dict] = None) -> object:
        """Create a new chat session"""
        if history is None:
            history = []
        return self.text_model.start_chat(history=history)
    
    def generate_creative_content(self, content_type: str, topic: str, style: str = "creative") -> str:
        """Generate creative content based on type and topic"""
        prompts = {
            'story': f"Write a creative {style} story about {topic}. Make it engaging and interesting with vivid descriptions.",
            'poem': f"Write a beautiful poem about {topic} in a {style} style. Make it emotional and meaningful.",
            'article': f"Write an informative article about {topic} in a {style} tone. Include relevant details and insights.",
            'script': f"Write a creative script about {topic} in a {style} style. Include dialogue and scene descriptions.",
            'essay': f"Write a well-structured essay about {topic} in a {style} tone. Include introduction, body, and conclusion."
        }
        
        prompt = prompts.get(content_type, f"Create {content_type} content about {topic} in a {style} style.")
        return self.generate_text_response(prompt)
    
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text"""
        prompt = f"""
        Analyze the sentiment of this text and provide a JSON response with the following structure:
        {{
            "overall_sentiment": "positive/negative/neutral",
            "confidence": 0.0-1.0,
            "emotions": ["emotion1", "emotion2"],
            "key_phrases": ["phrase1", "phrase2"],
            "summary": "brief analysis"
        }}
        
        Text to analyze: {text}
        """
        
        response = self.generate_text_response(prompt)
        
        # Try to extract JSON from response
        try:
            # Find JSON pattern in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                import json
                return json.loads(json_match.group())
        except:
            pass
        
        # Fallback response
        return {
            "overall_sentiment": "neutral",
            "confidence": 0.5,
            "emotions": ["unknown"],
            "key_phrases": [],
            "summary": response
        }
    
    def translate_text(self, text: str, target_language: str, source_language: str = "auto") -> str:
        """Translate text to target language"""
        prompt = f"Translate the following text from {source_language} to {target_language}. Provide only the translation without any additional explanation: {text}"
        return self.generate_text_response(prompt)
    
    def summarize_text(self, text: str, max_length: int = 200) -> str:
        """Summarize text to specified length"""
        prompt = f"Summarize the following text in {max_length} characters or less: {text}"
        return self.generate_text_response(prompt)
    
    def generate_hashtags(self, text: str, count: int = 5) -> List[str]:
        """Generate relevant hashtags for text"""
        prompt = f"Generate {count} relevant hashtags for this text. Return only the hashtags separated by spaces: {text}"
        response = self.generate_text_response(prompt)
        
        # Extract hashtags
        hashtags = re.findall(r'#\w+', response)
        return hashtags[:count]
    
    def improve_text(self, text: str, improvement_type: str = "grammar") -> str:
        """Improve text based on type (grammar, style, clarity)"""
        prompts = {
            'grammar': f"Correct the grammar and spelling in this text: {text}",
            'style': f"Improve the writing style and make it more engaging: {text}",
            'clarity': f"Make this text clearer and more concise: {text}",
            'formal': f"Make this text more formal and professional: {text}",
            'casual': f"Make this text more casual and conversational: {text}"
        }
        
        prompt = prompts.get(improvement_type, f"Improve this text: {text}")
        return self.generate_text_response(prompt) 