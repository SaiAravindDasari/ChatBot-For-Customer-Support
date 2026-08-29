# QueryDesk — Enterprise Deployment & Operations Guide

This guide describes how to deploy and operate **QueryDesk** in enterprise production environments.

---

## 1. Quick Production Launch (Docker Compose)

The fastest way to deploy QueryDesk with production Nginx reverse proxy, gzip compression, and rate limiting:

```bash
# 1. Clone repository & configure environment variables
cp .env.example .env

# 2. Build & launch containers
docker-compose up -d --build

# 3. Check logs & service health
docker-compose logs -f api
```

The service will be accessible at:
- **Chat Web App**: `http://localhost/`
- **Enterprise Console**: `http://localhost/admin`
- **Prometheus Metrics**: `http://localhost/metrics`
- **Readiness Probe**: `http://localhost/health/ready`

---

## 2. Bare-Metal & Virtual Machine Deployment

For Ubuntu / Debian / RHEL servers:

```bash
# Install virtualenv & Python 3.11+
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with Gunicorn/Uvicorn multi-worker process manager
uvicorn backend.app:app --host 0.0.0.0 --port 5000 --workers 4 --log-level info
```

### Systemd Service Configuration (`/etc/systemd/system/querydesk.service`)
```ini
[Unit]
Description=QueryDesk Enterprise AI Platform
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/querydesk
ExecStart=/var/www/querydesk/venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 5000 --workers 4
Restart=always
RestartSec=5
EnvironmentFile=/var/www/querydesk/.env

[Install]
WantedBy=multi-user.target
```

---

## 3. Kubernetes / Helm Deployment

### Deployment Manifest (`k8s-deployment.yaml`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: querydesk-deployment
  labels:
    app: querydesk
spec:
  replicas: 3
  selector:
    matchLabels:
      app: querydesk
  template:
    metadata:
      labels:
        app: querydesk
    spec:
      containers:
      - name: querydesk
        image: querydesk:latest
        ports:
        - containerPort: 5000
        livenessProbe:
          httpGet:
            path: /health/live
            port: 5000
          initialDelaySeconds: 15
          periodSeconds: 20
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 10
        resources:
          limits:
            cpu: "1000m"
            memory: "1024Mi"
          requests:
            cpu: "250m"
            memory: "512Mi"
```

---

## 4. Monitoring & Prometheus Metrics

QueryDesk exports standard OpenMetrics format on `GET /metrics`.

Sample Prometheus scrape config:
```yaml
scrape_configs:
  - job_name: 'querydesk'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:5000']
```

Exported Metrics:
- `querydesk_http_requests_total{method, path, status}`
- `querydesk_http_request_duration_seconds_sum`
- `querydesk_websocket_active_connections{type}`
- `querydesk_nlp_intents_total{intent}`
- `querydesk_tickets_escalated_total{priority}`
- `querydesk_rag_cache_hits_total`
