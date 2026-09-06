import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
import os
import random
import time
import datetime
import hmac
import hashlib
import struct
import base64
import re
import json

# ==========================================
# ➜ বটের মূল কনফিগারেশন ও অ্যাডমিনদের লিস্ট
# ==========================================
TOKEN = '8732062813:AAFdiVXZ3yqMWqfL_sZFilMuZdLhDoGxUnc'
ADMIN_IDS = [8707571669, 6108727047]
MIN_WITHDRAW = 50.0

bot = telebot.TeleBot(TOKEN)
try:
    bot_info = bot.get_me()
    BOT_USERNAME = bot_info.username
except Exception as e:
    BOT_USERNAME = "GoTaskPayBot"

# 𖤓 ফায়ারবেস রিয়েলটাইম ডাটাবেজ URL
FIREBASE_URL = "https://x7e77eey-default-rtdb.firebaseio.com"

# ==========================================
# 𖤓 নাম ডাটাবেজ
# ==========================================
FEMALE_FIRST_NAMES = [
    "Olivia", "Charlotte", "Emma", "Amelia", "Sophia", "Mia", "Isabella", "Evelyn", "Sofia", "Eliana", 
    "Ava", "Luna", "Camila", "Harper", "Lily", "Eleanor", "Violet", "Aurora", "Elizabeth", "Emily", 
    "Scarlett", "Ella", "Avery", "Mila", "Aria", "Abigail", "Chloe", "Ellie", "Nora", "Hazel", 
    "Penelope", "Layla", "Lillian", "Addison", "Riley", "Zoey", "Paisley", "Stella", "Willow", "Lucy", 
    "Naomi", "Elena", "Ivy", "Grace", "Victoria", "Emilia", "Natalie", "Hannah", "Valentina", "Leah", 
    "Maya", "Claire", "Genesis", "Madeline", "Sadie", "Delilah", "Aubrey", "Kinsley", "Ruby", "Sophie", 
    "Isla", "Alice", "Caroline", "Iris", "Nevaeh", "Everleigh", "Jasmine", "Athena", "Gabriella", "Peyton", 
    "Rylee", "Clara", "Vivian", "Lydia", "Madelyn", "Raelynn", "Melody", "Julia", "Piper", "Brielle", 
    "Reagan", "Rose", "Eliza", "Cora", "Hadley", "Melanie", "Mackenzie", "Faith", "Kylie", "Daisy", 
    "Josie", "Maria", "Isabelle", "Autumn", "Adeline", "Taylor", "Josephine", "Kennedy", "Sarah", 
    "Delaney", "Jade", "Parker", "Londyn", "Eloise", "Jordyn", "Morgan", "Emery", "Charlie", "Arianna"
]

MALE_FIRST_NAMES = [
    "Liam", "Noah", "Oliver", "Theodore", "Henry", "James", "Elijah", "Mateo", "William", "Lucas", 
    "Benjamin", "Levi", "Mason", "Ethan", "Logan", "Alexander", "Jackson", "Sebastian", "Jack", "Michael", 
    "Daniel", "Owen", "Asher", "Ezra", "John", "Hudson", "Luca", "Aiden", "Joseph", "David", 
    "Jacob", "Leo", "Julian", "Luke", "Wesley", "Wyatt", "Matthew", "Grayson", "Carter", "Isaac", 
    "Jayden", "Gabriel", "Anthony", "Dylan", "Lincoln", "Thomas", "Maverick", "Elias", "Josiah", "Charles", 
    "Caleb", "Christopher", "Ezekiel", "Miles", "Jaxon", "Isaiah", "Andrew", "Joshua", "Nathan", "Nolan"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", 
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", 
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", 
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"
]

# ==========================================
# ➜ ফায়ারবেস ফাংশন (REST API)
# ==========================================
def db_get(path):
    try:
        res = requests.get(f"{FIREBASE_URL}/{path}.json", timeout=10).json()
        return res if res is not None else {}
    except:
        return {}

def db_put(path, data):
    try: 
        requests.put(f"{FIREBASE_URL}/{path}.json", json=data, timeout=10)
    except: 
        pass

def db_patch(path, data):
    try: 
        requests.patch(f"{FIREBASE_URL}/{path}.json", json=data, timeout=10)
    except: 
        pass

def db_post(path, data):
    try: 
        res = requests.post(f"{FIREBASE_URL}/{path}.json", json=data, timeout=10).json()
        return res.get("name") if isinstance(res, dict) else None
    except: 
        return None

def db_delete(path):
    try: 
        requests.delete(f"{FIREBASE_URL}/{path}.json", timeout=10)
    except: 
        pass

# ==========================================
# ➜ 2FA / TOTP রিয়েলটাইম ইঞ্জিন
# ==========================================
def sanitize_base32(key_str):
    if not key_str:
        return ""
    return re.sub(r'[^A-Za-z2-7]', '', str(key_str).upper())

def is_valid_base32(key_str):
    clean = sanitize_base32(key_str)
    if len(clean) in [16, 26, 32, 48, 64]:
        return True
    if len(clean) >= 16 and re.match(r'^[A-Z2-7]+$', clean):
        return True
    return False

def generate_totp_code_local(secret_key):
    try:
        clean_key = sanitize_base32(secret_key)
        missing_padding = len(clean_key) % 8
        if missing_padding != 0:
            clean_key += '=' * (8 - missing_padding)
        
        key_bytes = base64.b32decode(clean_key, casefold=True)
        current_time = int(time.time())
        time_step = struct.pack(">Q", current_time // 30)
        
        hmac_hash = hmac.new(key_bytes, time_step, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        code_int = struct.unpack(">I", hmac_hash[offset:offset+4])[0] & 0x7FFFFFFF
        code = str(code_int % 1000000).zfill(6)
        remaining_seconds = 30 - (current_time % 30)
        return code, remaining_seconds
    except Exception:
        return None, 0

def fetch_totp_code(secret_key):
    clean_key = sanitize_base32(secret_key)
    if not clean_key:
        return None, 0
    
    local_code, rem = generate_totp_code_local(clean_key)
    
    try:
        api_url = f"https://2fa.cn/codes/{clean_key}"
        res = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict):
                if "code" in data and str(data["code"]).isdigit():
                    return str(data["code"]).zfill(6), rem
                elif "data" in data and isinstance(data["data"], dict) and "code" in data["data"]:
                    return str(data["data"]["code"]).zfill(6), rem
    except Exception:
        pass
    
    if local_code:
        return local_code, rem
    return None, 0

# ==========================================
# ➜ ডাইনামিক পরিচয় ও পাসওয়ার্ড জেনারেটর
# ==========================================
def generate_dynamic_credentials(platform="FACEBOOK"):
    today_day = datetime.datetime.now().strftime("%d")
    is_female = random.choice([True, False])
    first_name = random.choice(FEMALE_FIRST_NAMES) if is_female else random.choice(MALE_FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    
    pwd_style = f"Rube1@{today_day}"
    suffixes = ["sky", "top", "pro", "mail", "live", "bd", "star", "net"]
    rand_num = random.randint(100, 9999)
    email = f"{first_name.lower()}{rand_num}{random.choice(suffixes)}@gmail.com"
    username = f"{first_name.lower()}.{last_name.lower()}{random.randint(10, 999)}"
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}",
        "password": pwd_style,
        "email": email,
        "username": username
    }

# ==========================================
# ↻ ডিফল্ট ডাটাবেজ ইনিশিয়ালাইজেশন
# ==========================================
def init_data():
    channels = [
        ("@RS_FUTURE_JOB_EXPRESS_OTP", "https://t.me/RS_FUTURE_JOB_EXPRESS_OTP"),
        ("@RS_FUTURE_JOB_EXPRESS_MOTHER", "https://t.me/RS_FUTURE_JOB_EXPRESS_MOTHER"),
        ("@Rs_express_jod", "https://t.me/Rs_express_jod")
    ]
    
    existing_channels = db_get("force_channels")
    if not existing_channels:
        for idx, (username, url) in enumerate(channels):
            db_put(f"force_channels/ch_{idx}", {"username": username, "url": url})
            
    db_put("settings/admin_contact", {"value": "https://t.me/Rubel_Owner"})
    db_put("settings/support_channel", {"value": "https://t.me/RS_FUTURE_JOB_EXPRESS_OTP"})
    db_put("settings/tutorial_link", {"value": "https://t.me/RS_FUTURE_JOB_EXPRESS_VIDEO"})
    if not db_get("settings/min_withdraw"):
        db_put("settings/min_withdraw", {"value": MIN_WITHDRAW})

    existing_tasks = db_get("tasks")
    if not existing_tasks:
        db_put("tasks/task_fb_1", {"platform": "FACEBOOK", "name": "FB 2FA", "price": 5.50, "type": "2fa"})
        db_put("tasks/task_fb_2", {"platform": "FACEBOOK", "name": "FB Cookies", "price": 5.10, "type": "cookies"})
        db_put("tasks/task_ig_1", {"platform": "INSTAGRAM", "name": "Instagram 2FA", "price": 2.00, "type": "2fa"})
        db_put("tasks/task_gm_1", {"platform": "GMAIL", "name": "Gmail Task", "price": 14.00, "type": "gmail"})

init_data()

def get_setting(key, default=""):
    res = db_get(f"settings/{key}")
    return res.get("value", default) if isinstance(res, dict) else default

# ==========================================
# 𖤓 টেক্সট ডিকশনারি ও মেনু বাটন
# ==========================================
lang_dict = {
    "bn": {
        "menu_profile": "❖ 𝐏𝐑𝐎𝐅𝐈𝐋𝐄", "menu_task": "⚡ 𝐓𝐀𝐒𝐊", "menu_withdraw": "⛃ 𝐖𝐈𝐓𝐇𝐃𝐑𝐀𝐖",
        "menu_support": "☏ 𝐒𝐔𝐏𝐏𝐎𝐑𝐓", "menu_refer": "⊛ 𝐑𝐄𝐅𝐄𝐑𝐑𝐀𝐋", "menu_how": "⚙ 𝐇𝐎𝐖 𝐓𝐎 𝐖𝐎𝐑𝐊",
        "menu_lang": "↻ 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄", "menu_leader": "≡ 𝐋𝐄𝐀𝐃𝐄𝐑𝐁𝐎𝐀𝐑𝐃",
        "welcome": "❖ 𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐓𝐎 𝐆𝐎𝐓𝐀𝐒𝐊 𝐏𝐀𝐘\n**{}**\n\nꪜ প্রতিদিন টাস্ক কমপ্লিট করুন আর ইনকাম করুন।\nꪜ ১০০% অটোমেটিক পেমেন্ট সিস্টেম।\n⚡ ইনস্ট্যান্ট উত্তোলন সুবিধা।\n✦ বন্ধুদের রেফার করে আজীবন ১০% কমিশন পান।\n\n➜ আজই ইনকাম শুরু করুন!"
    },
    "en": {
        "menu_profile": "❖ 𝐏𝐑𝐎𝐅𝐈𝐋𝐄", "menu_task": "⚡ 𝐓𝐀𝐒𝐊", "menu_withdraw": "⛃ 𝐖𝐈𝐓𝐇𝐃𝐑𝐀𝐖",
        "menu_support": "☏ 𝐒𝐔𝐏𝐏𝐎𝐑𝐓", "menu_refer": "⊛ 𝐑𝐄𝐅𝐄𝐑𝐑𝐀𝐋", "menu_how": "⚙ 𝐇𝐎𝐖 𝐓𝐎 𝐖𝐎𝐑𝐊",
        "menu_lang": "↻ 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄", "menu_leader": "≡ 𝐋𝐄𝐀𝐃𝐄𝐑𝐁𝐎𝐀𝐑𝐃",
        "welcome": "❖ 𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐓𝐎 𝐆𝐎𝐓𝐀𝐒𝐊 𝐏𝐀𝐘\n**{}**\n\nꪜ Complete tasks & earn daily income.\nꪜ 100% Automatic Payment System.\n⚡ Instant Withdrawal Support.\n✦ Invite friends & get 10% referral bonus forever.\n\n➜ Start your journey now!"
    }
}

