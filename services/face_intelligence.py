import os
import cv2
import numpy as np
import base64
import json
import time
from deepface import DeepFace
from models.user import User
from models.db import db
from flask import current_app

class FaceIntelligence:
    MODEL_NAME = "ArcFace"
    DETECTOR_BACKEND = "opencv"
    
    _STUDENT_CACHE = None
    _CACHE_TIMESTAMP = 0
    CACHE_EXPIRY = 60 # 1 minute
    
    @staticmethod
    def get_cached_students():
        now = time.time()
        if FaceIntelligence._STUDENT_CACHE is None or (now - FaceIntelligence._CACHE_TIMESTAMP) > FaceIntelligence.CACHE_EXPIRY:
            FaceIntelligence._STUDENT_CACHE = User.query.filter(User.face_encoded.isnot(None), User.role == 'student').all()
            FaceIntelligence._CACHE_TIMESTAMP = now
            db.session.remove() # Close session to prevent pool leak
        return FaceIntelligence._STUDENT_CACHE
    
    @staticmethod
    def base64_to_cv2(b64_string):
        if "," in b64_string:
            b64_string = b64_string.split(",")[1]
        img_data = base64.b64decode(b64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    @staticmethod
    def get_embedding(img_cv2, enforce_detection=True):
        try:
            results = DeepFace.represent(
                img_path=img_cv2,
                model_name=FaceIntelligence.MODEL_NAME,
                detector_backend=FaceIntelligence.DETECTOR_BACKEND,
                enforce_detection=enforce_detection,
                align=True
            )
            if results:
                return results[0]["embedding"], results[0]["face_confidence"]
            return None, 0
        except Exception as e:
            print(f"[FaceIntelligence] Embedding Error: {e}")
            return None, 0

    @staticmethod
    def calculate_confidence(distance, threshold=0.68):
        """Convert cosine distance to 0-100 confidence score."""
        # 0 distance = 100% confidence
        # threshold (0.68) = 50% confidence (approx)
        # > threshold significantly drops
        conf = max(0, min(100, 100 * (1 - (distance / (threshold * 1.5)))))
        return round(conf, 2)

    @staticmethod
    def match_face(embedding):
        if not embedding:
            return None, 0
            
        all_students = FaceIntelligence.get_cached_students()
        if not all_students:
            return None, 0

        best_match = None
        min_dist = 2.0 # Cosine distance max is 2
        
        target_vec = np.array(embedding)

        for student in all_students:
            try:
                # Assuming face_encoded stores a list of encodings (avg or multiple)
                stored_data = json.loads(student.face_encoded)
                if not isinstance(stored_data, list):
                    stored_data = [stored_data] # Backward compat
                
                for stored_vec in stored_data:
                    dist = FaceIntelligence.cosine_distance(target_vec, np.array(stored_vec))
                    if dist < min_dist:
                        min_dist = dist
                        best_match = student
            except Exception as e:
                continue

        # Convert distance to confidence
        # ArcFace threshold is typically 0.68
        confidence = FaceIntelligence.calculate_confidence(min_dist)
        
        return best_match, confidence

    @staticmethod
    def cosine_distance(v1, v2):
        return 1 - (np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    @staticmethod
    def register_student(data, images_b64):
        """
        Process multiple face angles and save student.
        images_b64: list of base64 images
        """
        embeddings = []
        best_image_path = None
        
        student_id = data.get('student_id')
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'faces', student_id)
        os.makedirs(upload_dir, exist_ok=True)

        for i, b64 in enumerate(images_b64):
            img = FaceIntelligence.base64_to_cv2(b64)
            if img is not None:
                emb, conf = FaceIntelligence.get_embedding(img)
                if emb:
                    embeddings.append(emb)
                    # Save the first good face as profile pic
                    if not best_image_path:
                        filename = f"profile.jpg"
                        best_image_path = os.path.join(upload_dir, filename)
                        cv2.imwrite(best_image_path, img)
                    
                    # Save angle
                    cv2.imwrite(os.path.join(upload_dir, f"angle_{i}.jpg"), img)

        if not embeddings:
            return False, "No faces detected in the provided captures."

        # Final student creation
        user = User.query.filter_by(student_id=student_id).first()
        if user:
            # Update existing?
            user.role = 'student'
        else:
            user = User(
                username=student_id,
                role='student',
                student_id=student_id,
                name=data.get('name'),
                department=data.get('department'),
                phone=data.get('phone'),
                parent_phone=data.get('parent_phone')
            )
            user.set_password(student_id)
            db.session.add(user)

        user.face_encoded = json.dumps(embeddings) # Store all angles as list of embeddings
        user.face_image = best_image_path
        
        db.session.commit()
        db.session.remove()
        
        # Clear cache to force reload of new student
        FaceIntelligence._STUDENT_CACHE = None
        
        return True, "Identity Registered & Activated Successfully."
