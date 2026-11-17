# language: Python 3.10+, file: SINNERS_userbot.py, target: Telegram via Telethon
# pip install telethon
"""
SINNERS multi-userbot — hoster edition.
Per-command stop via s-prefix (srev, schud, ...).
"""

import asyncio
import json
import os
import random
import re
import time
from collections import defaultdict, deque

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.custom import Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import (
    ChatBannedRights,
    ReactionEmoji,
)
from telethon.tl.functions.messages import (
    SendReactionRequest,
    AddChatUserRequest,
)
from telethon.tl.functions.channels import InviteToChannelRequest

# ============================================================
# CONFIG
# ============================================================
API_ID = 39958068
API_HASH = "b0eb07651d0870691d7b3dd44f550353"
BOT_TOKEN = "9034402580:AAFzVLoap_xlrAV-wFd3Wujfqp83ry23tQQ"
OWNER_USERNAME = "immortalpython"

SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)
STATE_FILE = os.path.join(SESSIONS_DIR, "state.json")
BOT_SESSION = os.path.join(SESSIONS_DIR, "bot_control")

GUIDE_TEXT = """
🤍 𝙎𝙞𝙣𝙣𝙚𝙧𝙨 𝙈𝙪𝙡𝙩𝙞-𝙐𝙨𝙚𝙧𝙗𝙤𝙩 — 𝙂𝙪𝙞𝙙𝙚

🩷 𝙃𝙤𝙨𝙩𝙞𝙣𝙜
1. Click Host your userbot
2. Send string session OR phone number
3. If phone, enter OTP and 2FA if required
4. Once confirmed, your userbot is live

🩵 𝘾𝙤𝙢𝙢𝙖𝙣𝙙𝙨
Issued from YOUR Telegram account after login.
Send xhelp in any chat for the full list.

🤍 𝙎𝙪𝙥𝙥𝙤𝙧𝙩
@immortalpython
"""

# ============================================================
# GLYPH ENGINES
# ============================================================
_UPPER = 0x1D63C
_LOWER = 0x1D656
_DIGIT = 0x1D7EC


def fancy(text: str) -> str:
    out = []
    for ch in text:
        o = ord(ch)
        if 65 <= o <= 90:
            out.append(chr(_UPPER + o - 65))
        elif 97 <= o <= 122:
            out.append(chr(_LOWER + o - 97))
        elif 48 <= o <= 57:
            out.append(chr(_DIGIT + o - 48))
        else:
            out.append(ch)
    return "".join(out)


def math_italic(text: str) -> str:
    out = []
    for ch in text:
        o = ord(ch)
        if 65 <= o <= 90:
            out.append(chr(0x1D434 + o - 65))
        elif 97 <= o <= 122:
            if ch == "h":
                out.append("\u210E")
            else:
                out.append(chr(0x1D44E + o - 97))
        else:
            out.append(ch)
    return "".join(out)


# ============================================================
# UTF-16 LENGTH — Telegram counts UTF-16 code units (4096 limit).
# ============================================================
MAX_UTF16 = 4000


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def truncate_utf16(text: str, limit: int = MAX_UTF16) -> str:
    if utf16_len(text) <= limit:
        return text
    result = []
    used = 0
    for ch in text:
        c = 2 if ord(ch) > 0xFFFF else 1
        if used + c > limit:
            break
        result.append(ch)
        used += c
    return "".join(result)


# ============================================================
# STATE
# ============================================================
DEFAULT_CHUDAI_TEXTS = [
    "{name} AREY CHUP RANDYK UNFUNNY HUMOUR LESS INCEL😂😂😂",
    "{name} AGAR ME APKI माँ KO NAMAZ PADHTE WAQT CHODUN TO CYA VO SUNNAT HOGA?🤪",
    "{name} Teri mummy ko subah 5 baje uthake morning walk pe lejake break fast karake nahLake dholake lunch karake din me sulake raat me utha ke candle light date dinner krke phir Ghar pe lake dheere dheere pom pom krte krte chodunga 🤪🤏🏿 entry 🥵🥵🥵",
    "{name} 𝙏𝙚𝙧𝙞 𝙢𝙖 𝙠𝙞 𝙘𝙝𝙪𝙩 𝙆𝙖 𝙗𝙞𝙧𝙮𝙖𝙣𝙞 𝙥𝙠𝙖 𝙠𝙚 𝙠𝙝𝙖 𝙟𝙖𝙪𝙣𝙜𝙖😁",
    "{name} 𝙏𝙐 𝙏𝙊𝙃 𝙈𝙀𝙍𝘼 𝙒𝙊𝙃𝙄 𝙏𝘼𝙏𝙏𝘼 𝙃𝘼𝙄 𝙉𝘼 ? 𝙅𝙄𝙎𝙈𝙀 𝙍𝙊𝙕 𝙆𝙃𝙐𝙅𝙇𝙄 𝙃𝙊𝙏𝙄🤣",
    "{name} 𝙆𝙞𝙩𝙣𝙖 𝙘𝙝𝙪𝙙𝙚𝙜𝙖 𝘼𝙗 𝙩𝙚𝙧𝙞 𝙢𝙖 𝙠𝙤 𝙗𝙝𝙞 𝙢𝙤𝙠𝙖 𝙙𝙚 𝙘𝙝𝙪𝙙𝙣𝙚 𝙠𝙖🤗",
    "{name} Oye dost Teri randi maa ka 👙 aur 300 rupey reh gaye ake le ja Aur teri randi maa v yahi he Konsi maa Dharti maa Fatima Teri Ghar wali maa Ya teri dadi ki maa?",
    "{name} Ye dekh Tmkc me camel 🐪 ",
    "{name} Oho funny 🤣😂🤣😂🤣😂🤣😂🤣😂🤣😂🤣🤣😂🤣😂🤣😂🤣😂🤣😂🤣😂🤣😂🤣😂🤣😂🤣😂🤣😂🤣😂🤣 Ab trima chudegi😱",
    "{name} Baune trima cute RND he tri behen ko to slave banake rkha he mene itna attitude kese aara tujhme😂😂😂😂😂💔😂😂💔😂💔😂💔😂💔😂💔💔😂🥀🥀🥀",
    "{name} Apki mom itni RND kese he bina pese lie chud jaati😏🥀💔",
    "{name} Trima pe atomic bomb gir jae jo tre sarr pe pankha he na vo tut ke tre goto pe gire jo tre ghar pe cylinder he na tre ma jab uspe khana banari ho tb vi fatt jae jo tra nall he na vo leak hojae or tra ghar bhass jae mc",
    "{name} ＴＲＩＭＡ　ＣＨＵＤＧＹＩ　ＲＥ😜💜　        ほソがん       ˖ ᡣ𐭩 ⊹ ࣪  ౨ৎ˚₊",
    "{name} Beta lund chus bada ho pese duga 😏🥹",
    "{name} sun aukat anusar chud tu",
    "{name} chl mc apni mom ki kali chut ki mms send kr",
]

