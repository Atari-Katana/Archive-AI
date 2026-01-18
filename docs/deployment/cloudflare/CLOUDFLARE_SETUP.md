# Archive-AI Cloudflare Tunnel Setup Guide

This guide explains how to deploy Archive-AI with Cloudflare Tunnel for secure, public access.

---

## Overview

**What's Different from Standard Setup:**
- ✅ Single entry point (port 8080 only) - no separate UI server
- ✅ All internal services protected (localhost-only binding)
- ✅ Cloudflare provides SSL/TLS automatically
- ✅ No port forwarding or firewall rules needed
- ✅ DDoS protection and CDN included

**What You Get:**
- Public access: `https://your-domain.com`
- Automatic HTTPS with Cloudflare SSL
- Protection from direct attacks (server IP hidden)
- Free tier available

---

## Prerequisites

1. **Domain name** managed by Cloudflare (free tier works)
2. **Cloudflare account** ([sign up free](https://dash.cloudflare.com/sign-up))
3. **Archive-AI installed** on your server
4. **Server requirements**: Same as standard install (16GB VRAM GPU, 32GB RAM)

---

## Step 1: Install Cloudflared

On your Archive-AI server:

```bash
# Download cloudflared
curl -L --output cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

# Install
sudo dpkg -i cloudflared.deb

# Verify installation
cloudflared --version
```

---

## Step 2: Authenticate with Cloudflare

```bash
# This opens a browser window to authenticate
cloudflared tunnel login
```

- Login to your Cloudflare account
- Select the domain you want to use
- Approve the authorization

A credentials file will be saved to `~/.cloudflared/`

---

## Step 3: Create a Tunnel

```bash
# Create tunnel (choose a memorable name)
cloudflared tunnel create archive-ai

# Note the Tunnel ID shown (you'll need this)
```

This creates:
- Tunnel ID (e.g., `abcd1234-5678-90ef-ghij-klmnopqrstuv`)
- Credentials file: `~/.cloudflared/<TUNNEL-ID>.json`

---

## Step 4: Configure Archive-AI

### Update .env File

```bash
cd /path/to/Archive-AI
nano .env
```

Add or update these lines:

```bash
# Set your Cloudflare domain
PUBLIC_URL=https://your-domain.com

# Enable proxy trust
TRUST_PROXY=true

# Secure Redis (generate password: openssl rand -base64 32)
REDIS_PASSWORD=your-secure-password-here
```

**Replace `your-domain.com` with your actual domain!**

---

## Step 5: Configure Cloudflare Tunnel

Create config file:

```bash
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Add this configuration (replace `<TUNNEL-ID>` and domains):

```yaml
tunnel: <TUNNEL-ID>
credentials-file: /home/yourusername/.cloudflared/<TUNNEL-ID>.json

ingress:
  # Main domain
  - hostname: archive.your-domain.com
    service: http://localhost:8080

  # Optional: www subdomain
  - hostname: www.archive.your-domain.com
    service: http://localhost:8080

  # Catch-all (required, must be last)
  - service: http_status:404
```

**Important:** Use the full path to your credentials file!

---

## Step 6: Route DNS

Point your domain to the tunnel:

```bash
# Route subdomain (recommended)
cloudflared tunnel route dns archive-ai archive.your-domain.com

# Or route apex domain
cloudflared tunnel route dns archive-ai your-domain.com
```

This automatically creates DNS CNAME records in Cloudflare.

---

## Step 7: Start Archive-AI (Cloudflare Mode)

```bash
cd /path/to/Archive-AI

# Start with Cloudflare configuration
./go-cloudflare.sh
```

This starts Archive-AI with:
- Brain service on port 8080 (single entry point)
- UI served at `/ui/` path (no separate server)
- Internal services protected
- Health checks enabled

---

## Step 8: Start Cloudflare Tunnel

In a separate terminal or screen session:

```bash
# Start tunnel (foreground)
cloudflared tunnel run archive-ai

# Or run as background service
cloudflared tunnel run --url http://localhost:8080 archive-ai &
```

---

## Step 9: Test Access

**Local Test (should work):**
```bash
curl http://localhost:8080/health
```

**Public Test (should work after DNS propagates):**
```bash
curl https://archive.your-domain.com/health
```

**Browser Test:**
- Main UI: `https://archive.your-domain.com/ui/index.html`
- Metrics: `https://archive.your-domain.com/ui/metrics-panel.html`
- API Docs: `https://archive.your-domain.com/docs`

---

## Step 10: Run Tunnel as System Service

Make the tunnel start automatically on boot:

```bash
# Install as systemd service
sudo cloudflared service install

# Start service
sudo systemctl start cloudflared

# Enable on boot
sudo systemctl enable cloudflared

# Check status
sudo systemctl status cloudflared
```

---

## Architecture Diagram

```
Internet
   ↓
Cloudflare Edge Network (SSL, DDoS protection)
   ↓
Cloudflare Tunnel (encrypted)
   ↓
Your Server - localhost:8080 (Brain service)
   ├─→ /ui/            → Static UI files
   ├─→ /docs           → API documentation
   ├─→ /health         → Health check
   ├─→ /chat           → Chat API
   ├─→ /metrics        → Metrics API
   └─→ Internal Services (not publicly accessible)
       ├─→ Vorpal (localhost:8000)
       ├─→ Goblin (localhost:8081)
       ├─→ Redis (localhost:6379)
       ├─→ Voice (localhost:8001)
       └─→ Sandbox (localhost:8003)
```

---

## Security Best Practices

### 1. Firewall Configuration

Since Cloudflare Tunnel handles external access, block direct internet access:

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Block all other external access
sudo ufw deny 6379  # Redis
sudo ufw deny 8000  # Vorpal
sudo ufw deny 8001  # Voice
sudo ufw deny 8003  # Sandbox
sudo ufw deny 8080  # Brain (access via Cloudflare only)
sudo ufw deny 8081  # Goblin

# Enable firewall
sudo ufw enable
```

**Note:** Port 8080 doesn't need to be open externally - Cloudflare Tunnel handles it!

### 2. Cloudflare Security Settings

In your Cloudflare dashboard:

1. **SSL/TLS Mode:** Set to "Full" or "Full (strict)"
2. **Enable WAF** (Web Application Firewall) - Free tier available
3. **Enable Rate Limiting** - Protect against abuse
4. **DDoS Protection** - Automatic on all plans

### 3. Environment Variables

Never commit your `.env` file:

```bash
# Add to .gitignore
echo ".env" >> .gitignore
```

Rotate passwords periodically:

```bash
# Generate new Redis password
openssl rand -base64 32
```

---

## Troubleshooting

### Tunnel Won't Start

**Check tunnel status:**
```bash
cloudflared tunnel info archive-ai
```

**Check config syntax:**
```bash
cloudflared tunnel --config ~/.cloudflared/config.yml validate
```

**Check credentials file path:**
```bash
ls -la ~/.cloudflared/*.json
```

### Can't Access Publicly

**Test local access first:**
```bash
curl http://localhost:8080/health
```

**Check DNS propagation:**
```bash
dig archive.your-domain.com
```

Should show a CNAME to `<TUNNEL-ID>.cfargotunnel.com`

**Check tunnel logs:**
```bash
# If running as service
sudo journalctl -u cloudflared -f

# If running manually
cloudflared tunnel run archive-ai
```

### Services Not Communicating

**Check Docker network:**
```bash
docker network inspect archive-ai_archive-net
```

**Test internal connectivity:**
```bash
docker exec archive-brain-cf curl http://vorpal:8000/health
```

### 502 Bad Gateway

**Brain service not ready:**
```bash
# Check Brain logs
docker-compose logs -f brain

# Verify Brain health
curl http://localhost:8080/health
```

**Vorpal still loading model:**
```bash
# Vorpal can take 2-5 minutes to load 7B model
docker-compose logs -f vorpal
```

---

## Performance Optimization

### 1. Cloudflare Caching

Cache static assets (UI files):

In Cloudflare Dashboard → Caching → Configuration:
- Cache Level: Standard
- Browser Cache TTL: 4 hours
- Page Rules:
  - `archive.your-domain.com/ui/*` → Cache Everything

### 2. Compression

Enable Brotli compression in Cloudflare:
- Dashboard → Speed → Optimization → Brotli ✓

### 3. Argo Tunnel (Paid)

For better latency, upgrade to Argo Smart Routing (~$5/month):
- Reduces latency by routing through faster Cloudflare paths
- Improves performance for international users

---

## Monitoring

### Cloudflare Analytics

Monitor tunnel health in Cloudflare Dashboard:
- Analytics → Traffic
- Analytics → Attacks (WAF events)
- Analytics → Performance

### Archive-AI Metrics

Access metrics dashboard:
- `https://your-domain.com/ui/metrics-panel.html`
- Shows CPU, RAM, GPU usage
- Request rates and latency
- Service health

### Health Checks

```bash
# Local health check
bash scripts/health-check.sh

# Remote health check
curl https://your-domain.com/health
```

---

## Costs

**Cloudflare:**
- Free tier: ✅ Unlimited bandwidth, basic DDoS protection
- Pro tier ($20/month): Advanced DDoS, image optimization
- Business tier ($200/month): Custom SSL, 100% uptime SLA

**Archive-AI:**
- Zero marginal cost (runs on your hardware)
- Electricity cost for GPU server (~$50-150/month depending on usage)

**Total:** Can run entirely on free tier! 🎉

---

## Advanced: Multiple Tunnels

Run development and production environments:

```yaml
# ~/.cloudflared/config.yml
tunnel: <TUNNEL-ID>
credentials-file: ~/.cloudflared/<TUNNEL-ID>.json

ingress:
  # Production
  - hostname: ai.your-domain.com
    service: http://localhost:8080

  # Development
  - hostname: dev-ai.your-domain.com
    service: http://localhost:8081

  - service: http_status:404
```

---

## Backup and Disaster Recovery

### Backup Tunnel Config

```bash
# Backup tunnel credentials
cp ~/.cloudflared/*.json ~/backups/

# Backup config
cp ~/.cloudflared/config.yml ~/backups/

# Backup Archive-AI data
tar -czf archive-ai-backup.tar.gz data/ .env
```

### Restore on New Server

```bash
# Install cloudflared
# ... (see Step 1)

# Restore credentials
cp ~/backups/*.json ~/.cloudflared/
cp ~/backups/config.yml ~/.cloudflared/

# Restore Archive-AI
tar -xzf archive-ai-backup.tar.gz

# Start tunnel
cloudflared tunnel run archive-ai
```

---

## Migration from Standard Setup

If you're already running Archive-AI locally:

1. **Stop current setup:**
   ```bash
   ./shutdown.sh
   ```

2. **Update configuration:**
   ```bash
   # Edit .env
   nano .env
   # Add: PUBLIC_URL=https://your-domain.com
   # Add: TRUST_PROXY=true
   ```

3. **Start with Cloudflare config:**
   ```bash
   ./go-cloudflare.sh
   ```

4. **Data is preserved** - Redis data, memories, archives all migrate automatically

---

## Support

**Issues:**
- Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- Archive-AI: https://github.com/yourusername/archive-ai/issues

**Community:**
- Cloudflare Discord: https://discord.cloudflare.com
- Archive-AI discussions: See repository

---

**Version:** 1.0
**Last Updated:** 2026-01-04
**Compatible with:** Archive-AI v7.5+
