from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        args=["--disable-blink-features=AutomationControlled"]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
    page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))
    page.on("request", lambda req: print(f"[REQ] {req.method} {req.url}") if "analytics" in req.url or "turnstile" in req.url or "challenge" in req.url else None)
    page.on("response", lambda res: print(f"[RES] {res.status} {res.url}") if "analytics" in res.url or "challenge" in res.url else None)

    print("Navigating...")
    page.goto("https://guns.lol/osintowner", wait_until="commit")
    
    for i in range(15):
        time.sleep(1)
        has_turnstile = page.evaluate("() => typeof window.turnstile !== 'undefined'")
        has_getToken = page.evaluate("() => typeof window.getToken !== 'undefined'")
        print(f"Sec {i+1}: turnstile={has_turnstile}, getToken={has_getToken}")
        if has_turnstile and has_getToken:
            # check if turnstile rendered
            ts_res = page.evaluate("""() => {
                let el = document.querySelector('.cf-turnstile');
                return el ? el.outerHTML : 'no .cf-turnstile';
            }""")
            print("Turnstile element:", ts_res)
    
    browser.close()