DEFAULT_REV_TEXTS = [
    "𝐀ᴀᴊ 𝐌𝐀ɪ 𝐉ᴀᴀ𝐊ᴇ ꜱ𝐂𝐇ᴏᴏ𝐋 ❤️‍🩹                     {{ ////𝙉𝘼𝙈𝙀////// }}  ᴛ𝐄𝐑ɪ 𝐌ᴀ ᴋ𝐈 𝐂ʜᴜ𝐓 𝐌ᴀᴀ𝐑 ᴋ𝐄 ᴊᴀ𝐔𝐍ɢ𝐀 𝐁𝐇ᴜʟ💋                                                                                                              𝐀ᴀᴊ 𝐌𝐀ɪ 𝐉ᴀᴀ𝐊ᴇ ꜱ𝐂𝐇ᴏᴏ𝐋 ❤️‍🩹                     {{ ////𝙉𝘼𝙈𝙀////// }}  ᴛ𝐄𝐑ɪ 𝐌ᴀ ᴋ𝐈 𝐂ʜᴜ𝐓 𝐌ᴀᴀ𝐑 ᴋ𝐄 ᴊᴀ𝐔𝐍ɢ𝐀 𝐁𝐇ᴜʟ💋𝐀ᴀᴊ 𝐌𝐀ɪ 𝐉ᴀᴀ𝐊ᴇ ꜱ𝐂𝐇ᴏᴏ𝐋 ❤️‍🩹                     {{ ////𝙉𝘼𝙈𝙀////// }}  ᴛ𝐄𝐑ɪ 𝐌ᴀ ᴋ𝐈 𝐂ʜᴜ𝐓 𝐌ᴀᴀ𝐑 ᴋ𝐄 ᴊᴀ𝐔𝐍ɢ𝐀 𝐁𝐇ᴜʟ💋 𝐀ᴀᴊ 𝐌𝐀ɪ 𝐉ᴀᴀ𝐊ᴇ ꜱ𝐂𝐇ᴏᴏ𝐋 ❤️‍🩹                     {{ ////𝙉𝘼𝙈𝙀////// }}  ᴛ𝐄𝐑ɪ 𝐌ᴀ ᴋ𝐈 𝐂ʜ𝐮𝐓 𝐌ᴀᴀ𝐑 ᴋ𝐄 ᴊᴀ𝐔𝐍ɢ𝐀 𝐁𝐇ᴜʟ💋",
    "ָ𓂃 ࣪˖ ִֶָ 𝐂ʜᴀ𝐋𝐋 𝐓ᴜ 𝐋ᴇ𝐆ᴀ 𝙎𝙄𝙉 𝙂𝙊𝘿 ᴩᴀ𝐍ɢ𝐀 .ᐟ   {{ ////𝙉𝘼𝙈𝙀////// }}  𝐓ᴇʀ𝐈 𝐁ᴇʜ𝐀𝐍 𝐊ᴏ 𝐂𝐇ᴏᴅ𝐔ɴ𝐆ᴀ ᴋ𝐑𝐊ᴇ ɴ𝐀ɴ𝐆ᴀ 𓍼🌶𓍼 ִֶָ𓂃 ࣪˖ ִֶָ 𝐂ʜᴀ𝐋𝐋 𝐓ᴜ 𝐋ᴇ𝐆ᴀ 𝙎𝙄𝙉 𝙂𝙊𝘿 ᴩᴀ𝐍ɢ𝐀 .ᐟ   {{ ////𝙉𝘼𝙈𝙀////// }}  𝐓ᴇʀ𝐈 𝐁ᴇʜ𝐀𝐍 𝐊ᴏ 𝐂𝐇ᴏᴅ𝐔ɴ𝐆ᴀ ᴋ𝐑𝐊ᴇ ɴ𝐀ɴ𝐆ᴀ 𓍼🌶𓍼🖤ִֶָ𓂃 ࣪˖ ִֶָ 𝐂ʜᴀ𝐋𝐋 𝐓ᴜ 𝐋ᴇ𝐆ᴀ 𝙎𝙄𝙉 𝙂𝙊𝘿 ᴩᴀ𝐍ɢ𝐀 .ᐟ   {{ ////𝙉𝘼𝙈𝙀////// }}  𝐓ᴇʀ𝐈 𝐁ᴇʜ𝐀𝐍 𝐊ᴏ 𝐂𝐇ᴏᴅ𝐔ɴ𝐆ᴀ ᴋ𝐑𝐊ᴇ ɴ𝐀ɴ𝐆ᴀ 𓍼🌶𓍼",
    "𝐍𝐀𝐃𝐈 𝐊𝐈𝐍𝐀𝐑𝐄 𝐒𝐀𝐍𝐏🐍 𝐇𝐀𝐈 ☬         ☽         💦       ♆       ☾       💋      ☫☬      ✢      ♧       ⇍⇍⇍⇍🖤💙      💥 ★  {{ ////𝙉𝘼𝙈𝙀////// }}  𝐊𝐈 𝐌𝐀 𝐂𝐇𝐎𝐃𝐍𝐀 𝐏𝐀𝐀𝐏 𝐇𝐀𝐈🤩💋💦☬         ☽         💦       ♆       ☾       💋      ☫☬      ✢      ♧       ⇍⇍⇍⇍🖤💙      💥 ★✯✯",
    "𝙉𝘼𝙈𝙀  Nᴀᴍᴇ Rᴀᴋʜɴᴇ Wᴀʟᴇ Kᴀɴᴊᴀʀ Kɪ Mᴀᴀ Kɪ Cʜᴜᴛ Cʜᴏᴅ Kᴇ Bᴀɴᴀ Dᴜɴɢᴀ Bᴀɴᴊᴀʀ︵‿︵‿୨♡୧‿︵‿︵🤩჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻჻𝙎𝙄𝙉 𝘿𝘼𝘿 𝙎𝙄𝙉 𝘿𝘼𝘿 𝙈𝘼𝙏 𝙆𝘼𝙍 𝙍𝘼𝙉𝘿𝙄𝙆𝙀 𝘽𝘼𝘾𝘾𝙃𝙀﹌﹌﹌﹌﹌﹌✨️",
    "~~~~~~~ {{ ////𝙉𝘼𝙈𝙀////// }}  की भंगी माँ रांड चुद के भाग गयी~~~~~~~ 𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙🦋~~~~~~ {{ ////𝙉𝘼𝙈𝙀////// }}  की भंगी माँ रांड चुद के भाग गयी~~~~~~~ 𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙𓆙🦋",
]


def apply_name(text: str, name: str) -> str:
    s = text.replace("𝙉𝘼𝙈𝙀", name).replace("BAKUGRAM", name)
    return truncate_utf16(s)