user_states = {}

def get_unjoined_channels(user_id):
    if user_id in ADMIN_IDS: 
        return []
    unjoined = []
    channels = db_get("force_channels")
    if channels and isinstance(channels, dict):
        for key, ch_data in channels.items():
            ch_user = ch_data.get("username")
            ch_url = ch_data.get("url")
            try:
                status = bot.get_chat_member(ch_user, user_id).status
                if status not in ['member', 'administrator', 'creator']:
                    unjoined.append((ch_user, ch_url))
            except Exception:
                unjoined.append((ch_user, ch_url))
    return unjoined

def force_sub_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    channels = db_get("force_channels")
    if channels and isinstance(channels, dict):
        idx = 1
        for key, ch_data in channels.items():
            markup.add(InlineKeyboardButton(f"➜ JOIN OFFICIAL CHANNEL {idx}", url=ch_data.get("url")))
            idx += 1
    markup.add(InlineKeyboardButton("☑ VERIFY MEMBERSHIP", callback_data="check_join"))
    return markup

def main_keyboard(lang="bn"):
    if lang not in lang_dict:
        lang = "bn"
    t = lang_dict[lang]
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton(t["menu_profile"]), KeyboardButton(t["menu_task"]))
    markup.add(KeyboardButton(t["menu_withdraw"]), KeyboardButton(t["menu_support"]))
    markup.add(KeyboardButton(t["menu_refer"]), KeyboardButton(t["menu_how"]))
    markup.add(KeyboardButton(t["menu_lang"]), KeyboardButton(t["menu_leader"]))
    return markup

def ask_language(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("বাংলা (BANGLA)", callback_data="lang_bn"), InlineKeyboardButton("ENGLISH", callback_data="lang_en"))
    bot.send_message(chat_id, "↻ 𝐏𝐋𝐄𝐀𝐒𝐄 𝐒𝐄𝐋𝐄𝐂𝐓 𝐘𝐎𝐔𝐑 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄:\nদয়া করে আপনার ভাষা নির্বাচন করুন:", reply_markup=markup)

# ==========================================
# 🚀 USER SYSTEM & NAVIGATION
# ==========================================
@bot.message_handler(commands=['start'])
def send_start(message):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else (message.from_user.first_name or "User")
    text = message.text.split()
    referrer_id = text[1] if len(text) > 1 else None
    
    user = db_get(f"users/{user_id}")
    
    if not user:
        db_put(f"users/{user_id}", {
            "lang": "bn", 
            "username": username,
            "balance": 0.0, 
            "total_earned": 0.0,
            "total_submitted": 0,
            "pending_task": 0, 
            "approved_task": 0,
            "rejected_task": 0,
            "referrals": 0, 
            "referrer": referrer_id,
            "earned_from_ref": 0.0,
            "joined_at": int(time.time())
        })
        if referrer_id and referrer_id.isdigit() and int(referrer_id) != user_id:
            ref_data = db_get(f"users/{referrer_id}")
            if ref_data:
                current_refs = ref_data.get("referrals", 0)
                db_patch(f"users/{referrer_id}", {"referrals": current_refs + 1})
                try: 
                    bot.send_message(int(referrer_id), "✦ 𝐍𝐄𝐖 𝐑𝐄𝐅𝐄𝐑𝐑𝐀𝐋! একজন মেম্বার আপনার লিংকে জয়েন করেছে।")
                except: 
                    pass
        lang = "bn"
    else: 
        lang = user.get("lang", "bn")
        db_patch(f"users/{user_id}", {"username": username})

    unjoined = get_unjoined_channels(user_id)
    if unjoined:
        force_msg = "✖ **𝐀𝐂𝐂𝐄𝐒𝐒 𝐃𝐄𝐍𝐈𝐄𝐃**\nদয়া করে নিচের চ্যানেলগুলোতে জয়েন করে ভেরিফাই করুন:"
        bot.send_message(message.chat.id, force_msg, reply_markup=force_sub_keyboard(), parse_mode="Markdown")
        return

    handle_home(message, lang, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def verify_join_callback(call):
    user_id = call.from_user.id
    unjoined = get_unjoined_channels(user_id)
    
    if not unjoined:
        user = db_get(f"users/{user_id}")
        lang = user.get("lang", "bn") if user else "bn"
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        handle_home(call.message, lang, user_id)
    else:
        bot.answer_callback_query(call.id, "Checking...", show_alert=False)
        missed_ch = unjoined[0]
        alert_msg = f"✖ আপনি এখনো **{missed_ch[0]}** চ্যানেলে জয়েন করেননি!\nনিচের লিংকে ক্লিক করে জয়েন করুন।"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"➜ JOIN {missed_ch[0]}", url=missed_ch[1]))
        markup.add(InlineKeyboardButton("☑ VERIFY MEMBERSHIP", callback_data="check_join"))
        try: 
            bot.edit_message_text(alert_msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except: 
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_lang_callback(call):
    lang = call.data.split("_")[1]
    db_patch(f"users/{call.from_user.id}", {"lang": lang})
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    handle_home(call.message, lang, call.from_user.id)

def handle_home(message, lang="bn", user_id=None):
    if user_id is None: 
        user_id = message.from_user.id
    user_name = message.chat.first_name if hasattr(message, 'chat') and message.chat.first_name else "USER"
    if lang not in lang_dict: 
        lang = "bn"
    bot.send_message(message.chat.id, lang_dict[lang]["welcome"].format(user_name), reply_markup=main_keyboard(lang), parse_mode="Markdown")

# ==========================================
# 🚀 প্রোফাইল মেনু
# ==========================================
@bot.message_handler(func=lambda message: message.text in [lang_dict["bn"]["menu_profile"], lang_dict["en"]["menu_profile"], "❖ Profile", "❖ 𝐏𝐑𝐎𝐅𝐈𝐋𝐄", "Profile", "প্রোফাইল"])
def show_profile(message):
    user_id = message.from_user.id
    user = db_get(f"users/{user_id}")
    
    if not user:
        uname = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        db_put(f"users/{user_id}", {
            "lang": "bn", 
            "username": uname,
            "balance": 0.0, 
            "total_earned": 0.0,
            "total_submitted": 0,
            "pending_task": 0, 
            "approved_task": 0,
            "rejected_task": 0,
            "referrals": 0, 
            "earned_from_ref": 0.0
        })
        user = db_get(f"users/{user_id}")

    uname = user.get("username", f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name)
    bal = float(user.get("balance", 0.0))
    total_earned = float(user.get("total_earned", 0.0))
    total_sub = int(user.get("total_submitted", 0))
    pending = int(user.get("pending_task", 0))
    approved = int(user.get("approved_task", 0))
    rejected = int(user.get("rejected_task", 0))
    referrals = int(user.get("referrals", 0))

    profile_text = (
        f"❖ **𝐘𝐎𝐔𝐑 𝐀𝐂𝐂𝐎𝐔𝐍𝐓 𝐏𝐑𝐎𝐅𝐈𝐋𝐄** ❖\n\n"
        f"֎ **ইউজারনেম:** {uname}\n"
        f"⚡ **অ্যাকাউন্ট আইডি:** `{user_id}`\n"
        f"⛁ **বর্তমান ব্যালেন্স:** `{bal:.2f} 𝐓𝐊`\n"
        f"⛃ **মোট আয় করেছে:** `{total_earned:.2f} 𝐓𝐊`\n\n"
        f"⫶☰ **কাজের বিস্তারিত রিপোর্ট:**\n"
        f"☰ মোট কাজ আপলোড/জমা: `{total_sub} টি`\n"
        f"⏲ রিভিউ / পেন্ডিং আছে: `{pending} টি`\n"
        f"☑ সাকসেস / অ্যাপ্রুভড কাজ: `{approved} টি`\n"
        f"✖ বাতিল / রিজেক্টেড কাজ: `{rejected} টি`\n\n"
        f"⊛ মোট রেফারেল: `{referrals} জন`\n\n"
        f"➜ উত্তোলন করতে নিচের বাটনে ক্লিক করুন:"
    )

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✦ 𝐖𝐈𝐓𝐇𝐃𝐑𝐀𝐖𝐀𝐋", callback_data="menu_withdraw_inline"))
    bot.send_message(message.chat.id, profile_text, reply_markup=markup, parse_mode="Markdown")

# ==========================================
# 🚀 টাস্ক প্ল্যাটফর্ম ও ক্যাটাগরি মেনু
# ==========================================
@bot.message_handler(func=lambda message: message.text in [lang_dict["bn"]["menu_task"], lang_dict["en"]["menu_task"], "⚡ 𝐓𝐀𝐒𝐊", "Task", "কাজ"])
def show_platforms(message):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("⬩➤ Facebook Task", callback_data="show_plat_FACEBOOK"))
    markup.add(InlineKeyboardButton("⬩➤ Instagram Task", callback_data="show_plat_INSTAGRAM"))
    markup.add(InlineKeyboardButton("⬩➤ Gmail Task", callback_data="show_plat_GMAIL"))
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    
    bot.send_message(message.chat.id, "⫶☰ **কোন প্ল্যাটফর্মের কাজ করতে চান?**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_plat_"))
