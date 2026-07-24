import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import DAILY_CHECK_HOUR_UTC
from db.session import get_session
from db.models import Keyword, RankSnapshot, Project, User
from core.serp_client import check_rank, SerpClientError

logger = logging.getLogger(__name__)


async def run_daily_rank_check(bot):
    """Checks every active keyword, stores a snapshot, and notifies the owner on big moves."""
    session = get_session()
    try:
        keywords = session.query(Keyword).filter(Keyword.active == 1).all()
        logger.info("Daily rank check: %d keywords to process", len(keywords))

        for kw in keywords:
            project: Project = kw.project
            try:
                position, url = check_rank(
                    term=kw.term,
                    domain=project.domain,
                    engine=kw.engine,
                    device=kw.device,
                    location_code=kw.location_code,
                    language_code=kw.language_code,
                )
            except SerpClientError as e:
                logger.warning("SERP check failed for keyword %s: %s", kw.id, e)
                continue

            previous = (
                session.query(RankSnapshot)
                .filter(RankSnapshot.keyword_id == kw.id)
                .order_by(RankSnapshot.checked_at.desc())
                .first()
            )

            snapshot = RankSnapshot(keyword_id=kw.id, position=position, url=url)
            session.add(snapshot)
            session.commit()

            # Notify on a meaningful change (new keyword, dropped out, moved >= 5 spots)
            if bot is not None:
                owner: User = project.owner
                if previous is None:
                    continue  # first check, nothing to compare yet
                moved = None
                if previous.position and position:
                    moved = previous.position - position  # positive = improved
                if (previous.position is None and position is not None) or \
                   (previous.position is not None and position is None) or \
                   (moved is not None and abs(moved) >= 5):
                    text = _format_change_message(project.domain, kw.term, previous.position, position)
                    try:
                        await bot.send_message(owner.telegram_id, text)
                    except Exception as e:
                        logger.warning("Failed to notify user %s: %s", owner.telegram_id, e)
    finally:
        session.close()


def _format_change_message(domain, term, old_pos, new_pos):
    old_str = old_pos if old_pos is not None else "not ranked"
    new_str = new_pos if new_pos is not None else "not ranked"
    arrow = "📈" if (old_pos or 999) > (new_pos or 999) else "📉"
    return f"{arrow} {domain} — \"{term}\"\n{old_str} → {new_str}"


def start_scheduler(bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_daily_rank_check,
        trigger=CronTrigger(hour=DAILY_CHECK_HOUR_UTC, minute=0),
        args=[bot],
        id="daily_rank_check",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
