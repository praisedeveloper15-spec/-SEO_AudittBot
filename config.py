import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://", 1)

SERPAPI_KEY = os.environ["SERPAPI_KEY"]

DAILY_CHECK_HOUR_UTC = int(os.environ.get("DAILY_CHECK_HOUR_UTC", "3"))
MAX_KEYWORDS_PER_PROJECT = int(os.environ.get("MAX_KEYWORDS_PER_PROJECT", "50"))
MAX_PROJECTS_PER_USER = int(os.environ.get("MAX_PROJECTS_PER_USER", "5"))
