# Archive-AI Production Deployment Guide

**Version:** 7.5
**Date:** 2025-12-28
**Status:** Production Ready (72.1% feature complete)

---

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/yourusername/archive-ai.git
cd archive-ai

# 2. Configure environment
cp .env.example .env
nano .env  # Edit configuration

# 3. Create required directories
mkdir -p data/{redis,archive,library} models/{vorpal,whisper,f5-tts} ~/ArchiveAI/Library-Drop

# 4. Download models (see Model Setup below)

# 5. Start services
docker-compose -f docker-compose.prod.yml up -d

# 6. Verify health
curl http://localhost:8081/health
```

---

## System Requirements

### Hardware
- **CPU**: 8+ cores recommended
- **RAM**: 32GB minimum, 64GB recommended
- **GPU**: NVIDIA GPU with 16GB VRAM (for Vorpal LLM)
  - Tested: RTX 5060 Ti 16GB
  - Alternatives: RTX 4060 Ti 16GB, RTX 3090 24GB
- **Storage**: 50GB+ SSD
  - Models: ~10GB
  - Data: 5-20GB (grows with usage)
  - Archive: 1-10GB (grows over time)

### Software
- **OS**: Linux (Ubuntu 22.04+ recommended)
- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **NVIDIA Driver**: 535+
- **NVIDIA Container Toolkit**: Latest

---

## Model Setup

### Vorpal (Speed Engine) - Required
```bash
# Download Llama-3-8B-Instruct (EXL2 4.0bpw)
# Place in: ./models/vorpal/

# Model requirements:
# - Format: EXL2
# - Size: ~3GB VRAM
# - Quantization: 4.0bpw
```

### Whisper (Speech-to-Text) - Optional
```bash
# Models auto-download to ./models/whisper/ on first use
# No manual setup required

# Model options (set in .env):
# - tiny: 39M params, fast, less accurate
# - base: 74M params, balanced (default)
# - small: 244M params, good accuracy
# - medium: 769M params, very good
# - large: 1550M params, best accuracy
```

### F5-TTS (Text-to-Speech) - Optional
```bash
# Models auto-download to ./models/f5-tts/ on first use
# No manual setup required
```

---

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# Security - IMPORTANT!
REDIS_PASSWORD=<generate with: openssl rand -base64 32>

# Ports
BRAIN_PORT=8081

# Memory Management
ARCHIVE_DAYS=30          # Archive memories older than 30 days
ARCHIVE_KEEP=1000        # Keep 1000 most recent in Redis
ARCHIVE_HOUR=3           # Run archival at 3 AM

# Voice
WHISPER_MODEL=base       # STT model size
TTS_DEVICE=cpu           # Use CPU for TTS (GPU optional)

# Library
LIBRARY_DROP=~/ArchiveAI/Library-Drop
```

### Resource Limits

In `docker-compose.prod.yml`:

```yaml
# Redis: 24GB RAM limit
# Vorpal: ~3.5GB VRAM
# Brain: No specific limit (< 2GB typical)
# Sandbox: 2GB RAM, 2 CPU cores
# Voice: 8GB RAM, 4 CPU cores
# Librarian: 4GB RAM, 2 CPU cores
```

---

## Security Hardening

### 1. Network Security
```bash
# Bind services to localhost only (already configured)
# Ports bound to 127.0.0.1:
# - 6379: Redis
# - 8000: Vorpal
# - 8001: Voice
# - 8003: Sandbox

# Only Brain (8081) is externally accessible
# Use nginx reverse proxy with SSL:

sudo apt install nginx certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 2. Firewall Configuration
```bash
# UFW example
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Block direct access to internal ports
sudo ufw deny 6379
sudo ufw deny 8000
sudo ufw deny 8001
sudo ufw deny 8003
# Note: 8081 is the Brain API (allow if accessing directly)
```

### 3. Redis Password
```bash
# Generate strong password
openssl rand -base64 32 > .redis-password

