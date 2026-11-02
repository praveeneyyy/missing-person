# ==============================================================================
# Gunicorn Production Configuration
# AI-Based Missing Person Identification & Tracking System
# ==============================================================================
import multiprocessing
import os

bind = f"{os.environ.get('HOST', '0.0.0.0')}:{os.environ.get('PORT', '8000')}"

# Concurrency: For OpenCV ONNX inference, 2-4 workers prevent memory thrashing
default_workers = min(4, max(2, multiprocessing.cpu_count()))
workers = int(os.environ.get("WORKERS", default_workers))
worker_class = "uvicorn.workers.UvicornWorker"

# Worker lifecycle and timeouts
# Timeout set to 120s to allow intensive forensic video decoding & batch frame matching
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'
