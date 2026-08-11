import cv2
import json
import base64
import numpy as np

from services.face_intelligence import FaceIntelligence


class FaceUtils:

    @staticmethod
    def get_encoding(image_path):
        """Extract an ArcFace embedding from an image file."""
        try:
            img = cv2.imread(image_path)

            if img is None:
                return None

            embedding, confidence = FaceIntelligence.get_embedding(
                img,
                enforce_detection=True
            )

            if embedding:
                return embedding

            return None

        except Exception as e:
            print(f"Error extracting ArcFace embedding: {e}")
            return None

    @staticmethod
    def compare_faces(known_encodings, unknown_encoding, tolerance=0.5):
        """
        Compatibility wrapper for old FaceUtils API.

        If known_encodings are supplied, compare them using
        ArcFace cosine distance.

        If unknown_encoding is a base64 image, extract its
        ArcFace embedding first.
        """
        try:
            if isinstance(unknown_encoding, str):
                frame = FaceUtils.decode_base64_frame(unknown_encoding)

                if frame is None:
                    return False, "No face detected"

                embedding, confidence = FaceIntelligence.get_embedding(
                    frame,
                    enforce_detection=True
                )

                if not embedding:
                    return False, "No face detected"

                unknown_encoding = np.array(embedding)

            else:
                unknown_encoding = np.array(unknown_encoding)

            if not known_encodings:
                return False, "Face detected"

            results = []

            for known in known_encodings:
                known = np.array(known)

                distance = FaceIntelligence.cosine_distance(
                    known,
                    unknown_encoding
                )

                results.append(distance <= tolerance)

            return results, "Face compared"

        except Exception as e:
            print(f"Face comparison error: {e}")
            return False, "Face comparison failed"

    @staticmethod
    def get_face_distance(known_encodings, unknown_encoding):
        """Return ArcFace cosine distances."""
        if not known_encodings:
            return []

        try:
            unknown_encoding = np.array(unknown_encoding)

            distances = []

            for known in known_encodings:
                known = np.array(known)

                distance = FaceIntelligence.cosine_distance(
                    known,
                    unknown_encoding
                )

                distances.append(distance)

            return np.array(distances)

        except Exception as e:
            print(f"Face distance error: {e}")
            return []

    @staticmethod
    def check_spoof(frame):
        """Basic anti-spoofing using Laplacian variance."""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            variance = cv2.Laplacian(
                gray,
                cv2.CV_64F
            ).var()

            return variance > 100, variance

        except Exception:
            return False, 0

    @staticmethod
    def decode_base64_frame(base64_frame):
        """Decode a Base64 image into an OpenCV BGR frame."""
        try:
            if "," in base64_frame:
                _, encoded = base64_frame.split(",", 1)
            else:
                encoded = base64_frame

            image_bytes = base64.b64decode(encoded)

            img_array = np.frombuffer(
                image_bytes,
                np.uint8
            )

            return cv2.imdecode(
                img_array,
                cv2.IMREAD_COLOR
            )

        except Exception:
            return None

    @staticmethod
    def encode_to_json(numpy_array):
        """Convert embedding array to JSON."""
        return json.dumps(
            np.asarray(numpy_array).tolist()
        )

    @staticmethod
    def decode_from_json(json_string):
        """Convert stored JSON embedding back to NumPy array."""
        if not json_string:
            return None

        try:
            return np.array(
                json.loads(json_string)
            )

        except Exception:
            return None