# Set in .env
REDIS_PASSWORD=$(cat .redis-password)
```

### 4. Sandbox Isolation
Already configured in `docker-compose.prod.yml`:
- Read-only filesystem
- No new privileges
- Limited CPU/RAM
- Tmpfs for /tmp only

---

## Monitoring

### Health Checks
```bash
# All services
docker ps --format "table {{.Names}}\t{{.Status}}"

# Individual health
curl http://localhost:8081/health
curl http://localhost:8081/metrics

# Archive stats
curl http://localhost:8081/admin/archive_stats
```

### Resource Usage
```bash
# Real-time monitoring
docker stats

# GPU usage
nvidia-smi -l 1

# Disk usage
du -sh data/redis data/archive data/library
```

### Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker logs -f archive-brain

# Last 100 lines
docker logs --tail 100 archive-brain
```

---

## Backup & Restore

### Backup
```bash
#!/bin/bash
# backup-archive-ai.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=~/backups/archive-ai

mkdir -p $BACKUP_DIR

# 1. Redis data
docker exec archive-redis redis-cli SAVE
cp -r data/redis $BACKUP_DIR/redis-$DATE

# 2. Archive data
tar -czf $BACKUP_DIR/archive-$DATE.tar.gz data/archive

# 3. Library data
tar -czf $BACKUP_DIR/library-$DATE.tar.gz data/library

# 4. Configuration
cp .env $BACKUP_DIR/env-$DATE

echo "Backup complete: $BACKUP_DIR"
```

### Restore
```bash
# 1. Stop services
docker-compose -f docker-compose.prod.yml down

# 2. Restore data
cp -r ~/backups/archive-ai/redis-YYYYMMDD_HHMMSS/* data/redis/
tar -xzf ~/backups/archive-ai/archive-YYYYMMDD_HHMMSS.tar.gz

# 3. Restart services
docker-compose -f docker-compose.prod.yml up -d
```

---

## Maintenance

### Daily
- Monitor disk usage
- Check health endpoints
- Review error logs

### Weekly
- Backup data directories
- Review archive stats
- Check VRAM usage trends

### Monthly
- Update Docker images
- Review and optimize configs
- Test backup restoration

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs [service]

# Check dependencies
docker ps -a

# Verify ports not in use
sudo netstat -tulpn | grep -E '8080|6379|8000'
```

### High Memory Usage
```bash
# Check Redis memory
docker exec archive-redis redis-cli INFO memory

# Trigger manual archival
curl -X POST http://localhost:8080/admin/archive_old_memories

# Adjust ARCHIVE_KEEP in .env (default 1000)
```

### GPU Issues
```bash
# Verify GPU available
nvidia-smi

# Check CUDA in container
docker exec archive-vorpal nvidia-smi

# Reduce GPU usage
# Edit .env: GPU_MEMORY_UTILIZATION=0.15
```

---

## Performance Tuning

### Optimize Redis
```yaml
# In docker-compose.prod.yml
environment:
  - REDIS_ARGS=--maxmemory 20gb --maxmemory-policy allkeys-lru --save 900 1 --save 300 10
```

### Optimize Archive Schedule
```bash
# Low-traffic hours
ARCHIVE_HOUR=3  # 3 AM
ARCHIVE_MINUTE=0

# More aggressive archival
ARCHIVE_DAYS=14  # Archive after 2 weeks
ARCHIVE_KEEP=500  # Keep only 500 recent
```

### Optimize Voice Models
```bash
# Faster STT (less accurate)
WHISPER_MODEL=tiny

# Faster STT (balanced)
WHISPER_MODEL=base  # Recommended
```

---

## API Documentation

Access interactive API docs:
- Swagger UI: http://localhost:8081/docs
- ReDoc: http://localhost:8081/redoc
- OpenAPI JSON: http://localhost:8081/openapi.json

---

## Support

- **Issues**: https://github.com/yourusername/archive-ai/issues
- **Documentation**: See /Docs directory
- **Checkpoints**: See /checkpoints directory for implementation details

---

## License

[Your License Here]

---

**Last Updated**: 2025-12-28
**Deployment Status**: ✅ Production Ready
**Completion**: 72.1% (31/43 chunks)
