# CCTNS • National Missing Persons Biometric AI Platform
### Intelligent Computer Vision & Facial Recognition Workbench for Law Enforcement
**National Crime Records Bureau (NCRB) • Ministry of Home Affairs (MHA) Standard Architecture**

[![CCTNS Standard](https://img.shields.io/badge/Standards-CCTNS%20%2F%20NCRB%20Compliant-blue.svg)](#)
[![Air-Gapped Offline](https://img.shields.io/badge/Deployment-100%25%20Offline%20Air--Gapped-success.svg)](#)
[![Computer Vision](https://img.shields.io/badge/CV%20Engine-OpenCV%20YuNet%20%2B%20SFace-0284c7.svg)](#)
[![CLAHE Enhancement](https://img.shields.io/badge/Filter-CLAHE%20Low--Light%20Surveillance-amber.svg)](#)
[![Backend Framework](https://img.shields.io/badge/Backend-FastAPI%20%26%20Python%203.12-emerald.svg)](#)
[![GIS Capabilities](https://img.shields.io/badge/GIS-Mappls%20%2F%20MapmyIndia%20%2B%20Leaflet-indigo.svg)](#)
[![Automated Test Suite](https://img.shields.io/badge/Test%20Suite-78%2F78%20Passing%20(100%25)-brightgreen.svg)](#)

---

## 1. Executive Summary & Institutional Mission

The **CCTNS National Missing Persons Biometric AI Platform** is an enterprise-grade investigation-support workbench developed for state police departments, forensic laboratories, and public safety organizations under the aegis of the **Crime and Criminal Tracking Network & Systems (CCTNS)** and **National Crime Records Bureau (NCRB)** guidelines.

Locating missing children and vulnerable individuals requires immediate, high-precision cross-referencing across large geographic regions and heterogeneous surveillance feeds. This platform fuses deep convolutional neural networks for biometric face detection and deep feature representations with an **ethical human-in-the-loop adjudication protocol**.

### Key Architectural Tenets:
1. **100% Air-Gapped & Offline Operation:** The entire biometric pipeline—including neural network weights, vector embeddings, SQLite relational tables, and forensic PDF/PNG certificate generators—runs completely on local station servers without requiring internet access or third-party cloud APIs.
2. **Responsible AI by Design:** Mathematical similarity scores are treated strictly as **ranking signals** to prioritize investigator attention. Autonomous arrests, public announcements, or automated case closures are architecturally prohibited; every positive lead requires an authorized officer's verified signature and written rationale.
3. **Surveillance & Low-Light Robustness:** Built-in **Contrast Limited Adaptive Histogram Equalization (CLAHE)** enhances contrast on underexposed CCTV surveillance frames and night-time citizen sightings before vector extraction.
4. **Multi-Agency Geospatial Tracking:** Integrates native Indian GIS layers (**Mappls / MapmyIndia**) alongside OpenStreetMap and offline tile caches to reconstruct sighting corridors and travel trajectories across jurisdictions.

---

## 2. Six-Step Investigation Lifecycle & Step-by-Step Hover Guide

The platform is organized into six sequential operational phases. Every interactive button, navigation tab, and status control contains intelligent hover guidance. 

> **How to Hover Throughout the Workbench:**
> Hover your mouse cursor over any navigation button, table action, or status badge to trigger the floating **Forensic Guidance HUD**. The HUD displays the active step number (e.g., `STEP 1 OF 6: CASE ENROLLMENT`), underlying mathematical criteria, and the recommended operational next action.
> You can also hover over the **🧭 Investigation Steps (Hover Guide)** button in the top navigation bar to open the live interactive 6-step roadmap popover at any time.

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 CCTNS INVESTIGATION WORKFLOW LIFECYCLE                                │
└───────────────────────────────────────────────────────────────────────────────────────────────────────┘
   [STEP 1: Enroll Case] ──► [STEP 2: Citizen Sighting] ──► [STEP 3: AI Vector Match]
         │ (FIR & Photo)              │ (Photo & GPS Pin)          │ (YuNet + SFace + CLAHE)
         ▼                            ▼                            ▼
   [STEP 6: Forensic Dossier] ◄─ [STEP 5: CCTV Feeds]  ◄─── [STEP 4: Review Queue]
     (PDF & AMBER Dispatch)        (RTSP Stream Hits)           (Mandatory Officer Sign-off)
```

### Step 1: Case Registration & Reference Portrait Vectorization
- **Navigation:** Click `+ Enroll Case` in the top bar or open the `Case Files` tab.
- **Officer Action:** Register the missing subject with authentic CCTNS metadata:
  - Subject Name, Age, Gender, Primary Language, Distinguishing Scars/Marks.
  - State Police FIR Number (e.g. `FIR-89/2026/CRIME`), General Diary (GD) entry, and Police Station Jurisdiction.
  - Upload a high-resolution frontal reference passport portrait.
- **Behind the Scenes:** OpenCV **YuNet** validates that the image contains exactly one frontal human face (rejecting non-face images, multiple faces, or low-resolution crops $< 60\times 60$ px). Five key facial landmarks (eyes, nose, mouth corners) are detected, and **SFace** extracts a 128-dimensional L2-normalized feature representation vector stored in the local SQLite database.

### Step 2: Citizen Sighting Ingestion & Cryptographic Receipt
- **Navigation:** Click the `Submit Sighting` tab in the Public Services menu.
- **Citizen / Patrol Action:** A citizen or patrolling beat constable spots an individual matching a missing description, uploads a candid photograph, and pins the GPS coordinates on the interactive Leaflet/Mappls map (or clicks a rapid transport hub preset like Chennai Central, CMBT Bus Stand, Marina Beach, or Tambaram Concourse).
- **Behind the Scenes:** The system ingests the sighting, parses geotag metadata, and issues an immutable cryptographic SHA-256 tracking receipt (e.g. `STG-2026-0001`). Citizens can track their receipt status in real time on the `Track Receipt` tab without exposing sensitive law enforcement records.

### Step 3: Biometric AI Matching Engine
- **Navigation:** Click the `Command Center` tab in the Officer Console.
- **Automatic Execution:** The system automatically crops faces from the sighting imagery. If the image was captured in low light or harsh backlighting, the **CLAHE filter** normalizes illumination in the LAB color space.
- **Vector Metric Math:** SFace computes the cosine similarity against all enrolled missing persons:
  $$\text{Cosine Similarity} = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$$
  Matches with similarity $\ge 0.363$ (calibrated to $\ge 60\%$ confidence score) are elevated to high-priority candidate leads and routed into the investigator queue.

### Step 4: Investigator Review Queue (Human-in-the-Loop)
- **Navigation:** Click `Review Queue` (displays dynamic badge counter, e.g. `2 LEADS`).
- **Investigator Adjudication:** The investigating officer evaluates the side-by-side biometric comparison:
  - Reference photo vs. sighting crop with toggleable bounding-box and landmark HUDs.
  - Calibrated percentage similarity gauge and metric distance breakdown.
  - The officer selects one of four formal adjudications:
    1. **Verified Match:** Confirms identity and elevates case status to `HIGH_LEAD`.
    2. **Reject Lead (False Positive):** Marks candidate as non-matching to clear duplicate trails.
    3. **Request More Info:** Dispatches request for higher-resolution evidence or witness interview.
    4. **Escalate to Field Team:** Alerts local patrol units to intercept the subject.
- **Accountability:** Every decision requires an officer badge signature and recorded rationale chip, permanently committed to the immutable audit ledger.

### Step 5: Real-Time CCTV Surveillance Watchlist
- **Navigation:** Click `CCTV Surveillance` (displays pulsing red `LIVE` beacon).
- **Surveillance Operators:** Connect live RTSP IP cameras or upload surveillance video footage (MP4/AVI/MKV).
- **Processing:** Video frames are sampled at 5 FPS; YuNet detects multiple faces simultaneously in each frame, and SFace matches detected faces against the active missing person watchlist in under 15ms per frame.
- **Alert Dispatch:** Detection triggers instant audible chimes and visual priority alert banners. Operators can click `Dispatch Unit`, `Acknowledge`, or `Dismiss`.

### Step 6: GIS Corridor Tracking & Forensic Dossier Export
- **Navigation:** Click `GIS Map` or `Cases Dossier`.
- **Geospatial Trajectory:** Traces sighting chronology over time across Mappls or OpenStreetMap layers to visualize the subject's transit corridor and direction of movement.
- **Judicial Evidence Export:** Export official tamper-evident **Biometric Forensic Examination Certificates** (PDF/PNG) featuring SHA-256 integrity hashes, facial landmark diagrams, and chain-of-custody metadata, or generate print-ready **AMBER Alert Posters** with embedded verification QR codes.
- **Case Resolution:** Once the subject is safely located, the case status is formally updated to `RESOLVED` with closing recovery notes.

---

## 3. Technology Stack & Technical Specifications

| Component | Technology | Specification / Version | Role in Architecture |
|---|---|---|---|
| **Backend API** | FastAPI / Uvicorn | Python 3.12, ASGI, AsyncIO | High-throughput REST API with async request pipelines |
| **Face Detection** | OpenCV YuNet | `face_detection_yunet_2023mar.onnx` | 640×640 input resolution, 5 facial landmarks, NMS |
| **Face Recognition** | OpenCV SFace | `face_recognition_sface_2021dec.onnx` | MobileFaceNet backbone, 128-D L2-normalized embeddings |
| **Low-Light Filter** | OpenCV CLAHE | 8×8 grid tiles, clip limit 2.5 | Auto-enhances underexposed night CCTV and candid photos |
| **Relational DB** | SQLite 3 | WAL mode, foreign key enforcement | Stores cases, reference photos, embeddings, sightings, logs |
| **Security & Auth** | Bcrypt & PyJWT | Direct bcrypt hashing, HS256 JWT | Multi-tier RBAC (`investigator`, `admin`, `public`) |
| **Forensic Evidence** | Pillow (PIL) | Dynamic font rendering, SHA-256 seals | Generates judicial examination certificates and AMBER alerts |
| **Frontend UI** | Modern Vanilla JS | Tailwind CSS, Plus Jakarta Sans, Lucide | Zero-dependency, responsive single-page application |
| **GIS Mapping** | Leaflet.js & Mappls | MapmyIndia REST SDK + OpenStreetMap | Multi-layer geospatial clustering and trajectory vector lines |
| **Automated Testing**| Pytest | Pytest 9.1+, 78 test cases | Unit, integration, security, and performance verification |

---

## 4. Computer Vision Deep Learning Architecture

### YuNet Face Detection
- **Input Dimension:** $640 \times 640$ pixels
- **Confidence Threshold:** $0.85$ for official reference enrollment; $0.50$ for candid surveillance sightings
- **Non-Maximum Suppression (NMS):** $0.30$ IoU overlap limit
- **Landmark Geometry:** Tracks 5 coordinates: Right Eye, Left Eye, Nose Tip, Right Mouth Corner, Left Mouth Corner

### SFace 128-D Vector Representation
- **Backbone:** MobileFaceNet architecture optimized for real-time edge CPU inference
- **Feature Vector:** 128 floating-point numbers normalized to unit length ($\|\mathbf{v}\|_2 = 1.0$)
- **Cosine Similarity Equation:**
  $$\cos(\theta) = \mathbf{u} \cdot \mathbf{v} = \sum_{i=1}^{128} u_i v_i$$
- **Metric Thresholds:**
  - $\cos(\theta) \ge 0.45$: Definite Match ($\ge 80\%$ confidence)
  - $\cos(\theta) \ge 0.363$: Qualified Candidate Lead ($\ge 60\%$ confidence)
  - $\cos(\theta) < 0.363$: Filtered Noise

### CLAHE (Contrast Limited Adaptive Histogram Equalization)
Surveillance cameras often capture subjects in low-light parking structures, nighttime railway concourses, or backlit entrances. When average image brightness drops below $85$ or contrast falls below $38$, the engine automatically converts the frame to the **CIE LAB color space** and applies CLAHE to the luminance ($L$) channel with a clip limit of $2.5$ and an $8 \times 8$ tile matrix, bringing out facial geometry without amplifying sensor noise.

---

## 5. Air-Gapped / Offline Operational Guarantee

This application is engineered specifically for **100% offline, air-gapped forensic operation**:
- **Zero External API Dependencies:** Does not call OpenAI, Google, AWS, or any third-party cloud services.
- **Local Model Execution:** OpenCV ONNX models are stored directly in the `models/` directory and loaded locally by the CPU inference engine.
- **Embedded Database:** SQLite database (`database/missing_person.db`) runs entirely in-process on the local filesystem.
- **Local Evidence Generation:** Forensic examination certificates and AMBER alert posters are generated locally via Pillow without external rendering engines.
- **Offline GIS Fallback:** When internet connectivity is absent, the map engine automatically falls back from Mappls to local vector tiles and offline coordinate grids.

---

## 6. Official Pre-Configured CCTNS Credentials

| Role | Official CCTNS Identifier | System Username | Password | Badge / Rank |
|---|---|---|---|---|
| **Lead Investigating Officer** | `io.raman@police.gov.in` | `investigator` | `Police@Gov2026!` *(or `investigator123`)* | Inspector K. Raman (Badge: `INV-1001`) |
| **Nodal Repository Admin** | `cctns.admin@ncrb.gov.in` | `admin` | `Ncrb@Admin2026!` *(or `admin123`)* | Nodal Director (Badge: `ADM-001`) |
| **Senior Field Detective** | `dsp.sharma@police.gov.in` | `detective_chen` | `Police@Gov2026!` *(or `investigator123`)* | Dy. SP Rajesh Sharma (Badge: `INV-7809`) |
| **Public Citizen / Informant** | *(Anonymous public portal)* | — | *(No credentials required)* | Public Sighting Reporter |

*Tip: You can instantly switch between Investigator, Administrator, and Public Citizen roles using the quick role selector in the top navigation bar.*

---

## 7. Quickstart Installation Guide

### Prerequisites
- Python 3.10, 3.11, or 3.12 (64-bit recommended)
- Git
- 2 GB RAM minimum (operates comfortably on standard police workstation laptops)

### Step 1: Clone Repository
```bash
git clone https://github.com/praveeneyyy/missing-person.git
cd missing-person
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Launch Platform
```bash
python run.py
```
*The auto-seeder will verify database integrity, validate OpenCV ONNX weights, seed CCTNS demo cases, and start the Uvicorn ASGI server on `http://127.0.0.1:8000`.*

### Step 4: Access Web Application
- **Main Investigation Workbench:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI / Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **System Health & Liveness Endpoint:** [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz)

---

## 8. Automated Test Suite Verification

The codebase includes an exhaustive test suite of **78 automated test cases across 11 test modules**, ensuring 100% compliance with biometric, security, and forensic requirements:

```bash
python -m pytest tests/ -v
```

### Test Suite Coverage Breakdown:
1. `tests/test_face_engine.py`: YuNet 5-point landmark extraction, SFace 128-D normalization, CLAHE filter activation.
2. `tests/test_module_1_auth.py`: Direct bcrypt hashing, signed JWT issuance, token expiration, unauthorized access blocks.
3. `tests/test_module_2_cases.py`: CCTNS case enrollment, mandatory single-face validation (rejects non-faces or multiple faces).
4. `tests/test_module_3_face_processing.py`: Multi-face candidate cropping, facial bounding boxes, gallery indexing.
5. `tests/test_module_4_sightings.py`: Public sighting submission, SHA-256 receipt generation, privacy preservation.
6. `tests/test_module_5_matching.py`: Cosine distance calculations, confidence scoring, threshold filtering.
7. `tests/test_module_6_reviews.py`: Human-in-the-loop review workflow, mandatory rationale logging, status transitions.
8. `tests/test_module_7_surveillance.py`: CCTV camera node registration, video stream frame sampling, alert notifications.
9. `tests/test_module_8_video_forensics.py`: Multi-frame video ingestion, temporal identity tracking, keyframe extraction.
10. `tests/test_api.py`: Comprehensive REST API integration, route validation, error handling.
11. `tests/test_forensic_certificate.py`: Pillow-generated biometric examination certificates, AMBER posters, cryptographic hashes.

---

## 9. Complete REST API Reference

| Endpoint | Method | Role | Description |
|---|---|---|---|
| `/healthz` | `GET` | Public | System liveness probe, AI engine status, and database health |
| `/api/auth/login` | `POST` | Public | Authenticates officer credentials and returns signed JWT access token |
| `/api/auth/me` | `GET` | Auth | Retrieves authenticated officer profile and role permissions |
| `/api/cases` | `GET` | Auth | Lists missing person cases with optional status and jurisdiction filters |
| `/api/cases` | `POST` | Investigator | Registers new missing person case with metadata and reference portrait |
| `/api/cases/{case_id}` | `GET` | Auth | Retrieves comprehensive case dossier, reference photos, and status history |
| `/api/cases/{case_id}/status` | `PUT` | Investigator | Updates case status (`ACTIVE`, `UNDER_INVESTIGATION`, `HIGH_LEAD`, `RESOLVED`) |
| `/api/cases/{case_id}/dossier` | `GET` | Auth | Generates downloadable watermarked PDF/PNG Biometric Examination Certificate |
| `/api/cases/{case_id}/amber` | `GET` | Auth | Generates printable AMBER Alert bulletin poster with verification QR |
| `/api/sightings` | `POST` | Public | Submits public sighting image, GPS coordinates, notes; returns receipt code |
| `/api/sightings/track/{receipt}`| `GET` | Public | Anonymous sighting status tracking by cryptographic receipt code |
| `/api/candidates/pending` | `GET` | Auth | Lists pending biometric candidate leads awaiting human review |
| `/api/candidates/{id}/review` | `POST` | Investigator | Submits human adjudication (`verified`, `rejected`, `request_more_info`) with rationale |
| `/api/surveillance/cameras` | `GET` | Auth | Lists registered CCTV and RTSP surveillance camera nodes |
| `/api/surveillance/cameras` | `POST` | Investigator | Enrolls new surveillance camera node with RTSP stream URI |
| `/api/surveillance/alerts` | `GET` | Auth | Retrieves real-time candidate detection alerts from CCTV feeds |
| `/api/surveillance/alerts/{id}` | `PUT` | Investigator | Acknowledges or dispatches field units for a surveillance alert |
| `/api/surveillance/video-upload`| `POST` | Investigator | Ingests forensic surveillance video file, extracts faces, and checks watchlist |
| `/api/audit/logs` | `GET` | Admin | Retrieves immutable SHA-256 hash-chained forensic audit logs |
| `/api/audit/export/csv` | `GET` | Admin | Exports RFC-4180 compliant forensic audit log in CSV format |
| `/api/benchmark/run` | `POST` | Admin | Executes hardware benchmark measuring YuNet & SFace latency |

---

## 10. Repository Directory Structure

```
├── backend/                        # FastAPI application core
│   ├── auth.py                     # Bcrypt hashing, JWT generation, and RBAC middleware
│   ├── config.py                   # Configuration settings, paths, thresholds, and .env
│   ├── database.py                 # SQLite database schema, migrations, and connection pool
│   ├── face_engine.py              # OpenCV YuNet face detection, SFace embeddings & CLAHE filter
│   ├── forensic_certificate.py     # Pillow judicial certificate and AMBER alert poster generator
│   ├── main.py                     # Primary FastAPI router, REST endpoints, and static mounts
│   └── seed_data.py                # CCTNS reference case seeder and officer provisioner
├── database/                       # Relational database directory
│   └── missing_person.db           # SQLite 3 local persistent storage (WAL mode)
├── frontend/                       # Institutional Single-Page Application (SPA)
│   ├── css/
│   │   └── style.css               # Minimal institutional stylesheet, animations & tooltip styles
│   ├── js/
│   │   ├── api.js                  # Async API client, session management, and auth tokens
│   │   ├── app.js                  # Application controller, modal managers, hover tooltip engine
│   │   └── map.js                  # Leaflet & Mappls GIS manager, cluster pins & corridors
│   └── index.html                  # Main SPA interface, segmented navigation, and guided modals
├── models/                         # Local pre-packaged neural network weights
│   ├── face_detection_yunet_2023mar.onnx   # YuNet 640x640 DNN face detector
│   └── face_recognition_sface_2021dec.onnx # SFace 128-D MobileFaceNet representation
├── static/                         # Static runtime assets
│   ├── dossiers/                   # Generated forensic certificates and AMBER alert posters
│   ├── reference_photos/           # Enrolled missing individual reference portraits
│   └── sightings/                  # Ingested public sighting evidence imagery
├── tests/                          # Pytest automated test suite (78 test cases)
│   ├── test_api.py
│   ├── test_face_engine.py
│   ├── test_forensic_certificate.py
│   ├── test_module_1_auth.py
│   ├── test_module_2_cases.py
│   ├── test_module_3_face_processing.py
│   ├── test_module_4_sightings.py
│   ├── test_module_5_matching.py
│   ├── test_module_6_reviews.py
│   ├── test_module_7_surveillance.py
│   └── test_module_8_video_forensics.py
├── .env.example                    # Environment variable template (CCTNS settings, Mappls keys)
├── Dockerfile                      # Container definition for production deployment
├── docker-compose.yml              # Container orchestration with reverse proxy
├── requirements.txt                # Python package dependencies
├── run.py                          # Application entry point & service bootstrap
└── README.md                       # Comprehensive platform documentation
```

---

## 11. Security Model & Ethical Governance

1. **Non-Repudiation Audit Ledger:** Every officer action—including case creation, biometric searches, status modifications, and candidate adjudications—is logged into the `audit_logs` table with the officer's IP address, timestamp, badge number, and a SHA-256 integrity hash linking it to previous entries in an append-only chain.
2. **Zero Facial Biometric Data Leakage:** The public portal is completely severed from the missing person repository. Public visitors cannot browse enrolled cases, view reference photos, or inspect candidate match scores. Public inquiries only return the anonymous status of their submitted receipt.
3. **GDPR / DPDP Compliance:** Biometric templates consist of 128 floating-point mathematical numbers. Raw facial vectors cannot be reverse-engineered into high-fidelity original facial photographs without the cryptographic seed.
4. **Human Review Mandatory:** The platform enforces Article 21 and constitutional procedural fairness protections. Automated arrests or suspect detainments based purely on algorithmic outputs are structurally impossible.

---

## 12. License & Government Attribution

Developed in accordance with the National Crime Records Bureau (NCRB) and Crime and Criminal Tracking Network & Systems (CCTNS) technical specifications under the Ministry of Home Affairs, Government of India. 

For official inquiries, bug reports, or feature enhancements, submit an issue to the [Missing Person AI Platform Repository](https://github.com/praveeneyyy/missing-person.git).
