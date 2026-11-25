#!/usr/bin/env python3
"""
guns.lol Mega-Turbo Automated View Bot with Live Web Dashboard & Log Stream
Engineered for 24/7 Render Deployment (PID Safe & Memory Optimized)
Author: III
"""

import sys
import os
import time
import random
import threading
import queue
import argparse
import json
import re
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Distutils compatibility for Python 3.12+ / 3.14+
try:
    import setuptools._distutils as distutils
    import setuptools._distutils.version as distutils_version
    sys.modules['distutils'] = distutils
    sys.modules['distutils.version'] = distutils_version
except ImportError:
    pass

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests")
    import requests

try:
    import undetected_chromedriver as uc
except ImportError:
    os.system(f"{sys.executable} -m pip install undetected-chromedriver setuptools")
    import undetected_chromedriver as uc

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


LIVE_API_SOURCES = [
    "https://proxylist.geonode.com/api/proxy-list?limit=300&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?limit=300&page=2&sort_by=lastChecked&sort_type=desc",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=3000&country=all&ssl=yes",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "https://raw.githubusercontent.com/zloi-user/hideip.me/master/https.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/officialputuid/Kimmy-Proxy/master/http.txt"
]

driver_spawn_lock = threading.Lock()


class LogManager:
    def __init__(self, max_entries=200):
        self.logs = []
        self.lock = threading.Lock()
        self.max_entries = max_entries

    def emit(self, message, level="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = {"time": ts, "message": message, "level": level}
        with self.lock:
            self.logs.append(entry)
            if len(self.logs) > self.max_entries:
                self.logs.pop(0)
        print(f"[{ts}] [{level}] {message}", flush=True)

    def get_logs(self):
        with self.lock:
            return list(self.logs)


logger = LogManager()


class State:
    def __init__(self):
        self.target = "https://guns.lol/osintowner"
        self.threads = 8
        self.timeout = 22
        self.sent = 0
        self.success = 0
        self.failed = 0
        self.active_proxies = 0
        self.paused = False
        self.start_time = time.time()
        self.lock = threading.Lock()

    def add_success(self):
        with self.lock:
            self.sent += 1
            self.success += 1

    def add_fail(self):
        with self.lock:
            self.sent += 1
            self.failed += 1

    def get_metrics(self):
        with self.lock:
            elapsed = max(1, int(time.time() - self.start_time))
            rate = round(self.success / elapsed, 2)
            success_pct = round((self.success / max(1, self.sent)) * 100, 1)
            return {
                "target": self.target,
                "threads": self.threads,
                "sent": self.sent,
                "success": self.success,
                "failed": self.failed,
                "success_pct": success_pct,
                "rate_sec": rate,
                "rate_min": int(rate * 60),
                "rate_hour": int(rate * 3600),
                "active_proxies": self.active_proxies,
                "uptime_sec": elapsed,
                "paused": self.paused
            }


state = State()


def test_cf_proxy(p):
    try:
        r = requests.get(
            "https://cloudflare.com/cdn-cgi/trace",
            proxies={"http": f"http://{p}", "https": f"http://{p}"},
            timeout=2.5
        )
        if r.status_code == 200 and "ip=" in r.text:
            return p
    except Exception:
        pass
    return None


def fetch_live_candidates():
    candidates = set()
    for u in LIVE_API_SOURCES:
        try:
            r = requests.get(u, timeout=4)
            if "geonode" in u:
                data = r.json().get("data", [])
                for item in data:
                    candidates.add(f"{item['ip']}:{item['port']}")
            else:
                for l in r.text.splitlines():
                    l = l.strip()
                    if ":" in l and not l.startswith("#"):
                        candidates.add(l)
        except Exception:
            pass
    cand_list = list(candidates)
    random.shuffle(cand_list)
    return cand_list


def proxy_producer_loop(verified_queue, stop_event):
    logger.emit("100-Thread Turbo Proxy Doğrulayıcı motoru devrede.", "SYSTEM")
    while not stop_event.is_set():
        if verified_queue.qsize() < 100:
            candidates = fetch_live_candidates()
            if candidates:
                with ThreadPoolExecutor(max_workers=100) as ex:
                    results = ex.map(test_cf_proxy, candidates[:500])
                    added = 0
                    for p in results:
                        if p:
                            verified_queue.put(p)
                            added += 1
                            with state.lock:
                                state.active_proxies = verified_queue.qsize()
                    if added > 0:
                        logger.emit(f"Havuz güncellendi: +{added} yeni canlı Cloudflare proxy eklendi (Havuz: {verified_queue.qsize()})", "SUCCESS")
        time.sleep(4)


def get_chrome_executable():
    env_bin = os.environ.get("CHROME_BIN")
    if env_bin and os.path.exists(env_bin):
        return env_bin
    
    candidates = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/opt/render/project/chrome/opt/google/chrome/chrome",
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    found = shutil.which("google-chrome") or shutil.which("google-chrome-stable") or shutil.which("chrome")
    return found


def preheat_chromedriver():
    try:
        logger.emit("Chromedriver motoru önceden hazırlanıyor...", "SYSTEM")
        p = uc.Patcher()
        p.auto()
        logger.emit(f"Chromedriver hazırlandı: {p.executable_path}", "SUCCESS")
    except Exception as e:
        logger.emit(f"Chromedriver ön hazırlık uyarısı: {e}", "WARN")


def create_driver(proxy=None):
    options = uc.ChromeOptions()
    options.add_argument("--no-first-run")
    options.add_argument("--no-service-autorun")
    options.add_argument("--password-store=basic")
    options.add_argument("--window-position=-2500,-2500")
    options.add_argument("--window-size=500,500")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disk-cache-size=1")
    options.add_argument("--media-cache-size=1")
    options.add_argument("--blink-settings=imagesEnabled=false")

    chrome_bin = get_chrome_executable()
    if chrome_bin:
        options.binary_location = chrome_bin

    if proxy:
        if not proxy.startswith("http"):
            options.add_argument(f"--proxy-server=http://{proxy}")
        else:
            options.add_argument(f"--proxy-server={proxy}")

    # Eşzamanlı browser açılış çakışmalarını önleyen mutex kilidi
    with driver_spawn_lock:
        driver = uc.Chrome(options=options)
        time.sleep(0.15)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            window.__analytics_done = false;
            window.__analytics_status = 0;
            const origFetch = window.fetch;
            window.fetch = async function(...args) {
                let url = args[0];
                const res = await origFetch.apply(this, args);
                if (typeof url === 'string' && url.includes('analytics/view')) {
                    window.__analytics_done = true;
                    window.__analytics_status = res.status;
                }
                return res;
            };
        """
    })
    return driver


def worker(worker_id, verified_queue, timeout):
    while True:
        if state.paused:
            time.sleep(1)
            continue

        proxy = None
        if verified_queue is not None:
            try:
                proxy = verified_queue.get(timeout=4)
                with state.lock:
                    state.active_proxies = verified_queue.qsize()
            except queue.Empty:
                time.sleep(0.5)
                continue

        target_url = state.target
        driver = None
        try:
            driver = create_driver(proxy=proxy)
            driver.set_page_load_timeout(timeout)
            driver.get(target_url)

            success = False
            iterations = int(timeout / 0.3)
            for _ in range(iterations):
                time.sleep(0.3)
                done = driver.execute_script("return window.__analytics_done || false;")
                if done:
                    status = driver.execute_script("return window.__analytics_status || 0;")
                    if status == 200:
                        success = True
                    break

            if success:
                state.add_success()
                logger.emit(f"Worker #{worker_id} -> VIEW BAŞARILI! (Proxy: {proxy})", "SUCCESS")
            else:
                state.add_fail()
                logger.emit(f"Worker #{worker_id} -> Zaman aşımı/Drop (Proxy: {proxy})", "WARN")

        except Exception as e:
            state.add_fail()
            err_msg = str(e).split('\n')[0][:75]
            logger.emit(f"Worker #{worker_id} -> {err_msg}", "ERROR")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            if verified_queue:
                verified_queue.task_done()


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Guns.lol Turbo Viewbot Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090a0f;
            --card-bg: #11131b;
            --border: #1e2230;
            --accent: #00ffcc;
            --accent-glow: rgba(0, 255, 204, 0.25);
            --danger: #ff3366;
            --text-main: #f0f4fc;
            --text-muted: #79829c;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            padding: 24px;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
        }
        .logo {
            font-size: 24px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .badge-live {
            background: rgba(0, 255, 204, 0.15);
            color: var(--accent);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid var(--accent);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .badge-live::before {
            content: '';
            width: 8px;
            height: 8px;
            background: var(--accent);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--accent);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: transform 0.2s, border-color 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            border-color: rgba(0, 255, 204, 0.4);
        }
        .card-title {
            font-size: 13px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .card-value {
            font-size: 32px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            color: #fff;
        }
        .card-sub {
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 6px;
        }
        .terminal-container {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 480px;
        }
        .terminal-header {
            background: #0d0e14;
            padding: 12px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }
        .terminal-body {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            line-height: 1.6;
            background: #07080c;
        }
        .log-entry { margin-bottom: 4px; display: flex; gap: 12px; }
        .log-time { color: #5a647e; }
        .log-SUCCESS { color: var(--accent); }
        .log-INFO { color: #82aaff; }
        .log-WARN { color: #ffcb6b; }
        .log-ERROR { color: var(--danger); }
        .log-SYSTEM { color: #c792ea; font-weight: 600; }
        .controls {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
            background: var(--card-bg);
            border: 1px solid var(--border);
            padding: 16px;
            border-radius: 12px;
            align-items: center;
        }
        .controls input {
            flex: 1;
            background: #07080c;
            border: 1px solid var(--border);
            color: #fff;
            padding: 10px 14px;
            border-radius: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
        }
        .controls button {
            background: var(--accent);
            color: #000;
            border: none;
            padding: 10px 20px;
            font-weight: 700;
            border-radius: 8px;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        .controls button:hover { opacity: 0.9; }
        .btn-pause { background: #ffcb6b !important; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">
                <span>🔫 GUNS.LOL TURBO BOT</span>
                <span class="badge-live">7/24 CLOUD ACTIVE</span>
            </div>
            <div id="uptimeBadge" style="font-family: 'JetBrains Mono', monospace; font-size: 14px; color: var(--text-muted);">
                Uptime: 0s
            </div>
        </div>

        <div class="controls">
            <input type="text" id="targetInput" value="https://guns.lol/osintowner" placeholder="Hedef URL">
            <button onclick="updateTarget()">Hedefi Güncelle</button>
            <button id="toggleBtn" class="btn-pause" onclick="togglePause()">Durdur / Başlat</button>
        </div>

        <div class="grid">
            <div class="card">
                <div class="card-title">Başarılı View</div>
                <div class="card-value" id="valSuccess" style="color: var(--accent);">0</div>
                <div class="card-sub" id="valSuccessPct">%100 Başarı Oranı</div>
            </div>
            <div class="card">
                <div class="card-title">Anlık Hız</div>
                <div class="card-value" id="valSpeed">0.0</div>
                <div class="card-sub" id="valSpeedExt">0 view / dakika</div>
            </div>
            <div class="card">
                <div class="card-title">Aktif Worker</div>
                <div class="card-value" id="valWorkers">8</div>
                <div class="card-sub">PID Güvenli Browser</div>
            </div>
            <div class="card">
                <div class="card-title">Canlı Proxy Havuzu</div>
                <div class="card-value" id="valProxies" style="color: #c792ea;">0</div>
                <div class="card-sub">Cloudflare Doğrulanmış</div>
            </div>
        </div>

        <div class="terminal-container">
            <div class="terminal-header">
                <span>LIVE SYSTEM CONSOLE</span>
                <span id="logCount">0 logs</span>
            </div>
            <div class="terminal-body" id="terminalBody">
                <div class="log-entry"><span class="log-time">--:--:--</span><span class="log-SYSTEM">Sistem hazır, konsol akışı bağlanıyor...</span></div>
            </div>
        </div>
    </div>

    <script>
        async function fetchMetrics() {
            try {
                const res = await fetch('/api/metrics');
                const data = await res.json();
                document.getElementById('valSuccess').innerText = data.success.toLocaleString();
                document.getElementById('valSuccessPct').innerText = `%${data.success_pct} Başarı Oranı (${data.failed} drop)`;
                document.getElementById('valSpeed').innerText = `${data.rate_sec} v/s`;
                document.getElementById('valSpeedExt').innerText = `${data.rate_min} v/dk ~ ${data.rate_hour} v/saat`;
                document.getElementById('valWorkers').innerText = data.threads;
                document.getElementById('valProxies').innerText = data.active_proxies;
                document.getElementById('uptimeBadge').innerText = `Uptime: ${Math.floor(data.uptime_sec / 60)}d ${data.uptime_sec % 60}s`;
                document.getElementById('targetInput').value = data.target;
                
                const btn = document.getElementById('toggleBtn');
                if (data.paused) {
                    btn.innerText = "Devam Ettir";
                    btn.className = "btn-pause";
                } else {
                    btn.innerText = "Durdur";
                    btn.className = "";
                }
            } catch (e) {}
        }

        async function fetchLogs() {
            try {
                const res = await fetch('/api/logs');
                const logs = await res.json();
                document.getElementById('logCount').innerText = `${logs.length} logs`;
                const term = document.getElementById('terminalBody');
                term.innerHTML = logs.map(l => `
                    <div class="log-entry">
                        <span class="log-time">[${l.time}]</span>
                        <span class="log-${l.level}">${l.message}</span>
                    </div>
                `).join('');
                term.scrollTop = term.scrollHeight;
            } catch (e) {}
        }

        async function updateTarget() {
            const url = document.getElementById('targetInput').value.trim();
            if (!url) return;
            await fetch('/api/target', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({target: url})
            });
            alert('Hedef güncellendi: ' + url);
        }

        async function togglePause() {
            await fetch('/api/toggle', {method: 'POST'});
            fetchMetrics();
        }

        setInterval(fetchMetrics, 1000);
        setInterval(fetchLogs, 1500);
        fetchMetrics();
        fetchLogs();
    </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif parsed.path == "/api/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(state.get_metrics()).encode("utf-8"))
        elif parsed.path == "/api/logs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(logger.get_logs()).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_len = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else ""

        if parsed.path == "/api/target":
            try:
                data = json.loads(post_data)
                new_target = data.get("target", "").strip()
                if new_target:
                    if not new_target.startswith("http"):
                        new_target = f"https://guns.lol/{new_target.lstrip('@')}"
                    with state.lock:
                        state.target = new_target
                    logger.emit(f"Hedef URL güncellendi -> {new_target}", "SYSTEM")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception:
                self.send_response(400)
                self.end_headers()

        elif parsed.path == "/api/toggle":
            with state.lock:
                state.paused = not state.paused
            logger.emit(f"Bot durumu değiştirildi: {'DURDURULDU' if state.paused else 'ÇALIŞIYOR'}", "SYSTEM")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def start_web_server(port):
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    logger.emit(f"Web Arayüzü ve Log Dashboard PORT {port} üzerinde başlatıldı.", "SYSTEM")
    server.serve_forever()


def main():
    default_threads = int(os.environ.get("THREADS", 8))
    default_target = os.environ.get("TARGET_URL", "https://guns.lol/osintowner")
    web_port = int(os.environ.get("PORT", 10000))

    parser = argparse.ArgumentParser(description="guns.lol Mega-Turbo View Bot (PID Safe & Cloud Scaled)")
    parser.add_argument("-u", "--url", "--user", dest="target", default=default_target, help="Guns.lol hedefi")
    parser.add_argument("-t", "--threads", type=int, default=default_threads, help="Worker sayısı")
    parser.add_argument("--timeout", type=int, default=22, help="View zaman aşımı")
    parser.add_argument("-p", "--proxy-file", dest="proxy_file", help="Özel proxy dosyası")
    parser.add_argument("--direct", action="store_true", help="Proxy olmadan çalıştır")
    args = parser.parse_args()

    state.target = args.target.strip()
    if not state.target.startswith("http"):
        state.target = f"https://guns.lol/{state.target.lstrip('@')}"
    state.threads = args.threads
    state.timeout = args.timeout

    # Web Dashboard sunucusunu başlat
    threading.Thread(target=start_web_server, args=(web_port,), daemon=True).start()

    logger.emit(f"GUNS.LOL TURBO VIEW BOT AKTİF. Hedef: {state.target} | Worker: {state.threads}", "SYSTEM")

    chrome_path = get_chrome_executable()
    logger.emit(f"Tespit edilen Chrome: {chrome_path}", "INFO")

    # Chromedriver'ı ana thread'de önceden hazırla
    preheat_chromedriver()

    verified_queue = None
    stop_event = threading.Event()

    if not args.direct:
        verified_queue = queue.Queue()
        if args.proxy_file and os.path.exists(args.proxy_file):
            logger.emit(f"'{args.proxy_file}' dosyasındaki özel proxyler yükleniyor...", "INFO")
            with open(args.proxy_file, "r", encoding="utf-8") as f:
                p_lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
            for p in p_lines:
                verified_queue.put(p)
            state.active_proxies = verified_queue.qsize()
            logger.emit(f"{state.active_proxies} adet özel proxy yüklendi.", "INFO")
        else:
            producer_t = threading.Thread(target=proxy_producer_loop, args=(verified_queue, stop_event), daemon=True)
            producer_t.start()
            # Havuzun dolması için 5 saniye bekle
            time.sleep(5)

    # Worker'ları Render PID limitini aşmamak için 0.8s aralıklarla kademeli başlat
    for i in range(state.threads):
        t = threading.Thread(target=worker, args=(i + 1, verified_queue, state.timeout), daemon=True)
        t.start()
        time.sleep(0.8)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        logger.emit("Kullanıcı tarafından durduruldu.", "WARN")


if __name__ == "__main__":
    main()
