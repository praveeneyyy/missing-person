import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from backend.config import (
    YUNET_MODEL_PATH,
    SFACE_MODEL_PATH,
    SIMILARITY_THRESHOLD_HIGH,
    SIMILARITY_THRESHOLD_MODERATE
)

class FaceEngine:
    """
    Production-grade Computer Vision and Biometric Embedding Engine
    using OpenCV YuNet (Face Detection) and SFace (Face Recognition).
    """

    def __init__(self, yunet_path: str = YUNET_MODEL_PATH, sface_path: str = SFACE_MODEL_PATH):
        if not os.path.exists(yunet_path):
            raise FileNotFoundError(f"YuNet model not found at {yunet_path}")
        if not os.path.exists(sface_path):
            raise FileNotFoundError(f"SFace model not found at {sface_path}")

        self.yunet_path = yunet_path
        self.sface_path = sface_path
        self.detector_score_thresh = 0.6
        self.detector_nms_thresh = 0.3

        # Initialize SFace recognizer
        self.recognizer = cv2.FaceRecognizerSF_create(self.sface_path, "")

    def _get_detector(self, width: int, height: int):
        """Creates a YuNet detector instance configured for the input image dimensions."""
        return cv2.FaceDetectorYN_create(
            self.yunet_path,
            "",
            (width, height),
            self.detector_score_thresh,
            self.detector_nms_thresh,
            5000
        )

    def decode_image(self, image_bytes: bytes) -> np.ndarray:
        """Decodes raw image bytes into a BGR OpenCV NumPy array."""
        if not image_bytes:
            raise ValueError("Empty image data received.")
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Unsupported or corrupted image file format.")
        return img

    def detect_faces(self, img: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects all faces in the provided BGR image.
        Returns a list of detected face dictionaries containing:
        - bbox: [x, y, w, h] (integers)
        - landmarks: [[x, y], ...] (5 facial points: right eye, left eye, nose, right mouth, left mouth)
        - confidence: float detection score
        - raw_face: raw detection array required by alignCrop
        """
        h, w = img.shape[:2]
        detector = self._get_detector(w, h)
        _, raw_faces = detector.detect(img)

        results = []
        if raw_faces is not None:
            for face in raw_faces:
                bbox = [int(face[0]), int(face[1]), int(face[2]), int(face[3])]
                # Ensure bbox stays within image boundaries
                bbox[0] = max(0, bbox[0])
                bbox[1] = max(0, bbox[1])
                bbox[2] = min(w - bbox[0], bbox[2])
                bbox[3] = min(h - bbox[1], bbox[3])

                landmarks = []
                # Face elements 4 to 13 are 5 landmarks (x, y)
                for i in range(4, 14, 2):
                    landmarks.append([float(face[i]), float(face[i+1])])

                confidence = float(face[14])

                results.append({
                    "bbox": bbox,
                    "landmarks": landmarks,
                    "confidence": round(confidence, 4),
                    "raw_face": face
                })

        return results

    def extract_embedding(self, img: np.ndarray, raw_face: np.ndarray) -> List[float]:
        """
        Aligns, crops, and extracts a 128-dimensional normalized facial embedding vector.
        """
        aligned_face = self.recognizer.alignCrop(img, raw_face)
        feature = self.recognizer.feature(aligned_face)
        # Flatten to 1D float vector and normalize
        vec = feature.flatten().astype(float)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def validate_reference_photo(self, img: np.ndarray) -> Dict[str, Any]:
        """
        Validates reference photos for case registration.
        Acceptance criteria from PRD FR-02/FR-03:
        - Must contain exactly 1 unambiguous face.
        - Rejects zero faces with helpful guidance.
        - Rejects multiple faces to prevent identity ambiguity.
        """
        faces = self.detect_faces(img)
        if len(faces) == 0:
            raise ValueError(
                "No human face was detected in this reference photo. "
                "Please upload a clear, front-facing portrait with adequate lighting."
            )
        if len(faces) > 1:
            raise ValueError(
                f"Multiple faces ({len(faces)}) were detected. "
                "Reference photos must contain only the missing person to prevent identity ambiguity."
            )

        face = faces[0]
        embedding = self.extract_embedding(img, face["raw_face"])
        return {
            "bbox": face["bbox"],
            "landmarks": face["landmarks"],
            "confidence": face["confidence"],
            "embedding": embedding,
            "model_name": "YuNet + SFace",
            "model_version": "v1.0-onnx"
        }

    def process_sighting_image(self, img: np.ndarray) -> List[Dict[str, Any]]:
        """
        Processes sighting images (which may contain 0, 1, or multiple people).
        Extracts face detections and embeddings for every detected individual.
        """
        faces = self.detect_faces(img)
        processed_faces = []
        for idx, face in enumerate(faces):
            embedding = self.extract_embedding(img, face["raw_face"])
            processed_faces.append({
                "face_index": idx,
                "bbox": face["bbox"],
                "landmarks": face["landmarks"],
                "confidence": face["confidence"],
                "embedding": embedding
            })
        return processed_faces

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Computes cosine similarity between two normalized feature vectors.
        Returns a float between -1.0 and 1.0 (clamped).
        """
        u = np.array(vec1, dtype=np.float32)
        v = np.array(vec2, dtype=np.float32)
        norm_u = np.linalg.norm(u)
        norm_v = np.linalg.norm(v)
        if norm_u == 0 or norm_v == 0:
            return 0.0
        dot = np.dot(u, v) / (norm_u * norm_v)
        return float(np.clip(dot, -1.0, 1.0))

    def rank_candidates(
        self,
        query_embedding: List[float],
        enrolled_cases: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Ranks enrolled missing person cases against the query embedding.
        Enforces PRD FR-04:
        - Sorted descending by similarity score.
        - Top-K returned.
        - Distinct scores labeled as ranking signals, not probabilities.
        """
        candidates = []
        for case in enrolled_cases:
            ref_embedding = case.get("embedding")
            if not ref_embedding:
                continue

            similarity = self.cosine_similarity(query_embedding, ref_embedding)

            # Categorize similarity confidence tier
            if similarity >= SIMILARITY_THRESHOLD_HIGH:
                tier = "High Similarity"
            elif similarity >= SIMILARITY_THRESHOLD_MODERATE:
                tier = "Moderate Similarity"
            else:
                tier = "Low Similarity"

            candidates.append({
                "case_id": case["case_id"],
                "reference_image_id": case.get("reference_image_id"),
                "reference_no": case["reference_no"],
                "full_name": case["full_name"],
                "age": case.get("age"),
                "gender": case.get("gender"),
                "last_seen_date": case.get("last_seen_date"),
                "last_seen_location": case.get("last_seen_location"),
                "similarity_score": round(similarity, 4),
                "similarity_percent": round(max(0.0, similarity) * 100, 1),
                "confidence_tier": tier,
                "model_version": "v1.0-onnx",
                "requires_human_review": True
            })

        # Sort descending by similarity score
        candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_candidates = candidates[:top_k]

        # Assign ranks
        for rank_idx, item in enumerate(top_candidates, start=1):
            item["rank"] = rank_idx

        return top_candidates

    def annotate_image_with_bboxes(self, img: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """
        Draws bounding boxes and labels on an image copy for visual inspection.
        """
        annotated = img.copy()
        for idx, det in enumerate(detections):
            bbox = det.get("bbox", [])
            if len(bbox) == 4:
                x, y, w, h = bbox
                # Draw bounding box
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (59, 130, 246), 2)
                # Label box
                label = f"Face #{idx + 1}"
                if "confidence" in det:
                    label += f" ({int(det['confidence'] * 100)}%)"
                cv2.putText(
                    annotated,
                    label,
                    (x, max(20, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (59, 130, 246),
                    2
                )
        return annotated

# Global singleton instance
face_engine = FaceEngine()
