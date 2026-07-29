"""
FastAPI main server for VoiceAst
Handles WebSocket connections and REST API endpoints
"""
import sys
import os

# Prevent Windows CP1252 terminal UnicodeEncodeError on print statements
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

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
from image_store import image_store
from voice_recognition import voice_recognition
from text_to_speech import tts
from intent_recognizer import intent_recognizer
from device_controller import device_controller
from flexible_nlp import FlexibleIntentRecognizer
from ai_brain import ai_brain
from vision_recognition import vision
from system_monitor import SystemMonitor
from speaker_id import speaker_recognizer

# Initialize WebSocket Manager (Moved up for dependencies)
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"Client disconnected. Active: {len(self.active_connections)}")

    async def send_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"Send error: {e}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass

manager = ConnectionManager()

# Initialize flexible NLP
flexible_nlp = FlexibleIntentRecognizer()

# Initialize System Monitor
sys_monitor = SystemMonitor(manager)
try:
    sys_monitor.start()
except Exception as e:
    print(f"Failed to start System Monitor: {e}")

# Log AI status
if config.AI_ENABLED and ai_brain.is_available:
    print(f"✓ AI Brain enabled (custom local model)")
else:
    print("⚠ AI Brain disabled or unavailable - using pattern matching")

# ==================== Owner Recognition Helpers ====================

# The name stored in face_memory when the owner trained their own face.
# Change this to whatever name you used when you said "this is [name]".
OWNER_FACE_NAME = os.getenv("OWNER_FACE_NAME", "Aritra")

def _get_owner_title_from_voice(pcm_data: bytes) -> str:
    """
    Run speaker verification against the enrolled owner voice profile.
    Returns 'Sir' if the voice matches the owner, '' otherwise.
    Called from voice_audio_file and audio_stream paths.
    """
    if not speaker_recognizer.is_available:
        return ""
    try:
        result = speaker_recognizer.verify_voice(pcm_data)
        if result.get("match"):
            print(f"🎤 Voice: Owner recognised (similarity={result['similarity']:.2f})")
            return "Sir"
        else:
            print(f"🎤 Voice: Guest (similarity={result['similarity']:.2f})")
            return ""
    except Exception as e:
        print(f"[WRN] Speaker verify error: {e}")
        return ""

def _get_owner_title_from_face(image_base64: str) -> str:
    """
    Run face recognition against the trained face model.
    Returns 'Sir' if the detected face matches OWNER_FACE_NAME, '' otherwise.
    Called from voice_command path (camera frame available).
    """
    if not image_base64:
        return ""
    try:
        from face_memory import face_memory
        if not face_memory.is_trained:
            return ""
        recognition = face_memory.recognize_face(image_base64)
        # recognize_face returns "Name (XX% confidence)" or "Unknown Person"
        if OWNER_FACE_NAME.lower() in recognition.lower():
            print(f"📸 Face: Owner recognised → {recognition}")
            return "Sir"
        elif "unknown" not in recognition.lower() and "no face" not in recognition.lower():
            print(f"📸 Face: Guest recognised → {recognition}")
            return ""
    except Exception as e:
        print(f"[WRN] Face recognition error: {e}")
    return ""

def _apply_owner_title(response_text: str, title: str) -> str:
    """
    Append ', Sir.' to response if owner is detected and it isn't already there.
    Never appends to very short responses (< 5 chars).
    """
    if not title or len(response_text) < 5:
        return response_text
    if "sir" in response_text.lower():
        return response_text  # already has it
    return f"{response_text}, Sir."

