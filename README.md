# SEO_AudittBot

A Telegram bot that clones SERP Robot's core functionality: multi-engine keyword
rank tracking (Google/Bing/Yahoo/YouTube), on-page SEO audits, and ranking-history
charts — running on Railway with data in Postgres.

## Stack
- **aiogram 3** — Telegram bot framework (async, polling mode)
- **PostgreSQL + SQLAlchemy** — projects/keywords/rank history storage
- **APScheduler** — daily cron job that re-checks every tracked keyword
- **DataForSEO SERP API** — the actual Google/Bing/Yahoo/YouTube ranking data
- **BeautifulSoup** — on-page audit engine
- **matplotlib** — rank history chart images

## Local setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in BOT_TOKEN, DATABASE_URL, DATAFORSEO_LOGIN/PASSWORD
python main.py
```

You'll need:
1. A Telegram bot token from [@BotFather](https://t.me/BotFather) — pick the username `SEO_AudittBot` (or whatever's available) when prompted.
2. A [DataForSEO](https://dataforseo.com/) account — pay-as-you-go, no monthly minimum on the SERP API. Grab your login/password from the API Access dashboard page.
3. A local Postgres instance (or point `DATABASE_URL` at any reachable Postgres).

## Deploying to Railway

1. Push this repo to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo** → select this repo.
3. **Add a plugin → PostgreSQL.** Railway auto-injects `DATABASE_URL` into your service — you don't need to set it manually.
4. In your service's **Variables** tab, set:
   - `BOT_TOKEN`
   - `DATAFORSEO_LOGIN`
   - `DATAFORSEO_PASSWORD`
   - (optional) `DAILY_CHECK_HOUR_UTC`, `MAX_KEYWORDS_PER_PROJECT`, `MAX_PROJECTS_PER_USER`
5. Railway will build via Nixpacks and run `python main.py` (see `railway.json`/`Procfile`). Every push to your default branch auto-redeploys.
6. The bot runs in **polling mode**, so no public URL/webhook setup is needed — it just needs to stay running, which Railway handles.

## Bot commands

| Command | Description |
|---|---|
| `/newproject example.com` | Add a site to track |
| `/projects` | List your projects |
| `/addkeyword <project_id> <keyword>` | Track a keyword for a project (checks it immediately) |
| `/rankings <project_id>` | Latest positions for every keyword in a project |
| `/history <keyword_id>` | Ranking history chart (needs 2+ daily checks of data) |
| `/audit <url>` | Run an on-page SEO audit (title, meta, headings, alt text, word count, robots.txt, canonical) |

## How it works
- `/addkeyword` stores the keyword and runs an immediate check via DataForSEO.
- A daily cron job (`scheduler/jobs.py`, default 03:00 UTC) re-checks every active
  keyword, stores a new snapshot, and DMs the project owner when a keyword's
  position changes by 5+ spots, enters, or drops out of the tracked results.
- `/history` renders a matplotlib chart from stored snapshots.
- `/audit` fetches a URL live and evaluates it against on-page SEO fundamentals — no
  external API cost, since it's just HTML parsing.

## Extending this (roadmap ideas)
- Multi-engine keyword tracking is wired up in `core/serp_client.py`
  (`engine="google"|"bing"|"yahoo"|"youtube"`) — currently every keyword defaults
  to Google; add a `/setengine` command to let users choose per keyword.
- Location/device targeting already exists on the `Keyword` model
  (`location_code`, `device`, `language_code`) — DataForSEO's location codes are
  listed at https://docs.dataforseo.com/v3/appendix-locations/ — just needs bot
  commands to set them per keyword.
- Swap `db.session.init_db()` (auto-create tables) for real Alembic migrations
  once the schema stabilizes.
- Add inline keyboards instead of raw commands for a friendlier UX.
- CSV/PDF export of ranking history.
