import os, sys, json, time, random, pathlib, requests
from knowledge import UNIVERS_FLOW_KNOWLEDGE

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
X_EMAIL        = os.environ.get("X_EMAIL", "")
X_PASSWORD     = os.environ.get("X_PASSWORD", "")
X_USERNAME     = os.environ.get("X_USERNAME", "")
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
HISTORY_FILE = pathlib.Path("history.json")
MAX_LEN = 275

ANGLES = [
    "Share one specific feature and why it's genuinely useful (e.g. offline downloads, free streaming, follow artists).",
    "Ask the audience a casual, relatable music question (no link, just start a conversation).",
    "Post a relatable everyday music moment (commute, gym, study, late-night vibes) and tie it to the app naturally.",
    "Position it as a free alternative to paid streaming apps, friendly and confident.",
    "Drop a quick tip about how to do something in the app (like saving songs for offline).",
    "Hype a benefit: zero cost, millions of songs, listen offline — keep it punchy and real.",
    "Talk to students / people who don't want to pay for music.",
    "Mention it works on Android + as a web app, super easy to start in seconds.",
    "A short, confident one-liner with personality and a soft call to try it.",
    "Celebrate the community / vibe of discovering new artists and trending tracks.",
]

def load_history():
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception as e:
            print(f"Warning: Error loading history: {e}")
            return []
    return []

def save_history(history):
    HISTORY_FILE.write_text(json.dumps(history[-60:], ensure_ascii=False, indent=2), encoding="utf-8")

def generate_post(history):
    angle = random.choice(ANGLES)
    recent = "\n".join(f"- {h}" for h in history[-15:]) or "(no posts yet)"
    prompt = f"""You are the social media voice of Univers Flow, writing ONE tweet (X post).
Use ONLY the facts in this knowledge base:
{UNIVERS_FLOW_KNOWLEDGE}

ANGLE: {angle}

RULES:
- Sound like a real person, casual and natural.
- UNDER 275 characters total.
- 0-2 emojis max, sometimes none.
- 0-2 hashtags max, often none.
- Include https://universflow.in only sometimes.
- NO corporate buzzwords.

AVOID repeating: {recent}

Output ONLY the tweet text. No quotes, no labels."""

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0,
        "max_tokens": 200,
    }

    for attempt in range(4):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                text = r.json()["choices"][0]["message"]["content"].strip().strip('"').strip("'").strip()
                return text, angle
            if r.status_code in (429, 503, 500):
                print(f"Groq error {r.status_code} (attempt {attempt + 1}/4), retrying...")
                time.sleep(15 * (attempt + 1))
                continue
            if r.status_code == 400:
                error_msg = r.json().get("error", {}).get("message", "Unknown error")
                print(f"Groq API error (400): {error_msg}")
                if "decommissioned" in error_msg.lower():
                    sys.exit(f"ERROR: Model '{GROQ_MODEL}' is decommissioned. Check https://console.groq.com/docs/models for active models.")
                r.raise_for_status()
            elif r.status_code == 404:
                error_msg = r.json().get("error", {}).get("message", "Unknown error")
                print(f"Groq API error (404): {error_msg}")
                sys.exit(f"ERROR: Model '{GROQ_MODEL}' does not exist or you don't have access. Check https://console.groq.com/docs/models for available models.")
            else:
                print(f"Unexpected error {r.status_code}: {r.text}")
                r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Request error (attempt {attempt + 1}/4): {e}")
            if attempt < 3:
                time.sleep(10)
                continue
            raise
    raise RuntimeError("Groq unavailable after retries — try again later.")

def post_to_x_selenium(text):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options

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

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 40)

    try:
        # Use twitter.com login which uses standard HTML form
        print("Opening login page...")
        driver.get("https://twitter.com/login")
        time.sleep(5)
        print(f"URL: {driver.current_url}")
        driver.save_screenshot("/tmp/step1_login.png")

        # Email
        print("Entering email...")
        email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]')))
        email_input.click()
        time.sleep(0.5)
        for char in X_EMAIL:
            email_input.send_keys(char)
            time.sleep(0.05)
        time.sleep(1)
        email_input.send_keys(Keys.RETURN)
        time.sleep(3)
        driver.save_screenshot("/tmp/step2_after_email.png")
        print(f"URL after email: {driver.current_url}")

        # Unusual activity check
        try:
            unusual = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="ocfEnterTextTextInput"]')))
            print("Username verification needed...")
            for char in X_USERNAME:
                unusual.send_keys(char)
                time.sleep(0.05)
            unusual.send_keys(Keys.RETURN)
            time.sleep(3)
        except Exception:
            print("No username verification needed.")

        # Password
        print("Entering password...")
        pwd_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="password"]')))
        print(f"Password input found. Type: {pwd_input.get_attribute('type')}")
        pwd_input.click()
        time.sleep(0.5)
        for char in X_PASSWORD:
            pwd_input.send_keys(char)
            time.sleep(0.05)
        time.sleep(1)
        driver.save_screenshot("/tmp/step3_password_filled.png")
        pwd_input.send_keys(Keys.RETURN)
        time.sleep(6)
        print(f"URL after login: {driver.current_url}")
        driver.save_screenshot("/tmp/step4_after_login.png")

        # Check login success
        if "login" in driver.current_url and "home" not in driver.current_url:
            raise RuntimeError(f"Login failed. Still at: {driver.current_url}")

        # Handle intermediate pages
        for _ in range(8):
            cur = driver.current_url
            print(f"Current: {cur}")
            if "x.com/home" in cur or "twitter.com/home" in cur:
                break
            for btn_text in ["Skip for now", "Skip", "Next", "Continue", "Done", "Agree"]:
                try:
                    btns = driver.find_elements(By.XPATH, f"//span[contains(text(), '{btn_text}')]")
                    if btns:
                        driver.execute_script("arguments[0].click();", btns[0])
                        print(f"Clicked '{btn_text}'")
                        time.sleep(3)
                        break
                except Exception as e:
                    print(f"Could not find button '{btn_text}': {e}")
                    pass
            time.sleep(3)

        # Navigate to home
        driver.get("https://x.com/home")
        time.sleep(5)
        print(f"Home: {driver.current_url}")
        driver.save_screenshot("/tmp/step5_home.png")

        # Compose
        print("Finding compose button...")
        compose_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[data-testid="SideNav_NewTweet_Button"]')))
        compose_btn.click()
        time.sleep(3)

        # Type
        print("Typing post...")
        tweet_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]')))
        tweet_box.click()
        time.sleep(0.5)
        for char in text:
            tweet_box.send_keys(char)
            time.sleep(0.03)
        time.sleep(2)

        # Submit
        print("Clicking Post button...")
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
    # Cap at Telegram's 4096 character limit
    if len(body) > 4096:
        body = body[:4093] + "..."
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
