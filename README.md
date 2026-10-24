# AI-Based Missing Person Identification and Tracking System
**Computer Vision & Biometric Surveillance Intelligence Platform**

An end-to-end investigation-support system utilizing deep convolutional neural networks, biometric representation vectors, and automated surveillance stream processing for locating missing persons.

---

## 1. Project Overview

This platform implements an enterprise-grade investigation-support platform designed to assist law enforcement agencies in locating missing persons. Authorized officers register missing person cases with validated facial reference photos, descriptive metadata, and last-seen coordinates. The public portal enables citizen sightings with photo upload, geolocation pin placement, and tamper-resistant tracking receipt issuance.

An AI pipeline powered by OpenCV **YuNet** (DNN face detection) and **SFace** (MobileFaceNet deep representation) detects faces, extracts 128-dimensional normalized biometric embeddings, and ranks candidates using cosine similarity. Crucially, the platform adheres to responsible AI governance: **AI outputs are ranking signals, not autonomous identity confirmations.** All candidate matches require human investigator review and recorded rationale.

---

## 2. Eight Core Production Modules

| Module | Name | Key Functionality |
|---|---|---|
| **Module 1** | **Authentication & RBAC** | Secure authentication, bcrypt password hashing, signed JWT tokens, role-based endpoint authorization (`investigator`, `admin`, `public`), and immutable audit logging. |
| **Module 2** | **Case Registration** | Case profile enrollment (`MP-2026-xxx`), last-seen date/location metadata, reference photo ingestion with automated single-face validation. |
| **Module 3** | **Face Processing Engine** | Deep learning face detection (YuNet), landmark alignment, 128-D vector embedding extraction (SFace), bounding-box coordinate tracking. |
| **Module 4** | **Public Sighting Portal** | Citizen sighting intake with image upload, location pin selection (interactive map), observation notes, and privacy-preserving receipt issuance (`STG-2026-xxxx`). |
| **Module 5** | **AI Matching Engine** | Vector similarity computation using cosine distance, Top-K candidate ranking, and calibrated confidence tiers (`High ≥ 0.70`, `Moderate ≥ 0.50`). |
| **Module 6** | **Review & Tracking Workflow** | Side-by-side comparative evidence inspection, mandatory investigator rationale adjudication (`verified`, `escalated`, `request_more_info`, `rejected`), status workflow, and interactive GIS map. |
| **Module 7** | **Surveillance Stream & CCTV Alerting** | Automated CCTV camera feed ingestion, real-time video frame face extraction, live multi-target watchlist scanning, instant alert dispatch, and alert management. |
| **Module 8** | **Forensic Video Ingestion & Timeline Analysis** | Multi-format forensic video decoding, adaptive keyframe sampling, chronological timeline reconstruction, spatial sighting trajectory mapping, and forensic summary reporting. |

---

## 3. Technology Stack

- **Backend:** Python 3.12, FastAPI (REST API), Uvicorn (ASGI server)
- **Computer Vision & AI:** OpenCV 5.0+, YuNet (`face_detection_yunet_2023mar.onnx`), SFace (`face_recognition_sface_2021dec.onnx`)
- **Database:** SQLite 3 (relational schema, vector metadata, audit logs, CCTV nodes, surveillance alerts)
- **Security:** Bcrypt password hashing, Python-Jose (JWT Bearer authentication)
- **Evidence & Dossiers:** Pillow-powered Biometric Forensic Examination Certificates and AMBER Alert Posters
- **Frontend:** Responsive Single-Page Application (Tailwind CSS, Leaflet.js interactive maps, vanilla JavaScript)
- **Mobile Field Client:** Cross-platform Flutter application with tactical dark UI theme (`mobile_app/`)
- **Testing:** Pytest (78 automated unit, integration, and security tests across 11 test suites)

---

## 4. Quick Start Guide

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run Application & Auto-Seeder
```bash
python run.py
```

### Step 3: Access Web Application
- **Web Portal:** Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
- **Interactive Swagger API Docs:** Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
- **Mobile Field App (Optional):**
  ```bash
  cd mobile_app
  flutter run
  ```

---

## 5. Pre-Configured Demo Accounts

| Role | Username | Password | Full Name / Badge |
|---|---|---|---|
| **Lead Investigator** | `investigator` | `investigator123` | Senior Lead Investigator (Badge: `INV-1001`) |
| **Administrator** | `admin` | `admin123` | System Administrator (Badge: `ADM-001`) |
| **Senior Detective** | `detective_chen` | `investigator123` | Detective Chen (Badge: `INV-7809`) |
| **Public User** | *(No login required)* | — | Anonymous public submission |

*Note: You can easily switch roles using the quick role switcher in the top header.*

---

## 6. Running Automated Tests

To run the complete automated test suite (face engine, authentication, API routes, RBAC boundaries, video forensics, surveillance feeds, forensic certificates):

```bash
python -m pytest tests/ -v
```

All 78 test cases across 11 test suites verify:
- YuNet face detection and bounding-box accuracy.
- Strict single-face reference photo validation (rejects 0 faces and ambiguous faces).
- 128-dimensional embedding normalization and cosine ranking math.
- Public sighting submission receipt creation without data leakage.
- RBAC boundary enforcement (unauthenticated users blocked from private case data).
- Investigator review adjudication with mandatory rationale.
- Live CCTV camera feed registration, multi-target watchlist scanning, and real-time alert generation.
- Forensic video upload, frame sampling, timeline synthesis, and sighting trajectory tracing.
- Tamper-evident Biometric Forensic Examination Certificate and AMBER Alert Poster generation.


---

## 7. AI Governance & Privacy Controls

1. **Human-in-the-Loop Adjudication:** No sighting is automatically confirmed as a match. Officers must manually review side-by-side imagery and provide written justification.
2. **Confidentiality:** Public reporters receive only an opaque tracking receipt (`STG-2026-xxxx`). They cannot view match percentages, registered case details, or confidential records.
3. **Audit Trail:** Every login, case creation, photo enrollment, and review disposition is immutably logged with actor identity, timestamp, and metadata.
4. **Calibrated Thresholds:** Operating points are empirically evaluated: cosine similarity $\ge 0.70$ flags high-priority leads, while $\ge 0.50$ queues standard reviews.