def rev_texts_for(name: str):
    out = []
    line = math_italic(f"{name} MENE SUNA TERI MA CHINAR BAR DANCER HAI?") + "🤍⚠️彡☆"
    sep = "彡" * 22
    big = "\n\n".join([f"{line}\n{sep}" for _ in range(12)])
    out.append(truncate_utf16(big))
    for t in DEFAULT_REV_TEXTS:
        out.append(apply_name(t, name))
    for t in STATE.get("custom_rev_texts", []):
        s = fancy(t.replace("{name}", name))
        out.append(truncate_utf16(s))
    return out


STATE = {
    "delay": 0.0,
    "custom_texts": [],
    "custom_rev_texts": [],
    "prefix": "x",
}
CHOP_HALT = {"flag": False}
STOP_REACTIONS = {"flag": False}
REACT_ALL = {"enabled": False, "emoji": "🤍"}
XSALL = {"enabled": False, "text": ""}
XIS = {"enabled": False, "msg": None, "caption": ""}
CHOPPED = {}
CHOP_ACTIVE = set()
_OWNER = {"client": None}

# Per-command stop flags and task tracking
STOP_CATEGORIES = ("rev", "chud", "swipe", "revf", "imgspam")
STOP_FLAGS = defaultdict(lambda: {"flag": False})
RUNNING = defaultdict(set)
CHOP_TASKS = set()
reaction_tasks = set()


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            STATE["delay"] = float(data.get("delay", 0.0))
            STATE["custom_texts"] = list(data.get("custom_texts", []))
            STATE["custom_rev_texts"] = list(data.get("custom_rev_texts", []))
            STATE["prefix"] = str(data.get("prefix", "x")) or "x"
        except Exception as e:
            print(fancy(f"[!] state load: {e}"))


def save_state():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(STATE, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(fancy(f"[!] state save: {e}"))


def chudai_pool():
    return DEFAULT_CHUDAI_TEXTS + STATE["custom_texts"]


# ============================================================
# RUNTIME
# ============================================================
userbots = []
BOT_IDS = set()
spam_records = defaultdict(list)
muted_users = set()
antispam_chats = set()
antispam_tracker = defaultdict(lambda: deque(maxlen=40))
pending_login = {}
bot_login_state = {}


# ============================================================
# HELPERS
# ============================================================
async def _delayed_delete(event, seconds: float):
    await asyncio.sleep(seconds)
    try:
        await event.delete()
    except Exception:
        pass


async def flash(event, text, timeout=15):
    try:
        await event.edit(text)
    except Exception:
        pass
    asyncio.create_task(_delayed_delete(event, timeout))


async def secure_reply(event, text, timeout=15):
    chat = event.chat_id
    try:
        await event.delete()
    except Exception:
        pass
    try:
        msg = await event.client.send_message(chat, text)
    except Exception as e:
        print(fancy(f"[!] secure_reply: {e}"))
        return
    asyncio.create_task(_delayed_delete(msg, timeout))


def persist_userbot(ub, uid: int):
    path = os.path.join(SESSIONS_DIR, f"ub_{uid}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(ub.session.save())


def add_userbot(ub, me):
    userbots.append(ub)
    BOT_IDS.add(me.id)
    persist_userbot(ub, me.id)


def save_owner_session(ub):
    path = os.path.join(SESSIONS_DIR, "owner.session")
    with open(path, "w", encoding="utf-8") as f:
        f.write(ub.session.save())


async def attach_owner(ub, owner_id):
    if _OWNER["client"] is not None:
        try:
            await _OWNER["client"].disconnect()
        except Exception:
            pass
    _OWNER["client"] = ub
    register_handlers(ub, owner_id)
    asyncio.create_task(ub.run_until_disconnected())


async def resolve_target(event, arg):
    reply = await event.get_reply_message()
    if reply and reply.sender:
        return reply.sender_id
    if arg:
        try:
            entity = await event.client.get_entity(arg.strip().lstrip("@"))
            return entity.id
        except Exception as e:
            print(fancy(f"[!] resolve: {e}"))
    return None


def _bot_tag(me):
    return getattr(me, "username", None) or getattr(me, "first_name", None) or "bot"


async def run_spam(event, target_msg, texts, label, category):
    if not userbots or not texts:
        return
    flag = STOP_FLAGS[category]
    flag["flag"] = False
    delay = STATE["delay"]
    chat = target_msg.chat_id
    reply_id = target_msg.id
    count = {"n": 0}

    async def worker(ub):
        tag = "bot"
        try:
            tag = _bot_tag(await ub.get_me())
        except Exception:
            pass
        i = 0
        n = len(texts)
        fails = 0
        while not flag["flag"]:
            text = texts[i % n]
            i += 1
            sent = False
            try:
                msg = await ub.send_message(chat, text, reply_to=reply_id)
                spam_records[chat].append((ub, msg.id))
                count["n"] += 1
                fails = 0
                sent = True
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 1)
                sent = True
            except Exception:
                fails += 1
                try:
                    msg = await ub.send_message(chat, text)
                    spam_records[chat].append((ub, msg.id))
                    count["n"] += 1
                    sent = True
                except FloodWaitError as e2:
                    await asyncio.sleep(e2.seconds + 1)
                    sent = True
                except Exception as e2:
                    if fails == 1 or fails % 20 == 0:
                        print(fancy(f"[!] {tag}: {type(e2).__name__} {str(e2)[:60]}"))
            if not sent and fails >= 5:
                await asyncio.sleep(min(fails * 2, 30))
            if delay > 0:
                await asyncio.sleep(delay)

    async def anim():
        while not flag["flag"]:
            try:
                await event.edit(fancy(f"🩷 {label} · {count['n']}"))
            except Exception:
                pass
            await asyncio.sleep(1.5)

    for ub in userbots:
        t = asyncio.create_task(worker(ub))
        RUNNING[category].add(t)
        t.add_done_callback(RUNNING[category].discard)
    asyncio.create_task(anim())


async def run_forward_spam(event, target_msg, label):
    """Two-hop forward — target → bot's Saved Messages → chat.
    Source becomes the bot's own id, not the original target."""
    if not userbots:
        return
    flag = STOP_FLAGS["revf"]
    flag["flag"] = False
    delay = STATE["delay"]
    chat = target_msg.chat_id
    count = {"n": 0}

    async def worker(ub):
        tag = "bot"
        try:
            tag = _bot_tag(await ub.get_me())
        except Exception:
            pass
        fails = 0
        while not flag["flag"]:
            stash = None
            try:
                stash = await ub.forward_messages("me", target_msg)
                if isinstance(stash, list):
                    stash = stash[0] if stash else None
                if stash is None:
                    fails += 1
                    await asyncio.sleep(min(fails, 10))
                    continue
                out = await ub.forward_messages(chat, stash)
                if isinstance(out, list):
                    out = out[0] if out else None
                if out is not None:
                    spam_records[chat].append((ub, out.id))
                    count["n"] += 1
                fails = 0
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 1)
            except Exception as e:
                fails += 1
                if fails == 1 or fails % 20 == 0:
                    print(fancy(f"[!] {tag} fwd: {type(e).__name__} {str(e)[:60]}"))
                if fails >= 3:
                    await asyncio.sleep(min(fails * 2, 30))
            finally:
                if stash is not None:
                    try:
                        await ub.delete_messages("me", stash.id)
                    except Exception:
                        pass
            if delay > 0:
                await asyncio.sleep(delay)

    async def anim():
        while not flag["flag"]:
            try:
                await event.edit(fancy(f"🩷 {label} · {count['n']}"))
            except Exception:
                pass
            await asyncio.sleep(1.5)

    for ub in userbots:
        t = asyncio.create_task(worker(ub))
        RUNNING["revf"].add(t)
        t.add_done_callback(RUNNING["revf"].discard)
    asyncio.create_task(anim())


