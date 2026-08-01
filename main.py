import os
import asyncio
import re
from datetime import datetime
import pytz
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image, ImageDraw

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

YOUR_NAME = "A"

# حافظه‌ها و وضعیت‌ها
msg_store = {}
clock_enabled = True
current_clock_style = "1"

anti_delete_enabled = True
anti_edit_enabled = True

active_loops = {}  # برای ذخیره و مدیریت چندین Loop فعال
recent_tags = []   # برای ذخیره منشن‌های اخیر

muted_users = set()

afk_state = {
    "is_afk": False,
    "reason": ""
}

auto_pm_enabled = False
auto_pm_text = "سلام! در حال حاضر مشغول هستم، پیام بگذارید در اسرع وقت پاسخ می‌دهم. 🌹"

CLOCK_STYLES = {
    "1": {'0': '⓪', '1': '①', '2': '②', '3': '③', '4': '④', '5': '⑤', '6': '⑥', '7': '⑦', '8': '⑧', '9': '⑨'},
    "2": {'0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒', '5': '𝟓', '6': '𝟔', '7': '𝟕', '8': '𝟖', '9': '𝟗'},
    "3": {'0': '𝟷', '1': '𝟷', '2': '𝟸', '3': '𝟹', '4': '𝟺', '5': '𝟻', '6': '𝟼', '7': '𝟽', '8': '𝟾', '9': '𝟿'},
    "4": {'0': '𝟣', '1': '𝟣', '2': '𝟤', '3': '𝟥', '4': '𝟦', '5': '𝟧', '6': '𝟨', '7': '𝟩', '8': '𝟪', '9': '𝟫'}
}

def convert_to_fancy_time(time_str: str, style_id: str) -> str:
    style_map = CLOCK_STYLES.get(style_id, CLOCK_STYLES["1"])
    return "".join(style_map.get(char, char) for char in time_str)

# ----------------------------------------------------
# 📋 ۱. راهنمای کامل ابزارها (.help)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("help", prefixes="."))
async def show_help(client, message):
    clock_status = "🟢 روشن" if clock_enabled else "🔴 خاموش"
    afk_status = f"🟢 روشن ({afk_state['reason']})" if afk_state["is_afk"] else "🔴 خاموش"
    anti_del_status = "🟢 فعال" if anti_delete_enabled else "🔴 غیرفعال"
    pm_status = "🟢 روشن" if auto_pm_enabled else "🔴 خاموش"

    dashboard = f"""📋 **داشبورد سلف‌بات اختصاصی {YOUR_NAME}**
━━━━━━━━━━━━━━━━━━━━
⏰ **ساعت اسم:** [ {clock_status} | استایل {current_clock_style} ]
🌙 **حالت AFK:** [ {afk_status} ]
🛡 **ضد پاکسازی:** [ {anti_del_status} ]
🤖 **منشی پیوی:** [ {pm_status} ]
━━━━━━━━━━━━━━━━━━━━

🛠 **لیست دستورات کامل:**

⚡️ **مدیریت سیستم:**
• `.clock` ➔ روشن/خاموش کردن ساعت روی اسم
• `.clockstyle [1-4]` ➔ تغییر استایل فونت ساعت
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
• `.dl` یا `.save` ➔ ذخیره/دانلود رسانه یک‌بارمصرف (ریپلی)
• `.type [متن]` ➔ تایپ متحرک انیمیشنی
• `.sticker` ➔ تبدیل عکس یا متن به استیکر

🔄 **زمان‌بندی و ارسال:**
• `.loop [ID] [ثانیه] [متن]` ➔ ارسال تکراری هر X ثانیه
• `.loops` ➔ مشاهده ارسال‌های تکراری فعال
• `.stoploop` ➔ توقف تمام ارسال‌ها
• `.schedule [ID] [HH:MM] [متن]` ➔ ارسال سر ساعت مشخص
• `.spam [تعداد] [متن]` ➔ ارسال سریع پیام

🤖 **منشی و امنیت:**
• `.pm [on/off]` ➔ فعال/غیرفعال‌سازی منشی پیوی
• `.setpm [متن]` ➔ تنظیم متن منشی

🛠 **ابزارهای عمومی:**
• `.del [تعداد]` ➔ پاکسازی پیام‌های اخیر خودت
• `.info` ➔ مشخصات کامل چت یا کاربر
• `.font [متن انگلیسی]` ➔ ساخت فونت زیبا
• `.ping` ➔ تست آنلاین بودن ربات"""

    await message.edit_text(dashboard)