def show_platform_tasks(call):
    plat_name = call.data.split("show_plat_")[1].upper()
    tasks = db_get("tasks")
    markup = InlineKeyboardMarkup(row_width=1)
    
    found = False
    if tasks and isinstance(tasks, dict):
        for t_id, t_data in tasks.items():
            if t_data.get("platform", "").upper() == plat_name:
                t_name = t_data.get("name", "TASK")
                price = t_data.get("price", 0.0)
                markup.add(InlineKeyboardButton(f"⬩➤ {t_name} ({price:.2f} BDT)", callback_data=f"task_view_{t_id}"))
                found = True
                
    if not found:
        if plat_name == "FACEBOOK":
            markup.add(InlineKeyboardButton("⬩➤ FB 2FA (5.50 BDT)", callback_data="task_view_task_fb_1"))
            markup.add(InlineKeyboardButton("⬩➤ FB Cookies (5.10 BDT)", callback_data="task_view_task_fb_2"))
        elif plat_name == "INSTAGRAM":
            markup.add(InlineKeyboardButton("⬩➤ Instagram 2FA (2.00 BDT)", callback_data="task_view_task_ig_1"))
        elif plat_name == "GMAIL":
            markup.add(InlineKeyboardButton("⬩➤ Gmail Task (14.00 BDT)", callback_data="task_view_task_gm_1"))
            
    markup.add(InlineKeyboardButton("⚙ কাজের ভিডিও ও নিয়ম", callback_data="how_to_work_inline"))
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    
    title = f"⫶☰ **{plat_name} এর কাজসমূহ:**"
    try:
        bot.edit_message_text(title, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(call.message.chat.id, title, reply_markup=markup, parse_mode="Markdown")

# ==========================================
# 🚀 টাস্ক ডিটেইলস (One-Click Copyable Display)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("task_view_") or call.data.startswith("refresh_task_"))
def task_details(call):
    is_refresh = call.data.startswith("refresh_task_")
    task_id = call.data.split("refresh_task_")[1] if is_refresh else call.data.split("task_view_")[1]
    
    task = db_get(f"tasks/{task_id}")
    if not task:
        if "fb_2" in task_id:
            task = {"platform": "FACEBOOK", "name": "FB Cookies", "price": 5.10, "type": "cookies"}
        elif "fb" in task_id: 
            task = {"platform": "FACEBOOK", "name": "FB 2FA", "price": 5.50, "type": "2fa"}
        elif "ig" in task_id: 
            task = {"platform": "INSTAGRAM", "name": "Instagram 2FA", "price": 2.00, "type": "2fa"}
        elif "gm" in task_id: 
            task = {"platform": "GMAIL", "name": "Gmail Task", "price": 14.00, "type": "gmail"}
        else: 
            task = {"platform": "FACEBOOK", "name": "FB 2FA", "price": 5.50, "type": "2fa"}

    platform = task.get("platform", "FACEBOOK").upper()
    name = task.get("name", "TASK")
    price = float(task.get("price", 5.50))
    task_type = task.get("type", "2fa")
    
    accounts = db_get(f"task_accounts/{task_id}")
    if accounts and isinstance(accounts, dict) and len(accounts) > 0:
        acc_key, acc_data = list(accounts.items())[0]
        db_delete(f"task_accounts/{task_id}/{acc_key}")
        parts = acc_data.split("|")
        if len(parts) == 3:
            cred = {"first_name": parts[0], "last_name": parts[1], "password": parts[2], "email": f"{parts[0].lower()}{random.randint(100,999)}@gmail.com", "username": parts[0]}
        elif len(parts) == 2:
            cred = {"first_name": parts[0], "last_name": "", "password": parts[1], "email": f"{parts[0].lower()}@gmail.com", "username": parts[0]}
        else:
            cred = generate_dynamic_credentials(platform)
    else:
        cred = generate_dynamic_credentials(platform)

    user_states[call.from_user.id] = {
        'task_id': task_id,
        'platform': platform,
        'task_type': task_type,
        'cred': cred,
        'price': price,
        'name': name
    }

    markup = InlineKeyboardMarkup(row_width=1)
    tut_link = get_setting("tutorial_link", "https://t.me/RS_FUTURE_JOB_EXPRESS_VIDEO")
    
    if "GMAIL" in platform or task_type == "gmail":
        msg = (
            f"⚡ **𝐆𝐌𝐀𝐈𝐋 𝐂𝐑𝐄𝐀𝐓𝐈𝐎𝐍 𝐓𝐀𝐒𝐊**\n\n"
            f"֎ নির্ধারিত তথ্যগুলো ব্যবহার করে অ্যাকাউন্ট রেজিস্টার করুন এবং {price:.2f} TK আয় করুন:\n\n"
            f"֎ **First Name:** `{cred['first_name']}`\n"
            f"֎ **Last Name:** `{cred['last_name']}`\n"
            f"⌨ **Password:** `{cred['password']}`\n\n"
            f"✦ **টিপস:** তথ্যের উপর ক্লিক করলেই কপি হয়ে যাবে।\n"
            f"✖ অবশ্যই উপরে দেওয়া নির্দিষ্ট নাম ও পাসওয়ার্ড ব্যবহার করবেন।"
        )
        markup.add(InlineKeyboardButton("☑ জমা দিন", callback_data=f"gm_submit_step_{task_id}"))
        markup.add(InlineKeyboardButton("♻ Refresh Data", callback_data=f"refresh_task_{task_id}"))
        markup.add(InlineKeyboardButton("▶ কাজের ভিডিও", url=tut_link))
        markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
        
    elif "INSTAGRAM" in platform:
        msg = (
            f"⚡ **𝐈𝐍𝐒𝐓𝐀𝐆𝐑𝐀𝐌 𝟐𝐅𝐀 𝐓𝐀𝐒𝐊**\n\n"
            f"⬩➤ **টাস্ক:** {name}\n"
            f"⛁ **মূল্য:** {price:.2f} 𝐓𝐊\n\n"
            f"֎ **Username:** `{cred['username']}`\n"
            f"⌨ **Password:** `{cred['password']}`\n\n"
            f"✦ **টিপস:** তথ্যের উপর ক্লিক করলেই স্বয়ংক্রিয়ভাবে কপি হয়ে যাবে।\n"
            f"➜ একাউন্ট খোলার পর নিচে Submit Username বাটনে ক্লিক করুন!"
        )
        markup.add(InlineKeyboardButton("⬩➤ Submit Username", callback_data=f"ig_submit_user_{task_id}"))
        markup.add(InlineKeyboardButton("♻ Refresh Data", callback_data=f"refresh_task_{task_id}"))
        markup.add(InlineKeyboardButton("▶ কাজের ভিডিও", url=tut_link))
        markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))

    else:
        if "cookie" in task_type.lower() or "cookie" in name.lower():
            btn_text = "⬩➤ Submit UID (Cookies)"
            btn_call = f"fb_cookie_{task_id}"
            task_tag = "FB Cookies"
        else:
            btn_text = "⬩➤ Submit UID (2FA)"
            btn_call = f"fb_2fa_{task_id}"
            task_tag = "FB 2FA"

        msg = (
            f"⚡ **𝐅𝐀𝐂𝐄𝐁𝐎𝐎𝐊 𝐀𝐂𝐂𝐎𝐔𝐍𝐓 𝐓𝐀𝐒𝐊**\n\n"
            f"֎ আপনার নতুন কাজ প্রস্তুত!\n"
            f"⬩➤ **টাস্ক:** {task_tag}\n"
            f"⛁ **মূল্য:** {price:.2f} 𝐓𝐊\n\n"
            f"֎ **First Name:** `{cred['first_name']}`\n"
            f"֎ **Last Name:** `{cred['last_name']}`\n"
            f"⌨ **Password:** `{cred['password']}`\n\n"
            f"✦ **টিপস:** লেখার উপর এক ক্লিকেই কপি হয়ে যাবে।\n"
            f"➜ অ্যাকাউন্ট খোলার পর নিচে **{btn_text}** বাটনে ক্লিক করুন!"
        )
        markup.add(InlineKeyboardButton(btn_text, callback_data=btn_call))
        markup.add(InlineKeyboardButton("♻ Refresh Data", callback_data=f"refresh_task_{task_id}"))
        markup.add(InlineKeyboardButton("▶ কাজের ভিডিও", url=tut_link))
        markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))

    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

# ==========================================
# 🚀 GMAIL SUBMISSION FLOW
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("gm_submit_step_"))
def gm_submit_step(call):
    if call.from_user.id not in user_states:
        user_states[call.from_user.id] = {}
    user_states[call.from_user.id]['action'] = 'wait_gmail_email'
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    bot.send_message(call.message.chat.id, "✉ **তৈরি করা জিমেইল এড্রেসটি এখানে সেন্ড করুন:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'wait_gmail_email'))
def gm_final_save(message):
    email_text = message.text.strip()
    state = user_states.get(message.from_user.id, {})
    task_id = state.get('task_id', 'task_gm_1')
    cred = state.get('cred', {})
    price = state.get('price', 14.0)
    name = state.get('name', 'Gmail Task')
    
    submission_data = {
        "user_id": message.from_user.id,
        "task_id": task_id,
        "task_name": name,
        "platform": "GMAIL",
        "task_type": "gmail",
        "price": price,
        "first_name": cred.get('first_name', ''),
        "last_name": cred.get('last_name', ''),
        "email": email_text,
        "password": cred.get('password', 'N/A'),
        "status": "pending",
        "timestamp": int(time.time())
    }
    db_post("task_submissions", submission_data)
    
    user = db_get(f"users/{message.from_user.id}")
    pending = user.get("pending_task", 0) + 1 if user else 1
    total_sub = user.get("total_submitted", 0) + 1 if user else 1
    approved = user.get("approved_task", 0) if user else 0
    rejected = user.get("rejected_task", 0) if user else 0
    
    db_patch(f"users/{message.from_user.id}", {
        "pending_task": pending,
        "total_submitted": total_sub
    })
    
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
        
    success_msg = (
        f"☑ **𝐓𝐀𝐒𝐊 𝐒𝐔𝐁𝐌𝐈𝐓𝐓𝐄𝐃 𝐒𝐔𝐂𝐂𝐄𝐒𝐒𝐅𝐔𝐋𝐋𝐘!**\n\n"
        f"⫶☰ **আপনার কাজের রিপোর্ট:**\n"
        f"☰ মোট কাজ জমা: `{total_sub} টি`\n"
        f"⏲ পেন্ডিং কাজ: `{pending} টি`\n"
        f"☑ অ্যাপ্রুভড কাজ: `{approved} টি`\n"
        f"✖ বাতিল কাজ: `{rejected} টি`\n\n"
        f"➜ নতুন কাজ শুরু করতে নিচের বাটনে ক্লিক করুন:"
    )
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("⬩➤ আরো Gmail কাজ করুন", callback_data="show_plat_GMAIL"))
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    bot.send_message(message.chat.id, success_msg, reply_markup=markup, parse_mode="Markdown")

# ==========================================
# 🚀 2FA & COOKIES SUBMISSION HANDLERS
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("fb_2fa_"))
def fb_2fa_uid_step(call):
    task_id = call.data.split("fb_2fa_")[1]
    if call.from_user.id not in user_states:
        user_states[call.from_user.id] = {}
        
    user_states[call.from_user.id]['action'] = 'wait_2fa_uid'
    user_states[call.from_user.id]['task_id'] = task_id
    user_states[call.from_user.id]['task_type'] = '2fa'
    user_states[call.from_user.id]['platform'] = 'FACEBOOK'
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    bot.send_message(call.message.chat.id, "☑ **Send me the Facebook UID (User ID):**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'wait_2fa_uid'))
def fb_2fa_key_step(message):
    uid_data = message.text.strip()
    user_states[message.from_user.id]['uid_data'] = uid_data
    user_states[message.from_user.id]['action'] = 'wait_2fa_key'
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    bot.send_message(message.chat.id, "☑ **UID Received. Now send me the 2FA Key:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'wait_2fa_key'))
def process_2fa_key(message):
    raw_key = message.text.strip()
    clean_key = sanitize_base32(raw_key)
    
    if not is_valid_base32(clean_key):
        err_msg = "✖ আপনার 2FA Key-টি সঠিক নয়! এটি ১৬ অথবা ৩২ অক্ষরের সঠিক Base32 কোড হতে হবে।"
        bot.send_message(message.chat.id, err_msg)
        return
        
    code, rem = fetch_totp_code(clean_key)
    if not code:
        err_msg = "✖ 2FA কোড জেনারেট করা সম্ভব হয়নি। কি চেক করে আবার পাঠান।"
        bot.send_message(message.chat.id, err_msg)
        return

    user_states[message.from_user.id]['2fa_key'] = clean_key
    user_states[message.from_user.id]['2fa_code'] = code
    user_states[message.from_user.id]['action'] = 'ready_submit_2fa'
    
    msg = (
        f"☑ **2FA Key সফলভাবে গ্রহণ করা হয়েছে!**\n\n"
        f"⚡ **2FA Code:** `{code}`\n\n"
        f"➜ কোডটি একাউন্টে বসিয়ে নিচে থাকা ওটিপি বাটনে ট্যাপ করে সাবমিট সম্পন্ন করুন।"
    )
          
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton(f"ꪜ OTP: {code} (ট্যাপ করে সাবমিট করুন)", callback_data="final_submit_2fa"))
    markup.add(InlineKeyboardButton("♻ Refresh Code", callback_data=f"refresh_2fa_{clean_key}"))
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    
    bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("refresh_2fa_"))
