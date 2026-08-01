import asyncio
import os
import re
import sys
from datetime import datetime
from pytz import timezone
from pyrogram import Client, filters
from pyrogram.types import Message

# ==================== CONFIGURATION ====================
API_ID = int(os.getenv("API_ID", "6"))
API_HASH = os.getenv("API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e")
SESSION_STRING = os.getenv("SESSION_STRING", "")

if not SESSION_STRING:
    print("❌ ERROR: SESSION_STRING environment variable is missing or empty!")
    sys.exit(1)

app = Client("my_selfbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ==================== DEBUG HANDLER ====================
# این بخش تمام پیام‌های شما را در لاگ گیت‌هاب چاپ می‌کند تا از دریافت پیام مطمئن شویم
@app.on_message(filters.me)
async def debug_logger(client, message: Message):
    print(f"📩 Received Message: {message.text}")

@app.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping_handler(client, message: Message):
    await message.edit_text("⚡️ **سلف‌بات فعال و آنلاین است!**")

@app.on_message(filters.me & filters.command(["panel", "help"], prefixes="."))
async def show_panel(client, message: Message):
    await message.edit_text("📋 **پنل مدیریت سلف‌بات فعال است.**")

# ==================== MAIN RUNNER ====================
async def main():
    print("🔄 Starting Pyrogram Client...")
    await app.start()
    me = await app.get_me()
    print(f"✅ Logged in successfully as: {me.first_name} (ID: {me.id})")
    print("🚀 Listening for commands...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
