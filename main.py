import asyncio
import os
import re
from datetime import datetime
from pytz import timezone
from pyrogram import Client, filters
from pyrogram.types import Message

# ==================== CONFIGURATION ====================
API_ID = int(os.getenv("API_ID", "6"))
API_HASH = os.getenv("API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e")
SESSION_STRING = os.getenv("SESSION_STRING", "")

if SESSION_STRING:
    app = Client("my_selfbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    app = Client("my_selfbot", api_id=API_ID, api_hash=API_HASH)

# ==================== STATE MANAGEMENT ====================
STATE = {
    "clock": False,
    "clock_style": 1,
    "original_name": "",
    "dice_active": False,
    "dice_target": "even",
    "slot_active": False,
}

CLOCK_STYLES = {
    1: ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"],
    2: ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
}

def get_styled_time(style_num):
    tz = timezone('Asia/Tehran')
    now = datetime.now(tz).strftime("%H:%M")
    digits = CLOCK_STYLES.get(style_num, CLOCK_STYLES[1])
    return "".join(digits[int(c)] if c.isdigit() else c for c in now)

# ==================== CLOCK LOOP ====================
async def clock_loop():
    last_time = ""
    while True:
        try:
            if STATE["clock"]:
                time_str = get_styled_time(STATE["clock_style"])
                if time_str != last_time:
                    base_name = STATE["original_name"]
                    new_name = f"{base_name} | {time_str}"
                    await app.update_profile(first_name=new_name)
                    last_time = time_str
            await asyncio.sleep(20)
        except Exception as e:
            print(f"Clock Error (Safe Mode): {e}")
            await asyncio.sleep(30)

# ==================== COMMAND HANDLERS ====================
@app.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping_handler(client, message: Message):
    start = datetime.now()
    reply = await message.edit_text("🚀 در حال بررسی...")
    ms = (datetime.now() - start).microseconds / 1000
    await reply.edit_text(f"⚡️ **سلف‌بات فعال و پایدار است.**\nپینگ: `{ms:.1f}ms`")

@app.on_message(filters.me & filters.command("clock", prefixes="."))
async def toggle_clock(client, message: Message):
    STATE["clock"] = not STATE["clock"]
    if STATE["clock"]:
        await message.edit_text("⏰ **ساعت اسم روشن شد 🟢**")
    else:
        try:
            if STATE["original_name"]:
                await app.update_profile(first_name=STATE["original_name"])
        except Exception:
            pass
        await message.edit_text("⏰ **ساعت اسم خاموش شد 🔴**")

@app.on_message(filters.me & filters.command("rdice", prefixes="."))
async def rdice_command(client, message: Message):
    if len(message.command) < 2:
        await message.edit_text("❌ دستور اشتباه.\nاستفاده: `.rdice on` یا `.rdice off`")
        return
    sub = message.command[1].lower()
    if sub == "on":
        STATE["dice_active"] = True
        STATE["dice_target"] = message.command[2].lower() if len(message.command) > 2 else "even"
        await message.edit_text(f"🎲 **تاس خودکار روشن شد!**\nهدف: `{STATE['dice_target']}`\n(حالا توی گروه یک ایموجی 🎲 بفرست)")
    else:
        STATE["dice_active"] = False
        await message.edit_text("🎲 **تاس خودکار خاموش شد.**")

@app.on_message(filters.me & filters.command("rslot", prefixes="."))
async def rslot_command(client, message: Message):
    if len(message.command) < 2:
        await message.edit_text("❌ دستور اشتباه.\nاستفاده: `.rslot on` یا `.rslot off`")
        return
    sub = message.command[1].lower()
    if sub == "on":
        STATE["slot_active"] = True
        await message.edit_text("🎰 **اسلات خودکار روشن شد!**\n(حالا توی گروه یک ایموجی 🎰 بفرست تا خودش برات تکرار کنه)")
    else:
        STATE["slot_active"] = False
        await message.edit_text("🎰 **اسلات خودکار خاموش شد.**")

# ==================== GAME TRIGGER (EASY TRIGGER) ====================
@app.on_message(filters.me & filters.dice)
async def auto_game_trigger(client, message: Message):
    # اگر ایموجی تاس فرستادی و حالت تاس روشن بود
    if message.dice.emoji == "🎲" and STATE["dice_active"]:
        val = message.dice.value
        target = STATE["dice_target"]
        hit = False
        if target == "even" and val % 2 == 0: hit = True
        elif target == "odd" and val % 2 != 0: hit = True
        elif str(target) == str(val): hit = True

        if not hit:
            await asyncio.sleep(2.5) # تاخیر برای بلاک نشدن
            if STATE["dice_active"]:
                await client.send_dice(message.chat.id, emoji="🎲")
        else:
            await client.send_message(message.chat.id, f"🎯 **برنده شدی! عدد:** `{val}`")
            STATE["dice_active"] = False

    # اگر ایموجی اسلات فرستادی و حالت اسلات روشن بود
    elif message.dice.emoji == "🎰" and STATE["slot_active"]:
        val = message.dice.value
        if val != 64: # 64 یعنی ۷۷۷ (جک‌پات)
            await asyncio.sleep(2.5)
            if STATE["slot_active"]:
                await client.send_dice(message.chat.id, emoji="🎰")
        else:
            await client.send_message(message.chat.id, "🎉 **جک‌پات ۷۷۷ زدی!**")
            STATE["slot_active"] = False

# ==================== MAIN ====================
async def main():
    try:
        await app.start()
        me = await app.get_me()
        STATE["original_name"] = re.sub(r'\s*\|?\s*[\d۰-۹]+:[\d۰-۹]+', '', me.first_name).strip()
        asyncio.create_task(clock_loop())
        print("✅ Selfbot Online & Safe!")
        await asyncio.Event().wait()
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