# ----------------------------------------------------
# ⏰ ۲. تنظیمات ساعت اسم (.clock & .clockstyle)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("clock", prefixes="."))
async def toggle_clock(client, message):
    global clock_enabled
    clock_enabled = not clock_enabled
    if clock_enabled:
        await message.edit_text("⏰ **ساعت اسم روشن شد.**")
    else:
        await app.update_profile(first_name=YOUR_NAME)
        await message.edit_text("⏰ **ساعت اسم خاموش شد.**")

@app.on_message(filters.me & filters.command("clockstyle", prefixes="."))
async def set_clock_style(client, message):
    global current_clock_style
    args = message.text.split()
    if len(args) > 1 and args[1] in CLOCK_STYLES:
        current_clock_style = args[1]
        raw_time = datetime.now(pytz.timezone("Asia/Tehran")).strftime("%H:%M")
        sample_time = convert_to_fancy_time(raw_time, current_clock_style)
        await message.edit_text(f"✅ **استایل ساعت تغییر کرد!**\nپیش‌نمایش: `{sample_time}`")
        if clock_enabled:
            await app.update_profile(first_name=f"{YOUR_NAME} | {sample_time}")
    else:
        await message.edit_text("❌ لطفا عددی بین 1 تا 4 انتخاب کنید. مثال: `.clockstyle 2`")

async def update_clock_loop():
    while True:
        try:
            if clock_enabled:
                raw_time = datetime.now(pytz.timezone("Asia/Tehran")).strftime("%H:%M")
                fancy_time = convert_to_fancy_time(raw_time, current_clock_style)
                await app.update_profile(first_name=f"{YOUR_NAME} | {fancy_time}")
        except Exception as e:
            print(f"Clock Error: {e}")
        await asyncio.sleep(60)

# ----------------------------------------------------
# 🔄 ۳. زمان‌بندی و ارسال تکراری (.loop, .loops, .stoploop, .schedule)
# ----------------------------------------------------
async def loop_worker(client, chat_id, delay, text):
    while chat_id in active_loops:
        try:
            await client.send_message(chat_id, text)
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"Loop error in {chat_id}: {e}")
            await asyncio.sleep(delay)

@app.on_message(filters.me & filters.command("loop", prefixes="."))
async def custom_loop_messages(client, message):
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.edit_text("❌ نحوه استفاده:\n`.loop [آیدی چت] [ثانیه] [متن]`\n\nمثال:\n`.loop -1003329545310 246 سلام`")
        return

    try:
        raw_chat = args[1]
        target_chat = int(raw_chat) if (raw_chat.startswith("-") or raw_chat.isdigit()) else raw_chat
        delay = float(args[2])
        text = args[3]

        if target_chat in active_loops:
            active_loops[target_chat]["task"].cancel()

        task = asyncio.create_task(loop_worker(client, target_chat, delay, text))
        active_loops[target_chat] = {"delay": delay, "text": text, "task": task}

        await message.edit_text(
            f"✅ **ارسال تکراری ست شد!**\n"
            f"🏢 **چت:** `{target_chat}`\n"
            f"⏱ **هر {int(delay) if delay.is_integer() else delay} ثانیه**"
        )
    except Exception as e:
        await message.edit_text(f"❌ خطا: {e}")

@app.on_message(filters.me & filters.command("loops", prefixes="."))
async def list_loops(client, message):
    if not active_loops:
        await message.edit_text("❌ هیچ ارسال تکراریِ فعالی وجود ندارد!")
        return

    res = "📋 **لیست ارسال‌های تکراری فعال:**\n\n"
    for chat_id, info in active_loops.items():
        res += f"🏢 **چت:** `{chat_id}` | ⏱ **هر {info['delay']} ثانیه**\n💬 **متن:** {info['text'][:20]}...\n━━━━━━━━━━━━━━━━━━━━\n"
    await message.edit_text(res)

