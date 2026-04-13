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
    def compare_faces(known_encodings, unknown_encoding, tolerance=0.5):
        """Compares a list of known encodings against a single unknown encoding."""
        if not known_encodings:
            return []
        return face_recognition.compare_faces(known_encodings, unknown_encoding, tolerance=tolerance)

    @staticmethod
    def get_face_distance(known_encodings, unknown_encoding):
        """Returns the Euclidean distance between encodings."""
        if not known_encodings:
            return []
        return face_recognition.face_distance(known_encodings, unknown_encoding)

    @staticmethod
    def check_spoof(frame):
        """Anti-spoofing via Laplacian variance (blur detection)."""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            variance = cv2.Laplacian(gray, cv2.CV_64F).var()
            return variance > 100, variance # Returns True if real, False if likely a photo/screen
        except:
            return False, 0

    @staticmethod
    def decode_base64_frame(base64_frame):
        """Decodes base64 string to OpenCV BGR frame."""
        try:
            if "," in base64_frame:
                header, encoded = base64_frame.split(",", 1)
            else:
                encoded = base64_frame
            image_bytes = base64.b64decode(encoded)
            img_array = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return frame
        except:
            return None

    @staticmethod
    def encode_to_json(numpy_array):
        return json.dumps(numpy_array.tolist())
    
    @staticmethod
    def decode_from_json(json_string):
        if not json_string: return None
        try:
            return np.array(json.loads(json_string))
        except:
            return None
