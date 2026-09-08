import os
import re
import subprocess
import time
import requests

BOT_TOKEN = "8995269165:AAGzs3OBZsa9-f-OETfFjFQN9k0M4QjbZCU"


def get_chat_id():
    """বট থেকে সর্বশেষ মেসেজ পাঠানো ইউজারের চ্যাট আইডি নিয়ে আসে"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("result"):
            return res["result"][-1]["message"]["chat"]["id"]
    except Exception as e:
        print(f"Chat ID আনতে সমস্যা: {e}")
    return None


def send_telegram_message(chat_id, text):
    """টেলিগ্রামে মেসেজ পাঠায়"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"মেসেজ পাঠাতে সমস্যা: {e}")


def run_sshx_and_notify():
    chat_id = get_chat_id()

    # যদি চ্যাট আইডি না পাওয়া যায়, তবে ইউজারের একটি মেসেজ পাঠানোর জন্য অপেক্ষা করবে
    while not chat_id:
        print(
            "টেলিগ্রাম চ্যাট আইডি পাওয়া যায়নি! টেলিগ্রামে বটে গিয়ে /start লিখে মেসেজ দিন..."
        )
        time.sleep(5)
        chat_id = get_chat_id()

    print(f"চ্যাট আইডি পাওয়া গেছে: {chat_id}")
    send_telegram_message(chat_id, "🚀 sshx চালু করা হচ্ছে...")

    # sshx প্রসেস ব্যাকগ্রাউন্ডে রান করা
    process = subprocess.Popen(
        ["sshx"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    link_pattern = re.compile(r"https://sshx\.io/s/[a-zA-Z0-9#]+")
    link_sent = False

    # টার্মিনালের লাইভ আউটপুট পড়া
    for line in iter(process.stdout.readline, ""):
        print(line, end="")

        if not link_sent:
            match = link_pattern.search(line)
            if match:
                link = match.group(0)
                send_telegram_message(
                    chat_id, f"✅ আপনার sshx টার্মিনাল লিংক:\n{link}"
                )
                link_sent = True

    process.stdout.close()
    process.wait()
    send_telegram_message(chat_id, "⚠️ sshx সেশন বন্ধ হয়ে গেছে।")


if __name__ == "__main__":
    run_sshx_and_notify()
