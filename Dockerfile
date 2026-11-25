FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install base tools and Xvfb
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    unzip \
    xvfb \
    ca-certificates \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install official Google Chrome Stable
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends ./google-chrome-stable_current_amd64.deb \
    && rm -f google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV PORT=10000
ENV THREADS=35
ENV TARGET_URL=https://guns.lol/osintowner

# Start Xvfb virtual display, wait 2s for X11 socket, then launch 35-worker turbo bot
CMD sh -c "Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & sleep 2 && python guns_viewbot.py -u $TARGET_URL -t $THREADS"
