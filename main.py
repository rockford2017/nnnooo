import asyncio
import json
import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message

# ---------------------------------------------------------
# ۱. مدیریت ذخیره‌سازی دائمی تنظیمات (Persistent Config)
# ---------------------------------------------------------
CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "self_active": True,
    "auto_rescue": True,          # نجات خودکار گربه
    "auto_fish_action": "sell",   # 'sell', 'feed', 'fridge', 'off'
    "auto_fish_cmd": False,       # ارسال خودکار کلمه fish
    "auto_fish_target_chat": 0,   # چتی که باید fish فرستاده شود
    "auto_fish_stop_time": 0      # زمان پایان ارسال خودکار
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=4)
        return DEFAULT_CONFIG.copy()
    else:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            return DEFAULT_CONFIG.copy()

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

config = load_config()

# ---------------------------------------------------------
# ۲. ساخت و پیکربندی سلف‌بات با استفاده از محیط GitHub
# ---------------------------------------------------------
API_ID = int(os.environ.get("API_ID", 1234567))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

if SESSION_STRING:
    app = Client("momo_self", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    app = Client("momo_self", api_id=API_ID, api_hash=API_HASH)

# ---------------------------------------------------------
# ۳. موتور ارسال خودکار کلمه fish هر ۳۰ دقیقه
# ---------------------------------------------------------
async def auto_fish_loop():
    while True:
        try:
            if config["self_active"] and config["auto_fish_cmd"]:
                current_time = time.time()
                # بررسی زمان پایان (اگر ساعت تعیین شده باشد)
                if config["auto_fish_stop_time"] > 0 and current_time >= config["auto_fish_stop_time"]:
                    config["auto_fish_cmd"] = False
                    config["auto_fish_stop_time"] = 0
                    save_config()
                    print("⏰ زمان تعیین‌شده برای ارسال fish به پایان رسید.")
                else:
                    target_chat = config["auto_fish_target_chat"]
                    if target_chat != 0:
                        await app.send_message(target_chat, "fish")
                        print(f"🎣 کلمه fish ارسال شد به چت: {target_chat}")
            
            # ۳۰ دقیقه انتظار (۱۸۰۰ ثانیه)
            await asyncio.sleep(1800)
        except Exception as e:
            print(f"❌ خطا در ارسال ماهیگیری: {e}")
            await asyncio.sleep(60)

# ---------------------------------------------------------
# ۴. عملکرد هوشمند سلف در گروه‌ها (پاسخ/کلیک روی دکمه‌های ربات)
# ---------------------------------------------------------
@app.on_message(filters.group & ~filters.me)
async def handle_game_messages(client: Client, message: Message):
    if not config["self_active"]:
        return

    text = message.text or message.caption or ""

    # الف) نجات خودکار گربه خیابانی
    if config["auto_rescue"] and "نجات پیشی خیابونی" in text:
        if message.reply_markup and message.reply_markup.inline_keyboard:
            for row in message.reply_markup.inline_keyboard:
                for btn in row:
                    if "نجات" in btn.text or "کمک" in btn.text:
                        try:
                            await message.click(btn.text)
                            print("✅ نجات گربه انجام شد.")
                        except Exception as e:
                            print(f"❌ خطا در کلیک نجات: {e}")

    # ب) کلیک خودکار روی دکمه ماهی صیدشده
    fish_action = config["auto_fish_action"]
    if fish_action != "off" and "شما با موفقیت" in text and "گرفتید" in text:
        if message.reply_markup and message.reply_markup.inline_keyboard:
            target_keyword = ""
            if fish_action == "sell":
                target_keyword = "فروش ماهی"
            elif fish_action == "feed":
                target_keyword = "بده پیشی بخوره"
            elif fish_action == "fridge":
                target_keyword = "بندازش تو یخچال"

            if target_keyword:
                for row in message.reply_markup.inline_keyboard:
                    for btn in row:
                        if target_keyword in btn.text:
                            try:
                                await message.click(btn.text)
                                print(f"✅ دکمه {btn.text} کلیک شد.")
                            except Exception as e:
                                print(f"❌ خطا در کلیک ماهی: {e}")

# ---------------------------------------------------------
# ۵. دستورات مدیریتی (فقط در Saved Messages / پیام‌های ذخیره‌شده)
# ---------------------------------------------------------
@app.on_message(filters.me & filters.private & filters.command("panel", prefixes="."))
async def show_panel(client: Client, message: Message):
    # فقط در Saved Messages پاسخ بده
    if message.chat.id != (await client.get_me()).id:
        return

    status_self = "🟢" if config["self_active"] else "🔴"
    status_rescue = "🟢" if config["auto_rescue"] else "🔴"
    status_fish_cmd = "🟢" if config["auto_fish_cmd"] else "🔴"
    
    fish_modes = {
        "sell": "🟡 فروش",
        "feed": "🍖 غذا به گربه",
        "fridge": "❄️ یخچال",
        "off": "🔴 خاموش"
    }
    status_fish = fish_modes.get(config["auto_fish_action"], "🔴")

    panel_text = f"""
📋 **داشبورد سلف‌بات اختصاصی momo (Saved Messages)**
━━━━━━━ Status ━━━━━━━
🤖 وضعیت سلف: {status_self}
🐱 نجات گربه خودکار: {status_rescue}
🎣 ارسال خودکار fish: {status_fish_cmd}
🐟 اقدام ماهیگیری: {status_fish}
───────────────────────
━━━━━━━ Commands ━━━━━━━

🐱 **تنظیمات بازی Meowie:**
▫️ `.autorescue on/off` ➔ نجات خودکار گربه
▫️ `.autofishcmd on <چت_آیدی> [ساعت]` ➔ ارسال خودکار fish به گروه
  └ مثال: `.autofishcmd on -100123456789 5`
▫️ `.autofishcmd off` ➔ خاموش کردن ارسال fish
▫️ `.autofish [sell/feed/fridge/off]` ➔ انتخاب اقدام ماهی:
  └ 🟡 `sell`: فروش مستقیم
  └ 🍖 `feed`: بده پیشی بخوره
  └ ❄️ `fridge`: بندازش تو یخچال

⚡️ **تنظیمات عمومی:**
▫️ `.self on/off` ➔ خاموش/روشن سلف‌بات
▫️ `.ping` ➔ بررسی سرعت
"""
    await message.edit(panel_text)

# دستور فعال/غیرفعال‌سازی ارسال خودکار fish
@app.on_message(filters.me & filters.private & filters.command("autofishcmd", prefixes="."))
async def toggle_auto_fish_cmd(client: Client, message: Message):
    if message.chat.id != (await client.get_me()).id:
        return

    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        if opt == "on":
            if len(args) > 2:
                try:
                    target_chat = int(args[2])
                    config["auto_fish_cmd"] = True
                    config["auto_fish_target_chat"] = target_chat

                    if len(args) > 3 and args[3].isdigit():
                        hours = int(args[3])
                        config["auto_fish_stop_time"] = time.time() + (hours * 3600)
                        await message.edit(f"✅ ارسال خودکار `fish` به چت `{target_chat}` هر ۳۰ دقیقه فعال شد (برای {hours} ساعت).")
                    else:
                        config["auto_fish_stop_time"] = 0
                        await message.edit(f"✅ ارسال خودکار `fish` به چت `{target_chat}` هر ۳۰ دقیقه فعال شد.")

                    save_config()
                    # ارسال اولین ماهیگیری مستقیم به گروه
                    await client.send_message(target_chat, "fish")
                except ValueError:
                    await message.edit("❌ آیدی چت نامعتبر است! مثال:\n`.autofishcmd on -100123456789 4`")
            else:
                await message.edit("❌ لطفاً آیدی چت/گروه را وارد کن!\nمثال: `.autofishcmd on -100123456789`")

        elif opt == "off":
            config["auto_fish_cmd"] = False
            config["auto_fish_stop_time"] = 0
            save_config()
            await message.edit("❌ ارسال خودکار `fish` غیرفعال شد.")

# تعیین تکلیف ماهی صیدشده
@app.on_message(filters.me & filters.private & filters.command("autofish", prefixes="."))
async def set_auto_fish(client: Client, message: Message):
    if message.chat.id != (await client.get_me()).id:
        return

    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        if opt in ["sell", "feed", "fridge", "off"]:
            config["auto_fish_action"] = opt
            save_config()
            labels = {
                "sell": "فروش ماهی 🟡",
                "feed": "بده پیشی بخوره 🍖",
                "fridge": "بندازش تو یخچال ❄️",
                "off": "غیرفعال 🔴"
            }
            await message.edit(f"✅ اقدام ماهیگیری روی **{labels[opt]}** قرار گرفت.")
        else:
            await message.edit("❌ گزینه اشتباه! موارد مجاز: `sell`, `feed`, `fridge`, `off`")

# تغییر تنظیمات نجات گربه
@app.on_message(filters.me & filters.command("autorescue", prefixes="."))
async def set_auto_rescue(client: Client, message: Message):
    if message.chat.id != (await client.get_me()).id:
        return

    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        if opt == "on":
            config["auto_rescue"] = True
            save_config()
            await message.edit("✅ نجات خودکار گربه **فعال** شد.")
        elif opt == "off":
            config["auto_rescue"] = False
            save_config()
            await message.edit("❌ نجات خودکار گربه **غیرفعال** شد.")

# پینگ سلف
@app.on_message(filters.me & filters.private & filters.command("ping", prefixes="."))
async def ping_cmd(client: Client, message: Message):
    if message.chat.id != (await client.get_me()).id:
        return

    start = time.time()
    await message.edit("🏓 Pong!")
    end = time.time()
    await message.edit(f"🏓 Pong!\n⏱ سرعت: `{round((end - start) * 1000)}ms`")

# سوئیچ کلی سلف
@app.on_message(filters.me & filters.private & filters.command("self", prefixes="."))
async def toggle_self(client: Client, message: Message):
    if message.chat.id != (await client.get_me()).id:
        return

    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        if opt == "on":
            config["self_active"] = True
            save_config()
            await message.edit("🟢 سلف‌بات روشن شد.")
        elif opt == "off":
            config["self_active"] = False
            save_config()
            await message.edit("🔴 سلف‌بات خاموش شد.")

# اجرای اصلی
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(auto_fish_loop())
    print("Momo Selfbot Ready...")
    app.run()
