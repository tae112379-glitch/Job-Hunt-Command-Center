"""텔레그램 알림 봇. 환경변수: TELEGRAM_BOT_TOKEN (BotFather 발급), TELEGRAM_CHAT_ID(선택, 정기 알림용).

명령: /start /top /deadline /stats
실행: python -m jobhunter.bot
"""
from __future__ import annotations
import os
from . import db


def fmt_job(j: dict) -> str:
    d = f" · 마감 {j['deadline']}" if j.get("deadline") else ""
    return f"[{j['score']}] {j['title']} - {j.get('company') or '?'}{d}\n{j['url']}"


def top_text(n: int = 5) -> str:
    with db.conn() as c:
        rows = [db.row_to_dict(r) for r in c.execute(
            "SELECT * FROM jobs WHERE status='interested' ORDER BY score DESC LIMIT ?", (n,))]
    return "\n\n".join(fmt_job(r) for r in rows) or "저장된 공고가 없습니다."


def deadline_text(days: int = 7) -> str:
    from .api import deadlines
    rows = deadlines(days)
    return "\n\n".join(fmt_job(r) for r in rows) or f"{days}일 내 마감 공고가 없습니다."


def stats_text() -> str:
    from .api import stats
    s = stats()
    parts = ", ".join(f"{k}:{v}" for k, v in s["by_status"].items())
    return f"전체 {s['total']}건\n{parts}"


def build_app(token: str):
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes

    async def reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE, text: str):
        await update.message.reply_text(text, disable_web_page_preview=True)

    async def start(u, c): await reply(u, c, "/top 추천 공고 · /deadline 마감 임박 · /stats 현황")
    async def top(u, c): await reply(u, c, top_text())
    async def dl(u, c): await reply(u, c, deadline_text())
    async def st(u, c): await reply(u, c, stats_text())

    async def daily(ctx):
        chat = os.environ.get("TELEGRAM_CHAT_ID")
        if chat:
            await ctx.bot.send_message(chat, "📌 오늘의 마감 임박\n\n" + deadline_text(3))

    app = Application.builder().token(token).build()
    for name, fn in [("start", start), ("top", top), ("deadline", dl), ("stats", st)]:
        app.add_handler(CommandHandler(name, fn))
    if app.job_queue:
        import datetime as dt
        app.job_queue.run_daily(daily, time=dt.time(9, 0))
    return app


if __name__ == "__main__":
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not tok:
        raise SystemExit("TELEGRAM_BOT_TOKEN 환경변수를 설정하세요.")
    build_app(tok).run_polling()
