# AI-Based Missing Person Identification and Tracking Using Facial Recognition and Computer Vision

**Department of Computer Science and Engineering**  
**Professional Training I**  
- **Student:** S. Praveen Kumar (Registration No: 44111131)  
- **Faculty Guide:** Dr. S. Gayathri, Ph.D., Associate Professor, CSE  

---

## 1. Project Overview

This prototype implements an investigation-support platform designed to assist in locating missing persons. Authorized officers register cases with personal details and authorized reference photos. Public users submit potential sightings with photos, location, and timestamp metadata. 

An AI pipeline powered by OpenCV **YuNet** (DNN face detection) and **SFace** (MobileFaceNet deep representation) detects faces, extracts 128-dimensional normalized biometric embeddings, and ranks candidates using cosine similarity. Crucially, the platform adheres to responsible AI governance: **AI outputs are ranking signals, not autonomous identity confirmations.** All candidate matches require human investigator review and recorded rationale.

---

## 2. Six Core Modules

| Module | Name | Key Functionality |
|---|---|---|
| **Module 1** | **Authentication & RBAC** | Secure authentication, bcrypt password hashing, signed JWT tokens, role-based endpoint authorization (`investigator`, `admin`, `public`), and immutable audit logging. |
| **Module 2** | **Case Registration** | Case profile enrollment (`MP-2026-xxx`), last-seen date/location metadata, reference photo ingestion with automated single-face validation. |
| **Module 3** | **Face Processing** | Deep learning face detection (YuNet), landmark alignment, 128-D vector embedding extraction (SFace), bounding-box coordinate tracking. |
| **Module 4** | **Sighting Portal** | Public sighting intake with image upload, location pin selection (interactive map), observation notes, and privacy-preserving receipt issuance (`STG-2026-xxxx`). |
| **Module 5** | **AI Matching Engine** | Vector similarity computation using cosine distance, Top-K candidate ranking, and calibrated confidence tiers (`High ≥ 0.70`, `Moderate ≥ 0.50`). |
| **Module 6** | **Review & Tracking** | Side-by-side comparative evidence inspection, mandatory investigator rationale adjudication (`verified`, `escalated`, `request_more_info`, `rejected`), status workflow, and interactive GIS map. |

---

## 3. Technology Stack

- **Backend:** Python 3.12, FastAPI (REST API), Uvicorn (ASGI server)
- **Computer Vision & AI:** OpenCV 5.0+, YuNet (`face_detection_yunet_2023mar.onnx`), SFace (`face_recognition_sface_2021dec.onnx`)
- **Database:** SQLite 3 (relational schema, vector metadata, audit logs)
- **Security:** Bcrypt password hashing, Python-Jose (JWT Bearer authentication)
- **Frontend:** Responsive Single-Page Application (Tailwind CSS, Leaflet.js interactive maps, vanilla JavaScript)
- **Testing:** Pytest (16 automated unit & integration tests)

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

---

## 5. Pre-Configured Demo Accounts

| Role | Username | Password | Full Name / Badge |
|---|---|---|---|
| **Lead Investigator** | `investigator` | `investigator123` | S. Praveen Kumar (Badge: `INV-44111131`) |
| **Administrator** | `admin` | `admin123` | Dr. S. Gayathri (Badge: `ADM-001`) |
| **Senior Detective** | `detective_chen` | `investigator123` | Sarah Chen (Badge: `INV-7809`) |
| **Public User** | *(No login required)* | — | Anonymous public submission |

*Note: You can easily switch roles using the quick role switcher in the top header.*

---

## 6. Running Automated Tests

To run the complete automated test suite (face engine, authentication, API routes, RBAC boundaries):

```bash
python -m pytest tests/ -v
```

All 16 test cases verify:
- YuNet face detection and bounding-box accuracy.
- Strict single-face reference photo validation (rejects 0 faces and ambiguous faces).
- 128-dimensional embedding normalization and cosine ranking math.
- Public sighting submission receipt creation without data leakage.
- RBAC boundary enforcement (unauthenticated users blocked from private case data).
- Investigator review adjudication with mandatory rationale.

---

## 7. AI Governance & Privacy Controls

1. **Human-in-the-Loop Adjudication:** No sighting is automatically confirmed as a match. Officers must manually review side-by-side imagery and provide written justification.
2. **Confidentiality:** Public reporters receive only an opaque tracking receipt (`STG-2026-xxxx`). They cannot view match percentages, registered case details, or confidential records.
3. **Audit Trail:** Every login, case creation, photo enrollment, and review disposition is immutably logged with actor identity, timestamp, and metadata.
4. **Calibrated Thresholds:** Operating points are empirically evaluated: cosine similarity $\ge 0.70$ flags high-priority leads, while $\ge 0.50$ queues standard reviews.
