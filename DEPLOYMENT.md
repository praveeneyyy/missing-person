# Production Deployment & Operations Guide
## AI-Based Missing Person Identification and Tracking System

This guide outlines the complete operational procedures for deploying, hardening, monitoring, and maintaining the **AI-Based Missing Person Identification and Tracking Platform** in production environments.

---

## 1. Architecture Overview

```
                          [ Internet Traffic ]
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │  Nginx / Caddy Reverse Proxy  │ (SSL Termination, Rate Limiting,
                   │      (Ports 80 / 443)         │  Security Headers, Gzip)
                   └───────────────┬───────────────┘
                                   │ (Internal HTTP)
                                   ▼
                   ┌───────────────────────────────┐
                   │   Gunicorn + Uvicorn Workers  │ (FastAPI App, OpenCV Inference,
                   │         (Port 8000)           │  RBAC, Evidence Generation)
                   └───────────────┬───────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
   ┌──────────────────────┐                  ┌──────────────────────┐
   │ Persistent SQLite DB │                  │ Media Storage Volume │
   │ (missing_persons.db) │                  │ (/storage/references,│
   │                      │                  │  /storage/sightings) │
   └──────────────────────┘                  └──────────────────────┘
```

The system operates **entirely self-contained** without external AI cloud dependencies:
- **YuNet Face Detection**: Local ONNX neural network (`models/face_detection_yunet_2023mar.onnx`).
- **SFace Biometric Representation**: Local 128-D embedding extraction (`models/face_recognition_sface_2021dec.onnx`).
- **GIS Mapping**: Leaflet.js with OpenStreetMap.

---

## 2. Production Prerequisites

* **Hardware**:
  - Minimum: 2 vCPU, 4 GB RAM, 20 GB SSD storage.
  - Recommended: 4 vCPU, 8 GB RAM, 50 GB SSD (for concurrent video forensic analysis).
* **Operating System**: Linux (Ubuntu 22.04 LTS / Debian 12 / RHEL 9) or Windows Server 2022.
* **Container Runtime**: Docker Engine 24.0+ and Docker Compose v2.20+.

---

## 3. Quick Start: 1-Command Docker Deployment

### Step 1: Clone and Enter Repository
```bash
git clone <repository_url> /opt/missing-persons-platform
cd /opt/missing-persons-platform
```

### Step 2: Configure Production Environment Variables
```bash
cp .env.example .env
```
Generate a cryptographically secure 64-character JWT secret key:
```bash
openssl rand -hex 32
```
Update `.env` with your new secret, your domain, and your production settings:
```ini
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000
JWT_SECRET_KEY=<PASTE_GENERATED_64_CHAR_HEX_HERE>
ALLOWED_ORIGINS=https://your-domain.gov,https://police-portal.your-domain.gov
DATABASE_PATH=/app/data/missing_persons.db
STORAGE_DIR=/app/storage
```

### Step 3: Launch Production Containers
```bash
docker compose up -d --build
```

### Step 4: Verify Service Health
```bash
docker compose ps
curl -s http://127.0.0.1/healthz
curl -s http://127.0.0.1/api/v1/health
```

The application is now live on port 80 behind the Nginx reverse proxy.

---

## 4. HTTPS & SSL/TLS Configuration

Web camera capture, browser geolocation, and sensitive biometric data transfer **require HTTPS** in modern browsers.

### Option A: Using Certbot with Nginx (Recommended)
1. Install Certbot on your host:
   ```bash
   sudo apt-get update && sudo apt-get install -y certbot python3-certbot-nginx
   ```
2. Obtain and install certificates for your domain:
   ```bash
   sudo certbot certonly --standalone -d your-domain.gov
   ```
3. Mount the certificate directory in `docker-compose.yml` into Nginx:
   ```yaml
   volumes:
     - /etc/letsencrypt:/etc/letsencrypt:ro
   ```
4. Configure Nginx to listen on port 443 with SSL enabled in `deploy/nginx/nginx.conf`.

