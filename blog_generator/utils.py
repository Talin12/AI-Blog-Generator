import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
import time
import re

# Global rate limiting state
last_request_time = 0

load_dotenv()

def get_gemini_transcript(youtube_url: str) -> tuple:
    """Get video title and transcript using Gemini API with enhanced reliability"""
    global last_request_time
    
    try:
        print("Available models:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
        # Rate limiting - minimum 1.5 seconds between requests
        current_time = time.time()
        if current_time - last_request_time < 1.5:
            time.sleep(1.5 - (current_time - last_request_time))
        last_request_time = time.time()
        
        # Configure API
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("[CRITICAL] Missing GEMINI_API_KEY")
            return None, None
            
        genai.configure(api_key=api_key)
        
        # CORRECTED MODEL NAMES (as of July 2025)
        # Use one of these valid models:
        model = genai.GenerativeModel("gemini-1.5-flash")  # Basic version
        # OR for more advanced needs:
        # model = genai.GenerativeModel("gemini-1.5-pro")  # Advanced version
        
        # Enhanced prompt with strict JSON format requirements
        prompt = f"""
        EXTRACT VIDEO METADATA FOR: {youtube_url}
        Return ONLY valid JSON with these keys:
        {{
            "title": "exact video title string",
            "transcript": "full verbatim transcript text without timestamps"
        }}
        """
        
        # Generate content with safety settings
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=20000,  # Increased for long transcripts
                temperature=0.3
            ),
            safety_settings={
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
            }
        )
        
        # Extract and clean JSON string
        raw_text = response.text.strip()
        json_str = re.sub(r'^```json|```$', '', raw_text, flags=re.IGNORECASE).strip()
        
        # Parse JSON
        data = json.loads(json_str)
        
        # Validate response structure
        if 'title' not in data or 'transcript' not in data:
            print(f"[WARNING] Invalid response structure: {data.keys()}")
            return None, None
            
        return data['title'], data['transcript']
    
    except json.JSONDecodeError:
        print(f"[ERROR] Failed to parse JSON response: {raw_text[:200]}...")
        return None, None
        
    except genai.types.BlockedPromptException:
        print("[ERROR] Content blocked by safety filters")
        return None, None
        
    except genai.types.StopCandidateException as e:
        print(f"[ERROR] Response generation stopped: {str(e)}")
        return None, None
        
    except Exception as e:
        print(f"[GEMINI ERROR] {str(e)}")
        return None, None