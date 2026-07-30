import os
import asyncio
import random
from datetime import datetime, timedelta
import pytz
from pyrogram import Client, filters
from pyrogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ----------------------------------------------------
# ⚙️ تنظیمات اتصال به تلگرام
# ----------------------------------------------------
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
STRING_SESSION = os.environ.get("STRING_SESSION")

app = Client(
    "my_selfbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION
)

scheduler = AsyncIOScheduler(timezone="Asia/Tehran")

bot_state = {
    "clock": True,
    "afk": False,
    "afk_reason": "",
    "anti_delete": True
}

YOUR_NAME = "A"

msg_store = {}
mention_store = []
muted_users = set()

# ----------------------------------------------------
# 🛡 ۱. دانلود خودکار رسانه‌های تایمردار (TTL) + ضد پاکسازی
# ----------------------------------------------------
@app.on_message(filters.private & ~filters.me)
async def auto_save_ttl_and_cache(client, message: Message):
    if message.from_user and message.from_user.id in muted_users:
        await message.delete()
        return

    msg_store[message.id] = message

    is_ttl = False
    ttl_time = message.ttl_seconds or 0

    if message.ttl_seconds:
        is_ttl = True
    elif message.photo and getattr(message.photo, "ttl_seconds", None):
        is_ttl = True
        ttl_time = message.photo.ttl_seconds
    elif message.video and getattr(message.video, "ttl_seconds", None):
        is_ttl = True
        ttl_time = message.video.ttl_seconds
    elif message.voice and getattr(message.voice, "ttl_seconds", None):
        is_ttl = True
        ttl_time = message.voice.ttl_seconds

    if is_ttl:
        try:
            file_path = await client.download_media(message)
            sender_name = message.from_user.first_name if message.from_user else "ناشناس"
            username = f"@{message.from_user.username}" if message.from_user and message.from_user.username else "ندارد"
            
            await client.send_document(
                "me", 
                document=file_path, 
                caption=(
                    f"🔥 **رسانه تایمردار (یک‌بارمصرف) خودکار ذخیره شد!**\n\n"
                    f"👤 **فرستنده:** {sender_name} ({username})\n"
                    f"⏱ **زمان تایمر:** {ttl_time} ثانیه"
                )
            )
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"خطا در دانلود خودکار فایل تایمردار: {e}")

@app.on_deleted_messages(filters.private)
async def log_deleted_messages(client, messages):
    if not bot_state["anti_delete"]:
        return
    for msg in messages:
        if msg.id in msg_store:
            saved_msg = msg_store[msg.id]
            sender_name = saved_msg.from_user.first_name if saved_msg.from_user else "ناشناس"
            username = f"@{saved_msg.from_user.username}" if saved_msg.from_user and saved_msg.from_user.username else "ندارد"
            
            await client.send_message(
                "me",
                f"🗑 **پیام حذف‌شده در پیوی کشف شد!**\n\n"
                f"👤 **فرستنده:** {sender_name} ({username})"
            )
            try:
                await saved_msg.copy("me")
            except Exception as e:
                print(f"Error copying deleted message: {e}")
                
            del msg_store[msg.id]

# ----------------------------------------------------
# 🔔 ۲. ثبت منشن‌ها و ریپلی‌ها در گروه‌ها
# ----------------------------------------------------
@app.on_message(filters.mentioned & ~filters.me)
async def capture_mentions(client, message: Message):
    sender = message.from_user.first_name if message.from_user else "ناشناس"
    chat_title = message.chat.title if message.chat.title else "گروه"
    link = message.link if message.link else "لینک ندارد"
    
    entry = f"👤 **{sender}** در گروه **{chat_title}** شما رو منشن کرد:\n💬 `{message.text or '[رسانه]'}`\n🔗 [مشاهده پیام]({link})"
    mention_store.append(entry)
    if len(mention_store) > 15:
        mention_store.pop(0)

