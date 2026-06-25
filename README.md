# Daily Briefing

An automated morning briefing that fetches live weather and news, generates a spoken script with Claude, converts it to audio with edge-tts, and emails it to you every day.

---

## How It Works

Each morning the scheduler wakes up and runs the pipeline: it pulls current weather from wttr.in and top headlines from GNews, sends both to the Anthropic Claude API to write a polished 90-second radio-style script, passes the script to Microsoft Edge TTS to produce an MP3, and finally emails you both the audio file and the text transcript via Gmail SMTP — all without any manual input.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DAILY BRIEFING PIPELINE                  │
└─────────────────────────────────────────────────────────────────┘

  ┌───────────────┐     ┌───────────────┐
  │  wttr.in API  │     │  GNews API    │
  │  (weather)    │     │  (headlines)  │
  └──────┬────────┘     └──────┬────────┘
         │                     │
         └──────────┬──────────┘
                    │ weather dict + article list
                    ▼
          ┌─────────────────┐
          │  Claude API     │
          │  (script gen)   │
          │  claude-sonnet  │
          └────────┬────────┘
                   │ plain-text script (~600 words)
                   ▼
          ┌─────────────────┐
          │  Edge TTS       │
          │  (en-GB-Sonia)  │
          └────────┬────────┘
                   │ briefing_YYYY-MM-DD.mp3
                   ▼
          ┌─────────────────┐
          │  Gmail SMTP     │
          │  (port 587 TLS) │
          └────────┬────────┘
                   │ email with MP3 attachment + text body
                   ▼
             📬 Your Inbox
```

---

## Prerequisites

- **Python 3.10+** — uses `match` statements and modern type hints.
- **Anthropic API key** — sign up at [console.anthropic.com](https://console.anthropic.com).
- **GNews API key** — free tier at [gnews.io](https://gnews.io) (100 requests/day).
- **Gmail App Password** — generate one at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords); requires 2-Step Verification to be enabled on the Google account.

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/daily-briefing.git
   cd daily-briefing
   ```

2. **Create and activate a virtual environment** (recommended)

   ```bash
   python -m venv .venv
   # macOS / Linux
   source .venv/bin/activate
   # Windows
   .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Open `.env` in any text editor and fill in every variable (see [Configuration](#configuration) below).

---

## Configuration

All secrets and preferences are stored in `.env` (never committed to git).

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key.  Find it in the [Anthropic Console](https://console.anthropic.com) under *API Keys*. |
| `GNEWS_API_KEY` | Your GNews API key.  Copy it from your [GNews dashboard](https://gnews.io/dashboard) after signing up. |
| `GMAIL_ADDRESS` | The Gmail address used to **send** the email, e.g. `yourname@gmail.com`. |
| `GMAIL_APP_PASSWORD` | A 16-character Google App Password (not your regular Gmail password).  Generate one at *Google Account → Security → App Passwords*. |
| `TO_EMAIL` | The recipient email address where the briefing should be delivered.  Can be the same as `GMAIL_ADDRESS`. |

---

## How to Run Manually

Run the full pipeline once immediately:

```bash
python main.py
```

The MP3 is saved to `output/briefing_YYYY-MM-DD.mp3` and an email is sent to `TO_EMAIL`.

---

## How to Run the Scheduler

Keep the scheduler alive as a long-running process to get a briefing every morning at 07:00:

```bash
python scheduler/schedule.py
```

Leave the terminal open, or run it as a background service (see below).  The default fire time is **07:00 local time** and can be changed by editing `scheduler/schedule.py`.

**Running as a background service on Linux (systemd):**

```ini
# /etc/systemd/system/daily-briefing.service
[Unit]
Description=Daily Briefing Scheduler

[Service]
WorkingDirectory=/path/to/daily-briefing
ExecStart=/path/to/.venv/bin/python scheduler/schedule.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now daily-briefing
```

---

## Project Structure

```
daily-briefing/
├── .env                      # Your local secrets (git-ignored)
├── .env.example              # Template — copy to .env and fill in values
├── .gitignore                # Ignores .env, output MP3s, and __pycache__
├── requirements.txt          # Python package dependencies
├── README.md                 # This file
├── config.py                 # Loads and validates all environment variables
├── main.py                   # Pipeline entry point — run this directly
├── fetchers/
│   ├── __init__.py           # Package marker
│   ├── weather.py            # Fetches current weather from wttr.in (free, no key)
│   └── news.py               # Fetches top headlines from the GNews API
├── generator/
│   ├── __init__.py           # Package marker
│   └── script.py             # Calls Claude API to write the spoken briefing script
├── tts/
│   ├── __init__.py           # Package marker
│   └── synthesize.py         # Converts the script text to an MP3 via edge-tts
├── delivery/
│   ├── __init__.py           # Package marker
│   └── email_sender.py       # Emails the MP3 and script via Gmail SMTP (port 587)
├── scheduler/
│   ├── __init__.py           # Package marker
│   └── schedule.py           # APScheduler cron job — fires the pipeline daily at 07:00
└── output/
    └── .gitkeep              # Keeps the output directory in git; MP3s are git-ignored
```

---

## Cost Breakdown

| Service | Cost |
|---|---|
| **wttr.in** (weather) | Free — no account or API key needed |
| **GNews** (news) | Free tier: 100 requests/day, 10 articles/request — well within limits for one daily run |
| **Anthropic Claude API** | ~$0.004 per day (based on ~600-token prompt + ~600-token response with claude-sonnet pricing as of 2025) |
| **edge-tts** (TTS) | Free — uses Microsoft Edge's neural TTS service |
| **Gmail SMTP** (email) | Free — standard Gmail account with App Password |

**Total estimated cost: ~$0.004/day (~$1.50/year).**

---

## Troubleshooting

### SMTP port 587 is blocked

Some corporate networks and ISPs block outbound port 587.  Try switching to port 465 (implicit TLS):

```python
# In delivery/email_sender.py, replace smtplib.SMTP with:
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
    server.sendmail(...)
```

If both ports are blocked, you may need to use a different SMTP relay (e.g. SendGrid, Mailgun) or run the script on a cloud VM with unrestricted outbound access.

### edge-tts install issues on Windows

If `pip install edge-tts` fails or `edge-tts` commands hang on Windows, try:

1. **Upgrade pip** first: `python -m pip install --upgrade pip`
2. **Install the wheel directly**: `pip install edge-tts --only-binary :all:`
3. If you get a `RuntimeError: Event loop is closed` error when running the script, ensure you are using Python 3.10+ and that no other library is closing the asyncio event loop before `edge-tts` finishes.  The `synthesize_audio` function handles this with `asyncio.run()`.
4. On some Windows systems you may need to install the Microsoft Visual C++ Redistributable if a dependency fails to build.

### API key errors

- **`EnvironmentError: Required environment variable 'X' is not set`** — you have not filled in `.env`.  Copy `.env.example` to `.env` and add all five values.
- **`anthropic.AuthenticationError`** — your `ANTHROPIC_API_KEY` is wrong or has been revoked.  Double-check it in the [Anthropic Console](https://console.anthropic.com).
- **`requests.HTTPError: 401`** on GNews — your `GNEWS_API_KEY` is invalid.  Log in to [gnews.io](https://gnews.io) and confirm the key.
- **`smtplib.SMTPAuthenticationError`** — you have entered your regular Gmail password instead of an App Password, or the App Password has been revoked.  Generate a new one at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

---

## License

MIT License — see [LICENSE](LICENSE) for details.
