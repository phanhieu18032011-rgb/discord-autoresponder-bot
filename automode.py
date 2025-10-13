# automode.py
# Anti-spam & banned-words + auto warn -> mute after 3 warns (10 minutes)

import asyncio
import discord

BANNED_WORDS = ["chửi","spam","ngu","lồn","đm"]  # chỉnh tuỳ bạn
SPAM_LIMIT = 5       # messages
TIME_FRAME = 5       # seconds
WARN_LIMIT = 3
MUTE_SECONDS = 600   # 10 minutes

user_msgs = {}   # user_id -> list[timestamps]
user_warns = {}  # user_id -> warn_count

async def check_anti_spam(message: discord.Message):
    uid = message.author.id
    now = message.created_at.timestamp()
    if uid not in user_msgs:
        user_msgs[uid] = []
    user_msgs[uid].append(now)
    # drop older
    user_msgs[uid] = [t for t in user_msgs[uid] if now - t < TIME_FRAME]
    if len(user_msgs[uid]) >= SPAM_LIMIT:
        try:
            await message.delete()
        except:
            pass
        await warn_user(message, reason="Spam quá nhanh")

async def check_banned_words(message: discord.Message):
    txt = message.content.lower()
    for w in BANNED_WORDS:
        if w in txt:
            try:
                await message.delete()
            except:
                pass
            await warn_user(message, reason=f"dùng từ cấm '{w}'")
            break

async def warn_user(message: discord.Message, reason: str):
    uid = message.author.id
    user_warns[uid] = user_warns.get(uid, 0) + 1
    count = user_warns[uid]
    try:
        await message.channel.send(f"{message.author.mention} ⚠️ Vi phạm ({count}/{WARN_LIMIT}): {reason}", delete_after=6)
    except:
        pass
    if count >= WARN_LIMIT:
        # mute
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
            # schedule unmute
            async def unmute_later(member, r, delay):
                await asyncio.sleep(delay)
                try:
                    await member.remove_roles(r)
                    user_warns[member.id] = 0
                except:
                    pass
            asyncio.create_task(unmute_later(message.author, role, MUTE_SECONDS))
        except Exception as e:
            print("Automode mute error:", e)

async def handle_auto_mode(message: discord.Message):
    if message.author.bot:
        return
    await check_anti_spam(message)
    await check_banned_words(message)
