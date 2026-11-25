#!/usr/bin/env bash
# Render Native Environment Build Script

echo "==> Render Native Build: Checking Google Chrome & Xvfb..."
if ! command -v google-chrome &> /dev/null && ! command -v google-chrome-stable &> /dev/null; then
    echo "==> Downloading and extracting Google Chrome..."
    mkdir -p /opt/render/project/chrome
    cd /tmp
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    dpkg -x google-chrome-stable_current_amd64.deb /opt/render/project/chrome
    rm google-chrome-stable_current_amd64.deb
    echo "==> Google Chrome installed to /opt/render/project/chrome"
fi

pip install -r requirements.txt
echo "==> Build complete!"