@app.on_message(filters.me & filters.command(["stoploop", "unloop"], prefixes="."))
async def stop_loop(client, message):
    if not active_loops:
        await message.edit_text("❌ هیچ ارسال تکراریِ فعالی وجود ندارد!")
        return

    for chat_id, info in active_loops.items():
        info["task"].cancel()
    active_loops.clear()
    await message.edit_text("🛑 **تمام ارسال‌های تکراری (Loop) متوقف شدند.**")

@app.on_message(filters.me & filters.command("schedule", prefixes="."))
async def schedule_message(client, message):
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.edit_text("❌ نحوه استفاده: `.schedule [ID] [HH:MM] [متن]`")
        return

    raw_chat, time_str, text = args[1], args[2], args[3]
    target_chat = int(raw_chat) if (raw_chat.startswith("-") or raw_chat.isdigit()) else raw_chat

    await message.edit_text(f"⏳ **ارسال زمان‌بندی شد برای ساعت {time_str}**")

    while True:
        now = datetime.now(pytz.timezone("Asia/Tehran")).strftime("%H:%M")
        if now == time_str:
            await client.send_message(target_chat, text)
            break
        await asyncio.sleep(15)

# ----------------------------------------------------
# 🔇 ۴. مدیریت چت و کاربران (.mute, .purge, .usernames)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("mute", prefixes="."))
async def mute_user(client, message):
    reply = message.reply_to_message
    if reply and reply.from_user:
        muted_users.add(reply.from_user.id)
        await message.edit_text(f"🔇 کاربر {reply.from_user.first_name} بی‌صدا شد.")
    else:
        await message.edit_text("❌ روی پیام کاربر ریپلی کن!")

@app.on_message(filters.me & filters.command("unmute", prefixes="."))
async def unmute_user(client, message):
    reply = message.reply_to_message
    if reply and reply.from_user and reply.from_user.id in muted_users:
        muted_users.remove(reply.from_user.id)
        await message.edit_text(f"🔊 کاربر {reply.from_user.first_name} باصدا شد.")
    else:
        await message.edit_text("❌ کاربر در لیست بی‌صدا نیست یا ریپلی نشده!")

@app.on_message(filters.me & filters.command("purge", prefixes="."))
async def purge_messages(client, message):
    reply = message.reply_to_message
    if not reply:
        await message.edit_text("❌ برای پاکسازی باید روی یک پیام ریپلی کنی!")
        return

    msg_ids = list(range(reply.id, message.id + 1))
    await client.delete_messages(message.chat.id, msg_ids)

@app.on_message(filters.me & filters.command("usernames", prefixes="."))
async def get_usernames(client, message):
    reply = message.reply_to_message
    user = reply.from_user if reply else message.from_user
    
    if user:
        await message.edit_text(f"👤 **یوزرنیم فعلی:** @{user.username if user.username else 'ندارد'}\n🆔 **آیدی عددی:** `{user.id}`")
    else:
        await message.edit_text("❌ کاربر یافت نشد!")

# ----------------------------------------------------
# 🌐 ۵. ابزارهای کاربردی (.calc, .tags, .dl, .type, .sticker)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("calc", prefixes="."))
async def calculate(client, message):
    if len(message.text.split()) < 2:
        await message.edit_text("❌ یک عبارت ریاضی وارد کن! مثال: `.calc 2+2*5`")
        return
    expr = message.text.split(maxsplit=1)[1]
    try:
        allowed = "0123456789+-*/(). "
        if not all(c in allowed for c in expr):
            await message.edit_text("❌ عبارت شامل کاراکتر غیرمجاز است!")
            return
        res = eval(expr)
        await message.edit_text(f"🔢 **نتیجه:** `{res}`")
    except Exception as e:
        await message.edit_text(f"❌ خطا: {e}")

@app.on_message(filters.me & filters.command("tags", prefixes="."))
async def show_tags(client, message):
    if not recent_tags:
        await message.edit_text("❌ هیچ منشنی ثبت نشده است!")
        return
    res = "🏷 **۱۵ منشن اخیر شما:**\n\n" + "\n".join(recent_tags[-15:])
    await message.edit_text(res)

