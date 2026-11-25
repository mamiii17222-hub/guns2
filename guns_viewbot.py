#!/usr/bin/env python3
"""
guns.lol Mega-Turbo Automated View Bot (Enterprise Multi-Core & Render Scaled)
Engineered for 12 CPU Cores & 96 GB RAM Architecture
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
from concurrent.futures import ThreadPoolExecutor

# Setuptools distutils compat for Python 3.12+ / 3.14+
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
    print("[!] 'requests' kütüphanesi eksik. Yükleniyor...")
    os.system(f"{sys.executable} -m pip install requests")
    import requests

try:
    import undetected_chromedriver as uc
except ImportError:
    print("[!] 'undetected-chromedriver' eksik. Yükleniyor...")
    os.system(f"{sys.executable} -m pip install undetected-chromedriver setuptools")
    import undetected_chromedriver as uc

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


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


class Stats:
    def __init__(self):
        self.sent = 0
        self.success = 0
        self.failed = 0
        self.active_proxies = 0
        self.lock = threading.Lock()
        self.start_time = time.time()

    def add_success(self):
        with self.lock:
            self.sent += 1
            self.success += 1

    def add_fail(self):
        with self.lock:
            self.sent += 1
            self.failed += 1

    def print_progress(self, target):
        elapsed = max(1, int(time.time() - self.start_time))
        rate = round(self.success / elapsed, 2)
        rate_min = int(rate * 60)
        rate_hour = int(rate * 3600)
        sys.stdout.write(
            f"\r{Colors.CYAN}[Hedef: {target}]{Colors.RESET} "
            f"{Colors.GREEN}Başarılı: {self.success}{Colors.RESET} | "
            f"{Colors.RED}Drop: {self.failed}{Colors.RESET} | "
            f"{Colors.YELLOW}Hız: {rate} v/s ({rate_min} v/dk ~ {rate_hour} v/saat){Colors.RESET} | "
            f"{Colors.BLUE}Süre: {elapsed}s{Colors.RESET} | "
            f"{Colors.HEADER}Havuz: {self.active_proxies}{Colors.RESET}"
        )
        sys.stdout.flush()


def test_cf_proxy(p):
    """Ultra hızlı Cloudflare trace testi."""
    try:
        r = requests.get(
            "https://cloudflare.com/cdn-cgi/trace",
            proxies={"http": f"http://{p}", "https": f"http://{p}"},
            timeout=2.0
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


def proxy_producer_loop(verified_queue, stats, stop_event):
    """100 eşzamanlı iş parçacığıyla havuzu sürekli dolu tutar."""
    while not stop_event.is_set():
        if verified_queue.qsize() < 100:
            candidates = fetch_live_candidates()
            with ThreadPoolExecutor(max_workers=100) as ex:
                results = ex.map(test_cf_proxy, candidates[:600])
                for p in results:
                    if p:
                        verified_queue.put(p)
                        with stats.lock:
                            stats.active_proxies = verified_queue.qsize()
        time.sleep(4)


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

    if proxy:
        if not proxy.startswith("http"):
            options.add_argument(f"--proxy-server=http://{proxy}")
        else:
            options.add_argument(f"--proxy-server={proxy}")

    driver = uc.Chrome(options=options)
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


def worker(target_url, verified_queue, stats, timeout):
    while True:
        proxy = None
        if verified_queue is not None:
            try:
                proxy = verified_queue.get(timeout=3)
                with stats.lock:
                    stats.active_proxies = verified_queue.qsize()
            except queue.Empty:
                time.sleep(0.2)
                continue

        driver = None
        try:
            driver = create_driver(proxy=proxy)
            driver.set_page_load_timeout(timeout)
            driver.get(target_url)

            success = False
            iterations = int(timeout / 0.2)
            for _ in range(iterations):
                time.sleep(0.2)
                done = driver.execute_script("return window.__analytics_done || false;")
                if done:
                    status = driver.execute_script("return window.__analytics_status || 0;")
                    if status == 200:
                        success = True
                    break

            if success:
                stats.add_success()
            else:
                stats.add_fail()

        except Exception:
            stats.add_fail()
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            if verified_queue:
                verified_queue.task_done()

        stats.print_progress(target_url)


def start_dummy_health_server():
    """Render Web Service'in 7/24 uyanık kalması için HTTP port dinleyicisi."""
    port = int(os.environ.get("PORT", 10000))
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Guns.lol Mega-Turbo Viewbot 24/7 Running Active.")
        def log_message(self, format, *args):
            pass
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def main():
    default_threads = int(os.environ.get("THREADS", 35))
    default_target = os.environ.get("TARGET_URL", "https://guns.lol/osintowner")

    parser = argparse.ArgumentParser(description="guns.lol Mega-Turbo View Bot (12 CPU / 96 GB RAM Scaled)")
    parser.add_argument("-u", "--url", "--user", dest="target", default=default_target, help=f"Guns.lol hedefi (varsayılan: {default_target})")
    parser.add_argument("-t", "--threads", type=int, default=default_threads, help=f"Eşzamanlı browser worker sayısı (varsayılan: {default_threads})")
    parser.add_argument("--timeout", type=int, default=12, help="View bekleme zaman aşımı saniye (varsayılan: 12)")
    parser.add_argument("-p", "--proxy-file", dest="proxy_file", help="Özel proxy listesi dosyası (.txt)")
    parser.add_argument("--direct", action="store_true", help="Proxy olmadan doğrudan bağlantı ile çalıştır")
    args = parser.parse_args()

    if "PORT" in os.environ or os.environ.get("RENDER"):
        threading.Thread(target=start_dummy_health_server, daemon=True).start()

    print(f"{Colors.CYAN}{'='*60}")
    print("      GUNS.LOL MEGA-TURBO CLOUD VIEW BOT [7/24 RENDER]")
    print(f"           Scaled for High Concurrency (Worker: {args.threads})")
    print(f"{'='*60}{Colors.RESET}")

    target = args.target.strip()
    if not target.startswith("http"):
        target = f"https://guns.lol/{target.lstrip('@')}"

    verified_queue = None
    stop_event = threading.Event()
    stats = Stats()

    if not args.direct:
        verified_queue = queue.Queue()
        if args.proxy_file and os.path.exists(args.proxy_file):
            print(f"{Colors.YELLOW}[*] '{args.proxy_file}' dosyasındaki proxyler yükleniyor...{Colors.RESET}")
            with open(args.proxy_file, "r", encoding="utf-8") as f:
                p_lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
            for p in p_lines:
                verified_queue.put(p)
            stats.active_proxies = verified_queue.qsize()
            print(f"{Colors.GREEN}[+] {stats.active_proxies} adet özel proxy hazır!{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}[*] 100-thread Turbo Proxy Doğrulayıcı motoru başlatılıyor...{Colors.RESET}")
            producer_t = threading.Thread(target=proxy_producer_loop, args=(verified_queue, stats, stop_event), daemon=True)
            producer_t.start()
            
            print(f"{Colors.YELLOW}[*] İlk havuz dolduruluyor, lütfen bekleyin...{Colors.RESET}")
            for _ in range(15):
                time.sleep(1)
                if verified_queue.qsize() >= 5:
                    break
            print(f"{Colors.GREEN}[+] {verified_queue.qsize()} adet canlı Cloudflare proxy hazırlandı!{Colors.RESET}")

    thread_count = args.threads

    print(f"\n{Colors.GREEN}[*] Hedef: {target}{Colors.RESET}")
    print(f"{Colors.GREEN}[*] Worker Sayısı: {thread_count}{Colors.RESET}")
    print(f"{Colors.GREEN}[*] Mod: {'Doğrulanmış Canlı Proxy Havuzu' if verified_queue else 'Direct Connection'}{Colors.RESET}")
    print(f"{Colors.YELLOW}[*] Mega-Turbo bot başlatılıyor... (Durdurmak için CTRL+C){Colors.RESET}\n")

    threads = []
    for _ in range(thread_count):
        t = threading.Thread(target=worker, args=(target, verified_queue, stats, args.timeout), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(0.5)
            stats.print_progress(target)
    except KeyboardInterrupt:
        stop_event.set()
        print(f"\n\n{Colors.YELLOW}[!] İşlem kullanıcı tarafından durduruldu.{Colors.RESET}")

    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"Toplam Gönderim : {stats.sent}")
    print(f"Başarılı View   : {stats.success}")
    print(f"Hatalı / Drop   : {stats.failed}")
    print(f"{'='*60}{Colors.RESET}")


if __name__ == "__main__":
    main()