async def chop_burst(uid: int, name: str, trigger_msg):
    if uid in CHOP_ACTIVE:
        return
    if not userbots:
        return
    CHOP_ACTIVE.add(uid)
    CHOP_HALT["flag"] = False
    try:
        delay = STATE["delay"]
        duration = random.uniform(4.0, 5.0)
        deadline = time.time() + duration
        pool = chudai_pool()
        texts = [fancy(t.replace("{name}", name)) for t in pool]
        if not texts:
            return

        async def worker(ub):
            i = 0
            n = len(texts)
            while time.time() < deadline and not CHOP_HALT["flag"]:
                if uid not in CHOPPED:
                    return
                try:
                    msg = await ub.send_message(
                        trigger_msg.chat_id, texts[i % n],
                        reply_to=trigger_msg.id,
                    )
                    spam_records[trigger_msg.chat_id].append((ub, msg.id))
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
                except Exception:
                    pass
                i += 1
                if delay > 0:
                    await asyncio.sleep(delay)

        await asyncio.gather(*[worker(ub) for ub in userbots])
    finally:
        CHOP_ACTIVE.discard(uid)


async def stop_category(event, category):
    STOP_FLAGS[category]["flag"] = True
    n = 0
    for t in list(RUNNING[category]):
        t.cancel()
        n += 1
    RUNNING[category].clear()
    await flash(event, fancy(f"🩷 {category} stopped · {n}"), timeout=10)


# ============================================================
# BANNER
# ============================================================
def banner():
    print()
    print("  " + fancy("═" * 46))
    print("  " + fancy("🤍  SINNERS Multi-Userbot  🩷"))
    print("  " + fancy("🩵  hoster  🩵"))
    print("  " + fancy("═" * 46))
    print()


