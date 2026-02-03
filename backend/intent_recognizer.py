"""
Intent recognition module - pattern-based command understanding
No external NLP APIs required
"""
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import config

class IntentRecognizer:
    """Custom intent recognition using pattern matching"""
    
    def __init__(self):
        self.intent_patterns = self._build_patterns()
    
    def _build_patterns(self) -> Dict[str, List[Tuple[re.Pattern, str]]]:
        """Build regex patterns for intent recognition"""
        return {
            # Application control
            "open_app": [
                (re.compile(r"open\s+(\w+)", re.I), "app_name"),
                (re.compile(r"launch\s+(\w+)", re.I), "app_name"),
                (re.compile(r"start\s+(\w+)", re.I), "app_name"),
            ],
            "close_app": [
                (re.compile(r"close\s+(\w+)", re.I), "app_name"),
                (re.compile(r"quit\s+(\w+)", re.I), "app_name"),
                (re.compile(r"exit\s+(\w+)", re.I), "app_name"),
                (re.compile(r"terminate\s+(\w+)", re.I), "app_name"),
            ],
            
            # File operations
            "create_file": [
                (re.compile(r"create\s+(?:a\s+)?file\s+(?:named\s+)?([^\s]+)", re.I), "filename"),
                (re.compile(r"make\s+(?:a\s+)?file\s+(?:named\s+)?([^\s]+)", re.I), "filename"),
                (re.compile(r"new\s+file\s+([^\s]+)", re.I), "filename"),
            ],
            "delete_file": [
                (re.compile(r"delete\s+(?:the\s+)?file\s+([^\s]+)", re.I), "filename"),
                (re.compile(r"remove\s+(?:the\s+)?file\s+([^\s]+)", re.I), "filename"),
            ],
            "list_files": [
                (re.compile(r"list\s+files\s+(?:in\s+)?(.+)", re.I), "directory"),
                (re.compile(r"show\s+files\s+(?:in\s+)?(.+)", re.I), "directory"),
                (re.compile(r"what\s+files\s+are\s+in\s+(.+)", re.I), "directory"),
            ],
            "search_files": [
                (re.compile(r"search\s+for\s+(.+)\s+in\s+(.+)", re.I), "query,directory"),
                (re.compile(r"find\s+(.+)\s+in\s+(.+)", re.I), "query,directory"),
            ],
            
            # System control
            "volume_up": [
                (re.compile(r"(?:increase|raise|turn up)\s+(?:the\s+)?volume", re.I), None),
                (re.compile(r"volume\s+up", re.I), None),
            ],
            "volume_down": [
                (re.compile(r"(?:decrease|lower|turn down)\s+(?:the\s+)?volume", re.I), None),
                (re.compile(r"volume\s+down", re.I), None),
            ],
            "mute": [
                (re.compile(r"mute", re.I), None),
                (re.compile(r"silence", re.I), None),
            ],
            "brightness_up": [
                (re.compile(r"(?:increase|raise)\s+(?:the\s+)?brightness", re.I), None),
                (re.compile(r"brightness\s+up", re.I), None),
                (re.compile(r"make\s+it\s+brighter", re.I), None),
            ],
            "brightness_down": [
                (re.compile(r"(?:decrease|lower)\s+(?:the\s+)?brightness", re.I), None),
                (re.compile(r"brightness\s+down", re.I), None),
                (re.compile(r"make\s+it\s+darker", re.I), None),
            ],
            "switch_tab": [
                 (re.compile(r"switch\s+tab", re.I), "direction"),
                 (re.compile(r"next\s+tab", re.I), "direction"), 
                 (re.compile(r"previous\s+tab", re.I), "direction"),
                 (re.compile(r"go\s+back\s+(?:to\s+)?(?:the\s+)?last\s+tab", re.I), "direction"),
                 (re.compile(r"change\s+tab", re.I), "direction"),
            ],
            "screenshot": [
                (re.compile(r"take\s+(?:a\s+)?screenshot", re.I), None),
                (re.compile(r"capture\s+(?:the\s+)?screen", re.I), None),
                (re.compile(r"print\s+screen", re.I), None),
            ],
            "shutdown": [
                (re.compile(r"shut\s*down\s+(?:the\s+)?(?:computer|system|pc)", re.I), None),
                (re.compile(r"power\s+off", re.I), None),
            ],
            "restart": [
                (re.compile(r"restart\s+(?:the\s+)?(?:computer|system|pc)", re.I), None),
                (re.compile(r"reboot", re.I), None),
            ],
            
            # Information queries
            "time": [
                (re.compile(r"what\s+time\s+is\s+it", re.I), None),
                (re.compile(r"tell\s+me\s+the\s+time", re.I), None),
                (re.compile(r"current\s+time", re.I), None),
            ],
            "date": [
                (re.compile(r"what'?s?\s+the\s+date", re.I), None),
                (re.compile(r"tell\s+me\s+the\s+date", re.I), None),
                (re.compile(r"today'?s?\s+date", re.I), None),
            ],
            "system_info": [
                (re.compile(r"system\s+information", re.I), None),
                (re.compile(r"computer\s+info", re.I), None),
            ],
            
            # Web search
            "web_search": [
                (re.compile(r"search\s+(?:for\s+)?(.+)", re.I), "query"),
                (re.compile(r"google\s+(.+)", re.I), "query"),
                (re.compile(r"look\s+up\s+(.+)", re.I), "query"),
            ],
            
            # Keyboard/Mouse automation
            "type_text": [
                (re.compile(r"type\s+(.+)", re.I), "text"),
                (re.compile(r"write\s+(.+)", re.I), "text"),
            ],
            "press_key": [
                (re.compile(r"press\s+(\w+)", re.I), "key"),
            ],
            
            # Greeting/Help
            "greeting": [
                (re.compile(r"^(hello|hi|hey|greetings)", re.I), None),
                (re.compile(r"(hey|hi|hello)\s+prime", re.I), None),
            ],
            "help": [
                (re.compile(r"help", re.I), None),
                (re.compile(r"what\s+can\s+you\s+do", re.I), None),
                (re.compile(r"commands", re.I), None),
            ],
        }
    
    def recognize(self, text: str) -> Dict:
        """
        Recognize intent from text
        
        Args:
            text: Input text to analyze
        
        Returns:
            dict with 'intent', 'confidence', and 'parameters'
        """
        text = text.strip()
        
        if not text:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "parameters": {}
            }
        
        # Try to match patterns
        for intent, patterns in self.intent_patterns.items():
            for pattern, param_names in patterns:
                match = pattern.search(text)
                if match:
                    parameters = {}
                    
                    if param_names:
                        param_list = param_names.split(",")
                        for i, param_name in enumerate(param_list):
                            if i + 1 <= len(match.groups()):
                                parameters[param_name.strip()] = match.group(i + 1).strip()
                    
                    return {
                        "intent": intent,
                        "confidence": 0.9,
                        "parameters": parameters,
                        "original_text": text
                    }
        
        # No match found
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "parameters": {},
            "original_text": text
        }
    
    def get_response_template(self, intent: str) -> str:
        """Get response template for an intent"""
        templates = {
            "open_app": "Opening {app_name}",
            "close_app": "Closing {app_name}",
            "create_file": "Creating file {filename}",
            "delete_file": "Deleting file {filename}",
            "list_files": "Listing files in {directory}",
            "search_files": "Searching for {query} in {directory}",
            "volume_up": "Increasing volume",
            "volume_down": "Decreasing volume",
            "mute": "Muting audio",
            "brightness_up": "Increasing brightness",
            "brightness_down": "Decreasing brightness",
            "brightness_up": "Increasing brightness",
            "brightness_down": "Decreasing brightness",
            "switch_tab": "Switching tab",
            "screenshot": "Taking screenshot",
            "shutdown": "Shutting down system",
            "restart": "Restarting system",
            "time": "The current time is {time}",
            "date": "Today is {date}",
            "system_info": "Gathering system information",
            "web_search": "Searching for {query}",
            "type_text": "Typing text",
            "press_key": "Pressing {key}",
            "greeting": "Hello! How can I help you?",
            "help": "I can help you control your device, manage files, and answer questions. Try saying 'open notepad' or 'what time is it'",
            "unknown": "I'm sorry, I don't understand that command. Say 'help' for available commands.",
        }
        
        return templates.get(intent, "Processing your request")
    
    def format_response(self, intent: str, parameters: Dict) -> str:
        """Format response with parameters"""
        template = self.get_response_template(intent)
        
        # Add time/date for info queries
        if intent == "time":
            parameters["time"] = datetime.now().strftime("%I:%M %p")
        elif intent == "date":
            parameters["date"] = datetime.now().strftime("%B %d, %Y")
        
        try:
            return template.format(**parameters)
        except KeyError:
            return template

# Global intent recognizer instance
intent_recognizer = IntentRecognizer()
