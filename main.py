import asyncio
import random
import os
import json
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

# ---------------- CONFIGURATIONS ----------------
API_ID = int(os.environ.get("API_ID", 123456))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

app = Client("selfbot_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ---------------- STATE MANAGEMENT & PERSISTENCE ----------------
CONFIG = {
    "IS_SELF_ON": True,
    "IS_CLOCK_NAME": False,
    "IS_CLOCK_BIO": False,
    "CLOCK_STYLE": 1,
    "IS_AFK_ON": False,
    "AFK_REASON": "",
    "IS_ANTIDEL_ON": True,
    "IS_ANTIEDIT_ON": True,
    "IS_TTL_SAVE": True,
    "ORIGINAL_NAME": "",
    "ORIGINAL_BIO": "",
    # تنظیمات بازی‌ها
    "DICE_ON": False,
    "DICE_TARGET": "6",
    "SLOT_ON": False,
    "SLOT_TARGET": "64",
    "BASKET_ON": False,
    "BOWLING_ON": False,
    "GAME_DELAY": 0.25,
    # تنظیمات ارسال تکراری (Loop)
    "IS_LOOP_ON": False,
    "TARGET_CHAT_LOOP": None,
    "INTERVAL_LOOP": 300,
    "TEXT_LOOP": ""
}

IS_TAGGING = False
TAG_LOGS = []
SETTINGS_MSG_CAPTION = "#SELFBOT_CONFIG_DATA"

async def save_config_to_telegram():
    """ذخیره‌سازی دائمی تنظیمات در پیام‌های ذخیره‌شده (Saved Messages)"""
    try:
        config_json = json.dumps(CONFIG, ensure_ascii=False, indent=2)
        text = f"{SETTINGS_MSG_CAPTION}\n```json\n{config_json}\n```"
        
        async for msg in app.get_chat_history("me", limit=20):
            if msg.text and SETTINGS_MSG_CAPTION in msg.text:
                await msg.edit_text(text)
                return
        await app.send_message("me", text)
    except Exception as e:
        print(f"Error saving config: {e}")

async def load_config_from_telegram():
    """بازیابی تنظیمات پس از ری‌استارت"""
    global CONFIG
    try:
        async for msg in app.get_chat_history("me", limit=20):
            if msg.text and SETTINGS_MSG_CAPTION in msg.text:
                json_str = msg.text.split("```json\n")[1].split("\n```")[0]
                loaded_data = json.loads(json_str)
                CONFIG.update(loaded_data)
                print("Config loaded successfully!")
                return
    except Exception as e:
        print(f"Error loading config: {e}")

# ----------------- HELPER FUNCTIONS -----------------

def get_clock_string():
    now = datetime.now().strftime("%H:%M")
    styles = {
        1: f"⏰ {now}",
        2: f"[{now}]",
        3: f"✦ {now} ✦",
        4: f"• {now} •"
    }
    return styles.get(CONFIG["CLOCK_STYLE"], f"⏰ {now}")

# ----------------- BACKGROUND TASKS -----------------

async def clock_task():
    """وظیفه به‌روزرسانی هوشمند ساعت روی اسم و بیوگرافی"""
    while True:
        if CONFIG["IS_SELF_ON"]:
            clock_text = get_clock_string()
            
            if CONFIG["IS_CLOCK_NAME"]:
                try:
                    base_name = CONFIG["ORIGINAL_NAME"] or "User"
                    await app.update_profile(first_name=f"{base_name} {clock_text}")
                except Exception as e:
                    print(f"Clock Name Error: {e}")
            
            if CONFIG["IS_CLOCK_BIO"]:
                try:
                    base_bio = CONFIG["ORIGINAL_BIO"] or ""
                    new_bio = f"{base_bio} | {clock_text}".strip(" |")
                    await app.update_profile(bio=new_bio[:70])
                except Exception as e:
                    print(f"Clock Bio Error: {e}")

        await asyncio.sleep(60)

async def loop_sender_task():
    """ارسال تکراری هوشمند با ذخیره‌سازی وضعیت"""
    while True:
        if CONFIG["IS_SELF_ON"] and CONFIG["IS_LOOP_ON"] and CONFIG["TARGET_CHAT_LOOP"] and CONFIG["TEXT_LOOP"]:
            try:
                await app.send_message(CONFIG["TARGET_CHAT_LOOP"], CONFIG["TEXT_LOOP"])
            except Exception as e:
                print(f"Error in Loop: {e}")

            delay = CONFIG["INTERVAL_LOOP"] + random.randint(1, 5)
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(5)

# ----------------- DASHBOARD & PANEL -----------------

@app.on_message(filters.me & filters.command("self", prefixes="."))
async def toggle_selfbot(client, message):
    cmd = message.text.split()
    if len(cmd) > 1:
        if cmd[1].lower() == "off":
            CONFIG["IS_SELF_ON"] = False
            await message.edit_text("🔴 **سلف‌بات غیرفعال شد.**")
        elif cmd[1].lower() == "on":
            CONFIG["IS_SELF_ON"] = True
            await message.edit_text("🟢 **سلف‌بات فعال شد.**")
        await save_config_to_telegram()
    else:
        status = "🟢 روشن" if CONFIG["IS_SELF_ON"] else "🔴 خاموش"
        await message.edit_text(f"⚙️ **وضعیت کلی سلف‌بات:** {status}")

@app.on_message(filters.me & filters.command(["help", "panel"], prefixes="."))
async def show_help(client, message):
    if not CONFIG["IS_SELF_ON"]: return

    st_self = "🟢" if CONFIG["IS_SELF_ON"] else "🔴"
    st_cname = f"🟢 (استایل {CONFIG['CLOCK_STYLE']})" if CONFIG["IS_CLOCK_NAME"] else "🔴"
    st_cbio = "🟢" if CONFIG["IS_CLOCK_BIO"] else "🔴"
    st_afk = "🟢" if CONFIG["IS_AFK_ON"] else "🔴"
    st_antidel = "🟢" if CONFIG["IS_ANTIDEL_ON"] else "🔴"
    st_antiedit = "🟢" if CONFIG["IS_ANTIEDIT_ON"] else "🔴"
    st_loop = "🟢" if CONFIG["IS_LOOP_ON"] else "🔴"

    st_dice = f"🟢 (هدف: {CONFIG['DICE_TARGET']})" if CONFIG["DICE_ON"] else "🔴"
    st_slot = f"🟢 (هدف: {CONFIG['SLOT_TARGET']})" if CONFIG["SLOT_ON"] else "🔴"
    st_basket = "🟢" if CONFIG["BASKET_ON"] else "🔴"
    st_bowl = "🟢" if CONFIG["BOWLING_ON"] else "🔴"

    panel_text = (
        f"📋 **داشبورد سلف‌بات اختصاصی**\n"
        f"━━━━━━━ Status ━━━━━━━\n"
        f"🤖 وضعیت سلف: {st_self}\n"
        f"⏰ ساعت اسم: {st_cname}\n"
        f"📝 ساعت بیو: {st_cbio}\n"
        f"🌙 حالت AFK: {st_afk}\n"
        f"🛡 ضد پاکسازی: {st_antidel}\n"
        f"✏️ ضد ویرایش: {st_antiedit}\n"
        f"🔄 ارسال تکراری: {st_loop}\n"
        f"🏷 تگ‌های ثبت‌شده: {len(TAG_LOGS)} عدد\n"
        f"───────────────────────\n"
        f"🎲 تاس: {st_dice}\n"
        f"🎰 اسلات: {st_slot}\n"
        f"🏀 بسکتبال: {st_basket}\n"
        f"🎳 بولینگ: {st_bowl}\n"
        f"⏱ سرعت پرتاب: {CONFIG['GAME_DELAY']} ثانیه\n"
        f"━━━━━━━ Commands ━━━━━━━\n\n"
        f"🏷 **تگ‌ها و گزارش‌ها:**\n"
        f"▫️ `.tags` ➔ مشاهده لاگ تگ‌ها\n"
        f"▫️ `.cleartags` ➔ پاکسازی تاریخچه تگ\n"
        f"▫️ `.tag [متن]` ➔ تگ تکی اعضا\n"
        f"▫️ `.all [متن]` ➔ تگ ۵ تایی اعضا\n"
        f"▫️ `.stoptag` ➔ توقف تگ‌زنی\n\n"
        f"🎲 **تنظیم بازی‌ها:**\n"
        f"▫️ `.rdice on [1-6/even/odd]` / `.rdice off` ➔ تنظیم تاس\n"
        f"▫️ `.rslot on [1-64/777/bar]` / `.rslot off` ➔ تنظیم اسلات\n"
        f"▫️ `.rbasket on` / `.rbasket off` ➔ تنظیم بسکتبال\n"
        f"▫️ `.rbowl on` / `.rbowl off` ➔ تنظیم بولینگ\n"
        f"▫️ `.rdelay [ثانیه]` ➔ تنظیم سرعت پرتاب\n\n"
        f"⚡️ **تنظیمات حساب:**\n"
        f"▫️ `.self on/off` ➔ خاموش/روشن سلف‌بات\n"
        f"▫️ `.clockname` ➔ سوئیچ ساعت اسم\n"
        f"▫️ `.clockbio` ➔ سوئیچ ساعت بیوگرافی\n"
        f"▫️ `.clockstyle [1-4]` ➔ تغییر استایل ساعت\n"
        f"▫️ `.afk [دلیل]` / `.unafk` ➔ حالت غیبت\n"
        f"▫️ `.antidel on/off` ➔ ضد پاکسازی\n"
        f"▫️ `.antiedit on/off` ➔ ضد ویرایش\n\n"
        f"💣 **اسپم و ابزارها:**\n"
        f"▫️ `.spam [تعداد] [متن]` ➔ اسپم سریع\n"
        f"▫️ `.delayspam [تاخیر] [تعداد] [متن]` ➔ اسپم با تاخیر\n"
        f"▫️ `.loop [here/آیدی] [ثانیه] [متن]` ➔ ارسال تکراری\n"
        f"▫️ `.stoploop` ➔ توقف ارسال تکراری\n"
        f"▫️ `.del [تعداد]` / `.purge` ➔ پاکسازی پیام‌ها\n"
        f"▫️ `.calc [عبارت]` ➔ ماشین حساب\n"
        f"▫️ `.type [متن]` ➔ تایپ افکتی\n"
        f"▫️ `.info` ➔ دریافت اطلاعات کاربر\n"
        f"▫️ `.ping` ➔ بررسی سرعت سلف‌بات\n"
    )
    await message.edit_text(panel_text)

# ----------------- GAME COMMANDS -----------------

@app.on_message(filters.me & filters.command("rdice", prefixes="."))
async def config_dice(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    args = message.text.split()
    if len(args) > 1 and args[1].lower() == "off":
        CONFIG["DICE_ON"] = False
        await message.edit_text("🎲 **ربات تاس غیرفعال شد.**")
    elif len(args) > 2 and args[1].lower() == "on":
        CONFIG["DICE_ON"] = True
        CONFIG["DICE_TARGET"] = args[2]
        await message.edit_text(f"🎲 **ربات تاس فعال شد.** (هدف: {args[2]})")
    await save_config_to_telegram()

@app.on_message(filters.me & filters.command("rslot", prefixes="."))
async def config_slot(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    args = message.text.split()
    if len(args) > 1 and args[1].lower() == "off":
        CONFIG["SLOT_ON"] = False
        await message.edit_text("🎰 **ربات اسلات غیرفعال شد.**")
    elif len(args) > 2 and args[1].lower() == "on":
        CONFIG["SLOT_ON"] = True
        CONFIG["SLOT_TARGET"] = args[2]
        await message.edit_text(f"🎰 **ربات اسلات فعال شد.** (هدف: {args[2]})")
    await save_config_to_telegram()

@app.on_message(filters.me & filters.command("rbasket", prefixes="."))
async def config_basket(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    args = message.text.split()
    CONFIG["BASKET_ON"] = True if (len(args) > 1 and args[1].lower() == "on") else False
    await save_config_to_telegram()
    await message.edit_text(f"🏀 **ربات بسکتبال:** {'🟢 روشن' if CONFIG['BASKET_ON'] else '🔴 خاموش'}")

@app.on_message(filters.me & filters.command("rbowl", prefixes="."))
async def config_bowl(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    args = message.text.split()
    CONFIG["BOWLING_ON"] = True if (len(args) > 1 and args[1].lower() == "on") else False
    await save_config_to_telegram()
    await message.edit_text(f"🎳 **ربات بولینگ:** {'🟢 روشن' if CONFIG['BOWLING_ON'] else '🔴 خاموش'}")

@app.on_message(filters.me & filters.command("rdelay", prefixes="."))
async def config_delay(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    args = message.text.split()
    if len(args) > 1:
        try:
            CONFIG["GAME_DELAY"] = float(args[1])
            await save_config_to_telegram()
            await message.edit_text(f"⏱ **سرعت پرتاب روی {CONFIG['GAME_DELAY']} ثانیه تنظیم شد.**")
        except ValueError:
            pass

# ----------------- GAME RUNNERS -----------------

@app.on_message(filters.me & filters.dice)
async def handle_games(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    
    emoji = message.dice.emoji
    val = message.dice.value

    # تاس (🎲)
    if emoji == "🎲" and CONFIG["DICE_ON"]:
        target = CONFIG["DICE_TARGET"]
        win = False
        if target.isdigit() and val == int(target): win = True
        elif target == "even" and val % 2 == 0: win = True
        elif target == "odd" and val % 2 != 0: win = True

        if not win:
            await asyncio.sleep(CONFIG["GAME_DELAY"])
            await message.delete()
            await app.send_dice(message.chat.id, emoji="🎲")

    # اسلات (🎰)
    elif emoji == "🎰" and CONFIG["SLOT_ON"]:
        target = CONFIG["SLOT_TARGET"]
        win = False
        if target == "777" and val == 64: win = True
        elif target.isdigit() and val == int(target): win = True

        if not win:
            await asyncio.sleep(CONFIG["GAME_DELAY"])
            await message.delete()
            await app.send_dice(message.chat.id, emoji="🎰")

    # بسکتبال (🏀)
    elif emoji == "🏀" and CONFIG["BASKET_ON"]:
        if val < 4: # اگر گل نشد
            await asyncio.sleep(CONFIG["GAME_DELAY"])
            await message.delete()
            await app.send_dice(message.chat.id, emoji="🏀")

    # بولینگ (🎳)
    elif emoji == "🎳" and CONFIG["BOWLING_ON"]:
        if val < 6: # اگر ضربه کامل (Strike) نبود
            await asyncio.sleep(CONFIG["GAME_DELAY"])
            await message.delete()
            await app.send_dice(message.chat.id, emoji="🎳")

# ----------------- OTHER COMMANDS -----------------

@app.on_message(filters.me & filters.command("clockname", prefixes="."))
async def toggle_clock_name(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    CONFIG["IS_CLOCK_NAME"] = not CONFIG["IS_CLOCK_NAME"]
    if not CONFIG["IS_CLOCK_NAME"]:
        try: await app.update_profile(first_name=CONFIG["ORIGINAL_NAME"])
        except Exception: pass
    await save_config_to_telegram()
    await message.edit_text(f"👤 **ساعت اسم:** {'🟢 روشن' if CONFIG['IS_CLOCK_NAME'] else '🔴 خاموش'}")

@app.on_message(filters.me & filters.command("clockbio", prefixes="."))
async def toggle_clock_bio(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    CONFIG["IS_CLOCK_BIO"] = not CONFIG["IS_CLOCK_BIO"]
    if not CONFIG["IS_CLOCK_BIO"]:
        try: await app.update_profile(bio=CONFIG["ORIGINAL_BIO"])
        except Exception: pass
    await save_config_to_telegram()
    await message.edit_text(f"📝 **ساعت بیو:** {'🟢 روشن' if CONFIG['IS_CLOCK_BIO'] else '🔴 خاموش'}")

@app.on_message(filters.me & filters.command("clockstyle", prefixes="."))
async def change_clock_style(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    cmd = message.text.split()
    if len(cmd) > 1 and cmd[1].isdigit() and int(cmd[1]) in [1, 2, 3, 4]:
        CONFIG["CLOCK_STYLE"] = int(cmd[1])
        await save_config_to_telegram()
        await message.edit_text(f"✅ **استایل ساعت روی {CONFIG['CLOCK_STYLE']} تنظیم شد.**")

@app.on_message(filters.me & filters.command("afk", prefixes="."))
async def set_afk(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    CONFIG["AFK_REASON"] = message.text.replace(".afk", "").strip() or "در دسترس نیستم"
    CONFIG["IS_AFK_ON"] = True
    await save_config_to_telegram()
    await message.edit_text(f"🌙 **حالت غیبت فعال شد.**")

@app.on_message(filters.me & filters.command("unafk", prefixes="."))
async def unset_afk(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    CONFIG["IS_AFK_ON"] = False
    await save_config_to_telegram()
    await message.edit_text("☀️ **حالت غیبت غیرفعال شد.**")

@app.on_message(filters.me & filters.command("loop", prefixes="."))
async def start_loop(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.edit_text("❌ `.loop [here/آیدی] [ثانیه] [متن]`")
        return
    
    target = message.chat.id if args[1] == "here" else (int(args[1]) if args[1].lstrip('-').isdigit() else args[1])
    CONFIG["INTERVAL_LOOP"] = int(args[2])
    CONFIG["TEXT_LOOP"] = args[3]
    CONFIG["TARGET_CHAT_LOOP"] = target
    CONFIG["IS_LOOP_ON"] = True
    await save_config_to_telegram()
    await message.edit_text(f"🔄 **ارسال تکراری فعال و ذخیره شد!**\n🎯 **هدف:** `{target}`")

@app.on_message(filters.me & filters.command("stoploop", prefixes="."))
async def stop_loop(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    CONFIG["IS_LOOP_ON"] = False
    await save_config_to_telegram()
    await message.edit_text("🛑 **ارسال تکراری متوقف شد.**")

@app.on_message(filters.me & filters.command("spam", prefixes="."))
async def fast_spam(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    args = message.text.split(maxsplit=2)
    if len(args) < 3 or not args[1].isdigit():
        await message.edit_text("❌ `.spam [تعداد] [متن]`")
        return
    count = int(args[1])
    text = args[2]
    await message.delete()
    for _ in range(count):
        await app.send_message(message.chat.id, text)
        await asyncio.sleep(0.3)

@app.on_message(filters.me & filters.command("delayspam", prefixes="."))
async def delay_spam(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.edit_text("❌ `.delayspam [تاخیر به ثانیه] [تعداد] [متن]`")
        return
    delay = float(args[1])
    count = int(args[2])
    text = args[3]
    await message.delete()
    for _ in range(count):
        await app.send_message(message.chat.id, text)
        await asyncio.sleep(delay)

@app.on_message(filters.me & filters.command("del", prefixes="."))
async def delete_msgs(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    cmd = message.text.split()
    count = int(cmd[1]) if len(cmd) > 1 and cmd[1].isdigit() else 1
    async for msg in app.get_chat_history(message.chat.id, limit=count + 1):
        if msg.from_user and msg.from_user.is_self:
            await msg.delete()

@app.on_message(filters.me & filters.command("purge", prefixes="."))
async def purge_msgs(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    if not message.reply_to_message:
        await message.edit_text("❌ روی یک پیام ریپلای کنید.")
        return
    start_id = message.reply_to_message.id
    end_id = message.id
    await app.delete_messages(message.chat.id, list(range(start_id, end_id + 1)))

@app.on_message(filters.me & filters.command("type", prefixes="."))
async def typewriter_effect(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    text = message.text.replace(".type", "").strip()
    if not text: return
    current_text = ""
    for char in text:
        current_text += char
        await message.edit_text(current_text + "▒")
        await asyncio.sleep(0.1)
    await message.edit_text(current_text)

@app.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping_cmd(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    start = datetime.now()
    await message.edit_text("🚀")
    end = datetime.now()
    ms = (end - start).microseconds / 1000
    await message.edit_text(f"⚡️ `{ms:.2f} ms`")

@app.on_message(filters.me & filters.command("calc", prefixes="."))
async def calc_cmd(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    expr = message.text.replace(".calc", "").strip()
    try:
        res = eval(expr)
        await message.edit_text(f"🔢 `{res}`")
    except Exception as e:
        await message.edit_text(f"❌ Error: `{e}`")

# ----------------- TAGGING LOGS & FUNCTIONS -----------------

@app.on_message(filters.me & filters.command("tag", prefixes="."))
async def tag_single(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    global IS_TAGGING
    IS_TAGGING = True
    tag_text = message.text.replace(".tag", "").strip() or "تگ"
    await message.delete()
    async for member in app.get_chat_members(message.chat.id):
        if not IS_TAGGING: break
        if not member.user.is_bot:
            await app.send_message(message.chat.id, f"[{member.user.first_name}](tg://user?id={member.user.id}) {tag_text}")
            await asyncio.sleep(2)

@app.on_message(filters.me & filters.command("all", prefixes="."))
async def tag_five(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    global IS_TAGGING
    IS_TAGGING = True
    tag_text = message.text.replace(".all", "").strip() or "تگ"
    await message.delete()
    members_list = []
    async for member in app.get_chat_members(message.chat.id):
        if not IS_TAGGING: break
        if not member.user.is_bot:
            members_list.append(f"[{member.user.first_name}](tg://user?id={member.user.id})")
            if len(members_list) == 5:
                await app.send_message(message.chat.id, f"{' | '.join(members_list)}\n\n📣 {tag_text}")
                members_list = []
                await asyncio.sleep(3)

@app.on_message(filters.me & filters.command("stoptag", prefixes="."))
async def stop_tag(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    global IS_TAGGING
    IS_TAGGING = False
    await message.edit_text("🛑 **عملیات تگ متوقف شد.**")

@app.on_message(filters.me & filters.command("tags", prefixes="."))
async def show_tags_log(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    if not TAG_LOGS:
        await message.edit_text("🏷 **هیچ تگی ثبت نشده است.**")
    else:
        logs_text = "\n".join(TAG_LOGS[-10:])
        await message.edit_text(f"📋 **آخرین تگ‌های ثبت‌شده:**\n\n{logs_text}")

@app.on_message(filters.me & filters.command("cleartags", prefixes="."))
async def clear_tags_log(client, message):
    if not CONFIG["IS_SELF_ON"]: return
    global TAG_LOGS
    TAG_LOGS = []
    await message.edit_text("🗑 **تاریخچه تگ‌ها پاک شد.**")

@app.on_message(filters.mentioned)
async def log_mentions(client, message):
    if CONFIG["IS_SELF_ON"]:
        chat_name = message.chat.title if message.chat.title else "پی‌وی"
        sender = message.from_user.first_name if message.from_user else "ناشناس"
        log_entry = f"📍 {chat_name} | 👤 {sender}: {message.text[:20]}..."
        TAG_LOGS.append(log_entry)

# ----------------- SECURITY LISTENERS -----------------

@app.on_edited_message()
async def anti_edit_handler(client, message):
    if CONFIG["IS_SELF_ON"] and CONFIG["IS_ANTIEDIT_ON"]:
        if not message.from_user or message.from_user.is_self: return
        try:
            chat_title = message.chat.title if message.chat.title else "پی‌وی"
            user_info = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
            log_text = (
                f"✏️ **ویرایش پیام شناسایی شد!**\n\n"
                f"👤 **کاربر:** {user_info}\n"
                f"📍 **مکان:** {chat_title}\n"
                f"📝 **متن جدید:**\n`{message.text}`"
            )
            await app.send_message("me", log_text)
        except Exception:
            pass

@app.on_deleted_messages()
async def anti_delete_handler(client, messages):
    if CONFIG["IS_SELF_ON"] and CONFIG["IS_ANTIDEL_ON"]:
        for msg in messages:
            if msg.text:
                try:
                    await app.send_message("me", f"🗑 **پیام پاک‌شده:**\n\n`{msg.text}`")
                except Exception:
                    pass

# ----------------- STARTUP -----------------

async def main():
    await app.start()
    print("Selfbot started!")
    
    me = await app.get_me()
    CONFIG["ORIGINAL_NAME"] = me.first_name or ""
    
    try:
        full_user = await app.get_chat("me")
        CONFIG["ORIGINAL_BIO"] = full_user.bio or ""
    except Exception:
        CONFIG["ORIGINAL_BIO"] = ""

    # بازیابی تنظیمات قبلی از پیام‌های ذخیره‌شده
    await load_config_from_telegram()

    # فعال‌سازی وظایف پس‌زمینه
    asyncio.create_task(clock_task())
    asyncio.create_task(loop_sender_task())
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
