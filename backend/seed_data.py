import sys
import os
import json
import shutil
from pathlib import Path
import cv2
import numpy as np

# Ensure prototype root is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database import init_db, get_db
from backend.auth import hash_password
from backend.config import REFERENCES_DIR, SIGHTINGS_DIR, BASE_DIR
from backend.face_engine import face_engine

def seed_database(reset: bool = False):
    if reset:
        print("[Seed] Resetting database tables...")
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = OFF;")
            for tbl in ["notifications", "reviews", "candidate_matches", "sighting_media", "sightings", "reference_images", "cases", "audit_logs", "users"]:
                cursor.execute(f"DROP TABLE IF EXISTS {tbl};")
            cursor.execute("PRAGMA foreign_keys = ON;")

    print("[Seed] Initializing database schema...")
    init_db()

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Seed Users
        cursor.execute("SELECT COUNT(*) AS cnt FROM users;")
        if cursor.fetchone()["cnt"] == 0:
            print("[Seed] Seeding authorized staff users...")
            users = [
                ("admin", "admin@missingpersons.gov.in", hash_password("admin123"), "System Administrator", "ADM-001", "admin"),
                ("investigator", "investigator@missingpersons.gov.in", hash_password("investigator123"), "Senior Lead Investigator", "INV-1001", "investigator"),
                ("detective_chen", "chen.s@missingpersons.gov.in", hash_password("investigator123"), "Sarah Chen (Senior Detective)", "INV-7809", "investigator"),
            ]
            cursor.executemany("""
                INSERT INTO users (username, email, password_hash, full_name, badge_number, role, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, users)
            print("[Seed] Staff accounts seeded: admin, investigator, detective_chen")

        # 2. Check if cases exist
        cursor.execute("SELECT COUNT(*) AS cnt FROM cases;")
        if cursor.fetchone()["cnt"] == 0:
            print("[Seed] Seeding missing-person cases and authorized reference photos...")

            # Source test images
            sample_dir = BASE_DIR / "sample_data"
            img1_path = sample_dir / "sample_face.jpg"
            img2_path = sample_dir / "sample_messi.jpg"

            if not img1_path.exists() or not img2_path.exists():
                print("[Seed] Sample images not found, skipping photo enrollment seeding.")
                return

            # Case 1: Arunachalam Murugan
            cursor.execute("""
                INSERT INTO cases (
                    reference_no, full_name, age, gender, last_seen_date, last_seen_time,
                    last_seen_location, latitude, longitude, status, assigned_investigator_id,
                    identifying_features, clothing_description, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', 2, ?, ?, ?)
            """, (
                "MP-2026-001", "Arunachalam Murugan", 28, "Male", "2026-09-28", "14:30",
                "Chennai Central Railway Station, Tamil Nadu", 13.0827, 80.2707,
                "Scar near left eyebrow, brown eyes, height 5ft 9in",
                "Dark blue denim jacket and grey trousers",
                "Case enrolled following missing complaint filed at Central Railway Police Post."
            ))
            case1_id = cursor.lastrowid

            # Save reference photo 1
            ref1_stored = f"ref_{case1_id}_primary.jpg"
            ref1_dest = REFERENCES_DIR / ref1_stored
            shutil.copyfile(img1_path, ref1_dest)

            img1_mat = cv2.imread(str(img1_path))
            val1 = face_engine.validate_reference_photo(img1_mat)

            cursor.execute("""
                INSERT INTO reference_images (
                    case_id, file_path, original_filename, file_size, mime_type,
                    face_detected, bbox_json, landmarks_json, embedding_json, model_name, model_version
                ) VALUES (?, ?, 'reference_portrait_01.jpg', ?, 'image/jpeg', 1, ?, ?, ?, 'YuNet + SFace', 'v1.0-onnx')
            """, (
                case1_id, f"storage/references/{ref1_stored}", os.path.getsize(img1_path),
                json.dumps(val1["bbox"]), json.dumps(val1["landmarks"]), json.dumps(val1["embedding"])
            ))
            ref1_id = cursor.lastrowid

            # Case 2: Leo K. Martinez
            cursor.execute("""
                INSERT INTO cases (
                    reference_no, full_name, age, gender, last_seen_date, last_seen_time,
                    last_seen_location, latitude, longitude, status, assigned_investigator_id,
                    identifying_features, clothing_description, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', 2, ?, ?, ?)
            """, (
                "MP-2026-002", "Leo K. Martinez", 36, "Male", "2026-10-02", "19:15",
                "Marina Beach Promenade, Chennai, Tamil Nadu", 13.0499, 80.2824,
                "Short beard, light brown eyes, sports tattoo on right forearm",
                "Maroon polo t-shirt, beige shorts and black sports shoes",
                "Reported missing during evening jog near lighthouse."
            ))
            case2_id = cursor.lastrowid

            # Save reference photo 2
            ref2_stored = f"ref_{case2_id}_primary.jpg"
            ref2_dest = REFERENCES_DIR / ref2_stored
            shutil.copyfile(img2_path, ref2_dest)

            img2_mat = cv2.imread(str(img2_path))
            val2 = face_engine.validate_reference_photo(img2_mat)

            cursor.execute("""
                INSERT INTO reference_images (
                    case_id, file_path, original_filename, file_size, mime_type,
                    face_detected, bbox_json, landmarks_json, embedding_json, model_name, model_version
                ) VALUES (?, ?, 'reference_portrait_02.jpg', ?, 'image/jpeg', 1, ?, ?, ?, 'YuNet + SFace', 'v1.0-onnx')
            """, (
                case2_id, f"storage/references/{ref2_stored}", os.path.getsize(img2_path),
                json.dumps(val2["bbox"]), json.dumps(val2["landmarks"]), json.dumps(val2["embedding"])
            ))
            ref2_id = cursor.lastrowid

            print("[Seed] Enrolled cases MP-2026-001 and MP-2026-002 with facial embeddings.")

            # 3. Seed Realistic Sightings & Candidate Matches
            print("[Seed] Generating realistic public sightings and computing AI matches...")

            # Sighting 1: Sighting of Case 1 (Arunachalam Murugan)
            # Create a realistic sighting image by cropping & adjusting brightness
            h1, w1 = img1_mat.shape[:2]
            sight1_mat = img1_mat[int(h1*0.04):int(h1*0.96), int(w1*0.04):int(w1*0.96)]
            sight1_mat = cv2.resize(sight1_mat, (w1, h1))
            sight1_mat = cv2.convertScaleAbs(sight1_mat, alpha=0.94, beta=8)

            sight1_stored = "sight_1_tambaram.jpg"
            cv2.imwrite(str(SIGHTINGS_DIR / sight1_stored), sight1_mat)

            cursor.execute("""
                INSERT INTO sightings (
                    receipt_no, sighting_date, sighting_time, location_name,
                    latitude, longitude, description, reporter_name, reporter_phone,
                    consent_given, status
                ) VALUES (?, '2026-10-08', '11:45', 'Tambaram Railway Junction, Platform 3', 12.9249, 80.1000,
                          'Saw a person matching the general description standing near tea stall on Platform 3.',
                          'Ramesh V.', '+91 98401 23456', 1, 'pending_review')
            """, ("STG-2026-0001",))
            sight1_id = cursor.lastrowid

            sight1_faces = face_engine.process_sighting_image(sight1_mat)
            cursor.execute("""
                INSERT INTO sighting_media (
                    sighting_id, file_path, original_filename, faces_detected_count, faces_metadata_json
                ) VALUES (?, ?, 'sighting_photo_tambaram.jpg', ?, ?)
            """, (
                sight1_id, f"storage/sightings/{sight1_stored}", len(sight1_faces),
                json.dumps([{"bbox": f["bbox"], "confidence": f["confidence"]} for f in sight1_faces])
            ))

            # Match sighting 1 against enrolled cases
            enrolled = [
                {"case_id": case1_id, "reference_image_id": ref1_id, "reference_no": "MP-2026-001", "full_name": "Arunachalam Murugan", "embedding": val1["embedding"]},
                {"case_id": case2_id, "reference_image_id": ref2_id, "reference_no": "MP-2026-002", "full_name": "Leo K. Martinez", "embedding": val2["embedding"]}
            ]
            ranked1 = face_engine.rank_candidates(sight1_faces[0]["embedding"], enrolled, top_k=2)

            for item in ranked1:
                cursor.execute("""
                    INSERT INTO candidate_matches (
                        sighting_id, sighting_face_index, case_id, reference_image_id,
                        similarity_score, rank, model_version, status
                    ) VALUES (?, 0, ?, ?, ?, ?, ?, 'requires_human_review')
                """, (
                    sight1_id, item["case_id"], item["reference_image_id"],
                    item["similarity_score"], item["rank"], item["model_version"]
                ))

            # Sighting 2: Sighting of Case 2 (Leo K. Martinez)
            h2, w2 = img2_mat.shape[:2]
            sight2_mat = img2_mat[int(h2*0.03):int(h2*0.97), int(w2*0.03):int(w2*0.97)]
            sight2_mat = cv2.resize(sight2_mat, (w2, h2))
            sight2_mat = cv2.convertScaleAbs(sight2_mat, alpha=0.96, beta=5)

            sight2_stored = "sight_2_koyambedu.jpg"
            cv2.imwrite(str(SIGHTINGS_DIR / sight2_stored), sight2_mat)

            cursor.execute("""
                INSERT INTO sightings (
                    receipt_no, sighting_date, sighting_time, location_name,
                    latitude, longitude, description, reporter_name, reporter_phone,
                    consent_given, status
                ) VALUES (?, '2026-10-09', '09:20', 'Koyambedu Wholesale Market, Gate 4', 13.0694, 80.1948,
                          'Individual spotted carrying groceries near flower market area.',
                          'Deepa Shankar', '+91 94440 98765', 1, 'pending_review')
            """, ("STG-2026-0002",))
            sight2_id = cursor.lastrowid

            sight2_faces = face_engine.process_sighting_image(sight2_mat)
            cursor.execute("""
                INSERT INTO sighting_media (
                    sighting_id, file_path, original_filename, faces_detected_count, faces_metadata_json
                ) VALUES (?, ?, 'sighting_koyambedu.jpg', ?, ?)
            """, (
                sight2_id, f"storage/sightings/{sight2_stored}", len(sight2_faces),
                json.dumps([{"bbox": f["bbox"], "confidence": f["confidence"]} for f in sight2_faces])
            ))

            ranked2 = face_engine.rank_candidates(sight2_faces[0]["embedding"], enrolled, top_k=2)
            for item in ranked2:
                cursor.execute("""
                    INSERT INTO candidate_matches (
                        sighting_id, sighting_face_index, case_id, reference_image_id,
                        similarity_score, rank, model_version, status
                    ) VALUES (?, 0, ?, ?, ?, ?, ?, 'requires_human_review')
                """, (
                    sight2_id, item["case_id"], item["reference_image_id"],
                    item["similarity_score"], item["rank"], item["model_version"]
                ))

            # 4. Seed Audit Logs
            print("[Seed] Creating audit log records...")
            cursor.execute("""
                INSERT INTO audit_logs (actor_name, action, resource_type, resource_id, details_json)
                VALUES ('System Administrator', 'SYSTEM_INITIALIZED', 'system', 'root', '{\"version\": \"1.0.0\"}')
            """)
            cursor.execute("""
                INSERT INTO audit_logs (actor_name, action, resource_type, resource_id, details_json)
                VALUES ('Senior Lead Investigator', 'CASE_CREATED', 'cases', '1', '{\"reference_no\": \"MP-2026-001\"}')
            """)
            cursor.execute("""
                INSERT INTO audit_logs (actor_name, action, resource_type, resource_id, details_json)
                VALUES ('Senior Lead Investigator', 'CASE_CREATED', 'cases', '2', '{\"reference_no\": \"MP-2026-002\"}')
            """)
            cursor.execute("""
                INSERT INTO audit_logs (actor_name, action, resource_type, resource_id, details_json)
                VALUES ('Public Reporter', 'SIGHTING_SUBMITTED', 'sightings', '1', '{\"receipt_no\": \"STG-2026-0001\"}')
            """)
            cursor.execute("""
                INSERT INTO audit_logs (actor_name, action, resource_type, resource_id, details_json)
                VALUES ('Public Reporter', 'SIGHTING_SUBMITTED', 'sightings', '2', '{\"receipt_no\": \"STG-2026-0002\"}')
            """)

            # 5. Seed Investigator Notifications
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, category, link_url)
                VALUES (2, 'High Similarity Lead: Sighting STG-2026-0001', 'High confidence match (0.94) detected for Case MP-2026-001 at Tambaram. Review required.', 'match_alert', '/review/1')
            """)
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, category, link_url)
                VALUES (2, 'High Similarity Lead: Sighting STG-2026-0002', 'High confidence match (0.91) detected for Case MP-2026-002 at Koyambedu. Review required.', 'match_alert', '/review/2')
            """)

            print("[Seed] Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
