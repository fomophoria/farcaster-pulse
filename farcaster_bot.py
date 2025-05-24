import requests
import time
import schedule
import threading
from datetime import datetime, timedelta
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext
import os
import re

# === CONFIGURATION ===
TELEGRAM_TOKEN = "7599241241:AAFEX_O35qT8fF6kaC8Gkhn4oRtVg2efwvo"
CHAT_ID = "-1002587768754"
NEY_API_KEY = "3EFCD2D1-2D55-4AF2-9A5A-8C8FD6732222"
SEEN_HASHES_FILE = "seen_hashes.txt"

bot = Bot(token=TELEGRAM_TOKEN)
FIDS_TO_MONITOR = []
seen_hashes = set()
last_alert = None
last_alert_times = {}
start_time = datetime.now()

# === UTILS ===
def escape(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def load_fids():
    if not os.path.exists("popular_fids.txt"):
        return []
    with open("popular_fids.txt", "r") as f:
        return [int(line.strip()) for line in f if line.strip().isdigit()]

def load_seen_hashes():
    if os.path.exists(SEEN_HASHES_FILE):
        with open(SEEN_HASHES_FILE, "r") as f:
            return set(line.strip() for line in f)
    return set()

def save_seen_hash(hash_):
    with open(SEEN_HASHES_FILE, "a") as f:
        f.write(f"{hash_}\n")

FIDS_TO_MONITOR = load_fids()
seen_hashes = load_seen_hashes()

# === COMMAND HANDLERS ===
def about_command(update: Update, context: CallbackContext):
    message = (
        "*__About FarcasterPulse__*\n\n"
        "I'm FarcasterPulse\\. Built by @FOMOphoria, I'm programmed to monitor token deployments via Clanker on Farcaster in real\\-time\\.\n\n"
        "I monitor the top users on Farcaster with over 1200 FIDs in my records\\.\n\n"
        "I'll provide you alerts containing the cast, contract, and links so that you can be the first to buy\\.\n\n"
        "Built for alpha signal\\. Built for speed\\.\n"
        "Be ahead of the game\\."
    )
    context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode="MarkdownV2")

def commands_command(update: Update, context: CallbackContext):
    message = (
        "*Available Commands:*\n\n"
        "/about \\- Learn what FarcasterPulse is\n"
        "/commands \\- Show this command list\n"
        "/help \\- Summary of all commands\n"
        "/info \\- Number of FIDs being monitored\n"
        "/lastlaunch \\- Most recent token alert\n"
        "/start \\- Confirms the bot is live\n"
        "/uptime \\- Shows how long the bot has been running"
    )
    context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode="MarkdownV2")

def help_command(update: Update, context: CallbackContext):
    commands = ["/about", "/commands", "/help", "/info", "/lastlaunch", "/start", "/uptime"]
    context.bot.send_message(chat_id=update.effective_chat.id, text="Commands (A-Z):\n" + "\n".join(sorted(commands)))

def info_command(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"📡 Monitoring {len(FIDS_TO_MONITOR)} FIDs.")

def lastlaunch_command(update: Update, context: CallbackContext):
    if not last_alert:
        context.bot.send_message(chat_id=update.effective_chat.id, text="No launches detected yet.")
    else:
        name, username, text, url, ts = last_alert
        ago = datetime.now() - ts
        msg = (
            f"📡 Last launch:\n\n"
            f"🚀 @{username} — {name}\n"
            f"🕒 {str(ago).split('.')[0]} ago\n\n"
            f"🗣️ \"{text}\"\n\n"
            f"🔗 {url}"
        )
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

def start_command(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="🤖 FarcasterPulse is online.")

def uptime_command(update: Update, context: CallbackContext):
    uptime = datetime.now() - start_time
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"⏱️ Uptime: {str(uptime).split('.')[0]}")

def start_command_listener():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("about", about_command))
    dp.add_handler(CommandHandler("commands", commands_command))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("info", info_command))
    dp.add_handler(CommandHandler("lastlaunch", lastlaunch_command))
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("uptime", uptime_command))
    updater.start_polling()

# === DUMMY ALERT ON STARTUP ===
def send_dummy_launch():
    dummy_name = "Demo User"
    dummy_username = "demouser"
    dummy_text = "Just deployed via @clanker on Farcaster!"
    dummy_url = "https://warpcast.com/demouser/abcd1234"
    dummy_timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    dummy_contract = "0xDEMO000000000000000000000000000000000000"

    sigma_url = f"https://t.me/Sigma_buyBot?start={dummy_contract}"
    dexscreener_url = f"https://dexscreener.com/base/{dummy_contract}"
    clanker_url = f"https://clanker.world/clanker/{dummy_contract}"

    message = (
        f"🚨 *FarcasterPulse Alert*\n\n"
        f"🚀 {escape(dummy_name)} [@{escape(dummy_username)}](https://warpcast.com/{escape(dummy_username)}) just launched a token via Clanker\\!\n\n"
        f"🕒 Timestamp: `{dummy_timestamp}`\n"
        f"🗣️ Original cast:\n\"{escape(dummy_text)}\"\n\n"
        f"🔗 [View the cast]({escape(dummy_url)})\n\n"
        f"🧾 Contract:\n`{dummy_contract}`\n"
        f"🔗 [View token on Clanker]({clanker_url})"
    )

    buttons = [
        [InlineKeyboardButton("Buy via Sigma", url=sigma_url)],
        [InlineKeyboardButton("View on Dexscreener", url=dexscreener_url)]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="MarkdownV2", reply_markup=reply_markup)

