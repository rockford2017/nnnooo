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
auto_pm_enabled = False
auto_pm_text = "سلام! در حال حاضر مشغول هستم، پیام بگذارید در اسرع وقت پاسخ می‌دهم. 🌹"

# نگاشت اعداد انگلیسی به اعداد با فونت ریاضی خاص (Unicode Bold)
FONT_MAP = {
    '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒',
    '5': '𝟓', '6': '𝟔', '7': '𝟕', '8': '𝟖', '9': '𝟗'
}

def convert_to_fancy_time(time_str: str) -> str:
    """تبدیل ساعت معمولی به ساعت با فونت خاص یونیکد"""
    return "".join(FONT_MAP.get(char, char) for char in time_str)

# ----------------------------------------------------
# 📋 ۱. راهنمای ابزارها (.help)
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("help", prefixes="."))
async def show_help(client, message):
    clock_status = "🟢 فعال" if clock_enabled else "🔴 غیرفعال"
    pm_status = "🟢 فعال" if auto_pm_enabled else "🔴 غیرفعال"
    
    dashboard = f"""
✨ **داشبورد سلف‌بات اختصاصی {YOUR_NAME}**
━━━━━━━━━━━━━━━━━━━━
⏰ **ساعت خاص اسم:** [ {clock_status} ]
🤖 **منشی پیوی:** [ {pm_status} ]
━━━━━━━━━━━━━━━━━━━━

✍️ **انیمیشن و استیکر:**
• `.type [متن]` ➔ تایپ متحرک انیمیشنی
• `.sticker` ➔ تبدیل عکس یا متن به استیکر (ریپلی/متن)

⏰ **ساعت اسم:**
• `.clock` ➔ روشن/خاموش کردن ساعت با فونت خاص

📸 **رسانه و ذخیره‌ساز:**
• `.save` ➔ ذخیره دائمی عکس/ویدیو یک‌بارمصرف (ریپلی)

👁 **امنیت و مچ‌گیری:**
• مچ‌گیری خودکار پیام‌های ادیت‌شده در پیوی (Anti-Edit)

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

    # تبدیل عکس به استیکر
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

    # ساخت استیکر از روی متن
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
# ⏰ ۴. مدیریت و آپدیت ساعت با فونت خاص
# ----------------------------------------------------
@app.on_message(filters.me & filters.command("clock", prefixes="."))
async def toggle_clock(client, message):
    global clock_enabled
    clock_enabled = not clock_enabled
    if clock_enabled:
        await message.edit_text("⏰ **ساعت اسم با فونت خاص فعال شد.**")
    else:
        await app.update_profile(first_name=YOUR_NAME)
        await message.edit_text("⏰ **ساعت اسم خاموش شد.**")

async def update_clock_loop():
    while True:
        try:
            if clock_enabled:
                raw_time = datetime.now(pytz.timezone("Asia/Tehran")).strftime("%H:%M")
                fancy_time = convert_to_fancy_time(raw_time)
                new_name = f"{YOUR_NAME} | {fancy_time}"
                await app.update_profile(first_name=new_name)
        except Exception as e:
            print(f"Clock update error: {e}")
        await asyncio.sleep(60)

# ----------------------------------------------------
# 📸 ۵. ذخیره رسانه یک‌بارمصرف (.save)
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
# 👁 ۶. مچ‌گیری ادیت پیام (Anti-Edit)
# ----------------------------------------------------
@app.on_message(filters.private & ~filters.me)
async def cache_private_messages(client, message: Message):
    msg_store[message.id] = message.text or "[رسانه/غیرمتنی]"

@app.on_edited_message(filters.private & ~filters.me)
async def log_edited_messages(client, message: Message):
    if message.id in msg_store:
        old_text = msg_store[message.id]
        new_text = message.text or "[رسانه/غیرمتنی]"
        sender = message.from_user.first_name if message.from_user else "ناشناس"
        
        await client.send_message(
            "me",
            f"🕵️‍♂️ **مچ‌گیری تغییر پیام!**\n"
            f"👤 **فرستنده:** {sender}\n\n"
            f"❌ **متن اصلی:** `{old_text}`\n"
            f"✅ **متن جدید:** `{new_text}`"
        )
        msg_store[message.id] = new_text

# ----------------------------------------------------
# 🤖 ۷. سیستم منشی هوشمند
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
    if auto_pm_enabled:
        await message.reply_text(f"🤖 **پاسخ خودکار:**\n{auto_pm_text}")

# ----------------------------------------------------
# ⚡️ ۸. تست وضعیت
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
