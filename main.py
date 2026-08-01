import os
import asyncio
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
current_clock_style = "1"  # پیش‌فرض: دایره‌ای

anti_delete_enabled = True
anti_edit_enabled = True

loop_running = False  # کنترل وضعیت ارسال تکراری نامحدود

afk_state = {
    "is_afk": False,
    "reason": ""
}

auto_pm_enabled = False
auto_pm_text = "سلام! در حال حاضر مشغول هستم، پیام بگذارید در اسرع وقت پاسخ می‌دهم. 🌹"

# نقشه فونت‌های مختلف یونیکد برای ساعت
CLOCK_STYLES = {
    "1": {  # دایره‌ای (Circled)
        '0': '⓪', '1': '①', '2': '②', '3': '③', '4': '④',
        '5': '⑤', '6': '⑥', '7': '⑦', '8': '⑧', '9': '⑨'
    },
    "2": {  # ریاضی برجسته (Bold Math)
        '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒',
        '5': '𝟓', '6': '𝟔', '7': '𝟕', '8': '𝟖', '9': '𝟗'
    },
    "3": {  # تک‌فاصله/مدرن (Monospace)
        '0': '𝟷', '1': '𝟷', '2': '𝟸', '3': '𝟹', '4': '𝟺',
        '5': '𝟻', '6': '𝟼', '7': '𝟽', '8': '𝟾', '9': '𝟿'
    },
    "4": {  # ایتالیک (Italic Math)
        '0': '𝟣', '1': '𝟣', '2': '𝟤', '3': '𝟥', '4': '𝟦',
        '5': '𝟧', '6': '𝟨', '7': '𝟩', '8': '𝟪', '9': '𝟫'
    }
}

def convert_to_fancy_time(time_str: str, style_id: str) -> str:
    style_map = CLOCK_STYLES.get(style_id, CLOCK_STYLES["1"])
    return "".join(style_map.get(char, char) for char in time_str)

# ----------------------------------------------------
# 📋 ۱. راهنمای کامل ابزارها (.help)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("help", prefixes="."))
async def show_help(client, message):
    clock_status = "🟢 فعال" if clock_enabled else "🔴 غیرفعال"
    afk_status = f"🟢 فعال ({afk_state['reason']})" if afk_state["is_afk"] else "🔴 غیرفعال"
    pm_status = "🟢 فعال" if auto_pm_enabled else "🔴 غیرفعال"
    anti_del_status = "🟢 فعال" if anti_delete_enabled else "🔴 غیرفعال"
    
    dashboard = f"""
✨ **داشبورد سلف‌بات اختصاصی {YOUR_NAME}**
━━━━━━━━━━━━━━━━━━━━
⏰ **ساعت اسم:** [ {clock_status} | استایل {current_clock_style} ]
🌙 **حالت AFK:** [ {afk_status} ]
🛡 **ضد پاکسازی:** [ {anti_del_status} ]
🤖 **منشی پیوی:** [ {pm_status} ]
━━━━━━━━━━━━━━━━━━━━

✍️ **انیمیشن، استیکر و ارسال تکراری:**
• `.type [متن]` ➔ تایپ متحرک انیمیشنی
• `.sticker` ➔ تبدیل عکس یا متن به استیکر (ریپلی/متن)
• `.spam [تعداد] [متن]` ➔ ارسال سریع پیام تکراری
• `.loop [آیدی/چت] [ثانیه] [متن]` ➔ ارسال نامحدود زمان‌بندی‌شده
• `.unloop` یا `.stoploop` ➔ توقف ارسال نامحدود

⏰ **ساعت اسم:**
• `.clock` ➔ روشن/خاموش کردن ساعت
• `.clockstyle [1-4]` ➔ تغییر فونت ساعت

🌙 **حالت غیبت (AFK):**
• `.afk [دلیل]` ➔ فعال‌سازی حالت AFK
• `.unafk` ➔ غیرفعال‌سازی حالت AFK

📸 **رسانه و ذخیره‌ساز:**
• `.save` ➔ ذخیره دائمی عکس/ویدیو یک‌بارمصرف (ریپلی)

👁 **امنیت و مچ‌گیری:**
• کشف خودکار پیام‌های ادیت‌شده و پاک‌شده در پیوی

🤖 **منشی و مدیریت:**
• `.pm [on/off]` ➔ فعال/غیرفعال‌سازی منشی پیوی
• `.setpm [متن]` ➔ تنظیم متن منشی

⚡️ **تست سرعت:**
• `.ping` ➔ بررسی وضعیت سلف‌بات
"""
    await message.edit_text(dashboard)

