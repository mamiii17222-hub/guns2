import requests
import re

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://guns.lol/osintowner', headers=headers)
scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', r.text)

print(f"Scanning {len(scripts)} scripts...")
found_endpoints = set()

for s in scripts:
    if not s.startswith("http"):
        s = "https://guns.lol" + s
    try:
        js = requests.get(s, headers=headers, timeout=5).text
        # search for api, fetch, post, sendBeacon
        for m in re.findall(r'sendBeacon\([^\)]+\)', js):
            print(f"[{s}] sendBeacon:", m)
        for m in re.findall(r'fetch\(["\']([^"\']+)["\']', js):
            if not m.endswith('.js') and not m.endswith('.css'):
                found_endpoints.add((s, m))
        for m in re.findall(r'axios\.[a-z]+\(["\']([^"\']+)["\']', js):
            found_endpoints.add((s, m))
        for m in re.findall(r'/api/[a-zA-Z0-9_\-]+', js):
            found_endpoints.add((s, m))
    except Exception as e:
        pass

for s, ep in found_endpoints:
    print(f"Endpoint: {ep} (in {s.split('/')[-1]})")
