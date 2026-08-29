import os, sys, json, time, random, pathlib, requests
from knowledge import UNIVERS_FLOW_KNOWLEDGE

GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL     = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
X_EMAIL        = os.environ.get("X_EMAIL", "")
X_PASSWORD     = os.environ.get("X_PASSWORD", "")
X_USERNAME     = os.environ.get("X_USERNAME", "")
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
HISTORY_FILE = pathlib.Path("history.json")
MAX_LEN = 275

ANGLES = [
    "Share one specific feature and why it's genuinely useful (offline downloads, free streaming, follow artists).",
    "Ask the audience a casual relatable music question - no link, just conversation.",
    "Post a relatable everyday music moment (commute, gym, study, late-night) tied to the app.",
    "Position it as a free alternative to paid streaming, friendly and confident.",
    "Quick tip about how to use the app like saving songs for offline listening.",
    "Hype a benefit: zero cost, millions of songs, listen offline - punchy and real.",
    "Talk to students and people who do not want to pay for music.",
    "Mention it works on Android and as a web app, easy to start in seconds.",
    "Short confident one-liner with personality and soft call to try it.",
    "Celebrate discovering new artists and trending tracks.",
]

def load_history():
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_history(history):
    HISTORY_FILE.write_text(json.dumps(history[-60:], ensure_ascii=False, indent=2), encoding="utf-8")

def generate_post(history):
    angle = random.choice(ANGLES)
    recent = "\n".join(f"- {h}" for h in history[-10:]) or "none"

    system = "You are a social media manager for Univers Flow music app. Write short punchy tweets. Always respond with ONLY the tweet text, nothing else. No quotes, no labels, no preamble, no explanation."

    user = f"""Write one tweet for Univers Flow music app.

App facts:
{UNIVERS_FLOW_KNOWLEDGE}

Angle: {angle}

Rules:
- Under 275 characters
- Sound like a real person, casual
- 0 to 2 emojis max
- 0 to 2 hashtags max  
- Include https://universflow.in in about half the posts
- No corporate language

Recent posts to avoid repeating:
{recent}

Reply with ONLY the tweet text."""

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": 0.9,
        "max_tokens": 150,
        "stop": ["\n\n"],
    }

    for attempt in range(4):
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            data = r.json()
            print(f"Groq raw response: {data}")
            text = data["choices"][0]["message"]["content"].strip()
            text = text.strip('"').strip("'").strip()
            if text:
                return text, angle
            print("Empty response, retrying...")
            time.sleep(5)
            continue
        if r.status_code in (429, 503, 500):
            print(f"Groq {r.status_code}, retrying in {15*(attempt+1)}s...")
            time.sleep(15 * (attempt + 1))
            continue
        print(f"Groq error {r.status_code}: {r.text}")
        if r.status_code == 404:
            try:
                models_r = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=30)
                print(f"Available Groq models: {[m['id'] for m in models_r.json().get('data', [])]}")
            except Exception as ex:
                print(f"Could not list models: {ex}")
        r.raise_for_status()
    raise RuntimeError("Groq failed after retries.")