# ----------------------------------------------------
# 📊 ۳. راهنمای کامل دستورات (.help)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("help", prefixes="."))
async def show_help(client, message):
    clock_icon = "🟢 روشن" if bot_state["clock"] else "🔴 خاموش"
    afk_icon = f"🟢 روشن ({bot_state['afk_reason']})" if bot_state["afk"] else "🔴 خاموش"
    anti_del_icon = "🟢 فعال" if bot_state["anti_delete"] else "🔴 غیرفعال"

    dashboard = f"""
📋 **داشبورد سلف‌بات اختصاصی A**
━━━━━━━━━━━━━━━━━━━━
⏰ **ساعت اسم:** [ {clock_icon} ]
🌙 **حالت AFK:** [ {afk_icon} ]
🛡 **ضد پاکسازی:** [ {anti_del_icon} ]
━━━━━━━━━━━━━━━━━━━━

🛠 **لیست دستورات کامل:**

⚡️ **مدیریت سیستم:**
• `.clock` ➔ روشن/خاموش کردن ساعت روی اسم
• `.afk [دلیل]` ➔ فعال‌سازی حالت غیبت
• `.unafk` ➔ غیرفعال‌سازی حالت غیبت

🔇 **مدیریت کاربران و چت:**
• `.mute` ➔ بی‌صدا کردن کاربر (ریپلی)
• `.unmute` ➔ لغو بی‌صدا کردن کاربر
• `.purge` ➔ پاکسازی پیام‌ها تا پیام ریپلی‌شده
• `.usernames` ➔ دیدن تاریخچه یوزرنیم‌های کاربر (ریپلی)

🌐 **ابزارهای کاربردی:**
• `.calc [عبارت]` ➔ ماشین حساب
• `.tags` ➔ مشاهده ۱۵ منشن اخیر در گروه‌ها
• `.dl` ➔ دانلود هر نوع رسانه/تایمردار (ریپلی)

🔄 **زمان‌بندی و ارسال:**
• `.loop [ID] [حداقل ثانیه] [حداکثر ثانیه] [متن]` ➔ ارسال تکراری متغیر
• `.loops` ➔ مشاهده ارسال‌های تکراری فعال
• `.stoploop` ➔ توقف تمام ارسال‌ها
• `.schedule [ID] [HH:MM] [متن]` ➔ ارسال سر ساعت مشخص

🛠 **ابزارهای عمومی:**
• `.del [تعداد]` ➔ پاکسازی پیام‌های اخیر خودت
• `.info` ➔ مشخصات کامل چت یا کاربر
• `.font [متن انگلیسی]` ➔ ساخت ۵ مدل فونت
• `.ping` ➔ تست آنلاین بودن ربات
"""
    await message.edit_text(dashboard)

# ----------------------------------------------------
# 🔇 ۴. سیستم Mute / Unmute
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("mute", prefixes="."))
async def mute_user(client, message):
    reply = message.reply_to_message
    if reply and reply.from_user:
        muted_users.add(reply.from_user.id)
        await message.edit_text(f"🔇 کاربر **{reply.from_user.first_name}** بی‌صدا شد.")
    else:
        await message.edit_text("❌ روی پیام کاربر موردنظر ریپلی کن!")

@app.on_message(filters.me & filters.command("unmute", prefixes="."))
async def unmute_user(client, message):
    reply = message.reply_to_message
    if reply and reply.from_user and reply.from_user.id in muted_users:
        muted_users.remove(reply.from_user.id)
        await message.edit_text(f"🔊 کاربر **{reply.from_user.first_name}** از حالت بی‌صدا درآمد.")
    else:
        await message.edit_text("❌ این کاربر بی‌صدا نشده است.")

# ----------------------------------------------------
# 🧹 ۵. دستور Purge (پاکسازی سریع چت) & Usernames
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("purge", prefixes="."))
async def purge_messages(client, message):
    if not message.reply_to_message:
        await message.edit_text("❌ برای پاکسازی باید روی یک پیام ریپلی کنی!")
        return
    
    start_id = message.reply_to_message.id
    end_id = message.id
    chat_id = message.chat.id
    
    msg_ids = list(range(start_id, end_id + 1))
    
    for i in range(0, len(msg_ids), 100):
        await client.delete_messages(chat_id, msg_ids[i:i + 100])
        await asyncio.sleep(1)
        
    status = await client.send_message(chat_id, f"🧹 تعداد `{len(msg_ids)}` پیام پاکسازی شد.")
    await asyncio.sleep(3)
    await status.delete()

@app.on_message(filters.me & filters.command("usernames", prefixes="."))
async def get_usernames_history(client, message):
    reply = message.reply_to_message
    user_id = reply.from_user.id if reply and reply.from_user else message.chat.id
    
    try:
        user = await client.get_users(user_id)
        text = f"👤 **مشخصات کاربر:** {user.first_name}\n"
        text += f"🆔 **آیدی عددی:** `{user.id}`\n"
        text += f"🏷 **یوزرنیم فعلی:** @{user.username if user.username else 'ندارد'}\n"
        
        if getattr(user, "usernames", None):
            old_names = [f"@{u.username}" for u in user.usernames]
            text += f"📜 **سایر یوزرنیم‌ها:** {', '.join(old_names)}"
            
        await message.edit_text(text)
    except Exception as e:
        await message.edit_text(f"❌ خطا در دریافت اطلاعات: {e}")

