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
    "afk": False,
    "afk_reason": "",
    "antidelete": True,
    "sec_pv": False,
    "dice_active": False,
    "dice_target": None,
    "slot_active": False,
    "slot_target": 64,
    "loops": {},
    "tags": []
}

CLOCK_STYLES = {
    1: ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"],
    2: ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
    3: ["⓿", "❶", "❷", "❸", "❹", "❺", "❻", "❼", "❽", "❾"],
    4: ["𝟢", "𝟣", "𝟤", "𝟥", "𝟦", "𝟧", "𝟨", "𝟩", "𝟪", "𝟫"]
}

# ==================== HELPER FUNCTIONS ====================
def get_styled_time(style_num):
    tz = timezone('Asia/Tehran')
    now = datetime.now(tz).strftime("%H:%M")
    digits = CLOCK_STYLES.get(style_num, CLOCK_STYLES[1])
    styled = ""
    for char in now:
        if char.isdigit():
            styled += digits[int(char)]
        else:
            styled += char
    return styled

def get_dashboard_text():
    clock_status = f"🟢 فعال (استایل {STATE['clock_style']})" if STATE["clock"] else f"🔴 خاموش | استایل {STATE['clock_style']}"
    afk_status = "🟢 فعال" if STATE["afk"] else "🔴 خاموش"
    antidel_status = "🟢 فعال" if STATE["antidelete"] else "🔴 خاموش"
    sec_status = "🟢 فعال" if STATE["sec_pv"] else "🔴 خاموش"
    
    dice_st = "🔴 خاموش"
    if STATE["dice_active"]:
        dice_st = f"🟢 روشن (هدف: {STATE['dice_target']})"
        
    slot_st = "🔴 خاموش"
    if STATE["slot_active"]:
        slot_st = f"🟢 روشن (هدف: {STATE['slot_target']})"

    return f"""⚡️ **منوی راهنما و کنترل سلف‌بات**
━━━━━━━━━━━━━━━━━━━━
⏰ **ساعت روی اسم:** [ {clock_status} ]
🌙 **حالت غیبت (AFK):** [ {afk_status} ]
🛡 **ضد پاکسازی:** [ {antidel_status} ]
🤖 **منشی پیام شخصی:** [ {sec_status} ]
🎲 **تاس شانس:** [ {dice_st} ]
🎰 **اسلات شانس:** [ {slot_st} ]
━━━━━━━━━━━━━━━━━━━━

🔍 **دستورات اصلی:**

🎲🎰 **تاس و اسلات:**
• `.rdice on [even/odd/1-6]` ➔ تنظیم تاس
• `.rdice off` ➔ خاموش کردن تاس
• `.rslot on` / `.rslot off` ➔ اسلات خودکار

⚡️ **تنظیمات سیستم:**
• `.help` / `.panel` ➔ نمایش این راهنما
• `.clock` ➔ روشن/خاموش ساعت
• `.clockstyle [1-4]` ➔ تغییر فونت ساعت
• `.ping` ➔ بررسی وضعیت سلف‌بات

🔄 **ارسال زمان‌بندی شده:**
• `.loop [آیدی/چت] [ثانیه] [متن]` ➔ شروع ارسال تکراری
• `.loops` ➔ لیست حلقه‌های فعال
• `.stoploop` ➔ توقف تمام ارسال‌ها

🌐 **ابزارهای مدیریت:**
• `.tags` ➔ ارسال گزارش منشن‌ها به Saved Messages
• `.cleartags` ➔ پاکسازی تاریخچه منشن‌ها
• `.del [تعداد]` ➔ پاکسازی پیام‌های خودت
• `.calc [عبارت]` ➔ ماشین حساب ریاضی
• `.purge` ➔ پاکسازی گروهی روی ریپلای"""

# ==================== CLOCK TASK ====================
async def clock_loop():
    while True:
        if STATE["clock"]:
            try:
                me = await app.get_me()
                time_str = get_styled_time(STATE["clock_style"])
                base_name = re.sub(r'\s*\|?\s*[\d۰-۹⓿-❾𝟢-𝟫]+:[\d۰-۹⓿-❾𝟢-𝟫]+', '', me.first_name).strip()
                new_name = f"{base_name} | {time_str}"
                if me.first_name != new_name:
                    await app.update_profile(first_name=new_name)
            except Exception as e:
                print(f"Clock Error: {e}")
        await asyncio.sleep(60)

# ==================== HANDLERS ====================

# پشتیبانی همزمان از .help و .panel
@app.on_message(filters.me & filters.command(["panel", "help"], prefixes="."))
async def show_panel(client, message: Message):
    await message.edit_text(get_dashboard_text())

