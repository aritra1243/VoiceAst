import cv2
import numpy as np
import base64
import os
import json
import asyncio

class FaceMemory:
    def __init__(self, data_file="faces.yml", names_file="face_names.json"):
        self.data_file = data_file
        self.names_file = names_file
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.names = {} # Map ID to Name
        self.next_id = 0
        self.is_trained = False
        
        self.load_data()

    def load_data(self):
        """Load trained model and names"""
        if os.path.exists(self.names_file):
            with open(self.names_file, 'r') as f:
                data = json.load(f)
                self.names = {int(k): v for k, v in data['names'].items()}
                self.next_id = data['next_id']
        
        if os.path.exists(self.data_file):
            try:
                self.recognizer.read(self.data_file)
                self.is_trained = True
                print(f"✓ Face Memory loaded: {len(self.names)} people")
            except Exception as e:
                print(f"Error loading face model: {e}")

    def save_data(self):
        """Save model and names"""
        self.recognizer.write(self.data_file)
        with open(self.names_file, 'w') as f:
            json.dump({
                'names': self.names,
                'next_id': self.next_id
            }, f)

    def _base64_to_image(self, base64_string):
        """Convert base64 to numpy array"""
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]
        img_data = base64.b64decode(base64_string)
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def train_face(self, image_base64: str, name: str) -> bool:
        """Add a face to the memory"""
        try:
            gray = self._base64_to_image(image_base64)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                print("No face detected for training")
                return False
            
            # Use the largest face
            (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
            face_roi = gray[y:y+h, x:x+w]
            
            # Determine ID
            existing_id = None
            for id, n in self.names.items():
                if n.lower() == name.lower():
                    existing_id = id
                    break
            
            if existing_id is None:
                existing_id = self.next_id
                self.names[existing_id] = name
                self.next_id += 1
            
            # Update learner
            # LBPH can be updated? Actually standard OpenCV LBPH update is tricky in python bindings sometimes
            # We might need to re-train on all data if update() isn't available or crashes
            # But let's try update() if supported, else we just simple 'update'
            
            self.recognizer.update([face_roi], np.array([existing_id]))
            
            self.save_data()
            self.is_trained = True
            return True
        except Exception as e:
            print(f"Error training face: {e}")
            return False

    def recognize_face(self, image_base64: str) -> str:
        """Recognize face in image"""
        if not self.is_trained:
            return "Unknown (I haven't learned any faces yet)"
            
        try:
            gray = self._base64_to_image(image_base64)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                return "No face visible"
            
            # Use largest face
            (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
            face_roi = gray[y:y+h, x:x+w]
            
            id, confidence = self.recognizer.predict(face_roi)
            
            # Confidence: 0 is perfect match, 100+ is bad
            if confidence < 80:
                name = self.names.get(id, "Unknown")
                return f"{name} ({100 - confidence:.0f}% confidence)"
            else:
                return "Unknown Person"
                
        except Exception as e:
            print(f"Error recognizing face: {e}")
            return "Error reading face"

# Global instance
face_memory = FaceMemory()