def refresh_2fa_code_callback(call):
    clean_key = call.data.split("refresh_2fa_")[1]
    code, rem = fetch_totp_code(clean_key)
    
    if not code:
        bot.answer_callback_query(call.id, "Unable to generate code!", show_alert=True)
        return
        
    if call.from_user.id in user_states:
        user_states[call.from_user.id]['2fa_code'] = code
        
    msg = (
        f"☑ **2FA Key সফলভাবে গ্রহণ করা হয়েছে!**\n\n"
        f"⚡ **2FA Code:** `{code}`\n\n"
        f"➜ কোডটি একাউন্টে বসিয়ে নিচে থাকা ওটিপি বাটনে ট্যাপ করে সাবমিট সম্পন্ন করুন।"
    )
          
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton(f"ꪜ OTP: {code} (ট্যাপ করে সাবমিট করুন)", callback_data="final_submit_2fa"))
    markup.add(InlineKeyboardButton("♻ Refresh Code", callback_data=f"refresh_2fa_{clean_key}"))
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    
    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id, f"Code: {code}", show_alert=False)
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "final_submit_2fa")
def final_task_submit_2fa(call):
    data = user_states.get(call.from_user.id)
    if not data or data.get('action') != 'ready_submit_2fa': 
        bot.answer_callback_query(call.id, "Session expired, please restart task", show_alert=True)
        return
    
    task_id = data.get('task_id', 'task_fb_1')
    task_name = data.get('name', 'FB 2FA')
    price = float(data.get('price', 5.50))
    uid_data = data.get('uid_data', 'N/A')
    two_fa_key = data.get('2fa_key', '')
    two_fa_code = data.get('2fa_code', '')
    cred = data.get('cred', {})
    plat = data.get('platform', 'FACEBOOK')
    
    submission_data = {
        "user_id": call.from_user.id,
        "task_id": task_id,
        "task_name": task_name,
        "platform": plat,
        "task_type": "2fa",
        "price": price,
        "uid": uid_data,
        "name": f"{cred.get('first_name', '')} {cred.get('last_name', '')}".strip(),
        "password": cred.get('password', ''),
        "two_fa_key": two_fa_key,
        "two_fa_code": two_fa_code,
        "status": "pending",
        "timestamp": int(time.time())
    }
    db_post("task_submissions", submission_data)
    
    user = db_get(f"users/{call.from_user.id}")
    pending = user.get("pending_task", 0) + 1 if user else 1
    total_sub = user.get("total_submitted", 0) + 1 if user else 1
    approved = user.get("approved_task", 0) if user else 0
    rejected = user.get("rejected_task", 0) if user else 0
    
    db_patch(f"users/{call.from_user.id}", {
        "pending_task": pending,
        "total_submitted": total_sub
    })
    
    if call.from_user.id in user_states:
        del user_states[call.from_user.id]
    
    success_msg = (
        f"☑ **𝐓𝐀𝐒𝐊 𝐒𝐔𝐁𝐌𝐈𝐓𝐓𝐄𝐃 𝐒𝐔𝐂𝐂𝐄𝐒𝐒𝐅𝐔𝐋𝐋𝐘!**\n\n"
        f"⫶☰ **আপনার কাজের রিপোর্ট:**\n"
        f"☰ মোট কাজ জমা: `{total_sub} টি`\n"
        f"⏲ পেন্ডিং কাজ: `{pending} টি`\n"
        f"☑ অ্যাপ্রুভড কাজ: `{approved} টি`\n"
        f"✖ বাতিল কাজ: `{rejected} টি`\n\n"
        f"➜ নতুন কাজ শুরু করতে নিচের বাটনে ক্লিক করুন:"
    )
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("⬩➤ FB 2FA (5.50 BDT)", callback_data="task_view_task_fb_1"))
    markup.add(InlineKeyboardButton("⬩➤ FB Cookies (5.10 BDT)", callback_data="task_view_task_fb_2"))
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    
    try:
        bot.edit_message_text(success_msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(call.message.chat.id, success_msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("fb_cookie_"))
def fb_cookie_uid_step(call):
    task_id = call.data.split("fb_cookie_")[1]
    if call.from_user.id not in user_states:
        user_states[call.from_user.id] = {}
        
    user_states[call.from_user.id]['action'] = 'wait_cookie_uid'
    user_states[call.from_user.id]['task_id'] = task_id
    user_states[call.from_user.id]['task_type'] = 'cookies'
    user_states[call.from_user.id]['platform'] = 'FACEBOOK'
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    bot.send_message(call.message.chat.id, "☑ **Send me the UID (User ID) for Facebook:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'wait_cookie_uid'))
def fb_cookie_data_step(message):
    uid_data = message.text.strip()
    user_states[message.from_user.id]['uid_data'] = uid_data
    user_states[message.from_user.id]['action'] = 'wait_cookie_data'
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    bot.send_message(message.chat.id, "☑ **UID Received. Now send me the Facebook Cookies data:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'wait_cookie_data'))
def fb_cookie_confirm_step(message):
    cookie_str = message.text.strip()
    user_states[message.from_user.id]['cookie_data'] = cookie_str
    user_states[message.from_user.id]['action'] = 'ready_submit_cookie'
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("ꪜ Complete & Submit Cookies", callback_data="final_submit_cookie"))
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    
    bot.send_message(message.chat.id, "☑ **Cookies Data সফলভাবে গ্রহণ করা হয়েছে। কাজ জমা দিতে নিচের বাটনে ক্লিক করুন:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "final_submit_cookie")
def final_task_submit_cookie(call):
    data = user_states.get(call.from_user.id)
    if not data or data.get('action') != 'ready_submit_cookie':
        bot.answer_callback_query(call.id, "Session expired, please restart task", show_alert=True)
        return
        
    task_id = data.get('task_id', 'task_fb_2')
    task_name = data.get('name', 'FB Cookies')
    price = float(data.get('price', 5.10))
    uid_data = data.get('uid_data', 'N/A')
    cookie_str = data.get('cookie_data', '')
    cred = data.get('cred', {})
    
    submission_data = {
        "user_id": call.from_user.id,
        "task_id": task_id,
        "task_name": task_name,
        "platform": "FACEBOOK",
        "task_type": "cookies",
        "price": price,
        "uid": uid_data,
        "name": f"{cred.get('first_name', '')} {cred.get('last_name', '')}".strip(),
        "password": cred.get('password', ''),
        "cookies": cookie_str,
        "status": "pending",
        "timestamp": int(time.time())
    }
    db_post("task_submissions", submission_data)
    
    user = db_get(f"users/{call.from_user.id}")
    pending = user.get("pending_task", 0) + 1 if user else 1
    total_sub = user.get("total_submitted", 0) + 1 if user else 1
    approved = user.get("approved_task", 0) if user else 0
    rejected = user.get("rejected_task", 0) if user else 0
    
    db_patch(f"users/{call.from_user.id}", {
        "pending_task": pending,
        "total_submitted": total_sub
    })
    
    if call.from_user.id in user_states:
        del user_states[call.from_user.id]
        
    success_msg = (
        f"☑ **𝐓𝐀𝐒𝐊 𝐒𝐔𝐁𝐌𝐈𝐓𝐓𝐄𝐃 𝐒𝐔𝐂𝐂𝐄𝐒𝐒𝐅𝐔𝐋𝐋𝐘!**\n\n"
        f"⫶☰ **আপনার কাজের রিপোর্ট:**\n"
        f"☰ মোট কাজ জমা: `{total_sub} টি`\n"
        f"⏲ পেন্ডিং কাজ: `{pending} টি`\n"
        f"☑ অ্যাপ্রুভড কাজ: `{approved} টি`\n"
        f"✖ বাতিল কাজ: `{rejected} টি`\n\n"
        f"➜ নতুন কাজ শুরু করতে নিচের বাটনে ক্লিক করুন:"
    )
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("⬩➤ FB 2FA (5.50 BDT)", callback_data="task_view_task_fb_1"))
    markup.add(InlineKeyboardButton("⬩➤ FB Cookies (5.10 BDT)", callback_data="task_view_task_fb_2"))
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    
    try:
        bot.edit_message_text(success_msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(call.message.chat.id, success_msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ig_submit_user_"))
def ig_submit_user_step(call):
    task_id = call.data.split("ig_submit_user_")[1]
    if call.from_user.id not in user_states:
        user_states[call.from_user.id] = {}
        
    user_states[call.from_user.id]['action'] = 'wait_ig_user'
    user_states[call.from_user.id]['task_id'] = task_id
    user_states[call.from_user.id]['task_type'] = '2fa'
    user_states[call.from_user.id]['platform'] = 'INSTAGRAM'
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    bot.send_message(call.message.chat.id, "☑ **Send me your Instagram Username:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'wait_ig_user'))
def ig_received_user_step(message):
    uid_data = message.text.strip()
    user_states[message.from_user.id]['uid_data'] = uid_data
    user_states[message.from_user.id]['action'] = 'wait_2fa_key'
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✖ Cancel", callback_data="cancel"))
    bot.send_message(message.chat.id, "☑ **Username Received. Now send me the 2FA Key:**", reply_markup=markup, parse_mode="Markdown")

# ==========================================
# 🚀 WITHDRAWAL SYSTEM
# ==========================================
@bot.message_handler(func=lambda message: message.text in [lang_dict["bn"]["menu_withdraw"], lang_dict["en"]["menu_withdraw"], "⛃ 𝐖𝐈𝐓𝐇𝐃𝐑𝐀𝐖", "উত্তোলন", "Withdraw"])
def withdraw_request(message):
    send_withdraw_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "menu_withdraw_inline")
def withdraw_inline(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    send_withdraw_menu(call.message.chat.id)

def send_withdraw_menu(chat_id):
    min_w = float(get_setting("min_withdraw", MIN_WITHDRAW))
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("✦ BKASH", callback_data="wd_req_bKash"))
    markup.add(InlineKeyboardButton("✦ NAGAD", callback_data="wd_req_Nagad"))
    markup.add(InlineKeyboardButton("✦ ROCKET", callback_data="wd_req_Rocket"))
    markup.add(InlineKeyboardButton("✦ USDT (BEP-20)", callback_data="wd_req_USDT"))
    markup.add(InlineKeyboardButton("◄ BACK", callback_data="cancel"))
    bot.send_message(chat_id, f"⫶☰ **SELECT WITHDRAWAL METHOD:**\n(মিনিমাম উইথড্র {min_w:.2f} TK)", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("wd_req_"))
def ask_wd_number(call):
    method = call.data.split("wd_req_")[1]
    user_states[call.from_user.id] = {'action': 'withdraw_number', 'method': method}
    bot.send_message(call.message.chat.id, f"➜ **SEND YOUR {method.upper()} ACCOUNT/ADDRESS:**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'withdraw_number'))
def ask_wd_amount(message):
    min_w = float(get_setting("min_withdraw", MIN_WITHDRAW))
    user_states[message.from_user.id]['number'] = message.text.strip()
    user_states[message.from_user.id]['action'] = 'withdraw_amount'
    bot.send_message(message.chat.id, f"✦ **ENTER WITHDRAWAL AMOUNT:**\n(মিনিমাম {min_w:.2f} TK)", parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'withdraw_amount'))
def finish_wd(message):
    try:
        amount = float(message.text.strip())
        user_id = message.from_user.id
        min_w = float(get_setting("min_withdraw", MIN_WITHDRAW))
        
        if amount < min_w:
            bot.send_message(message.chat.id, f"✖ মিনিমাম উইথড্র {min_w:.2f} TK। সঠিক এমাউন্ট দিন।")
            if user_id in user_states:
                del user_states[user_id]
            return
            
        user_data = db_get(f"users/{user_id}")
        current_bal = float(user_data.get("balance", 0.0)) if user_data else 0.0
        
        if amount > current_bal:
            bot.send_message(message.chat.id, "✖ আপনার একাউন্টে পর্যাপ্ত ব্যালেন্স নেই। রিকোয়েস্ট বাতিল করা হলো।")
            if user_id in user_states:
                del user_states[user_id]
            return
            
        data = user_states[user_id]
        wd_data = {
            "user_id": user_id,
            "method": data['method'].upper(),
            "number": data['number'],
            "amount": amount,
            "status": "pending",
            "timestamp": int(time.time())
        }
        db_post("withdrawals", wd_data)
        
        new_balance = current_bal - amount
        db_patch(f"users/{user_id}", {"balance": new_balance})
        
        if user_id in user_states:
            del user_states[user_id]
        bot.send_message(message.chat.id, "☑ **WITHDRAWAL REQUEST SUBMITTED!**\nঅ্যাডমিন আপনার রিকোয়েস্ট ভেরিফাই করে পেমেন্ট সম্পন্ন করবে।", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "✖ INVALID AMOUNT. TRY AGAIN.")

# ==========================================
# 🚀 SUPPORT, REFERRAL, TUTORIAL & LEADERBOARD
# ==========================================
@bot.message_handler(func=lambda message: message.text in [lang_dict["bn"]["menu_support"], lang_dict["en"]["menu_support"], "☏ 𝐒𝐔𝐏𝐏𝐎𝐑𝐓", "সাপোর্ট"])
def support_menu(message):
    admin_contact = get_setting("admin_contact", "https://t.me/Rubel_Owner")
    channel_link = get_setting("support_channel", "https://t.me/RS_FUTURE_JOB_EXPRESS_OTP")
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("☏ CONTACT ADMIN", url=admin_contact))
    markup.add(InlineKeyboardButton("⚲ OFFICIAL CHANNEL", url=channel_link))
    bot.send_message(message.chat.id, "⫶☰ **FOR HELP & SUPPORT, CLICK BELOW:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in [lang_dict["bn"]["menu_refer"], lang_dict["en"]["menu_refer"], "⊛ 𝐑𝐄𝐅𝐄𝐑𝐑𝐀𝐋", "রেফারেল"])
def my_referral(message):
    user_id = message.from_user.id
    user = db_get(f"users/{user_id}")
    ref_count = user.get("referrals", 0) if user else 0
    ref_earned = user.get("earned_from_ref", 0.0) if user else 0.0
    bot_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    
    msg = (
        f"✦ **𝐑𝐄𝐅𝐄𝐑 & 𝐄𝐀𝐑𝐍 𝐏𝐑𝐎𝐆𝐑𝐀𝐌** ✦\n\n"
        f"বন্ধুদের ইনভাইট করুন এবং তাদের কাজের ১০% কমিশন আজীবন উপভোগ করুন!\n\n"
        f"⫶☰ **YOUR STATISTICS:**\n"
        f"֎ Total Referrals: `{ref_count}` জন\n"
        f"⛃ Total Earned: `{ref_earned:.2f} 𝐓𝐊`\n\n"
        f"➜ নিচের লিংকে ক্লিক করে শেয়ার করুন:"
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    share_url = f"https://t.me/share/url?url={bot_link}&text=Join%20this%20awesome%20bot!"
    markup.add(
        InlineKeyboardButton("⊛ COPY LINK", callback_data="copy_ref_link"),
        InlineKeyboardButton("➜ SHARE NOW", url=share_url)
    )
    bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "copy_ref_link")
def copy_ref(call):
    bot_link = f"https://t.me/{BOT_USERNAME}?start={call.from_user.id}"
    bot.send_message(call.message.chat.id, f"✦ **YOUR REFERRAL LINK:**\n`{bot_link}`", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in [lang_dict["bn"]["menu_how"], lang_dict["en"]["menu_how"], "⚙ 𝐇𝐎𝐖 𝐓𝐎 𝐖𝐎𝐑𝐊", "কাজের নিয়ম"])
def how_to_work(message):
    send_how_to_work(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "how_to_work_inline")
def how_to_work_callback(call):
    send_how_to_work(call.message.chat.id)

def send_how_to_work(chat_id):
    tut_link = get_setting("tutorial_link", "https://t.me/RS_FUTURE_JOB_EXPRESS_VIDEO")
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("▶ WATCH VIDEO TUTORIAL", url=tut_link))
    bot.send_message(chat_id, f"⚙ **TUTORIAL CHANNEL:**\n\nকাজের সকল ভিডিও দেখতে নিচের বাটনে ক্লিক করুন:\n{tut_link}", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in [lang_dict["bn"]["menu_leader"], lang_dict["en"]["menu_leader"], "≡ 𝐋𝐄𝐀𝐃𝐄𝐑𝐁𝐎𝐀𝐑𝐃", "লিডারবোর্ড"])
def show_leaderboard_menu(message):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("⚡ TASK LEADERBOARD", callback_data="lb_task"))
    markup.add(InlineKeyboardButton("⊛ REFERRAL LEADERBOARD", callback_data="lb_ref"))
    bot.send_message(message.chat.id, "≡ **SELECT LEADERBOARD CATEGORY:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data in ["lb_task", "lb_ref"])
def process_leaderboard(call):
    users = db_get("users")
    if not users or not isinstance(users, dict):
        return bot.answer_callback_query(call.id, "NO DATA AVAILABLE!", show_alert=True)
    
    user_list = []
    for uid, udata in users.items():
        if isinstance(udata, dict):
            user_list.append({
                "uid": str(uid), 
                "tasks": udata.get("approved_task", 0), 
                "refs": udata.get("referrals", 0)
            })
        
    is_task = (call.data == "lb_task")
    user_list.sort(key=lambda x: x["tasks"] if is_task else x["refs"], reverse=True)
    top_5 = user_list[:5]
    
    title = "❖ **LEADERBOARD - TOP 5 TASKS**" if is_task else "❖ **LEADERBOARD - TOP 5 REFERRALS**"
    msg = f"{title}\n\n"
    medals = ["1.", "2.", "3.", "4.", "5."]
    
    for idx, u in enumerate(top_5):
        if (is_task and u["tasks"] == 0) or (not is_task and u["refs"] == 0): 
            continue
        val = f"{u['tasks']} Tasks" if is_task else f"{u['refs']} Referrals"
        msg += f"{medals[idx]} USER `{u['uid'][:6]}...` ➜ {val}\n"
        
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("◄ BACK", callback_data="cancel"))
    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in [lang_dict["bn"]["menu_lang"], lang_dict["en"]["menu_lang"], "↻ 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄", "ভাষা পরিবর্তন"])
def change_lang_menu(message):
    ask_language(message.chat.id)

def message_handler_router(message, action_type):
    return message.from_user.id in user_states and user_states[message.from_user.id].get('action') == action_type

@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def cancel_any(call):
    if call.from_user.id in user_states:
        del user_states[call.from_user.id]
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

# ==========================================
# 𖤓 𝐌𝐄𝐆𝐀 𝐀𝐃𝐌𝐈𝐍 𝐏𝐀𝐍𝐄𝐋
# ==========================================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return bot.send_message(message.chat.id, "✖ ACCESS DENIED!")
    
    text = "❖ **𝐌𝐄𝐆𝐀 𝐀𝐃𝐌𝐈𝐍 𝐃𝐀𝐒𝐇𝐁𝐎𝐀𝐑𝐃** ❖\n\nম্যানেজ করার জন্য যেকোনো অপশন সিলেক্ট করুন:"
    markup = InlineKeyboardMarkup(row_width=2)
    
    # 🔴 ইউজার এপ্লাই টাস্ক বাটন
    markup.add(
        InlineKeyboardButton("🔴 ইউজার এপ্লাই টাস্ক", callback_data="admin_applied_tasks")
    )
    markup.add(
        InlineKeyboardButton("⚙ MANAGE TASKS", callback_data="admin_tasks"),
        InlineKeyboardButton("⫶☰ UPLOAD POOL", callback_data="admin_add_accounts")
    )
    markup.add(
        InlineKeyboardButton("✎ REVIEW TASKS", callback_data="review_users_list"),
        InlineKeyboardButton("⛃ WITHDRAWALS", callback_data="admin_wd")
    )
    markup.add(
        InlineKeyboardButton("✎ EDIT POOL", callback_data="admin_edit_accs"),
        InlineKeyboardButton("📣 BROADCAST", callback_data="admin_broadcast")
    )
    markup.add(
        InlineKeyboardButton("⚙ SETTINGS", callback_data="admin_settings"),
        InlineKeyboardButton("֎ USER MGR", callback_data="admin_user_mgr")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_home")
def back_to_admin_home(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    admin_panel(call.message)

# ==========================================
# 🔴 নতুন: ইউজার এপ্লাই টাস্ক ভিউ ও ডাইনামিক সাব-বাটন
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "admin_applied_tasks")
def admin_applied_tasks_users(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    subs = db_get("task_submissions")
    
    if not subs or not isinstance(subs, dict):
        return bot.answer_callback_query(call.id, "এখনো পর্যন্ত কোনো টাস্ক জমা পড়েনি!", show_alert=True)
    
    users_map = {}
    for s_id, s in subs.items():
        if isinstance(s, dict):
            uid = str(s.get("user_id"))
            if uid not in users_map:
                users_map[uid] = {"total": 0, "pending": 0}
            users_map[uid]["total"] += 1
            if s.get("status") == "pending":
                users_map[uid]["pending"] += 1
                
    markup = InlineKeyboardMarkup(row_width=1)
    for uid, counts in users_map.items():
        u_info = db_get(f"users/{uid}")
        uname = u_info.get("username", uid) if u_info else uid
        p_tag = f" (🔴 {counts['pending']} Pending)" if counts['pending'] > 0 else " (✓ Done)"
        markup.add(InlineKeyboardButton(f"֎ {uname} | ID: {uid}{p_tag}", callback_data=f"app_user_{uid}"))
        
    markup.add(InlineKeyboardButton("◄ BACK TO DASHBOARD", callback_data="admin_home"))
    
    msg = "🔴 **ইউজার এপ্লাই টাস্ক তালিকা:**\nযে ইউজারের কাজ চেক করতে চান তার নামের উপর ক্লিক করুন:"
    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

# ১. ইউজারে ক্লিক করলে তিনটি প্ল্যাটফর্ম বাটন আসবে
@bot.callback_query_handler(func=lambda call: call.data.startswith("app_user_"))
def admin_applied_platforms(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    target_uid = call.data.split("app_user_")[1]
    u_info = db_get(f"users/{target_uid}")
    uname = u_info.get("username", target_uid) if u_info else target_uid
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("✉️ Gmail Tasks", callback_data=f"app_cat_{target_uid}_GMAIL"))
    markup.add(InlineKeyboardButton("🇫 Facebook Tasks", callback_data=f"app_subcat_fb_{target_uid}"))
    markup.add(InlineKeyboardButton("📷 Instagram Tasks", callback_data=f"app_cat_{target_uid}_INSTAGRAM"))
    markup.add(InlineKeyboardButton("◄ BACK TO USER LIST", callback_data="admin_applied_tasks"))
    
    msg = f"֎ **ইউজার:** `{uname}`\n⚡ **ইউজার আইডি:** `{target_uid}`\n\nকোন প্ল্যাটফর্মের কাজ দেখতে চান?"
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

# ২. ফেসবুকে ক্লিক করলে ২টি সাব-বাটন আসবে (FB 2FA এবং FB Cookies)
@bot.callback_query_handler(func=lambda call: call.data.startswith("app_subcat_fb_"))
def admin_fb_subcategories(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    target_uid = call.data.split("app_subcat_fb_")[1]
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔑 FB 2FA", callback_data=f"app_cat_{target_uid}_FB_2FA"))
    markup.add(InlineKeyboardButton("🍪 FB Cookies", callback_data=f"app_cat_{target_uid}_FB_COOKIES"))
    markup.add(InlineKeyboardButton("◄ BACK", callback_data=f"app_user_{target_uid}"))
    
    msg = f"🇫 **Facebook Sub-Categories:**\nকোন ক্যাটাগরির কাজ দেখতে চান নির্বাচন করুন:"
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

# ৩. যেকোনো ক্যাটাগরিতে ক্লিক করলে সব আইডি এক-ক্লিকে কপিযোগ্য সুন্দর ফরম্যাটে দেখাবে
@bot.callback_query_handler(func=lambda call: call.data.startswith("app_cat_"))
def view_category_submissions(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    parts = call.data.split("_")
    target_uid = parts[2]
    cat = "_".join(parts[3:])
    
    subs = db_get("task_submissions")
    filtered = []
    
    if subs and isinstance(subs, dict):
        for s_id, s in subs.items():
            if isinstance(s, dict) and str(s.get("user_id")) == str(target_uid):
                plat = s.get("platform", "").upper()
                ttype = s.get("task_type", "").lower()
                
                match = False
                if cat == "GMAIL" and plat == "GMAIL":
                    match = True
                elif cat == "INSTAGRAM" and plat == "INSTAGRAM":
                    match = True
                elif cat == "FB_2FA" and plat == "FACEBOOK" and "cookie" not in ttype:
                    match = True
                elif cat == "FB_COOKIES" and plat == "FACEBOOK" and "cookie" in ttype:
                    match = True
                    
                if match:
                    s["sub_id"] = s_id
                    filtered.append(s)
                    
    if not filtered:
        return bot.answer_callback_query(call.id, "এই ক্যাটাগরিতে কোনো কাজের ডাটা নেই!", show_alert=True)
        
    pending_items = [s for s in filtered if s.get("status") == "pending"]
    pending_count = len(pending_items)
    unit_price = float(filtered[0].get("price", 5.0)) if filtered else 5.0
    total_price = sum(float(s.get("price", unit_price)) for s in pending_items)
    
    display_title = {
        "GMAIL": "✉️ GMAIL TASKS",
        "INSTAGRAM": "📷 INSTAGRAM TASKS",
        "FB_2FA": "🔑 FACEBOOK 2FA TASKS",
        "FB_COOKIES": "🍪 FACEBOOK COOKIES TASKS"
    }.get(cat, cat)
    
    msg = f"❖ **{display_title}** ❖\n"
    msg += f"֎ **ইউজার আইডি:** `{target_uid}`\n"
    msg += f"☰ **মোট জমা:** `{len(filtered)} টি` | **পেন্ডিং:** `{pending_count} টি`\n"
    msg += f"⛁ **পেন্ডিং মূল্য:** `{total_price:.2f} TK` (প্রতি কাজ `{unit_price:.2f} TK`)\n"
    msg += "━━━━━━━━━━━━━━━━━━━\n\n"
    
    for idx, item in enumerate(filtered, 1):
        status_tag = "🔴 [PENDING]" if item.get("status") == "pending" else "🟢 [APPROVED]" if "approved" in item.get("status") else "✖️ [REJECTED]"
        msg += f"📌 **টাস্ক #{idx}** - {status_tag}\n"
        
        if cat == "FB_COOKIES":
            uid = item.get("uid", "N/A")
            pwd = item.get("password", "N/A")
            cookie_data = item.get("cookies", "N/A")
            msg += f"🆔 **UID:** `{uid}`\n"
            msg += f"🔑 **Password:** `{pwd}`\n"
            msg += f"🍪 **Cookies (Click to Copy):**\n```\n{cookie_data}\n```\n"
            
        elif cat == "FB_2FA":
            uid = item.get("uid", "N/A")
            pwd = item.get("password", "N/A")
            two_fa = item.get("two_fa_key", "N/A")
            code = item.get("two_fa_code", "N/A")
            msg += f"🆔 **UID:** `{uid}`\n"
            msg += f"🔑 **Password:** `{pwd}`\n"
            msg += f"🔐 **2FA Key:** `{two_fa}`\n"
            msg += f"⚡ **OTP Code:** `{code}`\n\n"
            
        elif cat == "GMAIL":
            fname = item.get("first_name", "")
            lname = item.get("last_name", "")
            email = item.get("email", item.get("details", ""))
            pwd = item.get("password", "N/A")
            msg += f"👤 **Name:** `{fname} {lname}`\n"
            msg += f"✉️ **Email:** `{email}`\n"
            msg += f"🔑 **Password:** `{pwd}`\n\n"
            
        elif cat == "INSTAGRAM":
            uname = item.get("uid", "N/A")
            pwd = item.get("password", "N/A")
            two_fa = item.get("two_fa_key", "N/A")
            code = item.get("two_fa_code", "N/A")
            msg += f"👤 **Username:** `{uname}`\n"
            msg += f"🔑 **Password:** `{pwd}`\n"
            msg += f"🔐 **2FA Key:** `{two_fa}`\n"
            msg += f"⚡ **OTP Code:** `{code}`\n\n"
            
        msg += "───────────────────\n"

    markup = InlineKeyboardMarkup(row_width=1)
    if pending_count > 0:
        markup.add(InlineKeyboardButton(f"✔️ সম্পূর্ণ অ্যাপ্রুভ ({total_price:.2f} TK)", callback_data=f"app_act_full_{target_uid}_{cat}_{total_price}"))
        markup.add(InlineKeyboardButton(f"✏️ ভুল আইডি বাদ দিয়ে পে করুন", callback_data=f"app_act_deduct_{target_uid}_{cat}_{pending_count}_{unit_price}"))
        markup.add(InlineKeyboardButton("✖️ সম্পূর্ণ রিজেক্ট (Reject All)", callback_data=f"app_act_rej_{target_uid}_{cat}"))
        
    back_target = f"app_subcat_fb_{target_uid}" if "FB_" in cat else f"app_user_{target_uid}"
    markup.add(InlineKeyboardButton("◄ BACK", callback_data=back_target))
    
    if len(msg) > 4000:
        for x in range(0, len(msg), 3800):
            bot.send_message(call.message.chat.id, msg[x:x+3800], parse_mode="Markdown")
        bot.send_message(call.message.chat.id, "👇 অ্যাকশন বাটন:", reply_markup=markup)
    else:
        try:
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except:
            bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

# ৪. সম্পূর্ণ অ্যাপ্রুভ অ্যাকশন
@bot.callback_query_handler(func=lambda call: call.data.startswith("app_act_full_"))
def process_app_full_payout(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    parts = call.data.split("_")
    target_uid = parts[3]
    cat = "_".join(parts[4:-1])
    amount = float(parts[-1])
    
    subs = db_get("task_submissions")
    approved_count = 0
    if subs and isinstance(subs, dict):
        for s_id, s in subs.items():
            if isinstance(s, dict) and str(s.get("user_id")) == str(target_uid) and s.get("status") == "pending":
                plat = s.get("platform", "").upper()
                ttype = s.get("task_type", "").lower()
                
                match = False
                if cat == "GMAIL" and plat == "GMAIL": match = True
                elif cat == "INSTAGRAM" and plat == "INSTAGRAM": match = True
                elif cat == "FB_2FA" and plat == "FACEBOOK" and "cookie" not in ttype: match = True
                elif cat == "FB_COOKIES" and plat == "FACEBOOK" and "cookie" in ttype: match = True
                
                if match:
                    db_patch(f"task_submissions/{s_id}", {"status": "approved"})
                    approved_count += 1
                    
    user = db_get(f"users/{target_uid}")
    if user and isinstance(user, dict):
        new_bal = float(user.get("balance", 0.0)) + amount
        new_earned = float(user.get("total_earned", 0.0)) + amount
        appr = int(user.get("approved_task", 0)) + approved_count
        pend = max(0, int(user.get("pending_task", 0)) - approved_count)
        
        db_patch(f"users/{target_uid}", {
            "balance": new_bal, 
            "total_earned": new_earned,
            "approved_task": appr,
            "pending_task": pend
        })
        
        ref_id = user.get("referrer")
        if ref_id and str(ref_id).isdigit():
            ref_user = db_get(f"users/{ref_id}")
            if ref_user:
                com = amount * 0.10
                db_patch(f"users/{ref_id}", {
                    "balance": float(ref_user.get("balance", 0.0)) + com,
                    "earned_from_ref": float(ref_user.get("earned_from_ref", 0.0)) + com
                })
                
    try:
        bot.send_message(target_uid, f"☑ আপনার {approved_count}টি টাস্ক অ্যাপ্রুভ হয়েছে! {amount:.2f} TK আপনার ব্যালেন্সে যোগ করা হয়েছে।")
    except:
        pass
        
    bot.answer_callback_query(call.id, f"সফলভাবে {amount:.2f} TK পেমেন্ট সম্পন্ন হয়েছে!", show_alert=True)
    admin_applied_tasks_users(call)

# ৫. সম্পূর্ণ রিজেক্ট অ্যাকশন
@bot.callback_query_handler(func=lambda call: call.data.startswith("app_act_rej_"))
def process_app_full_reject(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    parts = call.data.split("_")
    target_uid = parts[3]
    cat = "_".join(parts[4:])
    
    subs = db_get("task_submissions")
    rej_count = 0
    if subs and isinstance(subs, dict):
        for s_id, s in subs.items():
            if isinstance(s, dict) and str(s.get("user_id")) == str(target_uid) and s.get("status") == "pending":
                plat = s.get("platform", "").upper()
                ttype = s.get("task_type", "").lower()
                
                match = False
                if cat == "GMAIL" and plat == "GMAIL": match = True
                elif cat == "INSTAGRAM" and plat == "INSTAGRAM": match = True
                elif cat == "FB_2FA" and plat == "FACEBOOK" and "cookie" not in ttype: match = True
                elif cat == "FB_COOKIES" and plat == "FACEBOOK" and "cookie" in ttype: match = True
                
                if match:
                    db_patch(f"task_submissions/{s_id}", {"status": "rejected"})
                    rej_count += 1
                    
    user = db_get(f"users/{target_uid}")
    if user and isinstance(user, dict):
        rej = int(user.get("rejected_task", 0)) + rej_count
        pend = max(0, int(user.get("pending_task", 0)) - rej_count)
        db_patch(f"users/{target_uid}", {
            "rejected_task": rej,
            "pending_task": pend
        })
        
    try:
        bot.send_message(target_uid, f"✖ দুঃখিত! আপনার সাবমিট করা {rej_count}টি টাস্ক ভুল তথ্যের কারণে রিজেক্ট করা হয়েছে।")
    except:
        pass
        
    bot.answer_callback_query(call.id, "সকল টাস্ক রিজেক্ট করা হয়েছে!", show_alert=True)
    admin_applied_tasks_users(call)

# ৬. ভুল আইডি বাদ দিয়ে আংশিক পেমেন্ট ক্যালকুলেটর
@bot.callback_query_handler(func=lambda call: call.data.startswith("app_act_deduct_"))
def prompt_deduct_bad_ids(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    parts = call.data.split("_")
    target_uid = parts[3]
    cat = f"{parts[4]}_{parts[5]}" if len(parts) == 8 else parts[4]
    pending_count = int(parts[-2])
    unit_price = float(parts[-1])
    
    user_states[call.from_user.id] = {
        'action': 'admin_apply_deduct_calc',
        'target_uid': target_uid,
        'cat': cat,
        'pending_count': pending_count,
        'unit_price': unit_price
    }
    
    msg = (
        f"✏ **ভুল আইডি বাদ দিয়ে হিসাব করুন:**\n\n"
        f"ইউজারের মোট `{pending_count}` টি পেন্ডিং কাজ আছে (প্রতিটি `{unit_price:.2f}` TK)।\n"
        f"এর মধ্যে **কয়টি আইডি ভুল বা বাতিল করতে চান** তা শুধু সংখ্যায় লিখে পাঠান:\n\n"
        f"*(যেমন: ১০টির মধ্যে ৪টি ভুল হলে শুধু `4` লিখে পাঠান। বাকি ৬টির টাকা অটো হিসাব হবে)*"
    )
    bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'admin_apply_deduct_calc'))
def process_deduct_calculation(message):
    try:
        bad_count = int(message.text.strip())
        state = user_states[message.from_user.id]
        target_uid = state['target_uid']
        cat = state['cat']
        pending_count = state['pending_count']
        unit_price = state['unit_price']
        
        if bad_count < 0 or bad_count > pending_count:
            bot.send_message(message.chat.id, f"✖ ভুল সংখ্যা! ০ থেকে {pending_count} এর মধ্যে লিখুন।")
            return
            
        valid_count = pending_count - bad_count
        payout_amount = valid_count * unit_price
        
        subs = db_get("task_submissions")
        target_subs = []
        if subs and isinstance(subs, dict):
            for s_id, s in subs.items():
                if isinstance(s, dict) and str(s.get("user_id")) == str(target_uid) and s.get("status") == "pending":
                    plat = s.get("platform", "").upper()
                    ttype = s.get("task_type", "").lower()
                    
                    match = False
                    if cat == "GMAIL" and plat == "GMAIL": match = True
                    elif cat == "INSTAGRAM" and plat == "INSTAGRAM": match = True
                    elif cat == "FB_2FA" and plat == "FACEBOOK" and "cookie" not in ttype: match = True
                    elif cat == "FB_COOKIES" and plat == "FACEBOOK" and "cookie" in ttype: match = True
                    
                    if match:
                        s["id"] = s_id
                        target_subs.append(s)
                        
        # Valid Tasks Approve
        for i in range(valid_count):
            sub = target_subs[i]
            db_patch(f"task_submissions/{sub['id']}", {"status": "approved"})
            
        # Bad Tasks Reject
        for i in range(valid_count, pending_count):
            sub = target_subs[i]
            db_patch(f"task_submissions/{sub['id']}", {"status": "rejected"})
            
        user = db_get(f"users/{target_uid}")
        if user and isinstance(user, dict):
            new_bal = float(user.get("balance", 0.0)) + payout_amount
            new_earned = float(user.get("total_earned", 0.0)) + payout_amount
            appr = int(user.get("approved_task", 0)) + valid_count
            rej = int(user.get("rejected_task", 0)) + bad_count
            pend = max(0, int(user.get("pending_task", 0)) - pending_count)
            
            db_patch(f"users/{target_uid}", {
                "balance": new_bal, 
                "total_earned": new_earned,
                "approved_task": appr,
                "rejected_task": rej,
                "pending_task": pend
            })
            
            ref_id = user.get("referrer")
            if ref_id and str(ref_id).isdigit() and payout_amount > 0:
                ref_user = db_get(f"users/{ref_id}")
                if ref_user:
                    com = payout_amount * 0.10
                    db_patch(f"users/{ref_id}", {
                        "balance": float(ref_user.get("balance", 0.0)) + com,
                        "earned_from_ref": float(ref_user.get("earned_from_ref", 0.0)) + com
                    })
                    
        del user_states[message.from_user.id]
        
        try:
            bot.send_message(
                int(target_uid), 
                f"☑ আপনার টাস্ক রিভিউ সম্পন্ন হয়েছে!\n\n"
                f"✔ অনুমোদিত কাজ: `{valid_count}` টি\n"
                f"✖ বাতিল কাজ: `{bad_count}` টি\n"
                f"⛁ আপনার অ্যাকাউন্টে `{payout_amount:.2f} TK` যোগ করা হয়েছে।"
            )
        except:
            pass
            
        success_text = (
            f"☑ **হিসাব ও পেমেন্ট সফলভাবে সম্পন্ন হয়েছে!**\n\n"
            f"֎ ইউজার আইডি: `{target_uid}`\n"
            f"✔ অনুমোদিত কাজ: `{valid_count}` টি\n"
            f"✖ বাতিল/মাইনাস কাজ: `{bad_count}` টি\n"
            f"⛁ ইউজারের একাউন্টে যোগ হয়েছে: `{payout_amount:.2f} TK`"
        )
        bot.send_message(message.chat.id, success_text, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"✖ ত্রুটি হয়েছে: {e}")

# ==========================================
# অন্যান্য অ্যাডমিন ফাংশনসমূহ (পূর্বের কোড)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "admin_add_accounts")
def admin_add_accounts_menu(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    tasks = db_get("tasks")
    if not tasks: 
        return bot.answer_callback_query(call.id, "NO TASKS CREATED YET!", show_alert=True)
    
    markup = InlineKeyboardMarkup(row_width=1)
    for t_id, t in tasks.items():
        markup.add(InlineKeyboardButton(f"❖ {t.get('name')} ({t.get('platform')})", callback_data=f"up_acc_{t_id}"))
    markup.add(InlineKeyboardButton("◄ BACK", callback_data="admin_home"))
    
    bot.edit_message_text("❖ **SELECT TASK TO UPLOAD ACCOUNTS FOR:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("up_acc_"))
def ask_account_data_upload(call):
    t_id = call.data.split("up_acc_")[1]
    user_states[call.from_user.id] = {'action': 'upload_accs', 't_id': t_id}
    msg = "✎ **SEND ACCOUNTS DATA (ONE PER LINE):**\n\nFORMAT FOR FACEBOOK:\n`Fname|Lname|Password`\n\nFORMAT FOR INSTAGRAM:\n`Username|Password`"
    bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'upload_accs'))
def process_acc_upload(message):
    t_id = user_states[message.from_user.id]['t_id']
    lines = message.text.strip().split('\n')
    count = 0
    for line in lines:
        if line.strip():
            db_post(f"task_accounts/{t_id}", line.strip())
            count += 1
    bot.send_message(message.chat.id, f"☑ {count} ACCOUNTS SUCCESSFULLY ADDED TO POOL!")
    del user_states[message.from_user.id]

@bot.callback_query_handler(func=lambda call: call.data == "admin_edit_accs")
def admin_edit_accs_menu(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    tasks = db_get("tasks")
    if not tasks: 
        return bot.answer_callback_query(call.id, "NO TASKS CREATED YET!", show_alert=True)
    
    markup = InlineKeyboardMarkup(row_width=1)
    for t_id, t in tasks.items():
        markup.add(InlineKeyboardButton(f"✎ Edit: {t.get('name')}", callback_data=f"edit_pool_{t_id}"))
    markup.add(InlineKeyboardButton("◄ BACK", callback_data="admin_home"))
    
    bot.edit_message_text("❖ **SELECT TASK TO EDIT POOL:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_pool_"))
def show_pool_accounts(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    t_id = call.data.split("edit_pool_")[1]
    accounts = db_get(f"task_accounts/{t_id}")
    
    if not accounts:
        return bot.answer_callback_query(call.id, "NO ACCOUNTS IN POOL TO EDIT!", show_alert=True)
        
    markup = InlineKeyboardMarkup(row_width=1)
    count = 0
    for acc_key, acc_data in accounts.items():
        if count >= 10: 
            break
        preview = str(acc_data)[:25] + "..."
        markup.add(InlineKeyboardButton(f"✎ {preview}", callback_data=f"modify_acc_{t_id}_{acc_key}"))
        count += 1
        
    markup.add(InlineKeyboardButton("◄ BACK", callback_data="admin_edit_accs"))
    bot.edit_message_text("Select an account to modify (Top 10):", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("modify_acc_"))
def modify_specific_acc(call):
    parts = call.data.split("_")
    t_id = parts[2]
    acc_key = parts[3]
    
    acc_data = db_get(f"task_accounts/{t_id}/{acc_key}")
    if not acc_data: 
        return bot.answer_callback_query(call.id, "ACCOUNT NOT FOUND!", show_alert=True)
    
    user_states[call.from_user.id] = {'action': 'save_modified_acc', 't_id': t_id, 'acc_key': acc_key}
    
    msg = f"Current Data:\n`{acc_data}`\n\nSend replacement data:"
    bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'save_modified_acc'))
def save_mod_acc(message):
    data = user_states[message.from_user.id]
    db_put(f"task_accounts/{data['t_id']}/{data['acc_key']}", message.text.strip())
    bot.send_message(message.chat.id, "☑ Account updated successfully!")
    del user_states[message.from_user.id]

@bot.callback_query_handler(func=lambda call: call.data == "review_users_list")
def review_users_submissions(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    subs = db_get("task_submissions")
    
    users = {}
    if subs and isinstance(subs, dict):
        for s_id, s in subs.items():
            if isinstance(s, dict) and s.get("status") == "pending":
                uid = s.get("user_id")
                users[uid] = users.get(uid, 0) + 1
                
    markup = InlineKeyboardMarkup(row_width=1)
    if not users:
        return bot.answer_callback_query(call.id, "NO PENDING SUBMISSIONS!", show_alert=True)
    
    for uid, count in users.items():
        markup.add(InlineKeyboardButton(f"֎ USER: {uid} ({count} TASKS PENDING)", callback_data=f"rev_user_{uid}"))
        
    markup.add(InlineKeyboardButton("◄ BACK", callback_data="admin_home"))
    bot.edit_message_text("❖ **PENDING SUBMISSIONS BY USER:**\nSelect a user to review:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("rev_user_"))
def review_specific_user(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    uid = call.data.split("rev_user_")[1]
    subs = db_get("task_submissions")
    user_subs = []
    
    if subs and isinstance(subs, dict):
        for s_id, s in subs.items():
            if isinstance(s, dict) and str(s.get("user_id")) == str(uid) and s.get("status") == "pending":
                s['id'] = s_id
                user_subs.append(s)
            
    if not user_subs:
        return bot.answer_callback_query(call.id, "ALREADY PROCESSED!", show_alert=True)
        
    total_price = sum(float(s.get("price", 0)) for s in user_subs)
    
    copy_text = ""
    for s in user_subs:
        copy_text += f"Task: {s.get('task_name')} | Platform: {s.get('platform', 'N/A')} | Data: {s.get('details', '')}\n"
        
    msg = (
        f"❖ **USER SUBMISSION REVIEW** ❖\n\n"
        f"֎ USER ID: `{uid}`\n"
        f"☰ TOTAL SUBMITTED: {len(user_subs)} TASKS\n"
        f"⛁ EXPECTED PAYOUT: {total_price:.2f} TK\n\n"
        f"▼ **ALL DATA (CLICK TO COPY):**\n```\n{copy_text}```\n\n"
        f"➜ CHOOSE ACTION:"
    )
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton(f"☑ APPROVE FULL ({total_price:.2f} TK)", callback_data=f"sub_pay_full_{uid}_{total_price}"))
    markup.add(InlineKeyboardButton("✖ REJECT ALL", callback_data=f"sub_pay_reject_{uid}"))
    markup.add(InlineKeyboardButton("◄ BACK TO USER LIST", callback_data="review_users_list"))
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_pay_full_"))
def process_sub_full(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    parts = call.data.split("_")
    target_uid = parts[3]
    amount = float(parts[4])
    
    user = db_get(f"users/{target_uid}")
    if user and isinstance(user, dict):
        new_bal = float(user.get("balance", 0.0)) + amount
        new_earned = float(user.get("total_earned", 0.0)) + amount
        appr = int(user.get("approved_task", 0)) + 1
        pend = max(0, int(user.get("pending_task", 0)) - 1)
        
        db_patch(f"users/{target_uid}", {
            "balance": new_bal, 
            "total_earned": new_earned,
            "approved_task": appr,
            "pending_task": pend
        })
        
        ref_id = user.get("referrer")
        if ref_id and str(ref_id).isdigit():
            ref_user = db_get(f"users/{ref_id}")
            if ref_user:
                com = amount * 0.10
                db_patch(f"users/{ref_id}", {
                    "balance": float(ref_user.get("balance", 0.0)) + com,
                    "earned_from_ref": float(ref_user.get("earned_from_ref", 0.0)) + com
                })
        
    subs = db_get("task_submissions")
    if subs and isinstance(subs, dict):
        for s_id, s in subs.items():
            if isinstance(s, dict) and str(s.get("user_id")) == str(target_uid) and s.get("status") == "pending":
                db_patch(f"task_submissions/{s_id}", {"status": "approved"})
                
    try: 
        bot.send_message(target_uid, f"☑ আপনার টাস্কগুলো অ্যাপ্রুভ হয়েছে! {amount:.2f} TK আপনার ব্যালেন্সে যোগ করা হয়েছে।")
    except: 
        pass
    
    bot.answer_callback_query(call.id, "PAYMENT DONE SUCCESSFULLY!", show_alert=True)
    review_users_submissions(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_pay_reject_"))
def process_sub_reject(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    target_uid = call.data.split("_")[3]
    
    user = db_get(f"users/{target_uid}")
    if user and isinstance(user, dict):
        rej = int(user.get("rejected_task", 0)) + 1
        pend = max(0, int(user.get("pending_task", 0)) - 1)
        db_patch(f"users/{target_uid}", {
            "rejected_task": rej,
            "pending_task": pend
        })
        
    subs = db_get("task_submissions")
    if subs and isinstance(subs, dict):
        for s_id, s in subs.items():
            if isinstance(s, dict) and str(s.get("user_id")) == str(target_uid) and s.get("status") == "pending":
                db_patch(f"task_submissions/{s_id}", {"status": "rejected"})
                
    try: 
        bot.send_message(target_uid, "✖ দুঃখিত! আপনার সাবমিট করা কিছু তথ্য ভুল থাকায় টাস্কগুলো রিজেক্ট করা হয়েছে।")
    except: 
        pass
    
    bot.answer_callback_query(call.id, "ALL REJECTED!", show_alert=True)
    review_users_submissions(call)

@bot.callback_query_handler(func=lambda call: call.data == "admin_wd")
def admin_withdrawals_menu(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    wds = db_get("withdrawals")
    users = {}
    
    if wds and isinstance(wds, dict):
        for w_id, w in wds.items():
            if isinstance(w, dict) and w.get("status") == "pending":
                uid = w.get("user_id")
                users[uid] = users.get(uid, 0) + 1
                
    markup = InlineKeyboardMarkup(row_width=1)
    if not users: 
        return bot.answer_callback_query(call.id, "NO PENDING WITHDRAWALS!", show_alert=True)
    
    for uid, count in users.items():
        markup.add(InlineKeyboardButton(f"֎ USER: {uid} ({count} REQUESTS)", callback_data=f"rev_wd_user_{uid}"))
    markup.add(InlineKeyboardButton("◄ BACK", callback_data="admin_home"))
    
    bot.edit_message_text("❖ **PENDING WITHDRAWALS BY USER:**\nSelect a user to review:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("rev_wd_user_"))
def review_wd_user(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    uid = call.data.split("rev_wd_user_")[1]
    wds = db_get("withdrawals")
    user_wds = []
    
    if wds and isinstance(wds, dict):
        for w_id, w in wds.items():
            if isinstance(w, dict) and str(w.get("user_id")) == str(uid) and w.get("status") == "pending":
                w['id'] = w_id
                user_wds.append(w)
            
    if not user_wds: 
        return bot.answer_callback_query(call.id, "ALREADY PROCESSED!", show_alert=True)
    
    msg = f"❖ **WITHDRAWAL DETAILS FOR `{uid}`**\n\n"
    markup = InlineKeyboardMarkup(row_width=1)
    
    for w in user_wds:
        msg += f"≡ METHOD: {w.get('method')}\n⛁ AMOUNT: {w.get('amount')} TK\n⌨ NUMBER: `{w.get('number')}`\n\n"
        markup.add(InlineKeyboardButton(f"☑ APPROVE {w.get('amount')} TK", callback_data=f"wd_app_{w['id']}_{w.get('amount')}_{uid}"))
        markup.add(InlineKeyboardButton(f"✖ REJECT & REFUND {w.get('amount')} TK", callback_data=f"wd_rej_{w['id']}_{w.get('amount')}_{uid}"))
        
    markup.add(InlineKeyboardButton("◄ BACK TO LIST", callback_data="admin_wd"))
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("wd_app_"))
def process_wd_app(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    parts = call.data.split("_")
    wd_id = parts[2]
    amount = parts[3]
    uid = parts[4]
    
    db_patch(f"withdrawals/{wd_id}", {"status": "approved"})
    
    try: 
        bot.send_message(uid, f"☑ অভিনন্দন! আপনার {amount} টাকার উইথড্র রিকোয়েস্ট সফলভাবে সম্পন্ন হয়েছে (Approved)!")
    except: 
        pass
    
    bot.edit_message_text("☑ REQUEST APPROVED!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("wd_rej_"))
def process_wd_rej(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    parts = call.data.split("_")
    wd_id = parts[2]
    amount = float(parts[3])
    uid = parts[4]
    
    db_patch(f"withdrawals/{wd_id}", {"status": "rejected"})
    
    user = db_get(f"users/{uid}")
    if user and isinstance(user, dict):
        new_bal = float(user.get("balance", 0.0)) + amount
        db_patch(f"users/{uid}", {"balance": new_bal})
        
    try: 
        bot.send_message(uid, f"✖ দুঃখিত! আপনার {amount:.2f} টাকার উইথড্র রিকোয়েস্ট রিজেক্ট করা হয়েছে। টাকা ব্যালেন্সে রিফান্ড করা হয়েছে।")
    except: 
        pass
    
    bot.edit_message_text("☑ REQUEST REJECTED AND BALANCE REFUNDED!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_tasks")
def admin_tasks_menu(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("✚ ADD NEW TASK", callback_data="add_task"))
    markup.add(InlineKeyboardButton("✖ REMOVE TASK", callback_data="remove_task_menu"))
    markup.add(InlineKeyboardButton("◄ BACK", callback_data="admin_home"))
    bot.edit_message_text("⚙ **MANAGE TASKS**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_task_"))
def delete_task_action(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    t_id = call.data.split("del_task_")[1]
    db_delete(f"tasks/{t_id}")
    db_delete(f"task_accounts/{t_id}")
    bot.edit_message_text("☑ TASK PERMANENTLY REMOVED!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast_step(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    user_states[call.from_user.id] = {'action': 'admin_broadcast_msg'}
    bot.send_message(call.message.chat.id, "📣 **SEND THE BROADCAST MESSAGE:**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'admin_broadcast_msg'))
def process_broadcast(message):
    users = db_get("users")
    text = message.text
    del user_states[message.from_user.id]
    
    if not users or not isinstance(users, dict):
        return bot.send_message(message.chat.id, "NO USERS REGISTERED YET!")
        
    bot.send_message(message.chat.id, f"⏳ Broadcasting message to {len(users)} users...")
    sent = 0
    failed = 0
    for uid in users.keys():
        try:
            bot.send_message(int(uid), text, parse_mode="Markdown")
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
            
    bot.send_message(message.chat.id, f"☑ Broadcast Complete!\nSent: {sent} users\nFailed: {failed} users")

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings_menu(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    min_w = get_setting("min_withdraw", MIN_WITHDRAW)
    tut = get_setting("tutorial_link", "https://t.me/RS_FUTURE_JOB_EXPRESS_VIDEO")
    supp = get_setting("admin_contact", "https://t.me/Rubel_Owner")
    
    msg = (
        f"⚙ **CURRENT BOT SETTINGS:**\n\n"
        f"✦ Min Withdrawal: `{min_w}` TK\n"
        f"✦ Tutorial Channel: `{tut}`\n"
        f"✦ Admin Support: `{supp}`\n\n"
        f"Select a setting to modify:"
    )
          
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("✎ Set Min Withdrawal", callback_data="set_min_w"))
    markup.add(InlineKeyboardButton("✎ Set Tutorial Channel Link", callback_data="set_tut_link"))
    markup.add(InlineKeyboardButton("✎ Set Support Contact", callback_data="set_supp_link"))
    markup.add(InlineKeyboardButton("◄ BACK", callback_data="admin_home"))
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data in ["set_min_w", "set_tut_link", "set_supp_link"])
def modify_setting_prompt(call):
    action_key = call.data
    user_states[call.from_user.id] = {'action': 'save_setting_val', 'setting_key': action_key}
    prompt_map = {
        "set_min_w": "Enter new Minimum Withdrawal Amount (e.g. 50):",
        "set_tut_link": "Enter new Tutorial Telegram Channel Link:",
        "set_supp_link": "Enter new Admin Telegram Contact Link:"
    }
    bot.send_message(call.message.chat.id, prompt_map[action_key])

@bot.message_handler(func=lambda m: message_handler_router(m, 'save_setting_val'))
def save_setting_val(message):
    key = user_states[message.from_user.id]['setting_key']
    val = message.text.strip()
    
    if key == "set_min_w":
        try:
            val = float(val)
            db_put("settings/min_withdraw", {"value": val})
            bot.send_message(message.chat.id, f"☑ Min Withdrawal updated to {val} TK!")
        except:
            bot.send_message(message.chat.id, "✖ Invalid amount!")
    elif key == "set_tut_link":
        db_put("settings/tutorial_link", {"value": val})
        bot.send_message(message.chat.id, "☑ Tutorial Link updated!")
    elif key == "set_supp_link":
        db_put("settings/admin_contact", {"value": val})
        bot.send_message(message.chat.id, "☑ Admin Support Contact updated!")
        
    del user_states[message.from_user.id]

@bot.callback_query_handler(func=lambda call: call.data == "admin_user_mgr")
def admin_user_mgr_prompt(call):
    if call.from_user.id not in ADMIN_IDS: 
        return
    user_states[call.from_user.id] = {'action': 'admin_lookup_uid'}
    bot.send_message(call.message.chat.id, "֎ **SEND TELEGRAM USER ID TO LOOKUP / MODIFY BALANCE:**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: message_handler_router(m, 'admin_lookup_uid'))
def admin_user_lookup_result(message):
    target_uid = message.text.strip()
    user = db_get(f"users/{target_uid}")
    del user_states[message.from_user.id]
    
    if not user or not isinstance(user, dict):
        return bot.send_message(message.chat.id, f"✖ User `{target_uid}` not found in database.", parse_mode="Markdown")
        
    bal = user.get("balance", 0.0)
    refs = user.get("referrals", 0)
    pending = user.get("pending_task", 0)
    approved = user.get("approved_task", 0)
    
    msg = (
        f"֎ **USER PROFILE: `{target_uid}`**\n\n"
        f"⛁ Balance: `{bal:.2f}` TK\n"
        f"⊛ Referrals: `{refs}`\n"
        f"⏲ Pending Tasks: `{pending}`\n"
        f"☑ Approved Tasks: `{approved}`\n\n"
        f"Choose an action:"
    )
          
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("✚ ADD BALANCE", callback_data=f"mod_bal_add_{target_uid}"))
    markup.add(InlineKeyboardButton("✖ DEDUCT BALANCE", callback_data=f"mod_bal_sub_{target_uid}"))
    markup.add(InlineKeyboardButton("◄ BACK", callback_data="admin_home"))
    
    bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("mod_bal_"))
def mod_bal_prompt(call):
    parts = call.data.split("_")
    op = parts[2]
    target_uid = parts[3]
    user_states[call.from_user.id] = {'action': 'save_bal_change', 'op': op, 'target_uid': target_uid}
    bot.send_message(call.message.chat.id, f"Enter amount to {'ADD to' if op == 'add' else 'DEDUCT from'} user `{target_uid}`:")

@bot.message_handler(func=lambda m: message_handler_router(m, 'save_bal_change'))
def process_bal_change(message):
    try:
        amount = float(message.text.strip())
        state = user_states[message.from_user.id]
        target_uid = state['target_uid']
        op = state['op']
        
        user = db_get(f"users/{target_uid}")
        if user and isinstance(user, dict):
            current_bal = float(user.get("balance", 0.0))
            new_bal = (current_bal + amount) if op == 'add' else max(0.0, current_bal - amount)
            db_patch(f"users/{target_uid}", {"balance": new_bal})
            bot.send_message(message.chat.id, f"☑ User `{target_uid}` balance updated: `{new_bal:.2f}` TK", parse_mode="Markdown")
            try:
                bot.send_message(int(target_uid), f"✦ আপনার অ্যাকাউন্টে অ্যাডমিন দ্বারা ব্যালেন্স পরিবর্তন করা হয়েছে। নতুন ব্যালেন্স: {new_bal:.2f} TK")
            except:
                pass
        del user_states[message.from_user.id]
    except:
        bot.send_message(message.chat.id, "✖ Invalid amount!")

# ==========================================
# 🚀 বট রান ও পুলিং
# ==========================================
if __name__ == "__main__":
    print("✦ Bot is running with all updated buttons and logic! ✦")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"Bot polling exception: {e}")
