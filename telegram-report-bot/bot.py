import os
import sqlite3
import asyncio
from datetime import datetime
import pytz
from dateutil import parser
from openpyxl import Workbook
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
TZ = os.environ.get("TIMEZONE", "Asia/Kolkata")
REPORT_HOUR = int(os.environ.get("REPORT_HOUR", "23"))
REPORT_MINUTE = int(os.environ.get("REPORT_MINUTE", "0"))

DB_PATH = os.environ.get("DB_PATH", "data.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS links(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, platform TEXT, url TEXT UNIQUE, received_at TEXT, exported_date TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT, received_at TEXT, exported_date TEXT)")
conn.commit()

def detect_platform(text):
    lower = text.lower()
    if "youtube.com" in lower or "youtu.be" in lower:
        return "youtube"
    if "instagram.com" in lower or "instagr.am" in lower:
        return "instagram"
    if "facebook.com" in lower or "fb.watch" in lower:
        return "facebook"
    return "other"

async def store_links_from_text(user_id, text):
    tokens = text.split()
    now = datetime.now(pytz.timezone(TZ)).isoformat()
    inserted = 0
    for t in tokens:
        if "http://" in t or "https://" in t:
            url = t.strip(".,;\"'<>")
            platform = detect_platform(url)
            try:
                cur.execute("INSERT OR IGNORE INTO links(user_id, platform, url, received_at, exported_date) VALUES(?,?,?,?,NULL)", (user_id, platform, url, now))
                if cur.rowcount:
                    inserted += 1
            except Exception:
                pass
    conn.commit()
    return inserted

async def store_message(user_id, text):
    now = datetime.now(pytz.timezone(TZ)).isoformat()
    cur.execute("INSERT INTO messages(user_id, text, received_at, exported_date) VALUES(?,?,?,NULL)", (user_id, text, now))
    conn.commit()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text or ""
    links_added = await store_links_from_text(user_id, text)
    await store_message(user_id, text)
    if links_added:
        await update.message.reply_text(f"{links_added} link(s) saved")
    else:
        await update.message.reply_text("Saved")

async def send_report_for_today(application):
    tz = pytz.timezone(TZ)
    today = datetime.now(tz).date().isoformat()
    cur.execute("SELECT id, user_id, platform, url, received_at FROM links WHERE exported_date IS NULL")
    links = cur.fetchall()
    cur.execute("SELECT id, user_id, text, received_at FROM messages WHERE exported_date IS NULL")
    msgs = cur.fetchall()
    if not links and not msgs:
        return
    df_links = pd.DataFrame(links, columns=["id", "user_id", "platform", "url", "received_at"])
    df_msgs = pd.DataFrame(msgs, columns=["id", "user_id", "text", "received_at"])
    filename = f"report_{today}.xlsx"
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        if not df_links.empty:
            df_links.to_excel(writer, sheet_name="Links", index=False)
        if not df_msgs.empty:
            df_msgs.to_excel(writer, sheet_name="Messages", index=False)
    if ADMIN_ID:
        try:
            await application.bot.send_document(ADMIN_ID, document=InputFile(filename))
        except Exception:
            pass
    ids_links = [str(r[0]) for r in links]
    ids_msgs = [str(r[0]) for r in msgs]
    if ids_links:
        cur.execute(f"UPDATE links SET exported_date=? WHERE id IN ({','.join(ids_links)})", (today,))
    if ids_msgs:
        cur.execute(f"UPDATE messages SET exported_date=? WHERE id IN ({','.join(ids_msgs)})", (today,))
    conn.commit()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot active")

async def send_manual_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Not allowed")
        return
    await update.message.reply_text("Preparing report")
    await 
async def send_report_for_today(application):
    tz = pytz.timezone(TZ)
    today = datetime.now(tz).date().isoformat()
    cur.execute("SELECT id, user_id, platform, url, received_at FROM links WHERE exported_date IS NULL")
    links = cur.fetchall()
    cur.execute("SELECT id, user_id, text, received_at FROM messages WHERE exported_date IS NULL")
    msgs = cur.fetchall()
    if not links and not msgs:
        return
    filename = f"report_{today}.xlsx"
    wb = Workbook()
    if links:
        ws = wb.active
        ws.title = "Links"
        ws.append(["id", "user_id", "platform", "url", "received_at"])
        for r in links:
            ws.append([r[0], r[1], r[2], r[3], r[4]])
    if msgs:
        if links:
            ws2 = wb.create_sheet("Messages")
        else:
            ws2 = wb.active
            ws2.title = "Messages"
        ws2.append(["id", "user_id", "text", "received_at"])
        for r in msgs:
            ws2.append([r[0], r[1], r[2], r[3]])
    wb.save(filename)
    if ADMIN_ID:
        try:
            await application.bot.send_document(ADMIN_ID, document=InputFile(filename))
        except Exception:
            pass
    ids_links = [str(r[0]) for r in links]
    ids_msgs = [str(r[0]) for r in msgs]
    if ids_links:
        cur.execute(f"UPDATE links SET exported_date=? WHERE id IN ({','.join(ids_links)})", (today,))
    if ids_msgs:
        cur.execute(f"UPDATE messages SET exported_date=? WHERE id IN ({','.join(ids_msgs)})", (today,))
    conn.commit()

def schedule_jobs(scheduler, app):
    trigger = CronTrigger(day_of_week="mon-fri", hour=REPORT_HOUR, minute=REPORT_MINUTE, timezone=TZ)
    scheduler.add_job(lambda: asyncio.create_task(send_report_for_today(app)), trigger)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("sendnow", send_manual_report_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    scheduler = AsyncIOScheduler(timezone=TZ)
    schedule_jobs(scheduler, app)
    scheduler.start()
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