# ----------------------------------------------------
# 🌐 ۶. ماشین‌حساب و منشن‌ها
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("calc", prefixes="."))
async def calculator(client, message):
    if len(message.text.split()) < 2:
        await message.edit_text("❌ عبارت ریاضی را وارد کنید.")
        return
    expression = message.text.split(maxsplit=1)[1]
    try:
        allowed = "0123456789+-*/(). "
        if all(c in allowed for c in expression):
            result = eval(expression)
            await message.edit_text(f"🔢 **عبارت:** `{expression}`\n✅ **پاسخ:** `{result}`")
        else:
            await message.edit_text("❌ کاراکتر غیرمجاز!")
    except Exception as e:
        await message.edit_text(f"❌ خطا: {e}")

@app.on_message(filters.me & filters.command("tags", prefixes="."))
async def show_mentions(client, message):
    if not mention_store:
        await message.edit_text("ℹ️ هیچ منشنی ثبت نشده است.")
        return
    text = "🔔 **آخرین منشن‌های شما در گروه‌ها:**\n\n" + "\n\n---\n\n".join(mention_store)
    await message.edit_text(text, disable_web_page_preview=True)

# ----------------------------------------------------
# ⏰ ۷. ساعت روی اسم A
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("clock", prefixes="."))
async def toggle_clock(client, message):
    bot_state["clock"] = not bot_state["clock"]
    if bot_state["clock"]:
        await message.edit_text("⏰ **ساعت اسم روشن شد.**")
    else:
        await app.update_profile(first_name=YOUR_NAME)
        await message.edit_text("⏰ **ساعت خاموش شد.**")

# ----------------------------------------------------
# 🌙 ۸. حالت غیبت (AFK)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("afk", prefixes="."))
async def set_afk(client, message):
    reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "در دسترس نیستم."
    bot_state["afk"] = True
    bot_state["afk_reason"] = reason
    await message.edit_text(f"🔴 **حالت AFK فعال شد.**\n💬 دلیل: {reason}")

@app.on_message(filters.me & filters.command("unafk", prefixes="."))
async def unset_afk(client, message):
    bot_state["afk"] = False
    bot_state["afk_reason"] = ""
    await message.edit_text("🟢 **حالت AFK غیرفعال شد.**")

@app.on_message(filters.private & ~filters.me)
async def auto_reply_afk(client, message):
    if bot_state["afk"]:
        await message.reply_text(f"🤖 **پاسخ خودکار:**\nمن در حال حاضر آنلاین نیستم.\n**دلیل:** {bot_state['afk_reason']}")

# ----------------------------------------------------
# 🔄 ۹. ارسال تکراری متغیر (تصادفی) و زمان‌بندی
# ----------------------------------------------------
async def send_random_loop_msg(chat_id, text, min_sec, max_sec, job_id):
    try:
        await app.send_message(chat_id, text)
        next_delay = random.randint(min_sec, max_sec)
        
        scheduler.add_job(
            send_random_loop_msg,
            'date',
            run_date=datetime.now(pytz.timezone("Asia/Tehran")) + timedelta(seconds=next_delay),
            args=[chat_id, text, min_sec, max_sec, job_id],
            id=job_id,
            replace_existing=True
        )
    except Exception as e:
        print(f"Loop Error: {e}")

@app.on_message(filters.me & filters.command("loop", prefixes="."))
async def loop_message(client, message):
    try:
        args = message.text.split(maxsplit=4)
        chat_id = int(args[1])
        min_sec = int(args[2])
        max_sec = int(args[3])
        text_to_send = args[4]
        
        job_id = f"loop_{chat_id}"
        await send_random_loop_msg(chat_id, text_to_send, min_sec, max_sec, job_id)
        
        await message.edit_text(
            f"✅ **ارسال تکراری متغیر ست شد!**\n"
            f"🏢 چت: `{chat_id}`\n"
            f"⏱ بازه زمانی: بین `{min_sec}` تا `{max_sec}` ثانیه (تصادفی)"
        )
    except Exception as e:
        await message.edit_text(
            "❌ **فرمت اشتباه!**\n"
            "مثال ارسال بین ۲۶۰ ثانیه (۴ دقیقه‌و‌بیست‌ثانیه) تا ۳۰۰ ثانیه (۵ دقیقه):\n"
            "`.loop -100123456789 260 300 متن پیام`"
        )

