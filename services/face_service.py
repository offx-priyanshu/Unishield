import os
import base64
import numpy as np
import cv2
import pickle
import time
from deepface import DeepFace

# Pre-import Cloudinary (Handle error gracefully if not found)
try:
    import cloudinary.uploader
    from config.cloudinary_config import *
except ImportError:
    pass

# Import the DB function (Handle gracefully)
try:
    from models.student_model import add_student
except ImportError:
    print("[ERROR] Could not import add_student from models.student_model")
    def add_student(student_id, student_name, image_url):
        pass

# Reduce TensorFlow logs
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# ================= PRELOAD MODEL =================
print("[INFO] Loading ArcFace model...")
try:
    DeepFace.build_model("ArcFace")
    print("[SUCCESS] ArcFace model loaded!")
except Exception as e:
    print("[ERROR] Model load failed:", e)

# ================= DIRECTORIES =================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
EMBEDDING_PATH = os.path.join(BASE_DIR, "trainer", "embeddings.pkl")

os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(os.path.dirname(EMBEDDING_PATH), exist_ok=True)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ================= GLOBAL STATE =================
KNOWN_EMBEDDINGS = []
KNOWN_IDS = []

# LOAD EMBEDDINGS ONCE (IMPORTANT)
if os.path.exists(EMBEDDING_PATH):
    try:
        with open(EMBEDDING_PATH, "rb") as f:
            KNOWN_EMBEDDINGS, KNOWN_IDS = pickle.load(f)
        print(f"[INFO] Loaded {len(KNOWN_EMBEDDINGS)} known embeddings.")
    except Exception as e:
        print(f"[ERROR] Failed to load embeddings: {e}")

class FaceService:
    CAPTURE_LIMIT = 30

    @staticmethod
    def cosine_distance(source_representation, test_representation):
        """ Calculate Cosine Distance between two embeddings for ArcFace """
        a = np.matmul(np.transpose(source_representation), test_representation)
        b = np.sum(np.multiply(source_representation, source_representation))
        c = np.sum(np.multiply(test_representation, test_representation))
        return 1 - (a / (np.sqrt(b) * np.sqrt(c)))

    @staticmethod
    def capture_face(data):
        """ Handles taking screenshots from frontend and saving them """
        student_id = data.get("id")
        student_name = data.get("name")
        image_data = data.get("image")

        if not student_id or not student_name or not image_data:
            return {"error": "Invalid data"}, 400

        key = f"{student_id}_{student_name}"
        save_dir = os.path.join(DATASET_DIR, key)
        os.makedirs(save_dir, exist_ok=True)

        # ✨ FIX 1: Dynamically determine the count to avoid RAM global state leak
        current_count = len([name for name in os.listdir(save_dir) if name.endswith('.jpg')])

        if current_count >= FaceService.CAPTURE_LIMIT:
            return {"count": current_count, "done": True}

        try:
            encoded = image_data.split(",")[1]
            img_bytes = base64.b64decode(encoded)
            img_array = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except Exception as e:
            return {"error": str(e)}, 400

        if frame is None:
            return {"count": current_count, "done": False}

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.2, 5)

        if len(faces) == 0:
            print("❌ No face detected")
            return {"count": current_count, "done": False}

        face = None
        done = False

        for (x, y, w, h) in faces[:1]:
            # ✨ FIX 4: Add padding to the face crop for better Cloudinary picture upload
            padding = 30
            h_im, w_im = frame.shape[:2]
            
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(w_im, x + w + padding)
            y2 = min(h_im, y + h + padding)

            face = frame[y1:y2, x1:x2]
            
            # The saved faces can be strictly resized to 160x160 as requested initially
            face_resized = cv2.resize(frame[y:y+h, x:x+w], (160, 160)) 

            current_count += 1
            # Using timestamp ensures unique naming safely across threads
            file_path = os.path.join(save_dir, f"{int(time.time() * 1000)}.jpg")
            cv2.imwrite(file_path, face_resized)

            if current_count >= FaceService.CAPTURE_LIMIT:
                done = True
                break

        # ✨ FIX 4 (Upload only if just finished padding process)
        if done and face is not None:
            try:
                # Upload the nice padded face to Cloudinary, not the tight 160x160 one
                _, buffer = cv2.imencode(".jpg", face)
                result = cloudinary.uploader.upload(buffer.tobytes())
                image_url = result.get("secure_url")

                add_student(student_id, student_name, image_url)
                print(f"[DB] Student {key} saved with image:", image_url)
            except Exception as e:
                print(f"[ERROR] Cloudinary/DB Error: {e}")

        return {
            "count": min(current_count, FaceService.CAPTURE_LIMIT),
            "done": done
        }

    @staticmethod
    def generate_embeddings():
        """ Extract DeepFace embeddings and save locally """
        global KNOWN_EMBEDDINGS, KNOWN_IDS
        embeddings = []
        labels = []

        if not os.path.exists(DATASET_DIR):
            return {"success": False, "error": "Dataset folder not found"}

        for folder in os.listdir(DATASET_DIR):
            folder_path = os.path.join(DATASET_DIR, folder)
            if not os.path.isdir(folder_path):
                continue
                
            student_id = folder.split("_")[0]
            
            for img_name in os.listdir(folder_path):
                if not img_name.endswith(('.png', '.jpg', '.jpeg')):
                    continue
                    
                path = os.path.join(folder_path, img_name)

                try:
                    rep = DeepFace.represent(
                        img_path=path,
                        model_name="ArcFace",
                        detector_backend="opencv",
                        enforce_detection=False
                    )

                    embeddings.append(rep[0]["embedding"])
                    labels.append(student_id)

                except Exception as e:
                    print(f"Training error on {path}: {e}")

        try:
            with open(EMBEDDING_PATH, "wb") as f:
                pickle.dump((embeddings, labels), f)
            
            KNOWN_EMBEDDINGS = embeddings
            KNOWN_IDS = labels
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def recognize_face(frame_or_data):
        """ Detect and recognize a face in a frame using DeepFace """
        global KNOWN_EMBEDDINGS, KNOWN_IDS

        if len(KNOWN_EMBEDDINGS) == 0:
            return []

        results = []
        
        try:
            if isinstance(frame_or_data, str) and "," in frame_or_data:
                encoded = frame_or_data.split(",")[1]
                img_bytes = base64.b64decode(encoded)
                img_array = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            else:
                frame = frame_or_data

            if frame is None:
                return []
            
            # ✨ FIX 2: We use DeepFace directly to handle both face detection AND precise alignment mapping 
            try:
                reps = DeepFace.represent(
                    img_path=frame,
                    model_name="ArcFace",
                    detector_backend="opencv",
                    enforce_detection=True # Ignore frames with no clear faces safely
                )
            except ValueError:
                return [] # No face detected gracefully

            for rep in reps:
                face_vector = np.array(rep["embedding"])
                
                # ✨ FIX 3: Using mathematical Cosine Distance for optimal ArcFace evaluation
                distances = [FaceService.cosine_distance(face_vector, np.array(emb)) for emb in KNOWN_EMBEDDINGS]

                if not distances:
                    continue
                
                min_dist = min(distances)
                index = distances.index(min_dist)

                print(f"Cosine Distance Score: {min_dist:.4f} for label {KNOWN_IDS[index]}")

                # DeepFace's optimal Cosine Threshold for ArcFace model is roughly 0.68.
                if min_dist <= 0.68:  
                    results.append(KNOWN_IDS[index])
                else:
                    results.append("Unknown")

        except Exception as e:
            print("[ERROR] Face recognition error:", e)
            results.append("Unknown")

        return results