@app.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping_handler(client, message: Message):
    start = datetime.now()
    reply = await message.edit_text("🚀 در حال بررسی وضعیت...")
    end = datetime.now()
    ms = (end - start).microseconds / 1000
    await reply.edit_text(f"⚡️ **سلف‌بات آنلاین است!**\nپینگ: `{ms:.1f}ms`")

# ---------------- CLOCK COMMANDS ----------------
@app.on_message(filters.me & filters.command("clock", prefixes="."))
async def toggle_clock(client, message: Message):
    STATE["clock"] = not STATE["clock"]
    st = "روشن 🟢" if STATE["clock"] else "خاموش 🔴"
    await message.edit_text(f"⏰ **ساعت روی اسم {st} شد.**")

@app.on_message(filters.me & filters.command("clockstyle", prefixes="."))
async def change_clock_style(client, message: Message):
    try:
        style = int(message.command[1])
        if style in CLOCK_STYLES:
            STATE["clock_style"] = style
            await message.edit_text(f"🎨 **استایل ساعت به حالت {style} تغییر کرد.**")
        else:
            await message.edit_text("❌ استایل معتبر نیست (۱ تا ۴).")
    except:
        await message.edit_text("❌ نحوه استفاده: `.clockstyle 1`")

# ---------------- TAG / MENTION TRACKER ----------------
# ضبط تگ‌ها در پس‌زمینه بدون ارسال پیام لحظه‌ای
@app.on_message(filters.mentioned & ~filters.me)
async def mention_tracker(client, message: Message):
    if message.chat.username:
        msg_link = f"https://t.me/{message.chat.username}/{message.id}"
    else:
        chat_id_str = str(message.chat.id).replace("-100", "")
        msg_link = f"https://t.me/c/{chat_id_str}/{message.id}"

    sender_name = message.from_user.first_name if message.from_user else "ناشناس"
    chat_title = message.chat.title if message.chat.title else "چت شخصی"

    tag_data = {
        "link": msg_link,
        "sender": sender_name,
        "chat": chat_title,
        "text": message.text or message.caption or "رسانه / ایموجی",
        "time": datetime.now(timezone('Asia/Tehran')).strftime("%H:%M")
    }
    
    # فقط ذخیره در حافظه
    STATE["tags"].append(tag_data)

# نمایش و ارسال تگ‌ها به Saved Messages فقط هنگام زدن دستور .tags
@app.on_message(filters.me & filters.command("tags", prefixes="."))
async def show_tags(client, message: Message):
    if not STATE["tags"]:
        await message.edit_text("📭 **هیچ منشن جدیدی ثبت نشده است.**")
        return

    text = "📌 **گزارش منشن‌ها و تگ‌های جدید:**\n━━━━━━━━━━━━━━━━━━━━\n"
    for idx, t in enumerate(STATE["tags"][-15:], 1):
        text += f"{idx}. 👥 **{t['chat']}** | 👤 {t['sender']} (`{t['time']}`)\n"
        text += f"   📝 {t['text'][:50]}\n"
        text += f"   🔗 [ورود به پیام]({t['link']})\n\n"

    text += "━━━━━━━━━━━━━━━━━━━━\n💡 *برای پاکسازی لیست دستور `.cleartags` را بزنید.*"
    
    # ویرایش پیام دستور و ارسال گزارش کامل به Saved Messages
    await message.edit_text("✅ **لیست منشن‌ها به Saved Messages ارسال شد.**")
    await client.send_message("me", text, disable_web_page_preview=True)

@app.on_message(filters.me & filters.command("cleartags", prefixes="."))
async def clear_tags(client, message: Message):
    STATE["tags"].clear()
    await message.edit_text("🧹 **لیست منشن‌ها کاملاً پاکسازی شد.**")

# ---------------- LOOP COMMANDS (اصلاح شده) ----------------
@app.on_message(filters.me & filters.command("loop", prefixes="."))
async def start_loop(client, message: Message):
    try:
        args = message.command
        if len(args) < 4:
            await message.edit_text("❌ **نحوه استفاده:**\n`.loop [آیدی یا چت] [زمان به ثانیه] [متن پیام]`\n\nمثال:\n`.loop @username 10 سلام روز بخیر`")
            return

        target = args[1]
        seconds = int(args[2])
        text = " ".join(args[3:])

        async def loop_worker(target_chat, sec, msg_text):
            while True:
                try:
                    await client.send_message(target_chat, msg_text)
                except Exception as err:
                    print(f"Loop Error: {err}")
                await asyncio.sleep(sec)

        task = asyncio.create_task(loop_worker(target, seconds, text))
        task_id = len(STATE["loops"]) + 1
        STATE["loops"][task_id] = {"task": task, "target": target, "sec": seconds, "text": text}
        
        await message.edit_text(f"🔄 **ارسال تکراری فعال شد!**\n\n🎯 **هدف:** `{target}`\n⏱ **فاصله:** هر `{seconds}` ثانیه\n📝 **متن:** {text}")
    except Exception as e:
        await message.edit_text(f"❌ **خطا در تنظیم ارسال تکراری:** {e}")

