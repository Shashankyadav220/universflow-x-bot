"""
Univers Flow — X (Twitter) auto-poster.
Generates a fresh, human-sounding post about Univers Flow with Gemini,
then publishes it to X. Runs free on GitHub Actions.

Run locally to preview WITHOUT posting:
    python post.py --dry-run
"""
import os
import sys
import json
import random
import pathlib
import requests
import tweepy

from knowledge import UNIVERS_FLOW_KNOWLEDGE

# ----------------------------------------------------------------------------
# Config (all secrets come from environment variables / GitHub Secrets)
# ----------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")

X_API_KEY = os.environ.get("X_API_KEY", "")
X_API_SECRET = os.environ.get("X_API_SECRET", "")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", "")

# Optional: get a Telegram ping every time the bot posts.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
X_USERNAME = os.environ.get("X_USERNAME", "")  # e.g. Universflowapp (for clean links)

HISTORY_FILE = pathlib.Path("history.json")
MAX_LEN = 275  # keep a little buffer under X's 280 limit

# Different "angles" keep posts varied so it never feels repetitive/botty.
ANGLES = [
    "Share one specific feature and why it's genuinely useful (e.g. offline downloads, free streaming, follow artists).",
    "Ask the audience a casual, relatable music question (no link, just start a conversation).",
    "Post a relatable everyday music moment (commute, gym, study, late-night vibes) and tie it to the app naturally.",
    "Position it as a free alternative to paid streaming apps, friendly and confident (not bashing competitors hard).",
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
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_history(history):
    HISTORY_FILE.write_text(
        json.dumps(history[-60:], ensure_ascii=False, indent=2), encoding="utf-8"
    )


def build_prompt(angle, history):
    recent = "\n".join(f"- {h}" for h in history[-15:]) or "(no posts yet)"
    return f"""You are the social media voice of Univers Flow, writing ONE tweet (X post).

Use ONLY the facts in this knowledge base — never invent features or claims:
{UNIVERS_FLOW_KNOWLEDGE}

ANGLE FOR THIS POST:
{angle}

VOICE & STYLE RULES (very important — must read like a real human, not an ad):
- Sound like a real person who loves music and happens to use this app.
- Casual, natural, a bit of personality. Contractions are good.
- Keep it UNDER 275 characters total.
- Use 0 to 2 emojis max — only if they fit naturally. Sometimes use none.
- Hashtags: 0 to 2 max, only if natural (e.g. #music, #freemusic). Often none.
- Include the link https://universflow.in only SOMETIMES (roughly half the posts). When the angle is a question or pure vibe, skip the link.
- NO corporate buzzwords, NO "Check out our app!", NO excessive caps, NO clickbait.
- Vary sentence structure and openings. Don't start with the brand name every time.

AVOID repeating the wording, structure, or topic of these recent posts:
{recent}

Output ONLY the tweet text. No quotes, no explanation, no label."""


def generate_post(history):
    angle = random.choice(ANGLES)
    prompt = build_prompt(angle, history)
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 1.05,
            "topP": 0.95,
            "maxOutputTokens": 200,
        },
    }
    import time
    data = None
    for attempt in range(4):
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            data = r.json()
            break
        if r.status_code == 429:  # rate limited — wait and retry
            time.sleep(8 * (attempt + 1))
            continue
        r.raise_for_status()
    if data is None:
        raise RuntimeError("Gemini rate-limited after retries — try again later.")
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    # Strip stray wrapping quotes the model sometimes adds
    text = text.strip().strip('"').strip("'").strip()
    return text, angle


def post_to_x(text):
    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_SECRET,
    )
    return client.create_tweet(text=text)


def send_telegram(message):
    """Send a Telegram message. Silently skips if not configured.
    Never crashes the bot if Telegram fails."""
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "disable_web_page_preview": False,
            },
            timeout=30,
        )
    except Exception as e:
        print(f"(Telegram notify failed, ignoring: {e})")


def main():
    dry_run = "--dry-run" in sys.argv

    if not GEMINI_API_KEY:
        sys.exit("ERROR: GEMINI_API_KEY is not set.")

    history = load_history()
    text, angle = generate_post(history)

    if len(text) > MAX_LEN:
        text = text[: MAX_LEN - 1].rstrip() + "\u2026"

    print(f"Angle : {angle}")
    print(f"Length: {len(text)} chars")
    print("-" * 50)
    print(text)
    print("-" * 50)

    if dry_run:
        print("DRY RUN — not posting to X.")
        return

    for key, name in [
        (X_API_KEY, "X_API_KEY"),
        (X_API_SECRET, "X_API_SECRET"),
        (X_ACCESS_TOKEN, "X_ACCESS_TOKEN"),
        (X_ACCESS_SECRET, "X_ACCESS_SECRET"),
    ]:
        if not key:
            sys.exit(f"ERROR: {name} is not set.")

    resp = post_to_x(text)
    tweet_id = resp.data.get("id") if getattr(resp, "data", None) else "?"
    print(f"Posted to X. Tweet ID: {tweet_id}")

    # Build a clean link to the tweet
    if X_USERNAME and tweet_id != "?":
        tweet_url = f"https://x.com/{X_USERNAME}/status/{tweet_id}"
    elif tweet_id != "?":
        tweet_url = f"https://x.com/i/web/status/{tweet_id}"
    else:
        tweet_url = "https://x.com/"

    # Ping Telegram with what just went out
    send_telegram(
        "\u2705 Univers Flow bot just posted on X:\n\n"
        f"\u201c{text}\u201d\n\n"
        f"\U0001F517 {tweet_url}"
    )

    history.append(text)
    save_history(history)


if __name__ == "__main__":
    main()
