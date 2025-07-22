# Deployment Guide

Complete guide for deploying Bassline-Bot in production environments.

## Deployment Options

### 1. Docker Deployment (Recommended)

#### Single Server Setup
```bash
# Clone repository
git clone https://github.com/Cthede11/bassline-bot.git
cd bassline-bot

# Configure environment
cp .env.example .env
nano .env  # Edit with production values

# Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Verify deployment
docker-compose ps
docker-compose logs bot
```

#### Multi-Server Setup
```bash
# Database server (separate machine)
docker-compose -f docker-compose.db.yml up -d

# Bot instances (multiple machines)
docker-compose -f docker-compose.bot.yml up -d

# Load balancer (if using dashboard)
docker-compose -f docker-compose.lb.yml up -d
```

### 2. Kubernetes Deployment

#### Basic Kubernetes Setup
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bassline-bot

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: bassline-bot-config
  namespace: bassline-bot
data:
  DATABASE_URL: "postgresql://bassline:password@postgres:5432/basslinebot"
  REDIS_URL: "redis://redis:6379"
  LOG_LEVEL: "INFO"

---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: bassline-bot-secrets
  namespace: bassline-bot
type: Opaque
stringData:
  DISCORD_TOKEN: "your-discord-token"
  SECRET_KEY: "your-secret-key"

---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bassline-bot
  namespace: bassline-bot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: bassline-bot
  template:
    metadata:
      labels:
        app: bassline-bot
    spec:
      containers:
      - name: bot
        image: bassline-bot:latest
        envFrom:
        - configMapRef:
            name: bassline-bot-config
        - secretRef:
            name: bassline-bot-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
```

#### Deploy to Kubernetes
```bash
# Apply configurations
kubectl apply -f k8s/

# Check status
kubectl get pods -n bassline-bot
kubectl logs -f deployment/bassline-bot -n bassline-bot

# Scale deployment
kubectl scale deployment bassline-bot --replicas=5 -n bassline-bot
```

### 3. Cloud Provider Deployments

#### AWS Deployment

**Using ECS:**
```json
{
  "family": "bassline-bot",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "bassline-bot",
      "image": "your-account.dkr.ecr.region.amazonaws.com/bassline-bot:latest",
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@rds-endpoint:5432/basslinebot"
        }
      ],
      "secrets": [
        {
          "name": "DISCORD_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:discord-token"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/bassline-bot",
          "awslogs-region": "us-west-2"
        }
      }
    }
  ]
}
```

**Using Lambda (for smaller bots):**
```python
# lambda_handler.py
import json
import asyncio
from src.bot import main

def lambda_handler(event, context):
    # Run bot for limited time
    asyncio.run(main())
    return {
        'statusCode': 200,
        'body': json.dumps('Bot executed successfully')
    }
```

#### Google Cloud Deployment

**Using Cloud Run:**
```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: bassline-bot
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
    spec:
      containers:
      - image: gcr.io/project-id/bassline-bot
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: DISCORD_TOKEN
          valueFrom:
            secretKeyRef:
              name: discord-secret
              key: token
        resources:
          limits:
            memory: 2Gi
            cpu: 1000m
```

#### Azure Deployment

**Using Container Instances:**
```yaml
# azure-container.yaml
apiVersion: 2019-12-01
location: eastus
name: bassline-bot
properties:
  containers:
  - name: bassline-bot
    properties:
      image: your-registry.azurecr.io/bassline-bot:latest
      resources:
        requests:
          cpu: 1
          memoryInGb: 2
      environmentVariables:
      - name: DATABASE_URL
        secureValue: postgresql://user:pass@server:5432/db
      - name: DISCORD_TOKEN
        secureValue: your-discord-token
  osType: Linux
  restartPolicy: Always
type: Microsoft.ContainerInstance/containerGroups
```

## Production Configuration

### Environment Setup
```env
# Production .env
DISCORD_TOKEN=your_production_token
DATABASE_URL=postgresql://bassline:secure_password@db-server:5432/basslinebot
REDIS_URL=redis://:auth_token@redis-server:6379
LOG_LEVEL=INFO
VERBOSE_LOGGING=false
DASHBOARD_ENABLED=true
METRICS_ENABLED=true
BILLING_ENABLED=true
MULTI_TENANT=true
SECRET_KEY=very_secure_random_key_here
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

### Database Setup

#### PostgreSQL Production
```sql
-- Create database and user
CREATE DATABASE basslinebot;
CREATE USER bassline WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE basslinebot TO bassline;

-- Optimize for production
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET wal_buffers = '16MB';
SELECT pg_reload_conf();
```

