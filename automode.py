# automode.py
# Anti-spam & banned words + auto warn -> mute after 3 warns (10 minutes)
import asyncio
import discord

# config (tweakable)
BANNED_WORDS = ["chửi", "spam", "ngu", "đm", "lồn"]  # edit as needed
SPAM_LIMIT = 5       # messages
TIME_FRAME = 5       # seconds window
WARN_LIMIT = 3
MUTE_SECONDS = 600   # 10 minutes

# in-memory storages
_user_msgs = {}   # user_id -> [timestamps]
_user_warns = {}  # user_id -> warn_count

async def _warn_user(message: discord.Message, reason: str):
    uid = message.author.id
    _user_warns[uid] = _user_warns.get(uid, 0) + 1
    count = _user_warns[uid]
    try:
        await message.channel.send(f"{message.author.mention} ⚠️ Vi phạm ({count}/{WARN_LIMIT}): {reason}", delete_after=6)
    except:
        pass
    if count >= WARN_LIMIT:
        try:
            guild = message.guild
            role = discord.utils.get(guild.roles, name="Muted")
            if not role:
                role = await guild.create_role(name="Muted")
                for ch in guild.channels:
                    try:
                        if isinstance(ch, discord.TextChannel):
                            await ch.set_permissions(role, send_messages=False)
                    except:
                        pass
            await message.author.add_roles(role)
            await message.channel.send(f"🔇 {message.author.mention} đã bị mute {MUTE_SECONDS//60} phút.")
            async def _unmute_later(member, r, delay):
                await asyncio.sleep(delay)
                try:
                    await member.remove_roles(r)
                    _user_warns[member.id] = 0
                except:
                    pass
            asyncio.create_task(_unmute_later(message.author, role, MUTE_SECONDS))
        except Exception as e:
            print("automode mute error:", e)

async def _check_spam(message: discord.Message):
    uid = message.author.id
    now = message.created_at.timestamp()
    if uid not in _user_msgs:
        _user_msgs[uid] = []
    _user_msgs[uid].append(now)
    # keep only last TIME_FRAME seconds
    _user_msgs[uid] = [t for t in _user_msgs[uid] if now - t < TIME_FRAME]
    if len(_user_msgs[uid]) >= SPAM_LIMIT:
        try:
            await message.delete()
        except:
            pass
        await _warn_user(message, "Spam quá nhanh")

async def _check_banned_words(message: discord.Message):
    txt = message.content.lower()
    for w in BANNED_WORDS:
        if w in txt:
            try:
                await message.delete()
            except:
                pass
            await _warn_user(message, f"dùng từ cấm '{w}'")
            break

async def handle_auto_mode(message: discord.Message):
    if message.author.bot:
        return
    # quick checks
    try:
        await _check_spam(message)
    except Exception as e:
        print("automode spam check error:", e)
    try:
        await _check_banned_words(message)
    except Exception as e:
        print("automode banned words error:", e)