@app.on_message(filters.me & filters.command("loops", prefixes="."))
async def list_loops(client, message: Message):
    if not STATE["loops"]:
        await message.edit_text("📭 **هیچ ارسال تکراری فعال نیست.**")
        return
    
    txt = "🔄 **لیست حلقه‌های ارسال فعال:**\n\n"
    for lid, ldata in STATE["loops"].items():
        txt += f"🔹 **شناسه:** `{lid}` | به: `{ldata['target']}` | هر `{ldata['sec']}` ثانیه\n"
    txt += "\n🛑 برای توقف همگی دستور `.stoploop` را بزنید."
    await message.edit_text(txt)

@app.on_message(filters.me & filters.command("stoploop", prefixes="."))
async def stop_loops(client, message: Message):
    if not STATE["loops"]:
        await message.edit_text("📭 هیچ حلقه فعال نیست.")
        return
        
    for lid, ldata in STATE["loops"].items():
        ldata["task"].cancel()
    STATE["loops"].clear()
    await message.edit_text("🛑 **تمام ارسال‌های تکراری متوقف شدند.**")

# ---------------- DICE & SLOT COMMANDS ----------------
@app.on_message(filters.me & filters.command("rdice", prefixes="."))
async def rdice_handler(client, message: Message):
    if len(message.command) < 2:
        await message.edit_text("❌ راهنما: `.rdice on` یا `.rdice off`")
        return
    
    sub = message.command[1].lower()
    if sub == "off":
        STATE["dice_active"] = False
        await message.edit_text("🎲 **تاس خودکار خاموش شد.**")
    elif sub == "on":
        target = message.command[2].lower() if len(message.command) > 2 else "even"
        STATE["dice_active"] = True
        STATE["dice_target"] = target
        await message.edit_text(f"🎲 **تاس خودکار فعال شد!**\nهدف: `{target}`")

@app.on_message(filters.me & filters.command("rslot", prefixes="."))
async def rslot_handler(client, message: Message):
    if len(message.command) < 2:
        await message.edit_text("❌ راهنما: `.rslot on` یا `.rslot off`")
        return
    
    sub = message.command[1].lower()
    if sub == "off":
        STATE["slot_active"] = False
        await message.edit_text("🎰 **اسلات خودکار خاموش شد.**")
    elif sub == "on":
        STATE["slot_active"] = True
        STATE["slot_target"] = 64
        await message.edit_text("🎰 **اسلات خودکار فعال شد!**")

# ---------------- GENERAL UTILITIES ----------------
@app.on_message(filters.me & filters.command("del", prefixes="."))
async def delete_messages(client, message: Message):
    try:
        count = int(message.command[1])
        async for msg in client.get_chat_history(message.chat.id, limit=count + 1):
            if msg.from_user and msg.from_user.is_self:
                await msg.delete()
    except Exception:
        await message.edit_text("❌ تعداد را مشخص کنید. مثال: `.del 5`")

@app.on_message(filters.me & filters.command("calc", prefixes="."))
async def calculator(client, message: Message):
    try:
        expr = " ".join(message.command[1:])
        result = eval(expr)
        await message.edit_text(f"🧮 **محاسبه:** `{expr}`\n✅ **نتیجه:** `{result}`")
    except Exception:
        await message.edit_text("❌ عبارت ریاضی نامعتبر است.")

@app.on_message(filters.me & filters.command("purge", prefixes="."))
async def purge_msgs(client, message: Message):
    if not message.reply_to_message:
        await message.edit_text("❌ روی پیام شروع پاکسازی ریپلای کنید.")
        return
    start_id = message.reply_to_message.id
    end_id = message.id
    msg_ids = list(range(start_id, end_id + 1))
    await client.delete_messages(message.chat.id, msg_ids)

# ==================== MAIN INITIALIZATION ====================
async def main():
    await app.start()
    asyncio.create_task(clock_loop())
    print("✅ Selfbot Started Successfully!")
    # زنده نگه داشتن سرور اکشنز
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