# ----------------------------------------------------
# ✍️ ۲. تایپ متحرک انیمیشنی (.type)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("type", prefixes="."))
async def typewriter_effect(client, message):
    if len(message.text.split()) < 2:
        await message.edit_text("❌ لطفا متنی وارد کنید!")
        return
    text = message.text.split(maxsplit=1)[1]
    typed = ""
    for char in text:
        typed += char
        try:
            await message.edit_text(f"`{typed}✍️`")
            await asyncio.sleep(0.2)
        except Exception:
            pass
    await message.edit_text(f"**{text}**")

# ----------------------------------------------------
# 🎨 ۳. ساخت سریع استیکر (.sticker)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("sticker", prefixes="."))
async def make_sticker(client, message):
    reply = message.reply_to_message
    sticker_path = "sticker.webp"

    if reply and reply.photo:
        await message.edit_text("⏳ در حال تبدیل عکس به استیکر...")
        img_path = await client.download_media(reply)
        img = Image.open(img_path)
        img.thumbnail((512, 512))
        img.save(sticker_path, "WEBP")
        
        await client.send_sticker(message.chat.id, sticker_path)
        await message.delete()
        
        if os.path.exists(img_path): os.remove(img_path)
        if os.path.exists(sticker_path): os.remove(sticker_path)
        return

    if len(message.text.split()) < 2:
        await message.edit_text("❌ متنی وارد کن یا روی یک عکس ریپلی کن!")
        return

    text = message.text.split(maxsplit=1)[1]
    await message.edit_text("⏳ در حال ساخت استیکر...")

    img = Image.new("RGBA", (512, 512), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    draw.rounded_rectangle([20, 20, 492, 492], radius=30, fill=(25, 25, 25, 240))
    draw.text((256, 256), text, fill=(255, 255, 255), anchor="mm")
    
    img.save(sticker_path, "WEBP")
    await client.send_sticker(message.chat.id, sticker_path)
    await message.delete()

    if os.path.exists(sticker_path):
        os.remove(sticker_path)

# ----------------------------------------------------
# 💣 ۴. ارسال پیام تکراری (Spam & Infinite Loop)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("spam", prefixes="."))
async def spam_messages(client, message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.edit_text("❌ نحوه استفاده: `.spam [تعداد] [متن]`")
        return
    try:
        count = int(args[1])
        text = args[2]
        await message.delete()
        for _ in range(count):
            await client.send_message(message.chat.id, text)
            await asyncio.sleep(0.1)
    except Exception as e:
        await message.edit_text(f"❌ خطا: {e}")

@app.on_message(filters.me & filters.command("loop", prefixes="."))
async def infinite_loop_messages(client, message):
    global loop_running
    args = message.text.split(maxsplit=3)
    
    if len(args) < 3:
        await message.edit_text("❌ نحوه استفاده:\n`.loop [آیدی/چت] [ثانیه] [متن]`\nیا:\n`.loop [ثانیه] [متن]`")
        return

    target_chat = message.chat.id
    delay = 1.0
    text = ""

    # بررسی اینکه آیا پارامتر اول آیدی عددی/یوزرنیم است یا ثانیه
    try:
        # اگر ورودی اول عدد اعشاری یا صحیح بود (یعنی ثانیه است)
        delay = float(args[1])
        text = " ".join(args[2:])
    except ValueError:
        # در غیر این صورت، پارامتر اول آیدی/یوزرنیم چت هدف است
        if len(args) < 4:
            await message.edit_text("❌ فرمت اشتباه! مثال:\n`.loop -10012345678 2 سلام`")
            return
        try:
            target_chat = int(args[1]) if (args[1].startswith("-") or args[1].isdigit()) else args[1]
            delay = float(args[2])
            text = args[3]
        except Exception as e:
            await message.edit_text(f"❌ خطا در ساختار ورودی: {e}")
            return

    loop_running = True
    await message.delete()

    while loop_running:
        try:
            await client.send_message(target_chat, text)
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"Loop Error: {e}")
            break

@app.on_message(filters.me & filters.command(["unloop", "stoploop"], prefixes="."))
async def stop_loop(client, message):
    global loop_running
    loop_running = False
    await message.edit_text("🛑 **ارسال پیام تکراری (Loop) متوقف شد.**")

# ----------------------------------------------------
# ⏰ ۵. مدیریت و تغییر استایل ساعت اسم
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("clock", prefixes="."))
async def toggle_clock(client, message):
    global clock_enabled
    clock_enabled = not clock_enabled
    if clock_enabled:
        await message.edit_text("⏰ **ساعت اسم فعال شد.**")
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
        
        await message.edit_text(f"✅ **استایل ساعت به کد {current_clock_style} تغییر کرد!**\n\nنمونه پیش‌نمایش: `{sample_time}`")
        if clock_enabled:
            await app.update_profile(first_name=f"{YOUR_NAME} | {sample_time}")
        return

    menu = """
🎨 **راهنمای انتخاب استایل ساعت:**

1️⃣ **دایره‌ای (پیش‌فرض):** `⑩:④⑤`
2️⃣ **ریاضی برجسته:** `𝟏𝟎:𝟒𝟓`
3️⃣ **تک‌فاصله/مدرن:** `𝟷𝟶:𝟺𝟻`
4️⃣ **ایتالیک/کج:** `𝟣𝟢:𝟦𝟧`

📌 **نحوه تنظیم:**
دستور `.clockstyle [شماره]` رو بفرست.
مثال: `.clockstyle 1`
"""
    await message.edit_text(menu)

