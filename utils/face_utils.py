import face_recognition
import numpy as np
import cv2
import json
import base64
from io import BytesIO
from PIL import Image

class FaceUtils:
    @staticmethod
    def get_encoding(image_path):
        """Extracts the first face encoding from an image file."""
        try:
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                return encodings[0].tolist()
            return None
        except Exception as e:
            print(f"Error extracting encoding: {e}")
            return None

    @staticmethod
    def compare_faces(known_encoding_list, base64_frame, tolerance=0.5):
        """Compares a base64 frame against a known encoding list."""
        try:
            header, encoded = base64_frame.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            image = Image.open(BytesIO(image_bytes))
            
            rgb_frame = np.array(image.convert('RGB'))
            
            unknown_encodings = face_recognition.face_encodings(rgb_frame)
            if not unknown_encodings:
                return False, "No face detected"
            
            results = face_recognition.compare_faces([np.array(known_encoding_list)], unknown_encodings[0], tolerance=tolerance)
            if results[0]:
                return True, "Match found"
            return False, "Face mismatch"
        except Exception as e:
            return False, f"Error comparing faces: {str(e)}"
            
    @staticmethod
    def encode_to_json(numpy_array):
        return json.dumps(numpy_array.tolist())
    
    @staticmethod
    def decode_from_json(json_string):
        return np.array(json.loads(json_string))
