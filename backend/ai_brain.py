"""
AI Brain - Ollama-powered Natural Language Understanding
Provides intelligent responses and command interpretation
"""
import json
import re
from typing import Dict, Tuple, Optional
from datetime import datetime

# Try to import ollama
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠ Ollama not installed. Run: pip install ollama")

import asyncio
import functools



class AIBrain:
    """
    AI-powered brain for Prime voice assistant.
    Uses Ollama for local LLM inference.
    """
    
    def __init__(self, model_name: str = "qwen2"):
        self.model_name = model_name
        self.is_available = OLLAMA_AVAILABLE
        self.conversation_history = []
        
        # Compact system prompt optimized for smaller/faster models
        self.system_prompt = """You are Prime, a voice assistant that controls a Windows PC. Always respond in JSON only.

ACTIONS (use "action" field):
- open_app: params {"app_name": "notepad/chrome/calculator/explorer/paint/cmd"}
- close_app: params {"app_name": "name"}
- take_screenshot: params {}
- volume_up, volume_down, mute: params {}
- brightness_up, brightness_down: params {}
- time, date: params {}
- web_search: params {"query": "term"}
- shutdown, restart, system_info: params {}
- open_camera, close_camera: params {}

FORMAT: {"response": "short reply", "action": "action_or_null", "params": {}}

Examples:
"open notepad" → {"response": "Opening Notepad!", "action": "open_app", "params": {"app_name": "notepad"}}
"what time" → {"response": "Checking!", "action": "time", "params": {}}
"volume up" → {"response": "Louder!", "action": "volume_up", "params": {}}
"hello" → {"response": "Hi! How can I help?", "action": null, "params": {}}

Return ONLY JSON. Keep response under 10 words."""
        
        if self.is_available:
            self._check_model()
    
    def _check_model(self):
        """Check if the model is available, suggest download if not"""
        try:
            # List available models - format changed in newer ollama versions
            response = ollama.list()
            
            # Handle different response formats
            models_list = []
            if isinstance(response, dict):
                models_list = response.get('models', [])
            elif hasattr(response, 'models'):
                models_list = response.models
            else:
                models_list = list(response) if response else []
            
            # Extract model names
            model_names = []
            for m in models_list:
                if isinstance(m, dict):
                    name = m.get('name', '').split(':')[0]
                elif hasattr(m, 'model'):
                    name = m.model.split(':')[0]
                elif hasattr(m, 'name'):
                    name = m.name.split(':')[0]
                else:
                    name = str(m).split(':')[0]
                if name:
                    model_names.append(name)
            
            print(f"📋 Available Ollama models: {model_names}")
            
            if self.model_name in model_names or any(self.model_name in m for m in model_names):
                print(f"✓ AI Brain initialized with model: {self.model_name}")
            else:
                print(f"⚠ Model '{self.model_name}' not found locally.")
                print(f"  Run: ollama pull {self.model_name}")
                # Still try to use it - it might work
                
        except Exception as e:
            print(f"⚠ Could not check Ollama models: {e}")
            print("  Attempting to use AI anyway...")
            # Don't disable - try to use it anyway
    
    def _detect_language(self, text: str) -> str:
        """Detect if text is Hindi or English"""
        # Check for Devanagari Unicode range
        hindi_pattern = re.compile(r'[\u0900-\u097F]')
        if hindi_pattern.search(text):
            return 'hi'
        return 'en'
    
    def _parse_response(self, raw_response: str) -> Dict:
        """Parse LLM response to extract action and response text"""
        try:
            # Try to find JSON in the response
            # Sometimes LLMs add extra text before/after JSON
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    'response': parsed.get('response', raw_response),
                    'action': parsed.get('action'),
                    'params': parsed.get('params', {})
                }
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Fallback: return raw response with no action
        return {
            'response': raw_response.strip(),
            'action': None,
            'params': {}
        }
    
    async def think(self, user_input: str) -> Dict:
        """
        Process user input and generate response with optional action.
        
        Args:
            user_input: The user's voice command or question
            
        Returns:
            Dict with 'response', 'action', and 'params'
        """
        if not self.is_available:
            return self._fallback_response(user_input)
        
        try:
            # Detect language for context
            language = self._detect_language(user_input)
            
            # Add context about current time
            current_time = datetime.now().strftime("%I:%M %p")
            current_date = datetime.now().strftime("%A, %B %d, %Y")
            
            # Build messages
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Current time: {current_time}, Date: {current_date}\n\nUser says: {user_input}"}
            ]
            
            # Call Ollama asynchronously to avoid blocking the event loop
            response = await asyncio.to_thread(
                ollama.chat,
                model=self.model_name,
                messages=messages,
                format="json",  # Force JSON output
                options={
                    "temperature": 0.3,      # Lower for more predictable output
                    "num_predict": 60,       # Shorter responses for speed
                    "num_ctx": 512,          # Smaller context for speed
                    "top_k": 10,             # Faster sampling
                    "top_p": 0.85,
                }
            )
            
            raw_response = response['message']['content']
            print(f"🤖 AI Raw: {raw_response}")
            
            # Parse the response
            parsed = self._parse_response(raw_response)
            parsed['language'] = language
            
            return parsed
            
        except Exception as e:
            print(f"❌ AI Error: {e}")
            return self._fallback_response(user_input)
    
    def _fallback_response(self, user_input: str) -> Dict:
        """Fallback when Ollama is not available - use pattern matching"""
        text = user_input.lower().strip()
        language = self._detect_language(user_input)
        
        # Basic pattern matching fallback
        patterns = {
            ('open', 'launch', 'start', 'खोलो', 'खोल'): ('open_app', "Opening that for you!"),
            ('close', 'quit', 'exit', 'बंद'): ('close_app', "Closing that!"),
            ('screenshot', 'screen shot', 'स्क्रीनशॉट'): ('take_screenshot', "Taking a screenshot!"),
            ('volume up', 'louder', 'आवाज बढ़ा'): ('volume_up', "Turning up the volume!"),
            ('volume down', 'quieter', 'आवाज कम'): ('volume_down', "Lowering the volume!"),
            ('mute', 'म्यूट'): ('mute', "Muting!"),
            ('time', 'समय', 'टाइम'): ('time', "Let me check the time."),
            ('date', 'तारीख'): ('date', "Let me check the date."),
            ('search', 'google', 'खोजो'): ('web_search', "Searching for that!"),
        }
        
        for keywords, (action, response) in patterns.items():
            if any(kw in text for kw in keywords):
                # Extract app name for open/close
                params = {}
                if action in ('open_app', 'close_app'):
                    for app in ['notepad', 'chrome', 'calculator', 'explorer', 'paint', 'cmd']:
                        if app in text:
                            params['app_name'] = app
                            break
                    else:
                        # Try to get word after 'open'
                        words = text.split()
                        for i, w in enumerate(words):
                            if w in ('open', 'launch', 'start', 'close'):
                                if i + 1 < len(words):
                                    params['app_name'] = words[i + 1]
                                break
                
                # Extract search query
                if action == 'web_search':
                    for kw in ('search for', 'search', 'google'):
                        if kw in text:
                            query = text.split(kw, 1)[-1].strip()
                            if query:
                                params['query'] = query
                            break
                
                return {
                    'response': response,
                    'action': action,
                    'params': params,
                    'language': language
                }
        
        # Default response
        return {
            'response': "I'm here to help! Try saying 'open notepad' or 'what time is it'.",
            'action': None,
            'params': {},
            'language': language
        }


# Global AI brain instance
ai_brain = AIBrain()