# ============================================================
# HANDLERS
# ============================================================
def register_handlers(client, owner_id):

    async def cmd_ping(event, arg):
        t0 = time.perf_counter()
        try:
            await event.edit(fancy("🤍 Pong"))
        except Exception:
            return
        ms = int((time.perf_counter() - t0) * 1000)
        try:
            await event.edit(fancy(f"🤍 Pong 🩷 {ms}ms 🩵"))
        except Exception:
            pass
        asyncio.create_task(_delayed_delete(event, 15))

    async def cmd_delay(event, arg):
        if not arg:
            await flash(event, fancy(f"🩷 Delay: {STATE['delay']}s"))
            return
        try:
            val = float(arg)
        except Exception:
            await flash(event, fancy("🩵 Invalid value"))
            return
        val = max(0.0, min(60.0, val))
        STATE["delay"] = val
        save_state()
        await flash(event, fancy(f"🩷 Delay set: {val}s"))

    async def cmd_ruk(event, arg):
        # Master halt: stop every category and clear chop
        for cat in STOP_CATEGORIES:
            STOP_FLAGS[cat]["flag"] = True
            for t in list(RUNNING[cat]):
                t.cancel()
            RUNNING[cat].clear()
        CHOP_HALT["flag"] = True
        CHOPPED.clear()
        CHOP_ACTIVE.clear()
        for t in list(CHOP_TASKS):
            t.cancel()
        CHOP_TASKS.clear()
        XSALL["enabled"] = False
        XIS["enabled"] = False
        REACT_ALL["enabled"] = False
        for t in list(reaction_tasks):
            t.cancel()
        reaction_tasks.clear()
        await flash(event, fancy("🩷 Everything halted"), timeout=10)

    # -------- individual stop commands --------
    async def cmd_srev(event, arg):
        await stop_category(event, "rev")

    async def cmd_schud(event, arg):
        await stop_category(event, "chud")

    async def cmd_sswipe(event, arg):
        await stop_category(event, "swipe")

    async def cmd_srevf(event, arg):
        await stop_category(event, "revf")

    async def cmd_simgspam(event, arg):
        await stop_category(event, "imgspam")

    async def cmd_schop(event, arg):
        n = len(CHOPPED)
        CHOPPED.clear()
        CHOP_ACTIVE.clear()
        CHOP_HALT["flag"] = True
        c = 0
        for t in list(CHOP_TASKS):
            t.cancel()
            c += 1
        CHOP_TASKS.clear()
        await flash(
            event,
            fancy(f"🩷 Chop off · {n} cleared · {c} tasks"),
            timeout=10,
        )

    async def cmd_ssall(event, arg):
        XSALL["enabled"] = False
        await flash(event, fancy("🩵 Reply-all off"))

    async def cmd_sis(event, arg):
        XIS["enabled"] = False
        XIS["msg"] = None
        XIS["caption"] = ""
        await flash(event, fancy("🩵 Image off"))

    async def cmd_setp(event, arg):
        p = arg.strip()
        if not p:
            await flash(event, fancy(f"🩵 Prefix: {STATE['prefix']}"))
            return
        if len(p) > 5:
            await flash(event, fancy("🩵 Max 5 chars"))
            return
        if any(c.isspace() for c in p):
            await flash(event, fancy("🩵 No spaces"))
            return
        STATE["prefix"] = p
        save_state()
        await flash(event, fancy(f"🩷 Prefix set: {p}"))

    async def cmd_addtext(event, arg):
        if not arg:
            await flash(event, fancy("🩵 Usage: addtext <text>"))
            return
        text = arg
        if "{name}" not in text:
            text = text + " {name}"
        STATE["custom_texts"].append(text)
        save_state()
        await flash(event, fancy(f"🩷 Text added — pool {len(chudai_pool())}"))

    async def cmd_texts(event, arg):
        pool = chudai_pool()
        rows = [fancy(f"🤍 Text pool — {len(pool)}")]
        for i, t in enumerate(pool[:25], 1):
            rows.append(fancy(f"{i}. {t}"))
        if len(pool) > 25:
            rows.append(fancy(f"… {len(pool) - 25} more"))
        await flash(event, "\n".join(rows), timeout=40)

    async def cmd_resettexts(event, arg):
        STATE["custom_texts"].clear()
        save_state()
        await flash(event, fancy("🩷 Custom texts cleared"))

    async def cmd_xrevt(event, arg):
        if not arg:
            await flash(event, fancy("🩵 Usage: revt <text>"))
            return
        text = arg
        if "{name}" not in text:
            text = text + " {name}"
        STATE["custom_rev_texts"].append(text)
        save_state()
        await flash(
            event,
            fancy(f"🩷 Rev text added — {len(STATE['custom_rev_texts'])}"),
        )

    async def cmd_revtexts(event, arg):
        pool = STATE["custom_rev_texts"]
        if not pool:
            await flash(event, fancy("🤍 No custom rev texts"))
            return
        rows = [fancy(f"🤍 Rev pool — {len(pool)}")]
        for i, t in enumerate(pool[:25], 1):
            rows.append(fancy(f"{i}. {t}"))
        if len(pool) > 25:
            rows.append(fancy(f"… {len(pool) - 25} more"))
        await flash(event, "\n".join(rows), timeout=40)

    async def cmd_resetrevtexts(event, arg):
        STATE["custom_rev_texts"].clear()
        save_state()
        await flash(event, fancy("🩷 Custom rev texts cleared"))

    async def cmd_xchud(event, arg):
        reply = await event.get_reply_message()
        if not reply:
            await flash(event, fancy("🩵 Reply to a target message first"))
            return
        if not userbots:
            await flash(event, fancy("🩵 No userbots loaded — use xuser"))
            return
        name = arg
        if not name and reply.sender and getattr(reply.sender, "first_name", None):
            name = reply.sender.first_name
        name = (name or "target").strip()
        pool = chudai_pool()
        texts = [fancy(t.replace("{name}", name)) for t in pool]
        asyncio.create_task(run_spam(event, reply, texts, f"Spamming {name}", "chud"))

    async def cmd_xswipe(event, arg):
        reply = await event.get_reply_message()
        if not reply:
            await flash(event, fancy("🩵 Reply to a target message first"))
            return
        if not userbots:
            await flash(event, fancy("🩵 No userbots loaded — use xuser"))
            return
        if not arg:
            await flash(event, fancy("🩵 Usage: swipe <text>"))
            return
        asyncio.create_task(run_spam(event, reply, [fancy(arg)], "Swiping", "swipe"))

    async def cmd_xrev(event, arg):
        reply = await event.get_reply_message()
        if not reply:
            await flash(event, fancy("🩵 Reply to a target message first"))
            return
        if not userbots:
            await flash(event, fancy("🩵 No userbots loaded — use xuser"))
            return
        name = arg
        if not name and reply.sender and getattr(reply.sender, "first_name", None):
            name = reply.sender.first_name
        name = (name or "target").strip()
        texts = rev_texts_for(name)
        asyncio.create_task(run_spam(event, reply, texts, f"Revving {name}", "rev"))

    async def cmd_xrevf(event, arg):
        reply = await event.get_reply_message()
        if not reply:
            await flash(event, fancy("🩵 Reply to a target message first"))
            return
        if not userbots:
            await flash(event, fancy("🩵 No userbots loaded — use xuser"))
            return
        asyncio.create_task(run_forward_spam(event, reply, "Forwarding"))

    async def cmd_xchop(event, arg):
        reply = await event.get_reply_message()
        if not reply or not reply.sender:
            await flash(event, fancy("🩵 Reply to target with a name"))
            return
        uid = reply.sender_id
        if uid is None:
            await flash(event, fancy("🩵 Cannot resolve target id"))
            return
        if uid in CHOPPED:
            CHOPPED.pop(uid, None)
            CHOP_ACTIVE.discard(uid)
            await flash(event, fancy("🩷 Chop removed"))
            return
        name = arg
        if not name and getattr(reply.sender, "first_name", None):
            name = reply.sender.first_name
        name = (name or "target").strip()
        CHOPPED[uid] = name
        await flash(event, fancy(f"🩷 Chopped — {name}"), timeout=20)

    async def cmd_xsall(event, arg):
        if not arg:
            XSALL["enabled"] = not XSALL["enabled"]
            state = "on" if XSALL["enabled"] else "off"
            await flash(event, fancy(f"🩷 Reply-all {state}"))
            return
        XSALL["text"] = arg
        XSALL["enabled"] = True
        await flash(event, fancy("🩷 Reply-all armed"))

    async def cmd_xis(event, arg):
        reply = await event.get_reply_message()
        if not reply or not reply.media:
            await flash(event, fancy("🩵 Reply to an image"))
            return
        XIS["msg"] = reply
        XIS["caption"] = arg or ""
        XIS["enabled"] = True
        await flash(event, fancy("🩷 Image armed"))

    async def cmd_xistop(event, arg):
        XIS["enabled"] = False
        XIS["msg"] = None
        XIS["caption"] = ""
        await flash(event, fancy("🩵 Image off"))

    async def cmd_ximg(event, arg):
        reply = await event.get_reply_message()
        if not reply or not reply.media:
            await flash(event, fancy("🩵 Reply to an image"))
            return
        if not userbots:
            await flash(event, fancy("🩵 No userbots"))
            return
        target = reply
        cap = arg or None

        async def do():
            for ub in userbots:
                try:
                    await ub.send_file(target.chat_id, target,
                                       caption=cap, reply_to=target.id)
                except Exception as e:
                    print(fancy(f"[!] ximg: {e}"))

        asyncio.create_task(do())
        await flash(event, fancy("🩷 Image sent"))

    async def cmd_ximgspam(event, arg):
        reply = await event.get_reply_message()
        if not reply or not reply.media:
            await flash(event, fancy("🩵 Reply to an image"))
            return
        if not userbots:
            await flash(event, fancy("🩵 No userbots"))
            return
        flag = STOP_FLAGS["imgspam"]
        flag["flag"] = False
        target = reply
        delay = STATE["delay"]
        cap = arg or None
        count = {"n": 0}

        async def worker(ub):
            while not flag["flag"]:
                try:
                    msg = await ub.send_file(
                        target.chat_id, target,
                        caption=cap, reply_to=target.id,
                    )
                    spam_records[target.chat_id].append((ub, msg.id))
                    count["n"] += 1
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
                except Exception:
                    pass
                if delay > 0:
                    await asyncio.sleep(delay)

        for ub in userbots:
            t = asyncio.create_task(worker(ub))
            RUNNING["imgspam"].add(t)
            t.add_done_callback(RUNNING["imgspam"].discard)
        await flash(event, fancy("🩷 Image spam armed"), timeout=10)

    async def cmd_re(event, arg):
        emoji = arg.strip()
        if not emoji:
            await flash(event, fancy("🩵 Usage: re <emoji>"))
            return
        reply = await event.get_reply_message()
        peer = event.chat_id
        msg_id = reply.id if reply else event.id
        STOP_REACTIONS["flag"] = False

        async def do_react():
            for ub in userbots:
                if STOP_REACTIONS["flag"]:
                    return
                try:
                    await ub(SendReactionRequest(
                        peer=peer, msg_id=msg_id,
                        reaction=[ReactionEmoji(emoticon=emoji)],
                    ))
                except Exception as e:
                    print(fancy(f"[!] react: {e}"))
            try:
                await client(SendReactionRequest(
                    peer=peer, msg_id=msg_id,
                    reaction=[ReactionEmoji(emoticon=emoji)],
                ))
            except Exception as e:
                print(fancy(f"[!] owner react: {e}"))

        task = asyncio.create_task(do_react())
        reaction_tasks.add(task)
        task.add_done_callback(reaction_tasks.discard)
        await flash(event, fancy(f"🩷 {emoji}"), timeout=300)

    async def cmd_reall(event, arg):
        if arg:
            REACT_ALL["emoji"] = arg.strip()
            REACT_ALL["enabled"] = True
            await flash(event, fancy(f"🩷 React-all {REACT_ALL['emoji']}"))
        else:
            REACT_ALL["enabled"] = not REACT_ALL["enabled"]
            state = "on" if REACT_ALL["enabled"] else "off"
            await flash(event, fancy(f"🩷 React-all {state}"))

    async def cmd_restop(event, arg):
        REACT_ALL["enabled"] = False
        STOP_REACTIONS["flag"] = True
        n = 0
        for t in list(reaction_tasks):
            t.cancel()
            n += 1
        reaction_tasks.clear()
        await flash(event, fancy(f"🩵 Stopped {n} reactions"), timeout=10)

    async def cmd_del(event, arg):
        chat = event.chat_id
        records = spam_records.pop(chat, [])
        if not records:
            await flash(event, fancy("🤍 Nothing to delete"))
            return
        by_client = defaultdict(list)
        for cl, mid in records:
            by_client[id(cl)].append((cl, mid))

        async def purge():
            for pairs in by_client.values():
                cl = pairs[0][0]
                mids = [p[1] for p in pairs]
                try:
                    await cl.delete_messages(chat, mids)
                except Exception as e:
                    print(fancy(f"[!] delete: {e}"))

        asyncio.create_task(purge())
        await flash(event, fancy(f"🩷 Deleting {len(records)}"), timeout=10)

    async def cmd_anti(event, arg):
        chat = event.chat_id
        if chat in antispam_chats:
            antispam_chats.discard(chat)
            await flash(event, fancy("🩵 Antispam off"))
        else:
            antispam_chats.add(chat)
            await flash(event, fancy("🩷 Antispam on"))

    async def cmd_dbrk(event, arg):
        reply = await event.get_reply_message()
        if not reply or not reply.sender:
            await flash(event, fancy("🩵 Reply to target"))
            return
        uid = reply.sender_id
        muted_users.add(uid)

        async def mute():
            for ub in userbots:
                try:
                    await ub.edit_permissions(event.chat_id, uid,
                                              send_messages=False, send_media=False)
                except Exception:
                    pass
            try:
                await client.edit_permissions(event.chat_id, uid,
                                              send_messages=False, send_media=False)
            except Exception:
                pass

        asyncio.create_task(mute())
        await flash(event, fancy("🩷 Muted"))

    async def cmd_brk(event, arg):
        uid = await resolve_target(event, arg)
        if not uid:
            await flash(event, fancy("🤍 Reply or provide @username"))
            return
        muted_users.discard(uid)

        async def unmute():
            for ub in userbots:
                try:
                    await ub.edit_permissions(event.chat_id, uid,
                                              send_messages=True, send_media=True)
                except Exception:
                    pass
            try:
                await client.edit_permissions(event.chat_id, uid,
                                              send_messages=True, send_media=True)
            except Exception:
                pass

        asyncio.create_task(unmute())
        await flash(event, fancy("🩷 Unmuted"))

    async def cmd_ub(event, arg):
        uid = await resolve_target(event, arg)
        if not uid:
            await flash(event, fancy("🤍 Reply or provide @username"))
            return
        rights = ChatBannedRights(until_date=None, view_messages=False)

        async def unban():
            for ub in userbots:
                try:
                    await ub.edit_permissions(event.chat_id, uid, rights)
                except Exception:
                    pass
            try:
                await client.edit_permissions(event.chat_id, uid, rights)
            except Exception:
                pass

        asyncio.create_task(unban())
        await flash(event, fancy("🩷 Unbanned"))

    async def cmd_as(event, arg):
        if not userbots:
            await flash(event, fancy("🩵 No userbots loaded"))
            return

        async def add_all():
            added = 0
            failed = 0
            for ub in userbots:
                try:
                    me = await ub.get_me()
                except Exception:
                    failed += 1
                    continue
                try:
                    await client(InviteToChannelRequest(event.chat_id, [me]))
                    added += 1
                except Exception:
                    try:
                        await client(AddChatUserRequest(
                            event.chat_id, me.id, fwd_limit=100,
                        ))
                        added += 1
                    except Exception as e:
                        print(fancy(f"[!] add {me.id}: {e}"))
                        failed += 1
            try:
                await event.edit(fancy(f"🩷 Added {added} · Failed {failed}"))
            except Exception:
                pass
            asyncio.create_task(_delayed_delete(event, 20))

        asyncio.create_task(add_all())
        await flash(event, fancy(f"🩷 Inviting {len(userbots)} userbots"))

    async def cmd_xuser(event, arg):
        pending_login[event.chat_id] = {"stage": "await_cred"}
        await event.edit(fancy("🩵 Send string session or phone number"))

    async def cmd_help(event, arg):
        p = STATE["prefix"]
        rows = [
            fancy(f"🤍 Prefix · {p}"),
            fancy("🩷 Core"),
            fancy(f"{p}ping · {p}delay · {p}ruk · {p}setp · {p}help"),
            fancy("🩵 Spam"),
            fancy(f"{p}chud <name>"),
            fancy(f"{p}swipe <text>"),
            fancy(f"{p}rev <name>"),
            fancy(f"{p}revf (reply)"),
            fancy(f"{p}chop <name>"),
            fancy(f"{p}sall <text>"),
            fancy("🤍 Text pool"),
            fancy(f"{p}addtext · {p}texts · {p}resettexts"),
            fancy(f"{p}revt · {p}revtexts · {p}resetrevtexts"),
            fancy("🩷 Images"),
            fancy(f"{p}is · {p}istop · {p}img · {p}imgspam"),
            fancy("🩵 Reactions"),
            fancy(f"{p}re · {p}reall · {p}restop"),
            fancy("🤍 Moderation"),
            fancy(f"{p}dbrk · {p}brk · {p}ub · {p}anti · {p}del"),
            fancy("🩷 System"),
            fancy(f"{p}as · {p}user"),
            fancy("🩵 Stop"),
            fancy("srev · schud · sswipe · srevf"),
            fancy("simgspam · schop · ssall · sis"),
        ]
        await flash(event, "\n".join(rows), timeout=60)

    HANDLERS = {
        "ping": cmd_ping,
        "delay": cmd_delay,
        "ruk": cmd_ruk,
        "setp": cmd_setp,
        "addtext": cmd_addtext,
        "texts": cmd_texts,
        "resettexts": cmd_resettexts,
        "revt": cmd_xrevt,
        "revtexts": cmd_revtexts,
        "resetrevtexts": cmd_resetrevtexts,
        "chud": cmd_xchud,
        "chudai": cmd_xchud,
        "swipe": cmd_xswipe,
        "rev": cmd_xrev,
        "revf": cmd_xrevf,
        "chop": cmd_xchop,
        "sall": cmd_xsall,
        "is": cmd_xis,
        "istop": cmd_xistop,
        "img": cmd_ximg,
        "imgspam": cmd_ximgspam,
        "re": cmd_re,
        "reall": cmd_reall,
        "restop": cmd_restop,
        "del": cmd_del,
        "anti": cmd_anti,
        "dbrk": cmd_dbrk,
        "brk": cmd_brk,
        "ub": cmd_ub,
        "as": cmd_as,
        "user": cmd_xuser,
        "help": cmd_help,
    }

    STOP_HANDLERS = {
        "rev": cmd_srev,
        "chud": cmd_schud,
        "chudai": cmd_schud,
        "swipe": cmd_sswipe,
        "revf": cmd_srevf,
        "imgspam": cmd_simgspam,
        "chop": cmd_schop,
        "sall": cmd_ssall,
        "is": cmd_sis,
    }

    async def handle_login(event, text):
        stage = pending_login[event.chat_id]["stage"]

        if stage == "await_cred":
            if re.match(r"^\+\d{6,15}$", text):
                ph = TelegramClient(StringSession(), API_ID, API_HASH)
                try:
                    await ph.connect()
                    await ph.send_code_request(text)
                    pending_login[event.chat_id] = {
                        "stage": "await_code", "phone": text, "client": ph,
                    }
                    await secure_reply(event, fancy("🩷 OTP sent — enter code"), timeout=60)
                except Exception as e:
                    await secure_reply(event, fancy(f"🩵 Error: {e}"))
                    pending_login.pop(event.chat_id, None)
                return
            try:
                ub = TelegramClient(StringSession(text), API_ID, API_HASH)
                await ub.connect()
                if not await ub.is_user_authorized():
                    raise Exception("not authorized")
                me = await ub.get_me()
                add_userbot(ub, me)
                uname = me.username or str(me.id)
                pending_login.pop(event.chat_id, None)
                await secure_reply(event, fancy(f"🩷 Added @{uname}"))
            except Exception as e:
                await secure_reply(event, fancy(f"🩵 Login failed: {e}"))
                pending_login.pop(event.chat_id, None)
            return

        if stage == "await_code":
            ph = pending_login[event.chat_id]["client"]
            phone = pending_login[event.chat_id]["phone"]
            try:
                await ph.sign_in(phone, text)
                me = await ph.get_me()
                add_userbot(ph, me)
                uname = me.username or str(me.id)
                pending_login.pop(event.chat_id, None)
                await secure_reply(event, fancy(f"🩷 Added @{uname}"))
            except SessionPasswordNeededError:
                pending_login[event.chat_id]["stage"] = "await_2fa"
                await secure_reply(event, fancy("🩷 2FA password required"), timeout=60)
            except Exception as e:
                await secure_reply(event, fancy(f"🩵 Error: {e}"))
                pending_login.pop(event.chat_id, None)
            return

        if stage == "await_2fa":
            ph = pending_login[event.chat_id]["client"]
            try:
                await ph.sign_in(password=text)
                me = await ph.get_me()
                add_userbot(ph, me)
                uname = me.username or str(me.id)
                pending_login.pop(event.chat_id, None)
                await secure_reply(event, fancy(f"🩷 Added @{uname}"))
            except Exception as e:
                await secure_reply(event, fancy(f"🩵 Error: {e}"))
                pending_login.pop(event.chat_id, None)

    @client.on(events.NewMessage(outgoing=True))
    async def dispatcher(event):
        text = (event.text or "").strip()
        if not text:
            return
        prefix = STATE["prefix"]
        is_cmd = text.lower().startswith(prefix.lower())
        cmd = ""
        arg = ""
        if is_cmd:
            body = text[len(prefix):].strip()
            parts = body.split(None, 1)
            if parts:
                cmd = parts[0].lower()
                arg = parts[1].strip() if len(parts) > 1 else ""

        # Login pending — allow commands to escape, block everything else
        if event.chat_id in pending_login:
            is_main = is_cmd and cmd in HANDLERS and cmd != "user"
            is_stop = (
                text.startswith("s") and len(text) > 1
                and text[1:].split(None, 1)[0].lower() in STOP_HANDLERS
            )
            if not (is_main or is_stop):
                await handle_login(event, text)
                return
            pending_login.pop(event.chat_id, None)

        # Main command takes priority
        if is_cmd:
            fn = HANDLERS.get(cmd)
            if fn:
                await fn(event, arg)
                return

        # Stop command: literal s-prefix, only fires if not a main command
        if text.startswith("s") and len(text) > 1:
            rest = text[1:]
            parts = rest.split(None, 1)
            sw = parts[0].lower()
            sarg = parts[1].strip() if len(parts) > 1 else ""
            if sw in STOP_HANDLERS:
                await STOP_HANDLERS[sw](event, sarg)

    @client.on(events.NewMessage(incoming=True))
    async def watchers(event):
        if event.sender_id in muted_users:
            try:
                await event.delete()
            except Exception:
                pass
            return
        if event.sender_id in BOT_IDS:
            return

        if REACT_ALL["enabled"]:
            peer = event.chat_id
            mid = event.id
            emoji = REACT_ALL["emoji"]

            async def react_all():
                for ub in userbots:
                    if STOP_REACTIONS["flag"]:
                        return
                    try:
                        await ub(SendReactionRequest(
                            peer=peer, msg_id=mid,
                            reaction=[ReactionEmoji(emoticon=emoji)],
                        ))
                    except Exception:
                        pass

            asyncio.create_task(react_all())

        if XSALL["enabled"] and XSALL["text"]:
            chat = event.chat_id
            mid = event.id
            body = fancy(XSALL["text"])

            async def do_xsall():
                for ub in userbots:
                    try:
                        await ub.send_message(chat, body, reply_to=mid)
                    except Exception:
                        pass

            asyncio.create_task(do_xsall())

        if XIS["enabled"] and XIS["msg"] is not None:
            stored = XIS["msg"]
            cap = XIS["caption"] or None
            chat = event.chat_id
            mid = event.id

            async def do_xis():
                for ub in userbots:
                    try:
                        await ub.send_file(chat, stored, caption=cap, reply_to=mid)
                    except Exception:
                        pass

            asyncio.create_task(do_xis())

        sid = event.sender_id
        if sid is not None and sid in CHOPPED:
            name = CHOPPED[sid]
            if sid not in CHOP_ACTIVE:
                t = asyncio.create_task(chop_burst(sid, name, event.message))
                CHOP_TASKS.add(t)
                t.add_done_callback(CHOP_TASKS.discard)

        if event.chat_id in antispam_chats and event.sender_id != owner_id:
            if event.is_private:
                return
            bucket = antispam_tracker[event.sender_id]
            bucket.append(time.time())
            cutoff = time.time() - 10
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) > 7:
                rights = ChatBannedRights(
                    until_date=None,
                    view_messages=False,
                    send_messages=False,
                    send_media=False,
                    send_stickers=False,
                    send_gifs=False,
                    send_games=False,
                    send_inline=False,
                    embed_links=False,
                )
                chat = event.chat_id
                uid = event.sender_id
                bucket.clear()

                async def do_ban():
                    try:
                        await client.edit_permissions(chat, uid, rights)
                        notice = await client.send_message(
                            chat, fancy("🩵 Spammer banned"),
                        )
                        asyncio.create_task(_delayed_delete(notice, 10))
                    except Exception as e:
                        print(fancy(f"[!] ban: {e}"))

                asyncio.create_task(do_ban())


