"""
FastAPI main server for VoiceAst
Handles WebSocket connections and REST API endpoints
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from pathlib import Path
from typing import List

# Import modules
import config
from database import db
from voice_recognition import voice_recognition
from text_to_speech import tts
from intent_recognizer import intent_recognizer
from device_controller import device_controller
from flexible_nlp import FlexibleIntentRecognizer
from ai_brain import ai_brain
from vision_recognition import vision

# Initialize flexible NLP (fallback)
flexible_nlp = FlexibleIntentRecognizer()

# Log AI status
if config.AI_ENABLED and ai_brain.is_available:
    print(f"✓ AI Brain enabled with model: {config.OLLAMA_MODEL}")
else:
    print("⚠ AI Brain disabled or unavailable - using pattern matching")

# Create FastAPI app
app = FastAPI(
    title="VoiceAst API",
    description="Voice Assistant with Full Device Control",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# ==================== Startup/Shutdown Events ====================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("=" * 60)
    print("VoiceAst - Voice Assistant Starting")
    print("=" * 60)
    
    # Connect to database
    await db.connect()
    
    # Check voice recognition
    if not voice_recognition.is_initialized:
        print("\n⚠ WARNING: Voice recognition not initialized!")
        print("  Run: python setup.py to download Vosk model\n")
    
    print(f"\n✓ Server starting on http://{config.HOST}:{config.PORT}")
    print("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await db.close()
    print("Server shutdown complete")

# ==================== REST API Endpoints ====================

# Frontend directory
frontend_dir = Path(__file__).parent.parent / "frontend"

@app.get("/")
async def serve_index():
    """Serve frontend index.html"""
    return FileResponse(frontend_dir / "index.html")

@app.get("/style.css")
async def serve_css():
    """Serve CSS file"""
    return FileResponse(frontend_dir / "style.css", media_type="text/css")

@app.get("/app.js")
async def serve_js():
    """Serve JavaScript file"""
    return FileResponse(frontend_dir / "app.js", media_type="application/javascript")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "voice_recognition": voice_recognition.is_initialized,
        "database": db.connected,
        "tts": tts.engine is not None
    }

@app.get("/api/history")
async def get_history(limit: int = 50):
    """Get command history"""
    history = await db.get_command_history(limit)
    return {"history": history}

@app.post("/api/history/clear")
async def clear_history():
    """Clear command history"""
    success = await db.clear_history()
    return {"success": success}

@app.get("/api/statistics")
async def get_statistics():
    """Get usage statistics"""
    stats = await db.get_statistics()
    return stats

@app.get("/api/preferences/{key}")
async def get_preference(key: str):
    """Get user preference"""
    value = await db.get_preference(key)
    return {"key": key, "value": value}

@app.post("/api/preferences/{key}")
async def set_preference(key: str, value: dict):
    """Set user preference"""
    success = await db.set_preference(key, value.get("value"))
    return {"success": success}

@app.get("/api/voices")
async def get_voices():
    """Get available TTS voices"""
    voices = tts.get_voices()
    return {"voices": voices}

@app.post("/api/tts/speak")
async def speak_text(data: dict):
    """Speak text via TTS"""
    text = data.get("text", "")
    if text:
        tts.speak(text)
        return {"success": True, "text": text}
    return {"success": False, "error": "No text provided"}

@app.post("/api/execute")
async def execute_command(data: dict):
    """Execute a text command"""
    command_text = data.get("command", "")
    
    if not command_text:
        return {"success": False, "error": "No command provided"}
    
    # Recognize intent
    intent_result = intent_recognizer.recognize(command_text)
    intent = intent_result["intent"]
    parameters = intent_result["parameters"]
    
    # Execute command
    result = await process_intent(intent, parameters)
    
    # Save to database
    await db.save_command(
        command=command_text,
        intent=intent,
        response=result.get("message", ""),
        success=result.get("success", False),
        metadata=result
    )
    
    return result

# ==================== WebSocket ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time voice interaction"""
    await manager.connect(websocket)
    
    # Create a recognizer for this session
    session_recognizer = voice_recognition.create_recognizer()
    print("✓ Session recognizer created")

    try:
        await manager.send_message({
            "type": "connected",
            "message": "Connected to VoiceAst"
        }, websocket)
        
        while True:
            # Handle both text and binary frames
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "ping":
                await manager.send_message({"type": "pong"}, websocket)
            
            elif message_type == "greeting":
                # User said "Hey Prime" or clicked Start - greet them fast!
                print("👋 Greeting activated!")
                
                # Short greetings for faster TTS
                greetings = [
                    "Hello! How can I help?",
                    "Hi! What can I do for you?",
                    "Hey! I'm listening.",
                    "Yes? How can I help?",
                ]
                import random
                greeting_text = random.choice(greetings)
                
                # Generate audio with male voice
                audio_base64 = tts.speak(greeting_text, voice_type="male")
                
                await manager.send_message({
                    "type": "result",
                    "success": True,
                    "message": greeting_text,
                    "audio": audio_base64,
                    "is_greeting": True
                }, websocket)
            
            elif message_type == "voice_command":
                # Process voice command using AI Brain
                command_text = message.get("text", "")
                language = message.get("language", "en")
                image_base64 = message.get("image")  # Camera frame if available
                
                if command_text:
                    # Send acknowledgment
                    await manager.send_message({
                        "type": "processing",
                        "command": command_text
                    }, websocket)
                    
                    # If image is provided, use vision model for the response
                    if image_base64 and vision.is_available:
                        print(f"👁️ Vision Q&A: '{command_text}'")
                        
                        # Create a prompt that combines the question with image analysis
                        vision_prompt = f"The user is asking: '{command_text}'. Look at the image and answer their question in 1-2 short sentences. Be conversational and natural."
                        
                        vision_result = await vision.analyze_image(image_base64, vision_prompt)
                        
                        if vision_result["success"]:
                            response_text = vision_result["description"]
                            print(f"👁️ Vision response: {response_text}")
                            
                            # Generate TTS audio
                            audio_base64 = await asyncio.to_thread(
                                tts.text_to_audio_base64, 
                                response_text, 
                                language
                            )
                            
                            # Send result
                            await manager.send_message({
                                "type": "result",
                                "success": True,
                                "message": response_text,
                                "audio": audio_base64,
                                "language": language,
                                "data": {"command": command_text, "vision": True}
                            }, websocket)
                            
                            # Save to database
                            await db.save_command(
                                command=command_text,
                                intent="vision_qa",
                                response=response_text,
                                success=True,
                                metadata={"vision": True}
                            )
                            continue  # Skip normal processing
                    
                    # FAST PATH: Quick pattern matching for common commands (skip AI for speed)
                    fast_patterns = {
                        'screenshot': ('take_screenshot', {}, "Screenshot captured!"),
                        'take a screenshot': ('take_screenshot', {}, "Screenshot captured!"),
                        'volume up': ('volume_up', {}, "Volume up!"),
                        'louder': ('volume_up', {}, "Louder!"),
                        'volume down': ('volume_down', {}, "Volume down!"),
                        'quieter': ('volume_down', {}, "Quieter!"),
                        'mute': ('mute', {}, "Muted!"),
                        'time': ('time', {}, ""),
                        'what time': ('time', {}, ""),
                        'date': ('date', {}, ""),
                        "what's the date": ('date', {}, ""),
                        'brightness up': ('brightness_up', {}, "Brighter!"),
                        'brightness down': ('brightness_down', {}, "Dimmer!"),
                    }
                    
                    command_lower = command_text.lower().strip()
                    fast_match = None
                    
                    # Check for fast pattern match
                    for pattern, (action, params, resp) in fast_patterns.items():
                        if pattern in command_lower:
                            fast_match = (action, params, resp)
                            break
                    
                    # Check for "open X" pattern
                    if not fast_match and command_lower.startswith('open '):
                        app_name = command_lower.replace('open ', '').strip()
                        fast_match = ('open_app', {'app_name': app_name}, f"Opening {app_name}!")
                    
                    # Check for "close X" pattern
                    if not fast_match and command_lower.startswith('close '):
                        app_name = command_lower.replace('close ', '').strip()
                        fast_match = ('close_app', {'app_name': app_name}, f"Closing {app_name}!")
                    
                    if fast_match:
                        # INSTANT execution - no AI needed!
                        action, params, response_text = fast_match
                        print(f"⚡ Fast path: {action}")
                        
                        action_result = await process_intent(action, params, language)
                        if not response_text:  # For time/date, use the action result message
                            response_text = action_result.get("message", "Done!")
                        
                        # Generate TTS with timeout and error handling
                        audio_base64 = ""
                        if response_text:
                            try:
                                # Timed TTS generation (max 3 seconds)
                                audio_base64 = await asyncio.wait_for(
                                    asyncio.to_thread(tts.text_to_audio_base64, response_text, language),
                                    timeout=3.0
                                )
                            except asyncio.TimeoutError:
                                print("⚠ TTS Generation timed out - skipping audio")
                            except Exception as e:
                                print(f"⚠ TTS Error: {e}")
                        
                        await manager.send_message({
                            "type": "result",
                            "success": action_result.get("success", True),
                            "message": response_text,
                            "audio": audio_base64,
                            "language": language,
                            "data": {"command": command_text, "action": action}
                        }, websocket)
                        
                        await db.save_command(command=command_text, intent=action, response=response_text, success=True)
                        continue  # Skip AI processing
                    
                    # Normal AI Brain processing (for complex/conversational commands)
                    if config.AI_ENABLED and ai_brain.is_available:
                        print(f"🤖 AI processing: '{command_text}'")
                        ai_result = await ai_brain.think(command_text)
                        
                        response_text = ai_result.get('response', '')
                        action = ai_result.get('action')
                        params = ai_result.get('params', {})
                        language = ai_result.get('language', 'en')
                        
                        print(f"🧠 AI: Action={action}, Params={params}")
                        
                        # Send intent
                        await manager.send_message({
                            "type": "intent",
                            "intent": action or "conversation",
                            "parameters": params,
                            "confidence": 0.95 if action else 0.8
                        }, websocket)
                        
                        # Execute action if available
                        action_result = {"success": True, "message": response_text}
                        if action:
                            action_result = await process_intent(action, params, language)
                            # If action has a specific message, append or use it
                            if action_result.get("message") and action != "time" and action != "date":
                                # Keep AI's natural response for most actions
                                pass
                            else:
                                # Use action result message for time/date
                                response_text = action_result.get("message", response_text)
                    else:
                        # Fallback to pattern matching
                        intent_result = flexible_nlp.recognize_flexible(command_text)
                        intent = intent_result["intent"]
                        parameters = intent_result["parameters"]
                        confidence = intent_result["confidence"]
                        
                        print(f"🧠 Pattern: '{command_text}' → {intent}")
                        
                        await manager.send_message({
                            "type": "intent",
                            "intent": intent,
                            "parameters": parameters,
                            "confidence": confidence
                        }, websocket)
                        
                        action_result = await process_intent(intent, parameters, language)
                        response_text = action_result.get("message", "")
                    
                    # Generate TTS audio (male voice, base64)
                    audio_base64 = ""
                    if response_text:
                        print(f"🗣️ TTS: '{response_text}'")
                        audio_base64 = await asyncio.to_thread(tts.text_to_audio_base64, response_text, language)
                        print(f"✓ Audio: {len(audio_base64)} chars")
                    
                    # Send result WITH audio
                    await manager.send_message({
                        "type": "result",
                        "success": action_result.get("success", True),
                        "message": response_text,
                        "audio": audio_base64,
                        "language": language,
                        "data": {"command": command_text}
                    }, websocket)
                    
                    # Save to database
                    await db.save_command(
                        command=command_text,
                        intent=action or "conversation",
                        response=response_text,
                        success=action_result.get("success", True),
                        metadata={}
                    )
                    
                    # Signal that we are ready for the next command
                    await manager.send_message({
                        "type": "ready",
                        "message": "Ready for next command"
                    }, websocket)
            
            elif message_type == "audio_stream":
                # Process streaming audio with Vosk (Stateful)
                audio_data = message.get("data") # Expecting list of bytes/ints
                
                if audio_data and session_recognizer:
                    # Convert list/b64 to bytes
                    # If it's a list from JS:
                    if isinstance(audio_data, list):
                        audio_bytes = bytes(audio_data)
                    # If base64 string
                    elif isinstance(audio_data, str):
                        import base64
                        audio_bytes = base64.b64decode(audio_data)
                    else:
                        audio_bytes = bytes(audio_data)
                    
                    # Recognize with SESSION recognizer
                    result = voice_recognition.process_chunk(session_recognizer, audio_bytes)
                    
                    if result:
                        text = result.get("text", "")
                        is_final = result.get("is_final", False)
                        
                        if text:
                            print(f"🎤 Vosk recognized ({'FINAL' if is_final else 'partial'}): '{text}'")
                            
                            # Send transcription update
                            await manager.send_message({
                                "type": "transcription",
                                "text": text,
                                "isFinal": is_final
                            }, websocket)
                            
                            # If final, execute command automatically
                            if is_final:
                                # Re-inject as a "voice_command" to reuse logic
                                # (We can just do a recursive call or copy code, but for cleaner flow let's just trigger it)
                                # Actually, just calling the logic above is cleaner
                                
                                # Use flexible NLP
                                intent_result = flexible_nlp.recognize_flexible(text)
                                intent = intent_result["intent"]
                                parameters = intent_result["parameters"]
                                confidence = intent_result["confidence"]
                                
                                print(f"🧠 Flexible NLP: '{text}' → {intent} (conf: {confidence})")
                                
                                # Send intent
                                await manager.send_message({
                                    "type": "intent",
                                    "intent": intent,
                                    "parameters": parameters,
                                    "confidence": confidence
                                }, websocket)
                                
                                # Execute
                                result = await process_intent(intent, parameters, "en") # Default en for now
                                
                                # TTS
                                response_text = result.get("message", "")
                                audio_base64 = ""
                                if response_text:
                                    print(f"🗣️ Generating male voice audio...")
                                    audio_base64 = await asyncio.to_thread(tts.text_to_audio_base64, response_text, "en")
                                
                                await manager.send_message({
                                    "type": "result",
                                    "success": result.get("success", False),
                                    "message": response_text,
                                    "audio": audio_base64,
                                    "language": "en",
                                    "data": result
                                }, websocket)
                                
                                # Save
                                await db.save_command(
                                    command=text,
                                    intent=intent,
                                    response=response_text,
                                    success=result.get("success", False),
                                    metadata=result
                                )
                                
                                # Signal that we are ready for the next command
                                await manager.send_message({
                                    "type": "ready",
                                    "message": "Ready for next command"
                                }, websocket)
            
            elif message_type == "voice_audio_file":
                # NEW: Handle complete WAV file from frontend
                import base64
                audio_b64 = message.get("audio")
                
                if audio_b64:
                    try:
                        # Decode base64 WAV
                        audio_bytes = base64.b64decode(audio_b64)
                        print(f"📥 Received audio file: {len(audio_bytes)} bytes")
                        
                        # Strip WAV header (44 bytes) to get raw PCM
                        pcm_data = audio_bytes[44:] if len(audio_bytes) > 44 else audio_bytes
                        
                        # Recognize with Vosk (Async to avoid blocking)
                        recognition_result = await asyncio.to_thread(voice_recognition.recognize_from_audio, pcm_data)
                        text = recognition_result.get("text", "").strip()
                        
                        print(f"🎤 Vosk recognized: '{text}'")
                        
                        if text:
                            # Send transcription
                            await manager.send_message({
                                "type": "transcription",
                                "text": text,
                                "isFinal": True
                            }, websocket)
                            
                            # Use AI Brain for understanding
                            if config.AI_ENABLED and ai_brain.is_available:
                                print(f"🤖 AI processing: '{text}'")
                                ai_result = await ai_brain.think(text)
                                
                                response_text = ai_result.get('response', '')
                                action = ai_result.get('action')
                                params = ai_result.get('params', {})
                                language = ai_result.get('language', 'en')
                                
                                print(f"🧠 AI: Action={action}, Params={params}")
                                
                                # Send intent
                                await manager.send_message({
                                    "type": "intent",
                                    "intent": action or "conversation",
                                    "parameters": params,
                                    "confidence": 0.95 if action else 0.8
                                }, websocket)
                                
                                # Execute action if available
                                action_result = {"success": True, "message": response_text}
                                if action:
                                    action_result = await process_intent(action, params, language)
                                    if action in ("time", "date"):
                                        response_text = action_result.get("message", response_text)
                            else:
                                # Fallback to pattern matching
                                intent_result = flexible_nlp.recognize_flexible(text)
                                action = intent_result["intent"]
                                params = intent_result["parameters"]
                                
                                await manager.send_message({
                                    "type": "intent",
                                    "intent": action,
                                    "parameters": params,
                                    "confidence": intent_result["confidence"]
                                }, websocket)
                                
                                action_result = await process_intent(action, params, "en")
                                response_text = action_result.get("message", "")
                                language = "en"
                            
                            # Generate TTS audio
                            audio_base64 = ""
                            if response_text:
                                print(f"🗣️ TTS: '{response_text}'")
                                audio_base64 = await asyncio.to_thread(tts.text_to_audio_base64, response_text, language)
                                print(f"✓ Audio: {len(audio_base64)} chars")
                            
                            # Send result WITH audio
                            await manager.send_message({
                                "type": "result",
                                "success": action_result.get("success", True),
                                "message": response_text,
                                "audio": audio_base64,
                                "language": language,
                                "data": {"command": text}
                            }, websocket)
                            
                            # Save to database
                            await db.save_command(
                                command=text,
                                intent=action or "conversation",
                                response=response_text,
                                success=action_result.get("success", True),
                                metadata={}
                            )
                            
                            # Signal that we are ready for the next command
                            await manager.send_message({
                                "type": "ready",
                                "message": "Ready for next command"
                            }, websocket)
                        else:
                            # No speech detected
                            await manager.send_message({
                                "type": "result",
                                "success": False,
                                "message": "I didn't catch that. Please try again.",
                                "audio": "",
                                "data": {}
                            }, websocket)
                            
                    except Exception as e:
                        print(f"❌ Error processing audio file: {e}")
                        await manager.send_message({
                            "type": "result",
                            "success": False,
                            "message": f"Error processing audio: {str(e)}",
                            "audio": "",
                            "data": {}
                        }, websocket)
            
            elif message_type == "audio_data":
                # Original audio_data handler (legacy)
                audio_bytes = message.get("audio")
                
                if audio_bytes:
                    # Recognize speech
                    recognition_result = voice_recognition.recognize_from_audio(audio_bytes)
                    
                    if recognition_result.get("text"):
                        await manager.send_message({
                            "type": "transcription",
                            "text": recognition_result["text"],
                            "confidence": recognition_result.get("confidence", 0)
                        }, websocket)
            
            elif message_type == "analyze_frame":
                # Vision recognition - analyze camera frame
                image_base64 = message.get("image", "")
                
                if image_base64:
                    print("📷 Analyzing camera frame...")
                    
                    # Analyze with LLaVA vision model
                    result = await vision.analyze_image(image_base64)
                    
                    if result["success"]:
                        description = result["description"]
                        print(f"👁️ Vision: {description}")
                        
                        # Generate TTS for the description
                        audio_base64 = await asyncio.to_thread(
                            tts.text_to_audio_base64, 
                            description, 
                            "en"
                        )
                        
                        await manager.send_message({
                            "type": "vision_result",
                            "success": True,
                            "description": description,
                            "audio": audio_base64
                        }, websocket)
                    else:
                        await manager.send_message({
                            "type": "vision_result",
                            "success": False,
                            "description": result.get("error", "Vision analysis failed"),
                            "audio": ""
                        }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# ==================== Command Processing ====================

# Translation dictionaries
HINDI_RESPONSES = {
    "greeting": "नमस्ते! मैं प्राइम हूं, आपका वॉइस असिस्टेंट। मैं आपकी कैसे मदद कर सकता हूं?",
    "help": "मैं आपके ऐप्लिकेशन को नियंत्रित करने, फ़ाइलें प्रबंधित करने, सिस्टम सेटिंग्स समायोजित करने और प्रश्नों के उत्तर देने में मदद कर सकता हूं।",
}

async def process_intent(intent: str, parameters: dict, language: str = "en") -> dict:
    """Process intent and execute corresponding action with language support"""
    
    try:
        # Application control
        if intent == "open_app":
            app_name = parameters.get("app_name", "")
            result = device_controller.open_application(app_name)
            if language == "hi" and result.get("success"):
                result["message"] = f"{app_name} खोला जा रहा है"
            return result
        
        elif intent == "close_app":
            app_name = parameters.get("app_name", "")
            result = device_controller.close_application(app_name)
            if language == "hi" and result.get("success"):
                result["message"] = f"{app_name} बंद किया जा रहा है"
            return result
        
        # File operations
        elif intent == "create_file":
            filename = parameters.get("filename", "")
            result = device_controller.create_file(filename)
            if language == "hi" and result.get("success"):
                result["message"] = f"फ़ाइल {filename} बनाई गई"
            return result
        
        elif intent == "delete_file":
            filename = parameters.get("filename", "")
            result = device_controller.delete_file(filename)
            if language == "hi" and result.get("success"):
                result["message"] = f"फ़ाइल {filename} हटाई गई"
            return result
        
        elif intent == "list_files":
            directory = parameters.get("directory", "documents")
            return device_controller.list_files(directory)
        
        elif intent == "search_files":
            query = parameters.get("query", "")
            directory = parameters.get("directory", "documents")
            return device_controller.search_files(query, directory)
        
        # System control
        elif intent == "volume_up":
            result = device_controller.adjust_volume("up")
            if language == "hi" and result.get("success"):
                result["message"] = "वॉल्यूम बढ़ाया जा रहा है"
            return result
        
        elif intent == "volume_down":
            result = device_controller.adjust_volume("down")
            if language == "hi" and result.get("success"):
                result["message"] = "वॉल्यूम घटाया जा रहा है"
            return result
        
        elif intent == "mute":
            result = device_controller.adjust_volume("mute")
            if language == "hi" and result.get("success"):
                result["message"] = "म्यूट किया जा रहा है"
            return result
        
        elif intent == "brightness_up":
            result = device_controller.adjust_brightness("up")
            if language == "hi" and result.get("success"):
                result["message"] = "चमक बढ़ाई जा रही है"
            return result
        
        elif intent == "brightness_down":
            result = device_controller.adjust_brightness("down")
            if language == "hi" and result.get("success"):
                result["message"] = "चमक घटाई जा रही है"
            return result
        
        elif intent in ("screenshot", "take_screenshot"):
            result = device_controller.take_screenshot()
            if language == "hi" and result.get("success"):
                result["message"] = "स्क्रीनशॉट लिया गया"
            return result
        
        elif intent == "shutdown":
            return device_controller.shutdown_system()
        
        elif intent == "restart":
            return device_controller.restart_system()
        
        # Information
        elif intent == "time":
            from datetime import datetime
            current_time = datetime.now().strftime("%I:%M %p")
            if language == "hi":
                return {
                    "success": True,
                    "message": f"अभी समय {current_time} बजे है",
                    "time": current_time
                }
            return {
                "success": True,
                "message": f"The current time is {current_time}",
                "time": current_time
            }
        
        elif intent == "date":
            from datetime import datetime
            current_date = datetime.now().strftime("%B %d, %Y")
            if language == "hi":
                return {
                    "success": True,
                    "message": f"आज की तारीख {current_date} है",
                    "date": current_date
                }
            return {
                "success": True,
                "message": f"Today is {current_date}",
                "date": current_date
            }
        
        elif intent == "system_info":
            return device_controller.get_system_info()
        
        # Web & Automation
        elif intent == "web_search":
            query = parameters.get("query", "")
            result = device_controller.web_search(query)
            if language == "hi" and result.get("success"):
                result["message"] = f"{query} खोजा जा रहा है"
            return result
        
        elif intent == "type_text":
            text = parameters.get("text", "")
            return device_controller.type_text(text)
        
        elif intent == "press_key":
            key = parameters.get("key", "")
            return device_controller.press_key(key)
        
        # Camera / Vision
        elif intent in ("open_camera", "camera"):
            return {
                "success": True,
                "message": "Opening camera. I'll describe what I see.",
                "action": "open_camera"
            }
        
        elif intent == "close_camera":
            return {
                "success": True,
                "message": "Camera closed.",
                "action": "close_camera"
            }
        
        # Help & Greeting
        elif intent == "greeting":
            if language == "hi":
                return {
                    "success": True,
                    "message": HINDI_RESPONSES["greeting"],
                    "intent": "greeting"
                }
            return {
                "success": True,
                "message": "Hello! I'm Prime, your voice assistant. How can I help you today?",
                "intent": "greeting"
            }
        
        elif intent == "help":
            if language == "hi":
                return {
                    "success": True,
                    "message": HINDI_RESPONSES["help"]
                }
            return {
                "success": True,
                "message": "I can help you control applications, manage files, adjust system settings, and answer questions. Try commands like 'open notepad', 'what time is it', or 'take screenshot'."
            }
        
        # Unknown
        else:
            response = intent_recognizer.format_response(intent, parameters)
            return {
                "success": False,
                "message": response,
                "intent": intent
            }
    
    except Exception as e:
        error_msg = f"Error executing command: {str(e)}" if language == "en" else f"कमांड चलाने में त्रुटि: {str(e)}"
        return {
            "success": False,
            "message": error_msg,
            "error": str(e)
        }

# ==================== Static Files ====================
# Note: Static file routes are defined earlier in the file (lines 106-114)

# ==================== Main ====================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,  # Disabled to prevent WebSocket disconnections
        log_level="info"
    )