# === STARTUP ===
def send_startup_message():
    try:
        startup = (
            "🟢 *FarcasterPulse v1\\.0 initialized*\n"
            f"> Watching *{len(FIDS_TO_MONITOR)}* FIDs\\.\n"
            "> Alerts will appear here in real\\-time\\."
        )
        bot.send_message(chat_id=CHAT_ID, text=startup, parse_mode="MarkdownV2")
        send_dummy_launch()
    except Exception as e:
        print(f"Startup message failed: {e}")

# === RUNNING ===
def monitor_and_alert():
    global last_alert
    for fid in FIDS_TO_MONITOR:
        url = f"https://api.neynar.com/v2/farcaster/feed?feed_type=user_casts&fid={fid}&limit=5"
        headers = {"api_key": NEY_API_KEY}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                continue
            casts = response.json().get("casts", [])
        except Exception as e:
            print(f"Error fetching casts for FID {fid}: {e}")
            continue

        for cast in casts:
            if cast.get("parent_hash") or cast.get("parent_url"):
                continue  # Skip replies

            hash_ = cast.get("hash")
            if not hash_ or hash_ in seen_hashes:
                continue

            text = cast.get("text", "")
            if "@clanker" not in text.lower() or "deploy" not in text.lower():
                continue

            author = cast.get("author", {})
            name = author.get("display_name", "Unknown")
            username = author.get("username", "unknown")
            followers = author.get("followers", 0)

            timestamp = cast.get("timestamp")
            try:
                formatted_time = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f").strftime("%d/%m/%Y %H:%M:%S")
            except:
                formatted_time = timestamp

            warpcast_url = f"https://warpcast.com/{username}/{hash_}"

            # Get replies to find Clanker confirmation
            reply_url = f"https://api.neynar.com/v2/farcaster/replies?cast_hash={hash_}&limit=10"
            try:
                reply_response = requests.get(reply_url, headers=headers)
                reply_casts = reply_response.json().get("result", {}).get("casts", [])
            except:
                reply_casts = []

            contract = None
            token_info = ""
            for reply in reply_casts:
                if reply.get("author", {}).get("username") == "clanker":
                    reply_text = reply.get("text", "")
                    match = re.search(r"0x[a-fA-F0-9]{40}", reply_text)
                    if match:
                        contract = match.group()
                    token_info = reply_text.strip().splitlines()[0]
                    break

            # Rate limit per user per hour
            last_time = last_alert_times.get(fid)
            if last_time and datetime.now() - last_time < timedelta(hours=1):
                continue

            message = (
                f"🚨 *FarcasterPulse Alert*\n\n"
                f"🚀 {escape(name)} [@{escape(username)}](https://warpcast.com/{escape(username)}) just launched a token via Clanker\\!\n\n"
                f"👥 Followers: `{followers}`\n"
                f"🕒 Timestamp: `{formatted_time}`\n"
                f"🗣️ Original cast:\n\"{escape(text)}\"\n\n"
                f"🔗 [View the cast]({escape(warpcast_url)})"
            )

            if contract:
                clanker_link = f"https://clanker.world/clanker/{contract}"
                dexscreener_url = f"https://dexscreener.com/base/{contract}"
                message += (
                    f"\n\n🧾 Contract:\n`{contract}`\n"
                    f"🔗 [View token on Clanker]({clanker_link})"
                )

                buttons = [
                    [InlineKeyboardButton("Buy via Sigma", url=f"https://t.me/Sigma_buyBot?start={contract}")],
                    [InlineKeyboardButton("View on Dexscreener", url=dexscreener_url)]
                ]
                reply_markup = InlineKeyboardMarkup(buttons)
            else:
                reply_markup = None

            bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="MarkdownV2", reply_markup=reply_markup)
            last_alert = (name, username, text, warpcast_url, datetime.now())
            last_alert_times[fid] = datetime.now()
            seen_hashes.add(hash_)
            save_seen_hash(hash_)


# === MAIN LOOP ===
if __name__ == "__main__":
    send_startup_message()
    schedule.every(1).seconds.do(monitor_and_alert)
    threading.Thread(target=start_command_listener).start()
    while True:
        schedule.run_pending()
        time.sleep(1)
