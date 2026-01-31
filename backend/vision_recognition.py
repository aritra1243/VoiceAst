"""
Vision Recognition Module
Uses Ollama's LLaVA model to analyze images from webcam
"""

import base64
import asyncio
from typing import Optional, Dict

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠ Ollama not installed. Vision features disabled.")


class VisionRecognition:
    """Vision recognition using Ollama LLaVA model"""
    
    def __init__(self, model_name: str = "llava"):
        self.model_name = model_name
        self.is_available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if LLaVA model is available"""
        if not OLLAMA_AVAILABLE:
            print("✗ Ollama library not available")
            return
        
        try:
            # Check if llava model exists
            models = ollama.list()
            model_names = [m['name'].split(':')[0] for m in models.get('models', [])]
            
            if self.model_name in model_names or f"{self.model_name}:latest" in [m['name'] for m in models.get('models', [])]:
                self.is_available = True
                print(f"✓ Vision model '{self.model_name}' available")
            else:
                print(f"⚠ Vision model '{self.model_name}' not found. Run: ollama pull llava")
                print(f"  Available models: {model_names}")
        except Exception as e:
            print(f"✗ Error checking vision model: {e}")
    
    async def analyze_image(self, image_base64: str, prompt: str = None) -> Dict:
        """
        Analyze an image and describe its contents
        
        Args:
            image_base64: Base64 encoded image (JPEG or PNG)
            prompt: Optional custom prompt for analysis
        
        Returns:
            dict with 'success', 'description', and 'error' fields
        """
        if not self.is_available:
            return {
                "success": False,
                "description": "",
                "error": "Vision model not available. Run: ollama pull llava"
            }
        
        if not prompt:
            prompt = "Describe what you see in this image in 1-2 short sentences. Be concise and natural, as if speaking to someone."
        
        try:
            # Run in thread to avoid blocking
            response = await asyncio.to_thread(
                ollama.chat,
                model=self.model_name,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_base64]
                }],
                options={
                    'temperature': 0.7,
                    'num_predict': 100,  # Keep responses short
                }
            )
            
            description = response['message']['content'].strip()
            
            return {
                "success": True,
                "description": description,
                "error": None
            }
            
        except Exception as e:
            print(f"Vision analysis error: {e}")
            return {
                "success": False,
                "description": "",
                "error": str(e)
            }
    
    async def identify_objects(self, image_base64: str) -> Dict:
        """Identify specific objects in the image"""
        prompt = "List the main objects you can see in this image. Be brief."
        return await self.analyze_image(image_base64, prompt)
    
    async def describe_scene(self, image_base64: str) -> Dict:
        """Describe the overall scene"""
        prompt = "Describe the scene in this image in one sentence."
        return await self.analyze_image(image_base64, prompt)
    
    async def read_text(self, image_base64: str) -> Dict:
        """Try to read any text visible in the image"""
        prompt = "Read and transcribe any text visible in this image. If no text is visible, say 'No text detected'."
        return await self.analyze_image(image_base64, prompt)


# Global instance
vision = VisionRecognition()