#### Database Backup
```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U bassline basslinebot > "$BACKUP_DIR/backup_$DATE.sql"

# Keep only 7 days of backups
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

### Reverse Proxy Setup

#### Nginx Configuration
```nginx
# /etc/nginx/sites-available/bassline-bot
server {
    listen 80;
    server_name dashboard.yourdomain.com;
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name dashboard.yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /metrics {
        proxy_pass http://localhost:9090;
        auth_basic "Metrics";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

#### Caddy Configuration
```caddyfile
# Caddyfile
dashboard.yourdomain.com {
    reverse_proxy localhost:8080
}

metrics.yourdomain.com {
    reverse_proxy localhost:9090
    basicauth {
        admin $2a$14$hashed_password
    }
}
```

## Monitoring & Alerting

### Prometheus Configuration
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'bassline-bot'
    static_configs:
      - targets: ['bot:9090']
  
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

rule_files:
  - "alert_rules.yml"
```

### Alert Rules
```yaml
# monitoring/alert_rules.yml
groups:
- name: bassline-bot
  rules:
  - alert: BotDown
    expr: up{job="bassline-bot"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Bassline-Bot is down"
      description: "Bassline-Bot has been down for more than 5 minutes"
  
  - alert: HighErrorRate
    expr: rate(basslinebot_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"
  
  - alert: DatabaseConnectionLoss
    expr: basslinebot_database_connections == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Database connection lost"
```

### Grafana Dashboards
```json
{
  "dashboard": {
    "title": "Bassline-Bot",
    "panels": [
      {
        "title": "Active Voice Connections",
        "type": "stat",
        "targets": [
          {
            "expr": "basslinebot_active_connections"
          }
        ]
      },
      {
        "title": "Commands per Second",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(basslinebot_commands_total[5m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(basslinebot_errors_total[5m])"
          }
        ]
      }
    ]
  }
}
```

## Security Hardening

### System Security
```bash
# Create dedicated user
sudo useradd -r -s /bin/false basslinebot

# Set up proper permissions
sudo chown -R basslinebot:basslinebot /opt/bassline-bot
sudo chmod 750 /opt/bassline-bot

# Configure firewall
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw --force enable
```

### Application Security
```env
# Secure configuration
SECRET_KEY=very_long_random_string_here
CORS_ENABLED=true
CORS_ORIGINS=https://yourdomain.com
RATE_LIMIT_ENABLED=true
SANITIZE_INPUTS=true
```

### SSL/TLS Setup
```bash
# Using Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d dashboard.yourdomain.com
sudo certbot renew --dry-run
```

## Performance Optimization

### System Optimization
```bash
# Increase file descriptors
echo "basslinebot soft nofile 65536" >> /etc/security/limits.conf
echo "basslinebot hard nofile 65536" >> /etc/security/limits.conf

# Optimize network
echo "net.core.somaxconn = 65535" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65535" >> /etc/sysctl.conf
sysctl -p
```

### Database Optimization
```sql
-- PostgreSQL optimization
ALTER SYSTEM SET max_connections = '200';
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
ALTER SYSTEM SET work_mem = '4MB';
SELECT pg_reload_conf();
```

### Application Tuning
```env
# Performance settings
MAX_CONCURRENT_DOWNLOADS=5
DOWNLOAD_TIMEOUT=30
SEARCH_CACHE_TTL=3600
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

## Scaling Strategies

### Horizontal Scaling
```yaml
# Multiple bot instances
version: '3.8'
services:
  bot-1:
    image: bassline-bot:latest
    environment:
      - INSTANCE_ID=1
  
  bot-2:
    image: bassline-bot:latest
    environment:
      - INSTANCE_ID=2
  
  bot-3:
    image: bassline-bot:latest
    environment:
      - INSTANCE_ID=3
```

### Load Balancing
```nginx
# Load balancer configuration
upstream basslinebot_backend {
    server bot-1:8080;
    server bot-2:8080;
    server bot-3:8080;
}

server {
    location / {
        proxy_pass http://basslinebot_backend;
    }
}
```

## Maintenance

### Update Procedure
```bash
# 1. Backup database
python scripts/backup.py

# 2. Pull new code
git pull origin main

# 3. Update dependencies
pip install -r requirements.txt

# 4. Run migrations
python scripts/migrate.py

# 5. Restart services
docker-compose restart bot

# 6. Verify deployment
curl http://localhost:8080/health
```

### Health Checks
```bash
# Automated health check script
#!/bin/bash
if curl -f http://localhost:8080/health; then
    echo "Bot is healthy"
else
    echo "Bot is unhealthy, restarting..."
    docker-compose restart bot
fi
```

## Troubleshooting

### Common Issues

1. **Out of memory**: Increase container memory limits
2. **Database connections**: Check connection pool settings
3. **Slow responses**: Enable Redis caching
4. **High CPU**: Optimize audio processing settings

### Debugging
```bash
# View logs
docker-compose logs -f bot

# Check resource usage
docker stats

# Monitor database
docker exec -it bassline-db psql -U bassline -d basslinebot -c "SELECT * FROM pg_stat_activity;"
```

This guide covers comprehensive deployment scenarios from simple Docker setups to enterprise Kubernetes deployments with full monitoring and security.