# ============================================================
# BOT FLOW
# ============================================================
async def bot_handle_login(event, text):
    uid = event.sender_id
    state = bot_login_state.get(uid)
    if not state:
        return
    stage = state["stage"]

    if stage == "await_cred":
        if re.match(r"^\+\d{6,15}$", text):
            ph = TelegramClient(StringSession(), API_ID, API_HASH)
            try:
                await ph.connect()
                await ph.send_code_request(text)
                bot_login_state[uid] = {
                    "stage": "await_code", "phone": text, "client": ph,
                }
                await event.respond(fancy("🩷 OTP sent — enter code"))
            except Exception as e:
                await event.respond(fancy(f"🩵 Error: {e}"))
                bot_login_state.pop(uid, None)
            return
        try:
            ub = TelegramClient(StringSession(text), API_ID, API_HASH)
            await ub.connect()
            if not await ub.is_user_authorized():
                raise Exception("not authorized")
            me = await ub.get_me()
            save_owner_session(ub)
            bot_login_state.pop(uid, None)
            await event.respond(fancy(f"🩷 Hosted @{me.username or me.id}"))
            await attach_owner(ub, me.id)
        except Exception as e:
            await event.respond(fancy(f"🩵 Login failed: {e}"))
            bot_login_state.pop(uid, None)
        return

    if stage == "await_code":
        ph = state["client"]
        phone = state["phone"]
        try:
            await ph.sign_in(phone, text)
            me = await ph.get_me()
            save_owner_session(ph)
            bot_login_state.pop(uid, None)
            await event.respond(fancy(f"🩷 Hosted @{me.username or me.id}"))
            await attach_owner(ph, me.id)
        except SessionPasswordNeededError:
            bot_login_state[uid]["stage"] = "await_2fa"
            await event.respond(fancy("🩷 2FA password required"))
        except Exception as e:
            await event.respond(fancy(f"🩵 Error: {e}"))
            bot_login_state.pop(uid, None)
        return

    if stage == "await_2fa":
        ph = state["client"]
        try:
            await ph.sign_in(password=text)
            me = await ph.get_me()
            save_owner_session(ph)
            bot_login_state.pop(uid, None)
            await event.respond(fancy(f"🩷 Hosted @{me.username or me.id}"))
            await attach_owner(ph, me.id)
        except Exception as e:
            await event.respond(fancy(f"🩵 Error: {e}"))
            bot_login_state.pop(uid, None)


