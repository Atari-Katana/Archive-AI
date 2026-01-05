#!/bin/bash
# Update Cloudflare Tunnel to point to Archive-AI
# Archive-AI v7.5 - Cloudflare Tunnel Update Script

set -euo pipefail

echo "🔧 Updating Cloudflare Tunnel Configuration..."
echo ""

# 1. Copy config files to system location
echo "📋 Step 1: Copying configuration files to /etc/cloudflared/"
sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/config.yml
sudo cp ~/.cloudflared/cert.pem /etc/cloudflared/cert.pem
echo "✓ Config files copied"
echo ""

# 2. Update the systemd service to use config file instead of token
echo "📝 Step 2: Updating systemd service..."
sudo tee /etc/systemd/system/cloudflared.service > /dev/null << 'EOF'
[Unit]
Description=cloudflared
After=network-online.target
Wants=network-online.target

[Service]
TimeoutStartSec=15
Type=notify
ExecStart=/usr/bin/cloudflared --no-autoupdate tunnel run vorpal-tunnel
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
echo "✓ Service file updated"
echo ""

# 3. Reload systemd and restart service
echo "🔄 Step 3: Restarting cloudflared service..."
sudo systemctl daemon-reload
sudo systemctl restart cloudflared
echo "✓ Service restarted"
echo ""

# 4. Wait a moment for service to start
sleep 3

# 5. Check status
echo "📊 Step 4: Checking service status..."
sudo systemctl status cloudflared --no-pager -l || true
echo ""

# 6. Update DNS routing
echo "🌐 Step 5: Updating DNS routing..."
echo ""
echo "Run these commands to set up DNS for archive.newvictoria.org:"
echo ""
echo "  cloudflared tunnel route dns vorpal-tunnel archive.newvictoria.org"
echo "  cloudflared tunnel route dns vorpal-tunnel www.archive.newvictoria.org"
echo ""
echo "Or update via Cloudflare Dashboard:"
echo "  1. Go to https://dash.cloudflare.com/"
echo "  2. Select your domain: newvictoria.org"
echo "  3. Go to DNS > Records"
echo "  4. Add CNAME record: archive -> fb082968-b56a-4dba-a2a9-e1e7264e27b7.cfargotunnel.com"
echo ""

echo "✅ Cloudflare tunnel update complete!"
echo ""
echo "Test your tunnel:"
echo "  Local:  http://localhost:8080/health"
echo "  Remote: https://archive.newvictoria.org/health"
echo ""
