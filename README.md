# guns.lol Turbo Automated View Bot (24/7 Render Ready)

Multi-threaded guns.lol view bot featuring native Cloudflare Turnstile bypass, WASM Proof-of-Work solver, live proxy validation, and 24/7 Render cloud deployment support.

## Features
- **Cloudflare Turnstile Bypass:** Runs offscreen/virtual display instances with undetected Chrome.
- **WASM Proof-of-Work:** Natively computes guns.lol client challenge.
- **Turbo Speed:** Disables unnecessary image rendering, polls analytics dispatch every 0.25s.
- **Live Proxy Engine:** Auto-scrapes and verifies HTTPS Cloudflare-compatible proxies.
- **24/7 Render Deployment:** Dockerfile with Google Chrome + Xvfb virtual display + built-in HTTP health listener on `PORT 10000`.

## Local Usage
```bash
# Run with automatic live proxy pool
python guns_viewbot.py -u https://guns.lol/osintowner -t 6

# Run with custom proxy list
python guns_viewbot.py -u https://guns.lol/osintowner -p proxies.txt -t 6
```

## Render Deployment
1. Connect this repo to Render (Web Service, Docker environment).
2. Render builds the Dockerfile and runs the bot 24/7 continuously.
# guns