@app.on_message(filters.me & filters.command(["dl", "save"], prefixes="."))
async def save_media(client, message):
    reply = message.reply_to_message
    if not reply or not reply.media:
        await message.edit_text("❌ روی یک عکس یا ویدیوی یک‌بارمصرف ریپلی کن!")
        return

    await message.edit_text("⏳ در حال ذخیره‌سازی...")
    try:
        file_path = await client.download_media(reply)
        await client.send_document("me", document=file_path, caption="📥 **ذخیره شده توسط سلف‌بات**")
        if os.path.exists(file_path): os.remove(file_path)
        await message.edit_text("✅ در Saved Messages ذخیره شد!")
    except Exception as e:
        await message.edit_text(f"❌ خطا: {e}")

@app.on_message(filters.me & filters.command("type", prefixes="."))
async def typewriter_effect(client, message):
    if len(message.text.split()) < 2:
        return
    text = message.text.split(maxsplit=1)[1]
    typed = ""
    for char in text:
        typed += char
        try:
            await message.edit_text(f"`{typed}✍️`")
            await asyncio.sleep(0.15)
        except Exception:
            pass
    await message.edit_text(f"**{text}**")

@app.on_message(filters.me & filters.command("sticker", prefixes="."))
async def make_sticker(client, message):
    reply = message.reply_to_message
    sticker_path = "sticker.webp"

    if reply and reply.photo:
        await message.edit_text("⏳ تبدیل به استیکر...")
        img_path = await client.download_media(reply)
        img = Image.open(img_path)
        img.thumbnail((512, 512))
        img.save(sticker_path, "WEBP")
        await client.send_sticker(message.chat.id, sticker_path)
        await message.delete()
        if os.path.exists(img_path): os.remove(img_path)
        if os.path.exists(sticker_path): os.remove(sticker_path)
        return

    text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "Hello"
    img = Image.new("RGBA", (512, 512), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([20, 20, 492, 492], radius=30, fill=(25, 25, 25, 240))
    draw.text((256, 256), text, fill=(255, 255, 255), anchor="mm")
    img.save(sticker_path, "WEBP")
    await client.send_sticker(message.chat.id, sticker_path)
    await message.delete()
    if os.path.exists(sticker_path): os.remove(sticker_path)

# ----------------------------------------------------
# 🛠 ۶. ابزارهای عمومی (.del, .info, .font, .ping, .spam)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("del", prefixes="."))
async def delete_my_messages(client, message):
    args = message.text.split()
    count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    
    async for msg in client.get_chat_history(message.chat.id, limit=count + 1):
        if msg.from_user and msg.from_user.is_self:
            try:
                await msg.delete()
            except Exception:
                pass

@app.on_message(filters.me & filters.command("info", prefixes="."))
async def get_info(client, message):
    reply = message.reply_to_message
    chat = message.chat
    user = reply.from_user if reply else message.from_user
    
    info_text = f"ℹ️ **اطلاعات چت / کاربر:**\n\n"
    info_text += f"🏢 **نام چت:** {chat.title if chat.title else 'پیوی'}\n"
    info_text += f"🆔 **آیدی چت:** `{chat.id}`\n"
    if user:
        info_text += f"👤 **نام کاربر:** {user.first_name}\n"
        info_text += f"🆔 **آیدی کاربر:** `{user.id}`\n"
    await message.edit_text(info_text)

@app.on_message(filters.me & filters.command("font", prefixes="."))
async def make_font(client, message):
    if len(message.text.split()) < 2:
        await message.edit_text("❌ متنی به انگلیسی وارد کن! مثال: `.font Hello`")
        return
    text = message.text.split(maxsplit=1)[1]
    
    fonts = [
        "".join(chr(ord(c) + 0x1D5D4 - 65) if 'A'<=c<='Z' else chr(ord(c) + 0x1D5EE - 97) if 'a'<=c<='z' else c for c in text),
        "".join(chr(ord(c) + 0x1D400 - 65) if 'A'<=c<='Z' else chr(ord(c) + 0x1D41A - 97) if 'a'<=c<='z' else c for c in text),
        "".join(chr(ord(c) + 0x1D434 - 65) if 'A'<=c<='Z' else chr(ord(c) + 0x1D44E - 97) if 'a'<=c<='z' else c for c in text),
    ]
    res = "🎨 **مدل‌های فونت:**\n\n" + "\n".join([f"`{f}`" for f in fonts])
    await message.edit_text(res)

@app.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping(client, message):
    await message.edit_text("⚡️ **سلف‌بات کاملاً آنلاین و فعال است!**")

@app.on_message(filters.me & filters.command("spam", prefixes="."))
async def spam_messages(client, message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return
    count, text = int(args[1]), args[2]
    await message.delete()
    for _ in range(count):
        await client.send_message(message.chat.id, text)
        await asyncio.sleep(0.1)

# ----------------------------------------------------
# 🌙 ۷. AFK و منشی و هوشمندسازی
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("afk", prefixes="."))
async def set_afk(client, message):
    reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "در دسترس نیستم."
    afk_state["is_afk"] = True
    afk_state["reason"] = reason
    await message.edit_text(f"🔴 **حالت AFK فعال شد.**\n💬 دلیل: {reason}")

@app.on_message(filters.me & filters.command("unafk", prefixes="."))
async def unset_afk(client, message):
    afk_state["is_afk"] = False
    await message.edit_text("🟢 **حالت AFK غیرفعال شد.**")

@app.on_message(filters.me & filters.command("pm", prefixes="."))
async def toggle_pm(client, message):
    global auto_pm_enabled
    args = message.text.split()
    if len(args) > 1:
        auto_pm_enabled = (args[1].lower() == "on")
        await message.edit_text(f"منشی پیوی {'🟢 فعال' if auto_pm_enabled else '🔴 غیرفعال'} شد.")

@app.on_message(filters.me & filters.command("setpm", prefixes="."))
async def set_pm_text(client, message):
    global auto_pm_text
    auto_pm_text = message.text.split(maxsplit=1)[1]
    await message.edit_text(f"✅ متن منشی تنظیم شد:\n`{auto_pm_text}`")

# ----------------------------------------------------
# 🛡 ۸. لیسنر هوشمند (Mute, Mention Tag, Delete/Edit Catch)
# ----------------------------------------------------
@app.on_message(~filters.me)
async def global_listener(client, message: Message):
    # پاکسازی اتوماتیک پیام افراد Mute شده
    if message.from_user and message.from_user.id in muted_users:
        try:
            await message.delete()
        except Exception:
            pass

    # ذخیره منشن‌ها
    if message.mentioned:
        chat_name = message.chat.title if message.chat.title else "پیوی"
        recent_tags.append(f"👤 از {message.from_user.first_name if message.from_user else 'ناشناس'} در **{chat_name}**")

    # پاسخ خودکار AFK و منشی
    if message.chat.type.value == "private":
        if afk_state["is_afk"]:
            await message.reply_text(f"🤖 **پاسخ خودکار:**\nمن آنلاین نیستم.\n**دلیل:** {afk_state['reason']}")
        elif auto_pm_enabled:
            await message.reply_text(f"🤖 **پاسخ خودکار:**\n{auto_pm_text}")

@app.on_message(filters.private & ~filters.me)
async def cache_private_messages(client, message: Message):
    msg_store[message.id] = message

@app.on_deleted_messages(filters.private)
async def log_deleted_messages(client, messages):
    if not anti_delete_enabled: return
    for msg in messages:
        if msg.id in msg_store:
            saved_msg = msg_store[msg.id]
            sender = saved_msg.from_user.first_name if saved_msg.from_user else "ناشناس"
            await client.send_message("me", f"🗑 **پیام حذف‌شده در پیوی از طرف {sender}!**")
            try: await saved_msg.copy("me")
            except Exception: pass
            del msg_store[msg.id]

@app.on_edited_message(filters.private & ~filters.me)
async def log_edited_messages(client, message: Message):
    if not anti_edit_enabled: return
    if message.id in msg_store:
        old_text = msg_store[message.id].text or "[رسانه]"
        new_text = message.text or "[رسانه]"
        sender = message.from_user.first_name if message.from_user else "ناشناس"
        await client.send_message(
            "me",
            f"🕵️‍♂️ **مچ‌گیری تغییر پیام!**\n👤 **فرستنده:** {sender}\n\n❌ **قدیم:** `{old_text}`\n✅ **جدید:** `{new_text}`"
        )
        msg_store[message.id] = message

# ----------------------------------------------------
# 🚀 اجرای برنامه
# ----------------------------------------------------
async def main():
    await app.start()
    asyncio.create_task(update_clock_loop())
    print("Self-Bot fully started!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
