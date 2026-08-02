import os
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

# ==========================================================
# 1. تنظیمات و پیکربندی سیشن (Session Setup)
# ==========================================================
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# استفاده از in_memory=True جهت جلوگیری از خرابی سیشن در GitHub Actions
app = Client(
    "stealth_selfbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

# متغيرهای عمومی سیستم
bot_data = {
    "afk": False,
    "afk_reason": "",
    "tags_log": [],
    "original_name": "",
    "clock_task": None
}

# امتیازهای هدف برای گیم‌ها (Dice, Slot, etc.)
TARGET_SCORES = {
    "🎰": [64],       # برد کامل اسلات (سه ۷)
    "🎲": [6],        # عدد ۶ تاس
    "🎯": [6],        # مرکز سیبل
    "🏀": [4, 5],     # گل بسکتبال
    "⚽": [3, 4, 5],  # گل فوتبال
    "🎳": [6]         # استرایک بولینگ
}

# ==========================================================
# 2. پنل مدیریت و راهنما (.panel / .help)
# ==========================================================
@app.on_message(filters.command(["panel", "help"], prefixes=".") & filters.me)
async def show_panel(client, message):
    panel_text = (
        "⚡️ **سلف‌بات پیشرفته و مخفی (Pyrogram Self-Bot)**\n\n"
        "🎮 **دستورات گیم و بازی (سیستم هوشمند):**\n"
        "├ `.roll [emoji]` - پرتاب خودکار تاس/اسلات تا رسیدن به هدف\n"
        "└ *ایموجی‌های پشتیبانی شده:* 🎲 🎰 🎯 🏀 ⚽ 🎳\n\n"
        "🏷 **دستورات تگ و فراخوانی:**\n"
        "├ `.tag [تعداد] [متن]` - تگ کردن اعضای گروه به صورت تک‌تک\n"
        "├ `.all [متن]` - تگ کردن ۵ تایی اعضا\n"
        "├ `.tagfast [متن]` - تگ سریع اعضا\n"
        "└ `.tags` - مشاهده تاریخچه و لاگ آخرین تگ‌ها\n\n"
        "⏰ **امکانات کاربردی:**\n"
        "├ `.clock` - روشن/خاموش کردن ساعت روی اسم پروفایل\n"
        "├ `.afk [علت]` - تنظیم حالت دور از دسترس\n"
        "└ `.unafk` - غیرفعال‌سازی حالت AFK\n"
    )
    await message.edit_text(panel_text)

# ==========================================================
# 3. سیستم هوشمند پرتاب تاس و اسلات (Game Automation)
# ==========================================================
@app.on_message(filters.command("roll", prefixes=".") & filters.me)
async def auto_roll(client, message):
    args = message.text.split()
    emoji = args[1] if len(args) > 1 else "🎲"
    
    if emoji not in TARGET_SCORES:
        emoji = "🎲"
        
    targets = TARGET_SCORES[emoji]
    
    # حذف دستور اولیه برای مخفی ماندن سلف‌بات در گروه
    await message.delete()
    
    attempts = 0
    max_attempts = 40  # حداکثر تلاش جهت جلوگیری از لوپ بی‌نهایت
    
    while attempts < max_attempts:
        attempts += 1
        try:
            # ارسال ایموجی شانس
            sent_msg = await client.send_dice(message.chat.id, emoji=emoji)
            score = sent_msg.dice.value
            
            # بررسی رسیدن به هدف
            if score in targets:
                break
            
            # پاک کردن پرتاب ناموفق پس از ۱ ثانیه برای خلوت ماندن گروه
            await asyncio.sleep(1.0)
            await sent_msg.delete()

            # تاخیر ۲ ثانیه‌ای برای عبور از سد Rate-Limit و لیمیت تلگرام
            await asyncio.sleep(2.0)

        except FloodWait as e:
            # مدیریت هوشمند محدودیت تلگرام
            await asyncio.sleep(e.value + 1)
        except Exception:
            break

# ==========================================================
# 4. سیستم‌های تگ‌زن و لاگر تگ (Tagging System & Logger)
# ==========================================================
@app.on_message(filters.command("tag", prefixes=".") & filters.me)
async def tag_members(client, message):
    args = message.text.split(maxsplit=2)
    count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 5
    text = args[2] if len(args) > 2 else "پینگ"
    
    await message.delete()
    chat_id = message.chat.id
    
    i = 0
    async for member in client.get_chat_members(chat_id):
        if member.user.is_bot or member.user.is_deleted:
            continue
        if i >= count:
            break
        mention = f"[{member.user.first_name}](tg://user?id={member.user.id})"
        await client.send_message(chat_id, f"{text} {mention}")
        
        # ثبت در لاگر تگ‌ها
        log_entry = f"[{datetime.now().strftime('%H:%M')}] Tagged {member.user.first_name} in {chat_id}"
        bot_data["tags_log"].append(log_entry)
        if len(bot_data["tags_log"]) > 20:
            bot_data["tags_log"].pop(0)
            
        i += 1
        await asyncio.sleep(1.5)

@app.on_message(filters.command("tags", prefixes=".") & filters.me)
async def show_tags_log(client, message):
    if not bot_data["tags_log"]:
        await message.edit_text("📜 **هیچ لاگ تگی ثبت نشده است.**")
        return
    
    logs = "\n".join(bot_data["tags_log"])
    await message.edit_text(f"📜 **آخرین لاگ‌های تگ:**\n\n{logs}")

# ==========================================================
# 5. ساعت روی اسم (Clock in Name)
# ==========================================================
async def clock_loop(client):
    while True:
        try:
            me = await client.get_me()
            if not bot_data["original_name"]:
                bot_data["original_name"] = me.first_name
                
            current_time = datetime.now().strftime("%H:%M")
            new_name = f"{bot_data['original_name']} [{current_time}]"
            
            await client.update_profile(first_name=new_name)
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            # بازگرداندن اسم اولیه هنگام خاموش کردن ساعت
            if bot_data["original_name"]:
                await client.update_profile(first_name=bot_data["original_name"])
            break
        except Exception:
            await asyncio.sleep(60)

@app.on_message(filters.command("clock", prefixes=".") & filters.me)
async def toggle_clock(client, message):
    if bot_data["clock_task"] is None or bot_data["clock_task"].done():
        bot_data["clock_task"] = asyncio.create_task(clock_loop(client))
        await message.edit_text("⏰ **ساعت روی اسم فعال شد.**")
    else:
        bot_data["clock_task"].cancel()
        bot_data["clock_task"] = None
        await message.edit_text("⏰ **ساعت روی اسم غیرفعال شد.**")

# ==========================================================
# 6. سیستم AFK (حالت دور از دسترس)
# ==========================================================
@app.on_message(filters.command("afk", prefixes=".") & filters.me)
async def set_afk(client, message):
    reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "ثبت نشده"
    bot_data["afk"] = True
    bot_data["afk_reason"] = reason
    await message.edit_text(f"🌙 **حالت AFK فعال شد.**\n📝 علت: {reason}")

@app.on_message(filters.command("unafk", prefixes=".") & filters.me)
async def unset_afk(client, message):
    bot_data["afk"] = False
    bot_data["afk_reason"] = ""
    await message.edit_text("☀️ **حالت AFK غیرفعال شد.**")

@app.on_message(filters.private & ~filters.me & ~filters.bot, group=1)
async def afk_responder(client, message):
    if bot_data["afk"]:
        reason = bot_data["afk_reason"]
        await message.reply_text(f"👋 **در حال حاضر آنلاین نیستم.**\n📝 **علت:** {reason}")

# ==========================================================
# 7. اجرای برنامه (Run Client)
# ==========================================================
if __name__ == "__main__":
    print("Self-bot is starting...")
    app.run()
