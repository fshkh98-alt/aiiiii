#!/bin/bash
# Ollama Server Setup Script
# Run this on your VPS (Ubuntu/Debian)

set -e

echo "=== Installing Ollama Server ==="

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
sudo systemctl enable ollama
sudo systemctl start ollama

# Pull models
echo "=== Pulling models ==="
ollama pull llama3.2
ollama pull phi3

# Create systemd service for remote access
cat << 'EOF' | sudo tee /etc/systemd/system/ollama-remote.service
[Unit]
Description=Ollama Remote Access
After=network.target

[Service]
Type=simple
User=root
Environment="OLLAMA_HOST=0.0.0.0:11434"
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ollama-remote
sudo systemctl start ollama-remote

# Open firewall port
sudo ufw allow 11434/tcp || true
sudo iptables -I INPUT -p tcp --dport 11434 -j ACCEPT || true

echo "=== Ollama Server Ready ==="
echo "URL: http://$(curl -s ifconfig.me):11434"
echo ""
echo "Add this to Railway environment variables:"
echo "OLLAMA_HOST=http://$(curl -s ifconfig.me):11434"