def setup_bot_handlers(bot):

    @bot.on(events.NewMessage(pattern=r"^/start"))
    async def on_start(event):
        buttons = [
            [Button.url("𝑂𝑊𝑁𝐸𝑅", f"https://t.me/{OWNER_USERNAME}")],
            [Button.inline("♡ 𝐻𝑂𝑆𝑇 𝑌𝑂𝑈𝑅 𝐵𝑂𝑇", b"host")],
            [Button.inline("✫ 𝐺𝑈𝐼𝐷𝐸", b"guide")],
        ]
        await event.reply(
            fancy("🤍 SINNERS Multi-Userbot\n🩷 Choose an option"),
            buttons=buttons,
        )

    @bot.on(events.CallbackQuery)
    async def on_cb(event):
        data = event.data
        uid = event.sender_id
        if data == b"host":
            await event.answer("Starting login...")
            bot_login_state[uid] = {"stage": "await_cred"}
            try:
                await event.edit(fancy("🩵 Send string session or phone number"))
            except Exception:
                await event.respond(fancy("🩵 Send string session or phone number"))
        elif data == b"guide":
            await event.answer()
            await event.respond(fancy(GUIDE_TEXT))

    @bot.on(events.NewMessage())
    async def on_msg(event):
        if not event.text:
            return
        if event.text.startswith("/"):
            return
        uid = event.sender_id
        if uid not in bot_login_state:
            return
        await bot_handle_login(event, event.text)