@app.on_message(filters.me & filters.command("loops", prefixes="."))
async def list_loops(client, message):
    jobs = scheduler.get_jobs()
    if not jobs:
        await message.edit_text("ℹ️ هیچ ارسالی فعال نیست.")
        return
    text = "🔄 **لیست ارسال‌های فعال:**\n\n"
    for j in jobs:
        text += f"• **شناسه:** `{j.id}` | **اجرای بعدی:** {j.next_run_time.strftime('%H:%M:%S')}\n"
    await message.edit_text(text)

@app.on_message(filters.me & filters.command("stoploop", prefixes="."))
async def stop_loops(client, message):
    scheduler.remove_all_jobs()
    await message.edit_text("🛑 **تمام ارسال‌ها متوقف شدند.**")

async def send_scheduled_msg(chat_id, text):
    try:
        await app.send_message(chat_id, text)
    except Exception as e:
        print(f"Schedule Error: {e}")

@app.on_message(filters.me & filters.command("schedule", prefixes="."))
async def schedule_msg(client, message):
    try:
        args = message.text.split(maxsplit=3)
        chat_id = int(args[1])
        time_str = args[2]
        text_to_send = args[3]
        now = datetime.now(pytz.timezone("Asia/Tehran"))
        target_time = datetime.strptime(time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day, tzinfo=pytz.timezone("Asia/Tehran")
        )
        scheduler.add_job(send_scheduled_msg, 'date', run_date=target_time, args=[chat_id, text_to_send])
        await message.edit_text(f"⏰ **ارسال برای ساعت {time_str} ست شد.**")
    except Exception as e:
        await message.edit_text(f"❌ **فرمت اشتباه!**\nمثال: `.schedule -100123456789 18:30 سلام`\nخطا: {e}")

# ----------------------------------------------------
# 🛠 ۱۰. ابزارهای عمومی و تکمیلی
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("del", prefixes="."))
async def mass_delete(client, message):
    try:
        count = int(message.text.split()[1])
        async for msg in client.get_chat_history(message.chat.id, limit=count + 1):
            if msg.from_user and msg.from_user.is_self:
                await msg.delete()
    except Exception as e:
        await message.edit_text(f"❌ خطا: {e}")

@app.on_message(filters.me & filters.command("info", prefixes="."))
async def get_info(client, message):
    chat = message.chat
    reply = message.reply_to_message
    if reply and reply.from_user:
        user = reply.from_user
        text = f"👤 **مشخصات کاربر:**\n• آیدی عددی: `{user.id}`\n• نام: {user.first_name}\n• یوزرنیم: @{user.username if user.username else 'ندارد'}"
    else:
        text = f"💬 **مشخصات چت:**\n• آیدی عددی: `{chat.id}`\n• عنوان: {chat.title if chat.title else 'پیوی'}"
    await message.edit_text(text)

@app.on_message(filters.me & filters.command("dl", prefixes="."))
async def download_media_cmd(client, message):
    reply = message.reply_to_message
    if not reply or not reply.media:
        await message.edit_text("❌ روی یک رسانه ریپلی کن!")
        return
    await message.edit_text("⏳ در حال دانلود...")
    file_path = await client.download_media(reply)
    await client.send_document("me", document=file_path, caption="📥 **رسانه ذخیره‌شده**")
    if os.path.exists(file_path):
        os.remove(file_path)
    await message.edit_text("✅ با موفقیت در Saved Messages ذخیره شد.")

@app.on_message(filters.me & filters.command("font", prefixes="."))
async def font_generator(client, message):
    if len(message.text.split()) < 2:
        await message.edit_text("❌ متن انگلیسی وارد کنید.")
        return
    text = message.text.split(maxsplit=1)[1]
    fonts = [
        f"🖥 `{text}`",
        f"✏️ **{text}**",
        f"🎨 ____{text}____",
        f"⚡ ~{text}~",
        f"💎 ||{text}||"
    ]
    await message.edit_text("\n\n".join(fonts))

@app.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping(client, message):
    await message.edit_text("⚡ **Self-Bot is Active & Running Smoothly!**")

# ----------------------------------------------------
# 🔄 ۱۱. آپدیت دقیقه‌به‌دقیقه ساعت روی اسم A
# ----------------------------------------------------
async def update_clock():
    while True:
        try:
            if bot_state["clock"]:
                ir_time = datetime.now(pytz.timezone("Asia/Tehran")).strftime("%H:%M")
                new_name = f"{YOUR_NAME} | {ir_time}"
                await app.update_profile(first_name=new_name)
        except Exception as e:
            print(f"Clock error: {e}")
        await asyncio.sleep(60)

async def main():
    await app.start()
    scheduler.start()
    asyncio.create_task(update_clock())
    print("Self-Bot started successfully!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
