import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, BufferedInputFile

from config import MAX_PROJECTS_PER_USER, MAX_KEYWORDS_PER_PROJECT
from db.session import get_session
from db.models import User, Project, Keyword, RankSnapshot
from core.serp_client import check_rank, SerpClientError
from core.audit import audit_url
from core.charts import render_rank_history

router = Router()
logger = logging.getLogger(__name__)


def _get_or_create_user(session, message: Message) -> User:
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if not user:
        user = User(telegram_id=message.from_user.id, username=message.from_user.username)
        session.add(user)
        session.commit()
    return user


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Welcome to SEO_AudittBot — your rank tracker & site auditor.\n\n"
        "<b>Commands</b>\n"
        "/newproject example.com — add a site to track\n"
        "/addkeyword &lt;project_id&gt; &lt;keyword&gt; — track a keyword\n"
        "/rankings &lt;project_id&gt; — latest positions for a project\n"
        "/history &lt;keyword_id&gt; — ranking history chart\n"
        "/audit &lt;url&gt; — run an on-page SEO audit\n"
        "/projects — list your projects\n",
        parse_mode="HTML",
    )


@router.message(Command("newproject"))
async def cmd_newproject(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Usage: /newproject example.com")
        return
    domain = command.args.strip().lower()

    session = get_session()
    try:
        user = _get_or_create_user(session, message)
        count = session.query(Project).filter_by(user_id=user.id).count()
        if count >= MAX_PROJECTS_PER_USER:
            await message.answer(f"You've hit the limit of {MAX_PROJECTS_PER_USER} projects.")
            return
        project = Project(user_id=user.id, domain=domain)
        session.add(project)
        session.commit()
        await message.answer(f"✅ Project created: {domain} (id: {project.id})")
    finally:
        session.close()


@router.message(Command("projects"))
async def cmd_projects(message: Message):
    session = get_session()
    try:
        user = _get_or_create_user(session, message)
        projects = session.query(Project).filter_by(user_id=user.id).all()
        if not projects:
            await message.answer("No projects yet. Create one with /newproject example.com")
            return
        lines = [f"#{p.id} — {p.domain} ({len(p.keywords)} keywords)" for p in projects]
        await message.answer("\n".join(lines))
    finally:
        session.close()


@router.message(Command("addkeyword"))
async def cmd_addkeyword(message: Message, command: CommandObject):
    if not command.args or len(command.args.split(maxsplit=1)) < 2:
        await message.answer("Usage: /addkeyword <project_id> <keyword>")
        return
    project_id_str, term = command.args.split(maxsplit=1)

    session = get_session()
    try:
        user = _get_or_create_user(session, message)
        project = session.query(Project).filter_by(id=int(project_id_str), user_id=user.id).first()
        if not project:
            await message.answer("Project not found.")
            return
        if len(project.keywords) >= MAX_KEYWORDS_PER_PROJECT:
            await message.answer(f"Limit of {MAX_KEYWORDS_PER_PROJECT} keywords per project reached.")
            return

        kw = Keyword(project_id=project.id, term=term.strip())
        session.add(kw)
        session.commit()

        await message.answer(f"🔎 Tracking \"{term}\" for {project.domain} — checking now...")
        try:
            position, url = check_rank(term=kw.term, domain=project.domain,
                                        engine=kw.engine, device=kw.device,
                                        location_code=kw.location_code,
                                        language_code=kw.language_code)
            session.add(RankSnapshot(keyword_id=kw.id, position=position, url=url))
            session.commit()
            pos_str = position if position is not None else "not found in top results"
            await message.answer(f"Current position: {pos_str}")
        except SerpClientError as e:
            await message.answer(f"⚠️ Initial check failed: {e}")
    finally:
        session.close()


@router.message(Command("rankings"))
async def cmd_rankings(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Usage: /rankings <project_id>")
        return

    session = get_session()
    try:
        user = _get_or_create_user(session, message)
        project = session.query(Project).filter_by(id=int(command.args.strip()), user_id=user.id).first()
        if not project:
            await message.answer("Project not found.")
            return
        if not project.keywords:
            await message.answer("No keywords tracked yet for this project.")
            return

        lines = [f"<b>{project.domain}</b>"]
        for kw in project.keywords:
            latest = (
                session.query(RankSnapshot)
                .filter_by(keyword_id=kw.id)
                .order_by(RankSnapshot.checked_at.desc())
                .first()
            )
            pos = latest.position if latest and latest.position else "—"
            lines.append(f"[{kw.id}] {kw.term}: {pos}")
        await message.answer("\n".join(lines), parse_mode="HTML")
    finally:
        session.close()


@router.message(Command("history"))
async def cmd_history(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Usage: /history <keyword_id>")
        return

    session = get_session()
    try:
        kw = session.query(Keyword).filter_by(id=int(command.args.strip())).first()
        if not kw:
            await message.answer("Keyword not found.")
            return
        snapshots = (
            session.query(RankSnapshot)
            .filter_by(keyword_id=kw.id)
            .order_by(RankSnapshot.checked_at.asc())
            .all()
        )
        if len(snapshots) < 2:
            await message.answer("Not enough history yet — check back after a couple of daily runs.")
            return

        dates = [s.checked_at for s in snapshots]
        positions = [s.position for s in snapshots]
        buf = render_rank_history(kw.term, dates, positions)
        await message.answer_photo(BufferedInputFile(buf.read(), filename="history.png"))
    finally:
        session.close()


@router.message(Command("audit"))
async def cmd_audit(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Usage: /audit https://example.com/page")
        return
    url = command.args.strip()
    await message.answer("🔍 Auditing... this takes a few seconds.")

    result = audit_url(url)
    metrics = result["metrics"]
    issues = result["issues"]

    lines = [f"<b>Audit: {url}</b>"]
    if metrics:
        lines.append(f"Title ({metrics.get('title_length', 0)} chars): {metrics.get('title') or '—'}")
        lines.append(f"Meta description ({metrics.get('meta_description_length', 0)} chars)")
        lines.append(f"H1 tags: {metrics.get('h1_count', 0)}")
        lines.append(f"Word count: {metrics.get('word_count', 0)}")
        lines.append(f"Images missing alt: {metrics.get('images_missing_alt', 0)}/{metrics.get('image_count', 0)}")

    lines.append("")
    if issues:
        lines.append(f"<b>Issues found ({len(issues)}):</b>")
        for issue in issues:
            lines.append(f"• [{issue['severity']}] {issue['message']}")
    else:
        lines.append("✅ No issues found.")

    await message.answer("\n".join(lines), parse_mode="HTML")