async def update_clock_loop():
    while True:
        try:
            if clock_enabled:
                raw_time = datetime.now(pytz.timezone("Asia/Tehran")).strftime("%H:%M")
                fancy_time = convert_to_fancy_time(raw_time, current_clock_style)
                new_name = f"{YOUR_NAME} | {fancy_time}"
                await app.update_profile(first_name=new_name)
        except Exception as e:
            print(f"Clock update error: {e}")
        await asyncio.sleep(60)

# ----------------------------------------------------
# 📸 ۶. ذخیره رسانه یک‌بارمصرف (.save)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("save", prefixes="."))
async def save_media(client, message):
    reply = message.reply_to_message
    if not reply or not reply.media:
        await message.edit_text("❌ روی یک عکس یا ویدیوی یک‌بارمصرف ریپلی کن!")
        return

    await message.edit_text("⏳ در حال ذخیره رسانه...")
    try:
        file_path = await client.download_media(reply)
        sender = reply.from_user.first_name if reply.from_user else "ناشناس"
        
        await client.send_document(
            "me",
            document=file_path,
            caption=f"📥 **رسانه ذخیره‌شده از طرف:** {sender}"
        )
        if os.path.exists(file_path):
            os.remove(file_path)
        await message.edit_text("✅ با موفقیت دائمی شد و در Saved Messages ذخیره گشت!")
    except Exception as e:
        await message.edit_text(f"❌ خطا در ذخیره‌سازی: {e}")