import os as _os  # for OWNER_FACE_NAME env read above

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
    
    # Connect to MongoDB
    await db.connect()
    
    # Connect to PostgreSQL image store
    await image_store.connect()
    
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
    await image_store.close()
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
    pg_stats = await image_store.get_stats()
    return {
        "status": "healthy",
        "voice_recognition": voice_recognition.is_initialized,
        "database_mongo": db.connected,
        "database_postgres": image_store.connected,
        "image_store_stats": pg_stats,
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

# ---- Image Store endpoints (PostgreSQL) ----

@app.get("/api/images")
async def list_images(limit: int = 20):
    """List recently saved webcam photos"""
    images = await image_store.list_images(limit)
    return {"images": images, "count": len(images)}

@app.get("/api/images/{label}")
async def get_image_by_label(label: str):
    """Get a saved webcam photo by label"""
    result = await image_store.get_image(label)
    if result:
        return {"found": True, "image": result}
    return JSONResponse({"found": False, "error": f"No image found for label '{label}'"}, status_code=404)

@app.get("/api/screenshots")
async def list_screenshots(limit: int = 20):
    """List recently saved screenshots"""
    shots = await image_store.list_screenshots(limit)
    return {"screenshots": shots, "count": len(shots)}

@app.get("/api/screenshots/latest")
async def get_latest_screenshot():
    """Get the most recent screenshot"""
    result = await image_store.get_screenshot()
    if result:
        return {"found": True, "screenshot": result}
    return JSONResponse({"found": False, "error": "No screenshots saved yet"}, status_code=404)

@app.get("/api/weather")
async def get_weather():
    """Get weather data server-side using requests (more stable)"""
    import requests
    import asyncio
    
    def fetch_weather_sync():
        city = "Delhi"
        # 1. Get location (Multi-provider fallback)
        location_providers = [
            ("http://ip-api.com/json", "city"),  # Very reliable
            ("https://ipapi.co/json/", "city"),
            ("https://ipinfo.io/json", "city"),
        ]
        
        for url, key in location_providers:
            try:
                print(f"🌍 Locating via {url}...")
                loc_res = requests.get(url, timeout=3.0)
                if loc_res.status_code == 200:
                    data = loc_res.json()
                    fetched_city = data.get(key)
                    if fetched_city:
                        city = fetched_city
                        print(f"📍 Location found: {city}")
                        break
            except Exception as e:
                print(f"Location provider {url} failed: {e}")
                continue
            
        # 2. Get weather
        try:
            weather_res = requests.get(f"https://wttr.in/{city}?format=j1", timeout=10.0)
            if weather_res.status_code == 200:
                data = weather_res.json()
                # Inject city name if missing
                if "nearest_area" in data and data["nearest_area"]:
                     if not data["nearest_area"][0]["areaName"][0]["value"]:
                         data["nearest_area"][0]["areaName"][0]["value"] = city
                return data
            else:
                raise Exception(f"Weather service returned {weather_res.status_code}")
        except Exception as e:
            print(f"Weather fetch error: {e}")
            raise e

    try:
        data = await asyncio.to_thread(fetch_weather_sync)
        return data
    except Exception as e:
        print(f"Weather API Error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

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
                # Send greeting
                import random
                greetings = [
                    "Hello Sir! How can I help?",
                    "Yes Sir? How can I help?",
                    "I'm listening, Sir.",
                    "At your service, Sir."
                ]
                text = random.choice(greetings)
                
                # Generate TTS
                audio_base64 = await asyncio.to_thread(tts.text_to_audio_base64, text, "en")
                
                await manager.send_message({
                    "type": "result", 
                    "success": True, 
                    "message": text, 
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
                    
                    # If image is provided AND command is a visual question, use vision model
                    VISUAL_KEYWORDS = (
                        "what", "who", "describe", "see", "show", "look",
                        "read", "tell me", "identify", "recognize", "what's",
                        "what is", "how many", "is there", "can you see",
                        "analyze", "examine", "inspect", "detect"
                    )
                    is_visual_question = (
                        image_base64
                        and vision.is_available
                        and any(kw in command_text.lower() for kw in VISUAL_KEYWORDS)
                        # Don't hijack clear action commands
                        and not any(kw in command_text.lower() for kw in (
                            "open ", "close ", "volume", "screenshot", "brightness",
                            "search for", "remember that", "play ", "mute",
                            "take a photo", "save this"
                        ))
                    )

                    if is_visual_question:
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
                    
                    # 2. Check for "Memory" triggers (Teaching mode)
                    # Patterns: "remember that...", "note that...", "memorize that..."
                    import re
                    command_lower = command_text.lower()
                    memory_match = re.search(r'\b(remember|note|memorize)\s+(that\s+)?(.+)', command_lower)
                    if memory_match and not any(kw in command_lower for kw in ['open', 'close', 'search', 'play']):
                        fact = memory_match.group(3).strip()
                        if len(fact) > 3:
                            # Store memory
                            await db.add_memory(fact)
                            
                            response_text = "Ok Sir, I'll remember that." if language == "en" else "ठीक है सर, मैं याद रखूंगा।"
                            
                            # Generate TTS
                            audio_base64 = ""
                            try:
                                audio_base64 = await asyncio.wait_for(
                                    asyncio.to_thread(tts.text_to_audio_base64, response_text, language),
                                    timeout=5.0
                                )
                            except:
                                pass
                            
                            await manager.send_message({
                                "type": "result",
                                "success": True,
                                "message": response_text,
                                "audio": audio_base64,
                                "language": language,
                                "data": {"command": command_text, "intent": "memory_store"}
                            }, websocket)
                            
                            await db.save_command(command=command_text, intent="memory_store", response=response_text, success=True)
                            continue # Skip further processing
                    
                    # 3. Visual Memory Triggers (Face Recognition)
                    # "This is [Name]" -> Train face
                    # Guard: only trigger if image is present and name looks like a real name
                    face_train_match = re.search(r'this is\s+([a-zA-Z][a-zA-Z\s]{1,30})$', command_lower)
                    GENERIC_WORDS = {"this", "that", "it", "broken", "wrong", "working", "done", "fine", "okay", "good", "bad", "nice", "cool"}
                    if face_train_match and image_base64:
                        candidate_name = face_train_match.group(1).strip()
                        # Skip if it looks like a generic word, not a person name
                        if candidate_name.lower() not in GENERIC_WORDS and len(candidate_name) >= 2:
                            from face_memory import face_memory
                            name = candidate_name
                            print(f"📸 Learning face: {name}")
                            
                            success = face_memory.train_face(image_base64, name)
                            msg = f"I've learned that this is {name}." if success else "I couldn't see a face clearly. Please try again."
                            
                            # TTS
                            t_audio = await asyncio.to_thread(tts.text_to_audio_base64, msg, language)
                            
                            await manager.send_message({
                                "type": "result", 
                                "success": success, 
                                "message": msg,
                                "audio": t_audio,
                                "data": {"intent": "face_train", "name": name}
                            }, websocket)
                            continue

                    # "Who is this" -> Recognize
                    if "who is this" in command_lower or "who is that" in command_lower:
                        if image_base64:
                            from face_memory import face_memory
                            print("📸 Recognizing face...")
                            
                            who = face_memory.recognize_face(image_base64)
                            msg = f"That looks like {who}."
                            
                            t_audio = await asyncio.to_thread(tts.text_to_audio_base64, msg, language)
                            
                            await manager.send_message({
                                "type": "result", 
                                "success": True, 
                                "message": msg,
                                "audio": t_audio, # Fixed variable name
                                "data": {"intent": "face_rec"}
                            }, websocket)
                            continue
                        else:
                            msg = "I can't see anyone. Please enable the camera."
                            t_audio = await asyncio.to_thread(tts.text_to_audio_base64, msg, language)
                            await manager.send_message({
                                "type": "result", "success": False, "message": msg, "audio": t_audio
                            }, websocket)
                            continue

                    # 4. Universal Messaging (Send X to Y on Z)
                    # Pattern: "send message to [Person] on [App] saying [Message]"
                    msg_match = re.search(r'send\s+(?:message|sms|text)\s+to\s+(.+?)\s+on\s+(.+?)\s+(?:saying|that)\s+(.+)', command_lower)
                    if msg_match:
                        person = msg_match.group(1).strip()
                        app_name = msg_match.group(2).strip()
                        msg_body = msg_match.group(3).strip()
                        
                        resp_txt = f"Sending message to {person} on {app_name}."
                        
                        # Acknowledge first (because the action takes time)
                        t_audio = await asyncio.to_thread(tts.text_to_audio_base64, resp_txt, language)
                        await manager.send_message({
                            "type": "result", "success": True, "message": resp_txt, "audio": t_audio,
                            "data": {"intent": "messaging"}
                        }, websocket)
                        
                        # Execute in background (don't block server)
                        asyncio.create_task(asyncio.to_thread(device_controller.send_message, app_name, person, msg_body))
                        
                        await db.save_command(command=command_text, intent="send_message", response=resp_txt, success=True)
                        continue

                    # FAST PATH: Quick pattern matching for common commands (skip AI for speed)
                    fast_patterns = {
                        'screenshot': ('take_screenshot', {}, "Screenshot captured!"),
                        'take a screenshot': ('take_screenshot', {}, "Screenshot captured!"),
                        # Image memory fast paths
                        'take a photo and remember': ('take_photo_remember', {}, ""),
                        'click a photo and remember': ('take_photo_remember', {}, ""),
                        'capture and remember': ('take_photo_remember', {}, ""),
                        'save this screenshot': ('take_screenshot_remember', {}, ""),
                        'screenshot and remember': ('take_screenshot_remember', {}, ""),
                        'remember this photo': ('take_photo_remember', {}, ""),
                        'show me the photo of': ('recall_image', {}, ""),
                        'recall image': ('recall_image', {}, ""),
                        # Existing patterns
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
                        
                        # For image memory intents, extract label from text and inject image
                        if action in ("take_photo_remember", "take_screenshot_remember"):
                            import re as _re
                            from datetime import datetime as _dt
                            m = _re.search(r"(?:as|called|label|named?\s+it)\s+(.+)$", command_lower)
                            params = dict(params)
                            params["label"] = m.group(1).strip() if m else _dt.now().strftime("photo_%Y%m%d_%H%M%S")
                            if action == "take_photo_remember" and image_base64:
                                params["image_base64"] = image_base64
                        elif action == "recall_image":
                            import re as _re
                            m = _re.search(r"(?:photo|image|picture|screenshot)\s+(?:of|named?|called)\s+(.+)$", command_lower)
                            params = dict(params)
                            if m:
                                params["label"] = m.group(1).strip()
                        
                        action_result = await process_intent(action, params, language)
                        if not response_text:  # For time/date, use the action result message
                            response_text = action_result.get("message", "Done!")
                        
                        # Generate TTS with timeout and error handling
                        audio_base64 = ""
                        if response_text:
                            try:
                                # Timed TTS generation (max 8 seconds to allow process spawn overhead)
                                audio_base64 = await asyncio.wait_for(
                                    asyncio.to_thread(tts.text_to_audio_base64, response_text, language),
                                    timeout=8.0
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
                    # --- Owner recognition (face, since we have camera frame here) ---
                    owner_title = _get_owner_title_from_face(image_base64)

                    if config.AI_ENABLED and ai_brain.is_available:
                        print(f"🤖 AI processing: '{command_text}'")
                        # Fetch relevant memories to provide context (RAG-lite)
                        memories = await db.search_memories(limit=10)
                        # Inject owner context
                        context = list(memories)
                        if owner_title == "Sir":
                            context.insert(0, "User is the Owner (Sir).")
                        else:
                            context.insert(0, "User is a Guest.")

                        result = await ai_brain.think(command_text, context_memories=context)

                        response_text = result.get("response", "")
                        action = result.get("action")
                        params = result.get("params", {})
                        language = result.get("language", language)

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

                    # Apply Sir/Guest title to response
                    response_text = _apply_owner_title(response_text, owner_title)

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
                                
                                # --- Owner recognition via VOICE (speaker ID) ---
                                # Also check face if camera is available, use whichever confirms owner
                                owner_title = _get_owner_title_from_voice(pcm_data)
                                if not owner_title and image_base64:
                                    owner_title = _get_owner_title_from_face(image_base64)

                                print(f"🤖 AI processing: '{text}'")

                                # Inject context about speaker identity
                                context_memories = []
                                if owner_title == "Sir":
                                    context_memories.append("User is the Owner (Sir).")
                                else:
                                    context_memories.append("User is a Guest.")

                                ai_result = await ai_brain.think(text, context_memories=context_memories)

                                response_text = ai_result.get('response', '')

                                # Apply Sir title consistently (not randomly)
                                response_text = _apply_owner_title(response_text, owner_title)

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
                                
                                # Special Handling for Enrollment (since we have the audio here)
                                if action == "enroll_voice" or (text and "learn my voice" in text.lower()):
                                    print("🎤 Enrollment triggered...")
                                    enroll_result = speaker_recognizer.enroll_voice(pcm_data)
                                    if enroll_result["success"]:
                                        response_text = "Voice learned successfully, Sir. i will recognize you from now on."
                                        action_result = {"success": True, "message": response_text}
                                    else:
                                        response_text = f"Failed to learn voice: {enroll_result.get('error')}"
                                        
                                elif action:
                                    # Inject webcam frame for photo memory actions
                                    if action == "take_photo_remember" and image_base64:
                                        params = dict(params)
                                        params["image_base64"] = image_base64
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
                # Vision recognition - analyze camera frame using custom EfficientNet-B0 + LSTM model
                image_base64 = message.get("image", "")

                if image_base64:
                    print("📷 Analyzing camera frame...")

                    # 1. Run face recognition to identify who is on camera
                    face_title = _get_owner_title_from_face(image_base64)
                    try:
                        from face_memory import face_memory as _fm
                        recognized_name = _fm.recognize_face(image_base64) if _fm.is_trained else "Unknown"
                    except Exception:
                        recognized_name = "Unknown"
                    is_owner_on_camera = face_title == "Sir"

                    # 2. Scene description via vision model (if available)
                    result = await vision.analyze_image(image_base64)

                    if result["success"]:
                        description = result["description"]
                        # If owner is on camera, add personalised prefix
                        if is_owner_on_camera:
                            description = f"Hello, Sir. {description}" if description else "Hello, Sir."
                        print(f"👁️ Vision: {description}")

                        audio_base64 = await asyncio.to_thread(
                            tts.text_to_audio_base64,
                            description,
                            "en"
                        )

                        await manager.send_message({
                            "type": "vision_result",
                            "success": True,
                            "description": description,
                            "audio": audio_base64,
                            "is_owner": is_owner_on_camera,
                            "recognized_name": recognized_name,
                        }, websocket)
                    else:
                        # Vision model not available — still send face recognition result
                        await manager.send_message({
                            "type": "vision_result",
                            "success": False,
                            "description": result.get("error", "Vision analysis failed"),
                            "audio": "",
                            "is_owner": is_owner_on_camera,
                            "recognized_name": recognized_name,
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
            
        elif intent == "switch_tab":
            direction = parameters.get("direction", "next")
            result = device_controller.switch_tabs(direction)
            if language == "hi" and result.get("success"):
                result["message"] = "टैब बदला जा रहा है"
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
        
        # ---- Image Memory (PostgreSQL) ----------------------------------------
        elif intent == "take_photo_remember":
            """
            Capture a webcam photo and remember it.
            Expects 'label' in parameters and 'image_base64' in the WS message
            (injected below before calling process_intent).
            """
            label = parameters.get("label", "untitled")
            image_b64 = parameters.get("image_base64", "")
            if not image_b64:
                return {
                    "success": False,
                    "message": "I can't see anything. Please enable the camera so I can capture a photo."
                }
            # Generate AI description (if vision model is available)
            description = ""
            if vision.is_available:
                vision_result = await vision.analyze_image(image_b64)
                description = vision_result.get("description", "")
            # Save to PostgreSQL
            row_id = await image_store.save_image(
                label=label,
                image_base64=image_b64,
                description=description,
                source="webcam",
            )
            if row_id:
                msg = f"Got it! I've remembered this photo as '{label}'."
                if description:
                    msg += f" It looks like: {description}"
                return {"success": True, "message": msg, "image_id": row_id}
            return {"success": False, "message": "Sorry, I couldn't save the photo. Check the PostgreSQL connection."}
        
        elif intent == "take_screenshot_remember":
            """
            Take a screenshot and save it to PostgreSQL.
            """
            import base64 as _base64
            label = parameters.get("label", "untitled")
            # Take screenshot via device_controller
            ss_result = device_controller.take_screenshot()
            if not ss_result.get("success"):
                return {"success": False, "message": "Couldn't take a screenshot."}
            # device_controller returns path; read and encode
            ss_path = ss_result.get("path", "")
            try:
                if ss_path:
                    with open(ss_path, "rb") as f:
                        image_b64 = _base64.b64encode(f.read()).decode()
                else:
                    # Fallback: take screenshot directly with pyautogui
                    import pyautogui
                    from io import BytesIO
                    img = pyautogui.screenshot()
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    image_b64 = _base64.b64encode(buf.getvalue()).decode()
                
                row_id = await image_store.save_screenshot(
                    image_base64=image_b64,
                    label=label,
                )
                if row_id:
                    return {"success": True, "message": f"Screenshot saved as '{label}'!", "screenshot_id": row_id}
                return {"success": False, "message": "Screenshot taken but couldn't save to database."}
            except Exception as e:
                return {"success": False, "message": f"Error saving screenshot: {e}"}
        
        elif intent == "recall_image":
            """
            Retrieve a saved image by label and describe it to the user.
            """
            label = parameters.get("label", "")
            if not label:
                return {"success": False, "message": "Please tell me which photo to recall. For example: 'show me the photo of my desk'."}
            
            result = await image_store.get_image(label)
            if not result:
                # Try screenshots too
                result = await image_store.get_screenshot(label)
            
            if result:
                desc = result.get("description") or "no description available"
                taken = result.get("taken_at", "")[:10]  # date only
                return {
                    "success": True,
                    "message": f"Found it! I saved '{result['label']}' on {taken}. It shows: {desc}",
                    "image_data": result,
                }
            return {
                "success": False,
                "message": f"I don't have any saved photo matching '{label}'. Try taking one first!",
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
        
        # User Identity
        elif intent == "enroll_voice":
             return {
                 "success": True,
                 "message": "I am listening. Please keep speaking for a few seconds so I can learn your voice.",
                 "action": "enroll_voice_step2" # Frontend/Main loop needs to handle the logic, but for now we just return message.
                 # Actually, to enroll, we need the AUDIO data. 
                 # This intent is triggered AFTER audio is processed. 
                 # So we missed the audio? No, we had audio in the valid request.
                 # Ideally, we should have enrolled it RIGHT THERE if we knew.
                 # But we can't rewind.
                 # Workaround: Tell user to say a specific phrase to enroll.
                 # Better: We need the audio that triggered this.
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