# ============================================================
# MAIN
# ============================================================
async def main():
    banner()
    if API_ID == 0 or not API_HASH or not BOT_TOKEN:
        print(fancy("[!] Set API_ID, API_HASH, BOT_TOKEN"))
        return

    load_state()
    print(fancy(
        f"[+] Delay {STATE['delay']}s · prefix {STATE['prefix']} · "
        f"custom texts {len(STATE['custom_texts'])} · "
        f"custom rev {len(STATE['custom_rev_texts'])}"
    ))

    session_path = os.path.join(SESSIONS_DIR, "owner.session")
    if os.path.exists(session_path):
        try:
            with open(session_path, "r", encoding="utf-8") as f:
                saved = f.read().strip()
            oc = TelegramClient(StringSession(saved), API_ID, API_HASH)
            await oc.connect()
            if await oc.is_user_authorized():
                me = await oc.get_me()
                print(fancy(f"[+] Owner restored: {me.first_name}"))
                _OWNER["client"] = oc
                register_handlers(oc, me.id)
                asyncio.create_task(oc.run_until_disconnected())
            else:
                await oc.disconnect()
        except Exception as e:
            print(fancy(f"[!] owner restore: {e}"))

    for fn in sorted(os.listdir(SESSIONS_DIR)):
        if fn.startswith(("owner", "bot")) or not fn.endswith(".txt"):
            continue
        path = os.path.join(SESSIONS_DIR, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                s = f.read().strip()
            ub = TelegramClient(StringSession(s), API_ID, API_HASH)
            await ub.connect()
            if await ub.is_user_authorized():
                userbots.append(ub)
                u = await ub.get_me()
                BOT_IDS.add(u.id)
                print(fancy(f"[+] Restored @{u.username or u.id}"))
        except Exception as e:
            print(fancy(f"[!] restore {fn}: {e}"))

    bot = TelegramClient(BOT_SESSION, API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    me_bot = await bot.get_me()
    print(fancy(f"[+] Control bot online: @{me_bot.username}"))

    setup_bot_handlers(bot)

    print(fancy(f"[+] {len(userbots)} userbots armed — sky open"))
    await bot.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())