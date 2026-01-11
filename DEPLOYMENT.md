# Deployment Guide

## Table of Contents
1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Monitoring & Logging](#monitoring--logging)
5. [Performance Tuning](#performance-tuning)

## Local Development

### Quick Start
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python app/main.py
```

### Development with Auto-reload
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Running Tests
```bash
# Basic functionality test
python test_system.py

# With server running (in another terminal):
python test_client.py
# OR
./test_api.sh
```

## Docker Deployment

### Build and Run
```bash
# Build image
docker build -t object-storage:latest .

# Run container
docker run -d \
  -p 8001:8001 \
  -v $(pwd)/storage_data:/data \
  --name object-storage \
  object-storage:latest
```

### Using Docker Compose
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Docker Environment Variables
Set in `docker-compose.yml` or pass with `-e`:
```bash
docker run -d \
  -p 8001:8001 \
  -e STORAGE_BASE_PATH=/data \
  -e MAX_FILE_SIZE=10737418240 \
  -e DEBUG=false \
  -v $(pwd)/storage_data:/data \
  object-storage:latest
```

## Production Deployment

### 1. System Prerequisites
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip nginx

# RHEL/CentOS
sudo dnf install -y python3.11 python3.11-pip nginx
```

### 2. Application Setup
```bash
# Create application directory
sudo mkdir -p /opt/object-storage
sudo chown $USER:$USER /opt/object-storage
cd /opt/object-storage

# Clone/copy application
# ... (copy your files here)

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn  # Production server

# Create .env file
cp .env.example .env
# Edit .env with production settings
nano .env
```

### 3. Setup Systemd Service
```bash
# Copy service file
sudo cp object-storage.service /etc/systemd/system/

# Create log directory
sudo mkdir -p /var/log/object-storage
sudo chown www-data:www-data /var/log/object-storage

# Create storage directory
sudo mkdir -p /var/lib/object-storage
sudo chown www-data:www-data /var/lib/object-storage

# Update .env to use production paths
echo "STORAGE_BASE_PATH=/var/lib/object-storage" >> .env

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable object-storage
sudo systemctl start object-storage

# Check status
sudo systemctl status object-storage
```

### 4. Nginx Reverse Proxy
Create `/etc/nginx/sites-available/object-storage`:
```nginx
upstream object_storage {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name storage.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name storage.example.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/storage.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/storage.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Upload size limit
    client_max_body_size 10G;
    client_body_timeout 300s;
    
    # Proxy settings
    location / {
        proxy_pass http://object_storage;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Streaming support
        proxy_buffering off;
        proxy_request_buffering off;
        
        # Timeouts for large uploads
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # Health check endpoint (no auth required)
    location /health {
        proxy_pass http://object_storage;
        access_log off;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/object-storage /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. SSL Certificate (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d storage.example.com
```

## Monitoring & Logging

### View Application Logs
```bash
# Systemd logs
sudo journalctl -u object-storage -f

# Application logs
sudo tail -f /var/log/object-storage/error.log
sudo tail -f /var/log/object-storage/access.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Health Monitoring
```bash
# Simple health check
curl http://localhost:8001/health

# Monitor with watch
watch -n 5 'curl -s http://localhost:8001/health | python -m json.tool'
```

### Metrics (Optional: Prometheus)
Add to requirements.txt:
```
prometheus-fastapi-instrumentator==6.1.0
```

Add to `app/main.py`:
```python
from prometheus_fastapi_instrumentator import Instrumentator

@app.on_event("startup")
async def startup():
    Instrumentator().instrument(app).expose(app)
```

## Performance Tuning

### 1. Worker Configuration
Adjust workers in systemd service or docker-compose:
```bash
# Formula: (2 x CPU cores) + 1
--workers 9  # For 4 core machine
```

### 2. File System Optimization
```bash
# For large file operations
echo 'vm.dirty_ratio = 10' | sudo tee -a /etc/sysctl.conf
echo 'vm.dirty_background_ratio = 5' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 3. Nginx Optimization
Add to nginx config:
```nginx
# Worker processes
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    use epoll;
}

http {
    # Keep alive
    keepalive_timeout 65;
    keepalive_requests 100;
    
    # Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types application/json text/plain;
}
```

### 4. Application Settings
Adjust in `.env`:
```bash
# Increase chunk size for better throughput
CHUNK_SIZE=2097152  # 2MB

# Increase max file size
MAX_FILE_SIZE=53687091200  # 50GB

# Disable path protection if not needed (faster)
ENABLE_PATH_TRAVERSAL_PROTECTION=false  # Only if behind firewall
```

## Backup Strategy

### Backup Script
```bash
#!/bin/bash
# /opt/object-storage/backup.sh

BACKUP_DIR="/backups/object-storage"
STORAGE_DIR="/var/lib/object-storage"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/storage_$DATE.tar.gz $STORAGE_DIR

# Keep only last 7 days
find $BACKUP_DIR -name "storage_*.tar.gz" -mtime +7 -delete
```

### Cron Job
```bash
# Add to crontab
0 2 * * * /opt/object-storage/backup.sh
```

## Troubleshooting

### Permission Issues
```bash
# Fix storage directory permissions
sudo chown -R www-data:www-data /var/lib/object-storage
sudo chmod -R 755 /var/lib/object-storage
```

### Port Already in Use
```bash
# Find process using port 8001
sudo lsof -i :8001
sudo netstat -tlnp | grep 8001

# Kill process
sudo kill -9 <PID>
```

### High Memory Usage
```bash
# Reduce workers
# Edit systemd service: --workers 2

# Monitor memory
watch -n 1 'ps aux | grep gunicorn | grep -v grep'
```

## Security Hardening

### 1. Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Rate Limiting (Nginx)
```nginx
http {
    limit_req_zone $binary_remote_addr zone=upload:10m rate=10r/s;
    
    server {
        location /api/v1/objects/ {
            limit_req zone=upload burst=20;
        }
    }
}
```

### 3. Authentication (Optional)
Consider adding JWT authentication or API keys for production use.

## Scaling

### Horizontal Scaling
- Deploy multiple instances behind a load balancer
- Use shared storage (NFS, S3, MinIO) as backend
- Implement session affinity for uploads

### Vertical Scaling
- Increase worker count
- Add more RAM for caching
- Use faster storage (SSD/NVMe)