### Option B: Automatic Zero-Config HTTPS with Caddy
If you prefer automatic certificate issuance and renewal, replace the Nginx container in `docker-compose.yml` with Caddy:
```yaml
  proxy:
    image: caddy:alpine
    container_name: missing_persons_caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    command: caddy reverse-proxy --from your-domain.gov --to app:8000
    volumes:
      - caddy_data:/data
      - caddy_config:/config
```

---

## 5. Native Linux Systemd Deployment (Without Docker)

For environments hosting directly on bare metal or VMs without Docker:

### Step 1: Install System Dependencies
```bash
sudo apt-get update && sudo apt-get install -y \
    python3-venv python3-pip libgl1 libglib2.0-0 libgomp1 nginx
```

### Step 2: Setup Application Directory & Virtualenv
```bash
sudo useradd -r -s /bin/false appuser
sudo mkdir -p /var/www/missing-persons /var/www/missing-persons/storage
sudo chown -R appuser:appuser /var/www/missing-persons

cd /var/www/missing-persons
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Create Systemd Service (`/etc/systemd/system/missing-persons.service`)
```ini
[Unit]
Description=Police AI Missing Person Dispatch & Tracking Server
After=network.target

[Service]
User=appuser
Group=appuser
WorkingDirectory=/var/www/missing-persons
EnvironmentFile=/var/www/missing-persons/.env
ExecStart=/var/www/missing-persons/venv/bin/gunicorn -c deploy/gunicorn_conf.py backend.main:app
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### Step 4: Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now missing-persons.service
sudo systemctl status missing-persons.service
```

---

## 6. Security Hardening & Best Practices

1. **Rotate Default Staff Passwords**:
   Immediately log in as `admin` and change passwords for:
   - `admin`
   - `investigator`
   - `detective_chen`
2. **Restrict CORS**:
   Set `ALLOWED_ORIGINS` to the exact production FQDNs. Never leave as `*` in public deployments.
3. **Firewall & Network Rules**:
   - Only expose ports `80` (HTTP redirect) and `443` (HTTPS) to the public internet.
   - Restrict port `8000` (FastAPI backend) to `localhost` or Docker internal bridge network.
4. **Audit Log Retention**:
   The `audit_logs` table stores an immutable log of all case enrollments, candidate reviews, and administrative actions. Ensure periodic log archival.

---

## 7. Data Persistence & Backup Procedures

### Critical Data Assets
1. **Relational Database**: `missing_persons.db`
2. **Media Storage**:
   - `storage/references/` (Facial reference portraits)
   - `storage/sightings/` (Public sighting photos and CCTV snapshots)

### Automated Daily Backup Script (`backup.sh`)
```bash
#!/bin/bash
BACKUP_DIR="/backups/missing-persons/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 1. Safe SQLite backup using SQLite online backup API
sqlite3 missing_persons.db ".backup '$BACKUP_DIR/missing_persons.db'"

# 2. Archive media storage
tar -czf "$BACKUP_DIR/storage.tar.gz" storage/

# 3. Retention policy: Remove backups older than 30 days
find /backups/missing-persons/ -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +

echo "Backup completed successfully at $BACKUP_DIR"
```

---

## 8. Health Probes & Monitoring

The platform provides standardized endpoints for load balancers and orchestrators:

| Endpoint | Method | Purpose | Response |
|---|---|---|---|
| `/healthz` | `GET` | Lightweight liveness probe for Kubernetes / Docker | `{"status": "ok"}` |
| `/api/v1/health` | `GET` | Comprehensive system & model diagnostic probe | `{"status": "healthy", "service": "...", "models": {...}}` |

### Prometheus / Uptime Monitoring
Set your monitoring tool (Datadog, Uptime Kuma, Prometheus Blackbox) to check:
- URL: `https://your-domain.gov/healthz`
- Expected Status Code: `200`
- Alert threshold: 3 consecutive failures over 60 seconds.