def post_to_x_selenium(text):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 40)

    try:
        print("Opening login page...")
        driver.get("https://x.com/i/flow/login")
        time.sleep(6)
        print(f"URL: {driver.current_url}")
        driver.save_screenshot("/tmp/step1.png")

        # Find ANY visible input on the page
        print("Looking for email input...")
        email_input = None
        for attempt in range(3):
            inputs = driver.find_elements(By.TAG_NAME, "input")
            print(f"Found {len(inputs)} input(s) on page")
            for inp in inputs:
                try:
                    if inp.is_displayed():
                        print(f"  Visible input: type={inp.get_attribute('type')} name={inp.get_attribute('name')} autocomplete={inp.get_attribute('autocomplete')}")
                        email_input = inp
                        break
                except Exception:
                    continue
            if email_input:
                break
            print(f"No visible input found, waiting... (attempt {attempt+1})")
            time.sleep(3)

        if not email_input:
            driver.save_screenshot("/tmp/no_input.png")
            raise RuntimeError("No visible input found on login page.")

        print("Typing email...")
        driver.execute_script("arguments[0].click();", email_input)
        time.sleep(0.5)
        for char in X_EMAIL:
            email_input.send_keys(char)
            time.sleep(0.05)
        email_input.send_keys(Keys.RETURN)
        time.sleep(4)
        driver.save_screenshot("/tmp/step2.png")

        # Username verification check
        try:
            unusual = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="ocfEnterTextTextInput"]')))
            print("Username verification...")
            for char in X_USERNAME:
                unusual.send_keys(char)
                time.sleep(0.05)
            unusual.send_keys(Keys.RETURN)
            time.sleep(3)
        except Exception:
            print("No username verification.")

        # Password
        print("Looking for password input...")
        time.sleep(2)
        driver.save_screenshot("/tmp/step3.png")

        pwd_input = None
        for sel in ['input[name="password"]', 'input[type="password"]']:
            try:
                pwd_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                print(f"Found password: {sel}")
                break
            except Exception:
                continue

        if not pwd_input:
            # Find any input that appeared after email step
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                try:
                    t = inp.get_attribute('type')
                    if t in ('password', 'text') and inp.is_displayed():
                        pwd_input = inp
                        print(f"Found password via tag search: type={t}")
                        break
                except Exception:
                    continue

        if not pwd_input:
            raise RuntimeError("Cannot find password input.")

        # Make it clickable and type
        driver.execute_script("""
            var el = arguments[0];
            el.style.cssText = 'opacity:1!important;pointer-events:auto!important;position:relative!important;';
            el.focus();
        """, pwd_input)
        time.sleep(0.5)
        active = driver.switch_to.active_element
        for char in X_PASSWORD:
            active.send_keys(char)
            time.sleep(0.05)
        time.sleep(0.5)
        active.send_keys(Keys.RETURN)
        time.sleep(6)
        print(f"URL after login: {driver.current_url}")
        driver.save_screenshot("/tmp/step4.png")

        if "mode=login" in driver.current_url:
            raise RuntimeError(f"Login failed. URL: {driver.current_url}")

        # Handle intermediate pages
        for _ in range(8):
            cur = driver.current_url
            if "/home" in cur:
                break
            print(f"Intermediate: {cur}")
            for btn in ["Skip for now", "Skip", "Next", "Continue", "Done", "Agree"]:
                try:
                    els = driver.find_elements(By.XPATH, f"//span[text()='{btn}']")
                    if els:
                        driver.execute_script("arguments[0].click();", els[0])
                        print(f"Clicked '{btn}'")
                        time.sleep(3)
                        break
                except Exception:
                    pass
            time.sleep(3)

        driver.get("https://x.com/home")
        time.sleep(5)
        driver.save_screenshot("/tmp/step5.png")

        # Compose
        compose_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[data-testid="SideNav_NewTweet_Button"]')))
        compose_btn.click()
        time.sleep(3)

        tweet_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]')))
        tweet_box.click()
        time.sleep(0.5)
        for char in text:
            tweet_box.send_keys(char)
            time.sleep(0.03)
        time.sleep(2)

        post_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="tweetButtonInline"]')))
        post_btn.click()
        time.sleep(5)
        print("✅ Posted to X successfully!")

    except Exception as e:
        driver.save_screenshot("/tmp/selenium_error.png")
        raise e
    finally:
        driver.quit()

def send_telegram(message):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=30)
    except Exception as e:
        print(f"(Telegram failed: {e})")

def post_to_telegram_channel(text):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID):
        return
    body = text if "universflow.in" in text else f"{text}\n\n🎧 universflow.in"
    try:
        r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHANNEL_ID, "text": body}, timeout=30)
        print("Posted to Telegram." if r.status_code == 200 else f"Telegram failed: {r.text[:200]}")
    except Exception as e:
        print(f"(Telegram channel failed: {e})")

def main():
    dry_run = "--dry-run" in sys.argv
    if not GROQ_API_KEY:
        sys.exit("ERROR: GROQ_API_KEY is not set.")
    if not dry_run and (not X_EMAIL or not X_PASSWORD):
        sys.exit("ERROR: X_EMAIL or X_PASSWORD is not set.")

    history = load_history()
    text, angle = generate_post(history)

    if len(text) > MAX_LEN:
        text = text[:MAX_LEN - 1].rstrip() + "…"

    print(f"Angle : {angle}")
    print(f"Length: {len(text)} chars")
    print("-" * 50)
    print(text)
    print("-" * 50)

    if dry_run:
        print("DRY RUN — not posting.")
        return

    post_to_x_selenium(text)
    post_to_telegram_channel(text)
    tweet_url = f"https://x.com/{X_USERNAME}" if X_USERNAME else "https://x.com/"
    send_telegram(f"✅ Univers Flow posted on X:\n\n\"{text}\"\n\n🔗 {tweet_url}")
    history.append(text)
    save_history(history)

if __name__ == "__main__":
    main()
