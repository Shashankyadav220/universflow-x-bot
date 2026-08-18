"""
Univers Flow — X (Twitter) auto-poster (Selenium version).
Generates a post with Gemini, then posts it to X via browser automation.
No X API needed — runs 100% free on GitHub Actions.

Run locally to preview WITHOUT posting:
    python post.py --dry-run
"""

import os
import sys
import json
import time
import random
import pathlib
import requests
from knowledge import UNIVERS_FLOW_KNOWLEDGE

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

X_EMAIL    = os.environ.get("X_EMAIL", "")
X_PASSWORD = os.environ.get("X_PASSWORD", "")
X_USERNAME = os.environ.get("X_USERNAME", "")

TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")

HISTORY_FILE = pathlib.Path("history.json")
MAX_LEN      = 275

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

# ----------------------------------------------------------------------------
# History
# ----------------------------------------------------------------------------

def load_history():
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            return []
        except Exception:
            return []
    return []

def save_history(history):
    HISTORY_FILE.write_text(
        json.dumps(history[-60:], ensure_ascii=False, indent=2), encoding="utf-8"
    )

# ----------------------------------------------------------------------------
# Gemini
# ----------------------------------------------------------------------------

def build_prompt(angle, history):
    recent = "\n".join(f"- {h}" for h in history[-15:]) or "(no posts yet)"
    return f"""You are the social media voice of Univers Flow, writing ONE tweet (X post).

Use ONLY the facts in this knowledge base:
{UNIVERS_FLOW_KNOWLEDGE}

ANGLE FOR THIS POST:
{angle}

RULES:
- Sound like a real person, casual and natural.
- UNDER 275 characters total.
- 0-2 emojis max, sometimes none.
- 0-2 hashtags max, often none.
- Include https://universflow.in only sometimes (about half the posts).
- NO corporate buzzwords or "Check out our app!".

AVOID repeating these recent posts:
{recent}

Output ONLY the tweet text. No quotes, no labels, no explanation."""


def generate_post(history):
    angle  = random.choice(ANGLES)
    prompt = build_prompt(angle, history)

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 1.0,
            "topP": 0.95,
            "maxOutputTokens": 200,
        },
    }

    data = None
    for attempt in range(4):
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            data = r.json()
            break
        if r.status_code == 429:
            time.sleep(30 * (attempt + 1))
            continue
        print(f"Gemini error {r.status_code}: {r.text}")
        r.raise_for_status()

    if data is None:
        raise RuntimeError("Gemini rate-limited after retries.")

    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = text.strip().strip('"').strip("'").strip()
    return text, angle

# ----------------------------------------------------------------------------
# Post to X via Selenium
# ----------------------------------------------------------------------------

def post_to_x_selenium(text):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options

    print("Starting Chrome...")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    wait   = WebDriverWait(driver, 40)

    try:
        # Step 1: Open login page
        print("Opening X login page...")
        driver.get("https://x.com/i/flow/login")
        time.sleep(5)
        driver.save_screenshot("/tmp/step1.png")
        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")

        # Step 2: Find and fill email input — try multiple selectors
        print("Entering email...")
        email_input = None
        selectors = [
            'input[autocomplete="username"]',
            'input[name="text"]',
            'input[type="text"]',
        ]
        for sel in selectors:
            try:
                email_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                print(f"Found input with: {sel}")
                break
            except Exception:
                continue

        if not email_input:
            driver.save_screenshot("/tmp/selenium_error.png")
            raise RuntimeError("Could not find email input. Screenshot saved.")

        email_input.click()
        time.sleep(0.5)
        for char in X_EMAIL:
            email_input.send_keys(char)
            time.sleep(0.04)
        time.sleep(1)
        email_input.send_keys(Keys.RETURN)
        time.sleep(4)
        driver.save_screenshot("/tmp/step2.png")

        # Step 3: Handle unusual activity check (username prompt)
        try:
            unusual = WebDriverWait(driver, 6).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[data-testid="ocfEnterTextTextInput"]')
                )
            )
            print("Unusual activity check — entering username...")
            for char in X_USERNAME:
                unusual.send_keys(char)
                time.sleep(0.04)
            unusual.send_keys(Keys.RETURN)
            time.sleep(4)
        except Exception:
            print("No unusual activity check, continuing...")

        # Step 4: Enter password
        print("Entering password...")
        pwd_input = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'input[name="password"]')
        ))
        pwd_input.click()
        time.sleep(0.5)
        for char in X_PASSWORD:
            pwd_input.send_keys(char)
            time.sleep(0.04)
        time.sleep(1)
        pwd_input.send_keys(Keys.RETURN)
        time.sleep(6)
        driver.save_screenshot("/tmp/step3.png")
        print(f"URL after login: {driver.current_url}")

        # Step 5: Verify login
        if "login" in driver.current_url:
            driver.save_screenshot("/tmp/selenium_error.png")
            raise RuntimeError("Login failed — check X_EMAIL and X_PASSWORD.")

        # Step 6: Click compose button
        print("Finding compose button...")
        time.sleep(2)
        compose_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'a[data-testid="SideNav_NewTweet_Button"]')
        ))
        compose_btn.click()
        time.sleep(3)
        driver.save_screenshot("/tmp/step4.png")

        # Step 7: Type post text
        print("Typing post text...")
        tweet_box = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]')
        ))
        tweet_box.click()
        time.sleep(0.5)
        for char in text:
            tweet_box.send_keys(char)
            time.sleep(0.03)
        time.sleep(2)
        driver.save_screenshot("/tmp/step5.png")

        # Step 8: Click Post button
        print("Clicking Post button...")
        post_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button[data-testid="tweetButtonInline"]')
        ))
        post_btn.click()
        time.sleep(5)
        driver.save_screenshot("/tmp/step6.png")

        print("✅ Posted to X successfully!")
        return True

    except Exception as e:
        driver.save_screenshot("/tmp/selenium_error.png")
        raise e
    finally:
        driver.quit()

# ----------------------------------------------------------------------------
# Telegram
# ----------------------------------------------------------------------------

def send_telegram(message):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=30,
        )
    except Exception as e:
        print(f"(Telegram notify failed: {e})")


def post_to_telegram_channel(text):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID):
        return
    body = text if "universflow.in" in text else f"{text}\n\n🎧 universflow.in"
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHANNEL_ID, "text": body},
            timeout=30,
        )
        print("Posted to Telegram channel." if r.status_code == 200 else f"Telegram failed: {r.text[:200]}")
    except Exception as e:
        print(f"(Telegram channel failed: {e})")

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    dry_run = "--dry-run" in sys.argv

    if not GEMINI_API_KEY:
        sys.exit("ERROR: GEMINI_API_KEY is not set.")

    history     = load_history()
    text, angle = generate_post(history)

    if len(text) > MAX_LEN:
        text = text[:MAX_LEN - 1].rstrip() + "…"

    print(f"Angle : {angle}")
    print(f"Length: {len(text)} chars")
    print("-" * 50)
    print(text)
    print("-" * 50)

    if dry_run:
        print("DRY RUN — not posting to X.")
        return

    if not X_EMAIL or not X_PASSWORD:
        sys.exit("ERROR: X_EMAIL or X_PASSWORD is not set.")

    post_to_x_selenium(text)
    post_to_telegram_channel(text)

    tweet_url = f"https://x.com/{X_USERNAME}" if X_USERNAME else "https://x.com/"
    send_telegram(f"✅ Univers Flow posted on X:\n\n\"{text}\"\n\n🔗 {tweet_url}")

    history.append(text)
    save_history(history)


if __name__ == "__main__":
    main()