# ----------------------------------------------------
# 👁 ۷. سیستم مچ‌گیری (ضد ادیت + ضد پاکسازی)
# ----------------------------------------------------
@app.on_message(filters.private & ~filters.me)
async def cache_private_messages(client, message: Message):
    msg_store[message.id] = message

@app.on_deleted_messages(filters.private)
async def log_deleted_messages(client, messages):
    if not anti_delete_enabled:
        return
    for msg in messages:
        if msg.id in msg_store:
            saved_msg = msg_store[msg.id]
            sender = saved_msg.from_user.first_name if saved_msg.from_user else "ناشناس"
            
            await client.send_message(
                "me",
                f"🗑 **پیام حذف‌شده در پیوی!**\n"
                f"👤 **فرستنده:** {sender}"
            )
            try:
                await saved_msg.copy("me")
            except Exception as e:
                print(f"Copy Error: {e}")
            del msg_store[msg.id]

@app.on_edited_message(filters.private & ~filters.me)
async def log_edited_messages(client, message: Message):
    if not anti_edit_enabled:
        return
    if message.id in msg_store:
        old_text = msg_store[message.id].text or "[رسانه/غیرمتنی]"
        new_text = message.text or "[رسانه/غیرمتنی]"
        sender = message.from_user.first_name if message.from_user else "ناشناس"
        
        await client.send_message(
            "me",
            f"🕵️‍♂️ **مچ‌گیری تغییر پیام!**\n"
            f"👤 **فرستنده:** {sender}\n\n"
            f"❌ **متن اصلی:** `{old_text}`\n"
            f"✅ **متن جدید:** `{new_text}`"
        )
        msg_store[message.id] = message

# ----------------------------------------------------
# 🌙 ۸. حالت غیبت (AFK)
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
    afk_state["reason"] = ""
    await message.edit_text("🟢 **حالت AFK غیرفعال شد.**")

@app.on_message(filters.private & ~filters.me)
async def auto_reply_afk(client, message):
    if afk_state["is_afk"]:
        await message.reply_text(f"🤖 **پاسخ خودکار:**\nمن در حال حاضر آنلاین نیستم.\n**دلیل:** {afk_state['reason']}")

# ----------------------------------------------------
# 🤖 ۹. سیستم منشی هوشمند
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("pm", prefixes="."))
async def toggle_pm(client, message):
    global auto_pm_enabled
    args = message.text.split()
    if len(args) > 1:
        if args[1].lower() == "on":
            auto_pm_enabled = True
            await message.edit_text("🟢 **منشی پیوی فعال شد.**")
            return
        elif args[1].lower() == "off":
            auto_pm_enabled = False
            await message.edit_text("🔴 **منشی پیوی غیرفعال شد.**")
            return
    await message.edit_text("❌ نحوه استفاده: `.pm on` یا `.pm off`")

@app.on_message(filters.me & filters.command("setpm", prefixes="."))
async def set_pm_text(client, message):
    global auto_pm_text
    if len(message.text.split()) < 2:
        await message.edit_text("❌ متن جدید منشی را وارد کن!")
        return
    auto_pm_text = message.text.split(maxsplit=1)[1]
    await message.edit_text(f"✅ **متن جدید منشی تنظیم شد:**\n\n`{auto_pm_text}`")

@app.on_message(filters.private & ~filters.me)
async def auto_reply_pm(client, message):
    if auto_pm_enabled and not afk_state["is_afk"]:
        await message.reply_text(f"🤖 **پاسخ خودکار:**\n{auto_pm_text}")

# ----------------------------------------------------
# ⚡️ ۱۰. تست وضعیت
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping(client, message):
    await message.edit_text("⚡️ **Gemini AI Self-Bot is Ready & Active!**")

# ----------------------------------------------------
# 🚀 اجرای سلف‌بات
# ----------------------------------------------------
async def main():
    await app.start()
    asyncio.create_task(update_clock_loop())
    print("Self-Bot started successfully!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
