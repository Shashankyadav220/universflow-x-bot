# Univers Flow — Free X (Twitter) Auto-Poster 🎵🤖

An AI agent that writes human-sounding posts about **Univers Flow** and posts
them to X automatically — on a schedule — for **$0**. It runs on GitHub Actions
(free), generates each post with **Google Gemini** (free tier), and posts via
the **X API** (free tier).

You set it up once (~10 min). After that it runs itself forever.

---

## What's in here
| File | What it does |
|------|--------------|
| `post.py` | Generates a human-style post with Gemini and posts it to X |
| `knowledge.py` | Everything about Univers Flow (edit anytime to change what it knows) |
| `.github/workflows/auto_post.yml` | The free scheduler (runs 10am + 6pm IST daily) |
| `requirements.txt` | Python packages |
| `history.json` | Auto-created — remembers recent posts so it never repeats |

---

## Setup — do this once

### 1. Create a GitHub repo
1. Go to https://github.com/new
2. Name it e.g. `universflow-x-bot`, set it to **Public** (free unlimited Actions minutes), click **Create**.
3. Upload all these files (keep the `.github/workflows/` folder structure). Easiest: "Add file → Upload files", drag everything in.

### 2. Get your X (Twitter) API keys — FREE
1. Go to https://developer.x.com → sign in with your **@Univers Flow** account → apply for a **Free** developer account.
2. Create a **Project** + **App**.
3. In the app's **Settings → User authentication settings**: set permissions to **Read and Write**. (Important — do this BEFORE making tokens.)
4. Go to **Keys and tokens** and generate:
   - **API Key** and **API Key Secret**
   - **Access Token** and **Access Token Secret**  ← regenerate these AFTER setting Read and Write
5. Copy all four somewhere safe.

> ⚠️ The #1 mistake: generating the Access Token BEFORE setting "Read and Write".
> If posting fails with a 403, regenerate the Access Token + Secret after fixing permissions.

### 3. Get your Gemini API key — FREE
1. Go to https://aistudio.google.com/apikey
2. Click **Create API key**, copy it.

### 4. Add all 5 keys as GitHub Secrets
In your repo: **Settings → Secrets and variables → Actions → New repository secret**.
Add these five (names must match EXACTLY):

| Secret name | Value |
|-------------|-------|
| `GEMINI_API_KEY` | your Gemini key |
| `X_API_KEY` | X API Key |
| `X_API_SECRET` | X API Key Secret |
| `X_ACCESS_TOKEN` | X Access Token |
| `X_ACCESS_SECRET` | X Access Token Secret |

**Optional but recommended — Telegram ping when it posts:**
| Secret name | Value |
|-------------|-------|
| `TELEGRAM_BOT_TOKEN` | your Telegram bot token (from @BotFather) |
| `TELEGRAM_CHAT_ID` | your chat ID (where the alert is sent) |
| `X_USERNAME` | your X handle, e.g. `Universflowapp` (makes the link clean) |

### 5. Test it
1. Go to the **Actions** tab in your repo → enable workflows if prompted.
2. Click **Univers Flow X Auto-Poster → Run workflow** (manual run button).
3. Watch the log. If it says `Posted to X. Tweet ID: ...` → 🎉 check your X profile.

That's it. From now on it posts automatically at **10:00 AM and 6:00 PM IST** every day.

---

## Optional: Get a Telegram message every time it posts 🔔

Free, takes 3 minutes.

### Get your bot token
1. In Telegram, search for **@BotFather** → start it.
2. Send `/newbot`, follow the prompts (name it e.g. "Univers Flow Alerts").
3. BotFather gives you a **token** like `123456:ABC-xyz...` — that's `TELEGRAM_BOT_TOKEN`.

### Get your chat ID
1. Search for **@userinfobot** in Telegram → start it → it replies with your **Id** (a number). That's `TELEGRAM_CHAT_ID`.
2. **Important:** open YOUR new bot (the one you made in step above) and tap **Start / send it "hi"** once. A bot can't message you until you message it first.

### Add them as GitHub Secrets
Add `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and (optional) `X_USERNAME` in
**Settings → Secrets and variables → Actions** — same as the others.

Now every time the bot posts, you'll get a Telegram message with the exact text
and a link to the tweet. If you skip this, the bot still works fine — the ping
just won't send.

---

## Customizing

**Change post times:** edit the `cron` lines in `.github/workflows/auto_post.yml`.
Times are UTC (India = UTC+5:30). Examples:
- Once a day at 9am IST → `30 3 * * *` (and delete the second line)
- Every 6 hours → `0 */6 * * *`

**Change how it talks / what it knows:** edit `knowledge.py` (the facts) or the
`ANGLES` list and `VOICE & STYLE RULES` in `post.py` (the tone).

**Preview posts without publishing (on your own computer):**
```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here      # Windows: set GEMINI_API_KEY=...
python post.py --dry-run
```

---

## Cost & limits (all free)
- **GitHub Actions:** free & unlimited for public repos.
- **Gemini API:** free tier is far more than 2 posts/day needs.
- **X API free tier:** allows posting (writes). 2/day ≈ 60/month — well within limits.

100% free. No surprises.
