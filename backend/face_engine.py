import os
import cv2
import numpy as np
import base64
import time
import math
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

    def analyze_face_image(self, img: np.ndarray) -> Dict[str, Any]:
        """
        Diagnostic inspection of the 3-stage computer vision pipeline:
        Stage 1: Detection & 5-Landmark Localization (YuNet DNN)
        Stage 2: Affine Canonical Alignment & 112x112 Cropping (SFace alignCrop)
        Stage 3: 128-Dimensional Feature Representation & L2 Normalization (SFace)
        """
        h, w = img.shape[:2]

        t0 = time.perf_counter()
        detector = self._get_detector(w, h)
        _, raw_faces = detector.detect(img)
        t_detect = (time.perf_counter() - t0) * 1000.0

        detections = []
        t_align_total = 0.0
        t_feature_total = 0.0

        if raw_faces is not None:
            for idx, face in enumerate(raw_faces):
                bbox = [int(face[0]), int(face[1]), int(face[2]), int(face[3])]
                bbox[0] = max(0, bbox[0])
                bbox[1] = max(0, bbox[1])
                bbox[2] = min(w - bbox[0], bbox[2])
                bbox[3] = min(h - bbox[1], bbox[3])

                landmarks = []
                for i in range(4, 14, 2):
                    landmarks.append([float(face[i]), float(face[i+1])])

                confidence = float(face[14])

                # Calculate pre-alignment eye tilt angle in degrees
                dx = landmarks[1][0] - landmarks[0][0]
                dy = landmarks[1][1] - landmarks[0][1]
                tilt_angle = math.degrees(math.atan2(dy, dx + 1e-7))

                # Stage 2: Canonical Affine Alignment (112x112)
                t_a0 = time.perf_counter()
                aligned_face = self.recognizer.alignCrop(img, face)
                t_align_total += (time.perf_counter() - t_a0) * 1000.0

                # Measure sharpness / blur of aligned face
                sharpness = float(cv2.Laplacian(aligned_face, cv2.CV_64F).var())

                # Stage 3: Feature Extraction (128-D)
                t_f0 = time.perf_counter()
                feature = self.recognizer.feature(aligned_face)
                vec = feature.flatten().astype(float)
                norm = float(np.linalg.norm(vec))
                if norm > 0:
                    vec = vec / norm
                t_feature_total += (time.perf_counter() - t_f0) * 1000.0

                # Encode 112x112 aligned thumbnail
                _, enc = cv2.imencode(".jpg", aligned_face, [cv2.IMWRITE_JPEG_QUALITY, 90])
                aligned_b64 = f"data:image/jpeg;base64,{base64.b64encode(enc).decode('utf-8')}"

                detections.append({
                    "face_index": idx,
                    "bbox": bbox,
                    "landmarks": landmarks,
                    "confidence": round(confidence, 4),
                    "tilt_angle_deg": round(tilt_angle, 2),
                    "sharpness_score": round(sharpness, 1),
                    "aligned_crop_base64": aligned_b64,
                    "embedding": vec.tolist(),
                    "embedding_summary": {
                        "dimensions": len(vec),
                        "l2_norm": round(float(np.linalg.norm(vec)), 5),
                        "min": round(float(np.min(vec)), 4),
                        "max": round(float(np.max(vec)), 4),
                        "mean": round(float(np.mean(vec)), 5),
                        "std": round(float(np.std(vec)), 5),
                        "preview": [round(float(x), 4) for x in vec[:8]]
                    }
                })

        total_time = t_detect + t_align_total + t_feature_total

        return {
            "image_dimensions": {"width": w, "height": h},
            "faces_detected_count": len(detections),
            "latency_profile_ms": {
                "detection_ms": round(t_detect, 2),
                "alignment_ms": round(t_align_total, 2),
                "feature_extraction_ms": round(t_feature_total, 2),
                "total_pipeline_ms": round(total_time, 2)
            },
            "model_metadata": {
                "detector": "OpenCV YuNet (ONNX)",
                "detector_version": "2023mar",
                "recognizer": "OpenCV SFace 128-D (ONNX)",
                "recognizer_version": "2021dec",
                "canonical_crop_size": "112x112",
                "feature_dimensions": 128,
                "metric": "Cosine Similarity"
            },
            "detections": detections
        }

    def compare_two_faces(self, img1: np.ndarray, img2: np.ndarray) -> Dict[str, Any]:
        """
        Direct pairwise biometric comparison between two face images.
        """
        diag1 = self.analyze_face_image(img1)
        diag2 = self.analyze_face_image(img2)

        if diag1["faces_detected_count"] == 0:
            raise ValueError("No face detected in Image 1.")
        if diag2["faces_detected_count"] == 0:
            raise ValueError("No face detected in Image 2.")

        face1 = diag1["detections"][0]
        face2 = diag2["detections"][0]

        sim = self.cosine_similarity(face1["embedding"], face2["embedding"])
        euclidean_dist = math.sqrt(max(0.0, 2.0 * (1.0 - sim)))

        if sim >= SIMILARITY_THRESHOLD_HIGH:
            disposition = "verified"
            disposition_label = "Confirmed Match (High Confidence ≥ 0.70)"
        elif sim >= SIMILARITY_THRESHOLD_MODERATE:
            disposition = "moderate"
            disposition_label = "Plausible Match (Moderate 0.50 - 0.69)"
        else:
            disposition = "non_match"
            disposition_label = "Non-Match (Low Similarity < 0.50)"

        return {
            "cosine_similarity": round(sim, 4),
            "similarity_percent": round(max(0.0, sim) * 100, 1),
            "euclidean_distance": round(euclidean_dist, 4),
            "disposition": disposition,
            "disposition_label": disposition_label,
            "image1": {
                "bbox": face1["bbox"],
                "landmarks": face1["landmarks"],
                "confidence": face1["confidence"],
                "sharpness": face1["sharpness_score"],
                "aligned_crop_base64": face1["aligned_crop_base64"],
                "embedding_preview": face1["embedding_summary"]["preview"]
            },
            "image2": {
                "bbox": face2["bbox"],
                "landmarks": face2["landmarks"],
                "confidence": face2["confidence"],
                "sharpness": face2["sharpness_score"],
                "aligned_crop_base64": face2["aligned_crop_base64"],
                "embedding_preview": face2["embedding_summary"]["preview"]
            },
            "combined_latency_ms": round(diag1["latency_profile_ms"]["total_pipeline_ms"] + diag2["latency_profile_ms"]["total_pipeline_ms"], 2)
        }

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
    def process_sighting_video(
        self,
        video_path: str,
        sample_fps: float = 1.0,
        max_sampled_frames: int = 60,
        cluster_threshold: float = 0.65
    ) -> Dict[str, Any]:
        """
        Processes video evidence for FR-08 (Video Support):
        1. Opens video container and extracts duration, fps, resolution, total frames.
        2. Samples keyframes at controlled intervals (e.g. 1 frame/sec, capped at max_sampled_frames).
        3. Detects faces in sampled frames and computes SFace 128-D normalized embeddings.
        4. Deduplicates repeated detections across frames into identity tracklet clusters.
        5. Selects the highest-quality exemplar detection for each cluster while preserving
           all timestamp occurrences for forensic timeline verification.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Unable to decode video stream from {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        if fps <= 0 or math.isnan(fps):
            fps = 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration_sec = round(total_frames / fps, 2) if total_frames > 0 else 0.0

        # Calculate sampling step interval
        step = max(1, int(round(fps / sample_fps)))
        if total_frames > 0 and (total_frames // step) > max_sampled_frames:
            step = max(1, total_frames // max_sampled_frames)

        raw_detections = []
        sampled_count = 0
        current_frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if current_frame_idx % step == 0:
                sampled_count += 1
                timestamp_sec = round(current_frame_idx / fps, 3)
                minutes = int(timestamp_sec // 60)
                seconds = timestamp_sec % 60
                timestamp_str = f"{minutes:02d}:{seconds:06.3f}"

                faces = self.detect_faces(frame)
                for face in faces:
                    emb = self.extract_embedding(frame, face["raw_face"])

                    # Generate crop thumbnail
                    bx, by, bw, bh = face["bbox"]
                    fh, fw = frame.shape[:2]
                    crop = frame[max(0, by):min(fh, by + bh), max(0, bx):min(fw, bx + bw)]
                    thumb_b64 = ""
                    if crop.size > 0:
                        try:
                            _, buf = cv2.imencode(".jpg", crop)
                            thumb_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('ascii')}"
                        except Exception:
                            thumb_b64 = ""

                    raw_detections.append({
                        "frame_index": current_frame_idx,
                        "timestamp_sec": timestamp_sec,
                        "timestamp_str": timestamp_str,
                        "bbox": face["bbox"],
                        "landmarks": face["landmarks"],
                        "confidence": face["confidence"],
                        "embedding": emb,
                        "thumbnail_b64": thumb_b64
                    })

                if sampled_count >= max_sampled_frames:
                    break

            current_frame_idx += 1

        cap.release()

        # Intra-video tracklet clustering and temporal deduplication
        clusters = []
        for det in raw_detections:
            emb = det["embedding"]
            best_cluster = None
            best_sim = -1.0

            for c in clusters:
                sim = self.cosine_similarity(emb, c["exemplar"]["embedding"])
                if sim > best_sim:
                    best_sim = sim
                    best_cluster = c

            if best_cluster is not None and best_sim >= cluster_threshold:
                best_cluster["occurrences"].append({
                    "frame_index": det["frame_index"],
                    "timestamp_sec": det["timestamp_sec"],
                    "timestamp_str": det["timestamp_str"],
                    "confidence": det["confidence"],
                    "bbox": det["bbox"]
                })
                # If new detection has higher confidence, promote as exemplar
                if det["confidence"] > best_cluster["exemplar"]["confidence"]:
                    best_cluster["exemplar"] = det
            else:
                cluster_id = len(clusters) + 1
                clusters.append({
                    "cluster_id": cluster_id,
                    "exemplar": det,
                    "occurrences": [{
                        "frame_index": det["frame_index"],
                        "timestamp_sec": det["timestamp_sec"],
                        "timestamp_str": det["timestamp_str"],
                        "confidence": det["confidence"],
                        "bbox": det["bbox"]
                    }]
                })

        # Format tracklet summaries
        tracklets = []
        for idx, c in enumerate(clusters):
            ex = c["exemplar"]
            occ = c["occurrences"]
            timestamps = [o["timestamp_str"] for o in occ]
            tracklets.append({
                "tracklet_id": idx,
                "exemplar_frame_index": ex["frame_index"],
                "exemplar_timestamp_sec": ex["timestamp_sec"],
                "exemplar_timestamp_str": ex["timestamp_str"],
                "confidence": ex["confidence"],
                "bbox": ex["bbox"],
                "landmarks": ex["landmarks"],
                "embedding": ex["embedding"],
                "thumbnail_b64": ex.get("thumbnail_b64", ""),
                "exemplar_thumbnail_b64": ex.get("thumbnail_b64", ""),
                "detection_count": len(occ),
                "total_sightings_in_video": len(occ),
                "all_timestamps": timestamps,
                "first_seen": occ[0]["timestamp_str"],
                "last_seen": occ[-1]["timestamp_str"],
                "first_seen_timestamp": occ[0]["timestamp_str"],
                "last_seen_timestamp": occ[-1]["timestamp_str"],
                "duration_span_sec": round(occ[-1]["timestamp_sec"] - occ[0]["timestamp_sec"], 3),
                "occurrences": [
                    {
                        "frame_idx": o["frame_index"],
                        "timestamp_seconds": o["timestamp_sec"],
                        "timestamp_formatted": o["timestamp_str"],
                        "confidence": o["confidence"],
                        "bbox": o["bbox"]
                    }
                    for o in occ
                ]
            })

        return {
            "video_metadata": {
                "duration_seconds": duration_sec,
                "fps": round(fps, 2),
                "resolution": f"{width}x{height}",
                "width": width,
                "height": height,
                "total_frames": total_frames,
                "sampled_frames_count": sampled_count,
                "total_face_detections": len(raw_detections),
                "unique_tracklets_count": len(tracklets)
            },
            "tracklets": tracklets
        }

# Global singleton instance
face_engine = FaceEngine()
