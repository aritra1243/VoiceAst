"""
Natural Language Understanding - Flexible Pattern Matching
Enhanced intent recognizer that understands natural language
"""
import re
from typing import Dict, List, Tuple

class FlexibleIntentRecognizer:
    """Enhanced intent recognition with natural language support"""
    
    def __init__(self):
        self.filler_words = ['please', 'can you', 'could you', 'would you', 'i want to', 'i need to', 'hey', 'ok']
        self.action_keywords = self._build_action_keywords()
        self.entity_keywords = self._build_entity_keywords()
    
    def _build_action_keywords(self) -> Dict[str, List[str]]:
        """Build flexible action keywords"""
        return {
            'open': ['open', 'launch', 'start', 'run', 'execute', 'खोलो', 'खोल', 'स्टार्ट'],
            'close': ['close', 'quit', 'exit', 'terminate', 'stop', 'बंद', 'बंद करो'],
            'take_screenshot': ['screenshot', 'screen shot', 'capture screen', 'take picture', 'स्क्रीनशॉट'],
            'volume_up': ['increase volume', 'volume up', 'louder', 'raise volume', 'वॉल्यूम बढ़ाओ', 'आवाज बढ़ा'],
            'volume_down': ['decrease volume', 'volume down', 'quieter', 'lower volume', 'वॉल्यूम घटाओ', 'आवाज कम'],
            'mute': ['mute', 'silence', 'quiet', 'म्यूट'],
            'brightness_up': ['increase brightness', 'brightness up', 'brighter', 'चमक बढ़ाओ'],
            'brightness_down': ['decrease brightness', 'brightness down', 'darker', 'चमक घटाओ'],
            'time': ['time', 'what time', 'current time', 'समय', 'टाइम'],
            'date': ['date', 'what date', 'today', 'तारीख'],
            'search': ['search', 'google', 'look up', 'find', 'खोजो'],
        }
    
    def _build_entity_keywords(self) -> Dict[str, List[str]]:
        """Build entity keywords (apps, targets, etc.)"""
        return {
            'notepad': ['notepad', 'text editor', 'नोटपैड'],
            'chrome': ['chrome', 'browser', 'google chrome', 'क्रोम'],
            'calculator': ['calculator', 'calc', 'कैलकुलेटर'],
            'file_explorer': ['explorer', 'file explorer', 'files', 'फाइल'],
        }
    
    def clean_text(self, text: str) -> str:
        """Remove filler words from text"""
        text_lower = text.lower().strip()
        
        for filler in self.filler_words:
            text_lower = text_lower.replace(filler, ' ')
        
        # Clean extra spaces
        text_lower = ' '.join(text_lower.split())
        return text_lower
    
    def recognize_flexible(self, text: str) -> Dict:
        """
        Recognize intent with flexible natural language understanding
        
        Args:
            text: User's natural language command
        
        Returns:
            dict with intent, confidence, and parameters
        """
        original_text = text
        text_clean = self.clean_text(text)
        
        print(f"Original: '{original_text}'")
        print(f"Cleaned: '{text_clean}'")
        
        # Check each action
        for action, keywords in self.action_keywords.items():
            for keyword in keywords:
                if keyword in text_clean:
                    # Found an action!
                    result = {
                        'intent': action,
                        'confidence': 0.9,
                        'parameters': {},
                        'original_text': original_text
                    }
                    
                    # For open/close, find the target app
                    if action in ['open', 'close']:
                        for entity, entity_keywords in self.entity_keywords.items():
                            for entity_keyword in entity_keywords:
                                if entity_keyword in text_clean:
                                    result['parameters']['app_name'] = entity
                                    result['intent'] = f'{action}_app'
                                    return result
                        
                        # Try to extract app name from text
                        words = text_clean.split()
                        if len(words) > 1:
                            # Take the word after the action
                            idx = next((i for i, word in enumerate(words) if keyword in word), -1)
                            if idx >= 0 and idx + 1 < len(words):
                                result['parameters']['app_name'] = words[idx + 1]
                                result['intent'] = f'{action}_app'
                    
                    # For search, extract query
                    if action == 'search':
                        # Everything after the keyword is the query
                        for kw in keywords:
                            if kw in text_clean:
                                query_start = text_clean.find(kw) + len(kw)
                                query = text_clean[query_start:].strip()
                                if query:
                                    result['parameters']['query'] = query
                                    result['intent'] = 'web_search'
                                break
                    
                    return result
        
        # No match found
        return {
            'intent': 'unknown',
            'confidence': 0.0,
            'parameters': {},
            'original_text': original_text
        }

# Example usage:
if __name__ == '__main__':
    recognizer = FlexibleIntentRecognizer()
    
    test_commands = [
        "please open notepad",
        "can you take a screenshot",
        "i want to increase the volume",
        "search for python tutorials",
        "नोटपैड खोलो",
        "वॉल्यूम बढ़ाओ",
        "स्क्रीनशॉट लो",
    ]
    
    for cmd in test_commands:
        result = recognizer.recognize_flexible(cmd)
        print(f"\n Command: {cmd}")
        print(f"  Intent: {result['intent']}")
        print(f"  Params: {result['parameters']}")
