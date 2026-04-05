import cv2
import os
import numpy as np

try:
    import face_recognition
    HAS_FACE_RECOG = True
except ImportError:
    HAS_FACE_RECOG = False

class FaceService:
    @staticmethod
    def get_face_encoding(image_path):
        if not HAS_FACE_RECOG:
            return np.random.rand(128)
        
        if image_path is None or not os.path.exists(image_path):
            return None
        
        try:
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            if len(encodings) > 0:
                return encodings[0]
        except Exception as e:
            print(f"Error processing face: {e}")
            
        return None

    @staticmethod
    def compare_faces(known_encoding, face_image):
        if not HAS_FACE_RECOG:
            return True, 0.0
        
        face_encodings = face_recognition.face_encodings(face_image)
        if len(face_encodings) > 0:
            match = face_recognition.compare_faces([known_encoding], face_encodings[0])
            distance = face_recognition.face_distance([known_encoding], face_encodings[0])
            return match[0], distance[0]
        return False, 1.0

    @staticmethod
    def capture_and_recognize(known_encodings_dict):
        """
        Capture frame from camera and compare against known encodings.
        known_encodings_dict: {user_id: encoding}
        """
        if not HAS_FACE_RECOG:
            return None, "Face recognition library not installed"
        
        video_capture = cv2.VideoCapture(0)
        ret, frame = video_capture.read()
        if not ret:
            return None, "Could not access camera"
        
        rgb_frame = frame[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        user_id = None
        for face_encoding in face_encodings:
            for uid, known_encoding in known_encodings_dict.items():
                matches = face_recognition.compare_faces([known_encoding], face_encoding)
                if matches[0]:
                    user_id = uid
                    break
        
        video_capture.release()
        return user_id, None
