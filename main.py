# main.py
# Full-feature single-file bot for Render/GitHub
# - Prefix "!" and slash "/"
# - Reads token from DISCORD_TOKEN env var (use Render Secrets)
# - Keep-alive via Flask for Render
# - Autoresponder, automode (basic), giveaway, masssend, uplevel/level
# - 100 admin placeholder commands and 50 fun placeholder commands (safe)
# - No persistent storage (RAM only)

import os
import asyncio
import random
import threading
from typing import Optional, Dict, Set, List
from flask import Flask

import discord
from discord.ext import commands
from discord import app_commands

# -------------------------
# CONFIG
# -------------------------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise SystemExit("Please set TOKEN environment variable (Render/GitHub secret).")

PREFIX = "!"
PORT = int(os.getenv("PORT", 10000))
MUTED_ROLE_NAME = "Muted"

# automode settings (basic)
BANNED_WORDS = ["discord.gg", "invite", "spam", "đm", "chửi"]
SPAM_WINDOW = 5       # seconds window
SPAM_COUNT = 5        # messages inside window => considered spam
WARN_LIMIT = 3
MUTE_SECONDS = 600    # 10 minutes

# -------------------------
# KEEP-ALIVE (Flask)
# -------------------------
app = Flask("keepalive")

@app.route("/")
def home():
    return "✅ Bot is alive"

def run_web():
    app.run(host="0.0.0.0", port=PORT)

threading.Thread(target=run_web, daemon=True).start()

# -------------------------
# BOT SETUP
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

def prefix_callable(bot, message):
    return PREFIX

bot = commands.Bot(command_prefix=prefix_callable, intents=intents)
tree = bot.tree

# -------------------------
# IN-MEMORY STORAGE (RAM)
# -------------------------
AUTORESPONDERS: Dict[str, str] = {}
LEVELS: Dict[int, int] = {}
USER_XP: Dict[int, int] = {}
WARNS: Dict[int, int] = {}
LOG_CHANNEL: Dict[int, int] = {}
WELCOME_MSG: Dict[int, str] = {}
GOODBYE_MSG: Dict[int, str] = {}
DISABLED_CMDS: Dict[int, Set[str]] = {}

# automode runtime
_user_msgs: Dict[int, List[float]] = {}
_user_warns: Dict[int, int] = {}

# -------------------------
# HELPERS
# -------------------------
def is_admin_inter(interaction: discord.Interaction) -> bool:
    try:
        return interaction.user.guild_permissions.administrator
    except Exception:
        return False

def is_admin_ctx(ctx: commands.Context) -> bool:
    try:
        return ctx.author.guild_permissions.administrator
    except Exception:
        return False

async def ensure_muted_role(guild: discord.Guild) -> Optional[discord.Role]:
    role = discord.utils.get(guild.roles, name=MUTED_ROLE_NAME)
    if role:
        return role
    try:
        role = await guild.create_role(name=MUTED_ROLE_NAME, reason="Create muted role")
        for ch in guild.channels:
            try:
                if isinstance(ch, discord.TextChannel):
                    await ch.set_permissions(role, send_messages=False, add_reactions=False)
                elif isinstance(ch, discord.VoiceChannel):
                    await ch.set_permissions(role, speak=False)
            except Exception:
                pass
        return role
    except Exception as e:
        print("Failed create muted role:", e)
        return None

async def send_log(guild: discord.Guild, text: str):
    cid = LOG_CHANNEL.get(guild.id)
    if cid:
        ch = guild.get_channel(cid)
        if ch:
            try:
                await ch.send(text)
            except Exception:
                pass

# -------------------------
# AUTOMODE (basic banned words + spam)
# -------------------------
async def _warn_and_maybe_mute(message: discord.Message, reason: str):
    uid = message.author.id
    _user_warns[uid] = _user_warns.get(uid, 0) + 1
    cnt = _user_warns[uid]
    try:
        await message.channel.send(f"{message.author.mention} ⚠️ Vi phạm ({cnt}/{WARN_LIMIT}): {reason}", delete_after=6)
    except Exception:
        pass
    if cnt >= WARN_LIMIT:
        try:
            guild = message.guild
            role = await ensure_muted_role(guild)
            if role:
                await message.author.add_roles(role)
                await message.channel.send(f"🔇 {message.author.mention} đã bị mute {MUTE_SECONDS//60} phút.")
                async def _unmute_later(member, r, delay):
                    await asyncio.sleep(delay)
                    try:
                        await member.remove_roles(r)
                        _user_warns[member.id] = 0
                    except Exception:
                        pass
                asyncio.create_task(_unmute_later(message.author, role, MUTE_SECONDS))
        except Exception as e:
            print("Automode mute error:", e)

async def handle_auto_mode(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    txt = message.content.lower()
    for w in BANNED_WORDS:
        if w in txt:
            try:
                await message.delete()
            except Exception:
                pass
            await _warn_and_maybe_mute(message, f"dùng từ cấm '{w}'")
            return
    # spam detection
    now = message.created_at.timestamp()
    uid = message.author.id
    if uid not in _user_msgs:
        _user_msgs[uid] = []
    _user_msgs[uid].append(now)
    _user_msgs[uid] = [t for t in _user_msgs[uid] if now - t <= SPAM_WINDOW]
    if len(_user_msgs[uid]) >= SPAM_COUNT:
        try:
            await message.delete()
        except Exception:
            pass
        await _warn_and_maybe_mute(message, "Spam quá nhanh")
        _user_msgs[uid] = []

# -------------------------
# EVENTS
# -------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot ready: {bot.user} (ID: {bot.user.id})")
    try:
        synced = await tree.sync()
        print(f"🔁 Synced {len(synced)} slash commands.")
    except Exception as e:
        print("Slash sync error:", e)

@bot.event
async def on_member_join(member: discord.Member):
    gid = member.guild.id
    if gid in WELCOME_MSG:
        msg = WELCOME_MSG[gid].replace("{user}", member.mention).replace("{server}", member.guild.name)
        try:
            target = member.guild.system_channel or (member.guild.text_channels[0] if member.guild.text_channels else None)
            if target:
                await target.send(msg)
        except Exception:
            pass
    await send_log(member.guild, f"👋 Member joined: {member} ({member.id})")

@bot.event
async def on_member_remove(member: discord.Member):
    gid = member.guild.id
    if gid in GOODBYE_MSG:
        msg = GOODBYE_MSG[gid].replace("{user}", member.name).replace("{server}", member.guild.name)
        try:
            target = member.guild.system_channel or (member.guild.text_channels[0] if member.guild.text_channels else None)
            if target:
                await target.send(msg)
        except Exception:
            pass
    await send_log(member.guild, f"❌ Member left: {member} ({member.id})")

@bot.event
async def on_message(message: discord.Message):
    # automode
    try:
        await handle_auto_mode(message)
    except Exception as e:
        print("automode error:", e)

    # autoresponder matching
    if not message.author.bot:
        txt = message.content.lower()
        for trigger, resp in AUTORESPONDERS.items():
            if trigger in txt:
                try:
                    await message.channel.send(resp)
                except Exception:
                    pass
                break

    # leveling xp (simple)
    try:
        uid = message.author.id
        USER_XP[uid] = USER_XP.get(uid, 0) + random.randint(5, 12)
        new_lvl = USER_XP[uid] // 100
        if LEVELS.get(uid, 0) < new_lvl:
            LEVELS[uid] = new_lvl
            try:
                await message.channel.send(f"🎉 {message.author.mention} đã lên cấp {new_lvl}!")
            except Exception:
                pass
    except Exception:
        pass

    await bot.process_commands(message)

# -------------------------
# AUTORESPONDER (slash + prefix)
# -------------------------
@tree.command(name="add", description="Thêm autoresponder (trigger -> response)")
@app_commands.describe(trigger="Trigger substring", response="Bot response")
async def slash_add(interaction: discord.Interaction, trigger: str, response: str):
    AUTORESPONDERS[trigger.lower()] = response
    await interaction.response.send_message(f"✅ Added: `{trigger}` → {response}", ephemeral=True)

@tree.command(name="remove", description="Xóa autoresponder theo trigger")
@app_commands.describe(trigger="Trigger to remove")
async def slash_remove(interaction: discord.Interaction, trigger: str):
    if trigger.lower() in AUTORESPONDERS:
        del AUTORESPONDERS[trigger.lower()]
        await interaction.response.send_message(f"🗑️ Removed `{trigger}`", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Trigger not found.", ephemeral=True)

@tree.command(name="list", description="List all autoresponders")
async def slash_list(interaction: discord.Interaction):
    if not AUTORESPONDERS:
        await interaction.response.send_message("📭 No autoresponders.", ephemeral=True)
        return
    text = "\n".join([f"`{k}` → {v}" for k, v in AUTORESPONDERS.items()])
    if len(text) > 1800:
        fname = "autoresponders.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(text)
        await interaction.response.send_message("📄 List attached.", file=discord.File(fname), ephemeral=True)
    else:
        await interaction.response.send_message(f"📋 {text}", ephemeral=True)

@bot.command(name="add")
async def pfx_add(ctx: commands.Context, trigger: str, *, response: str):
    AUTORESPONDERS[trigger.lower()] = response
    await ctx.send(f"✅ Added: `{trigger}` → {response}")

@bot.command(name="remove")
async def pfx_remove(ctx: commands.Context, trigger: str):
    if trigger.lower() in AUTORESPONDERS:
        del AUTORESPONDERS[trigger.lower()]
        await ctx.send(f"🗑️ Removed `{trigger}`")
    else:
        await ctx.send("⚠️ Trigger not found.")

@bot.command(name="list")
async def pfx_list(ctx: commands.Context):
    if not AUTORESPONDERS:
        await ctx.send("📭 No autoresponders.")
        return
    text = "\n".join([f"`{k}` → {v}" for k, v in AUTORESPONDERS.items()])
    await ctx.send(f"📋 {text}")

# -------------------------
# Moderation & utility commands (real examples)
# -------------------------
@tree.command(name="ping", description="Bot latency")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency*1000)} ms", ephemeral=True)

@bot.command(name="ping")
async def ping_cmd(ctx: commands.Context):
    await ctx.send(f"Pong! {round(bot.latency*1000)} ms")

@tree.command(name="ban", description="Ban member (Admin)")
@app_commands.describe(member="Member to ban", reason="Reason optional")
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
    if not is_admin_inter(interaction):
        return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    await interaction.guild.ban(member, reason=reason)
    await interaction.response.send_message(f"🚫 Banned {member.mention}", ephemeral=False)
    await send_log(interaction.guild, f"[BAN] {member} by {interaction.user} — {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
    await ctx.guild.ban(member, reason=reason)
    await ctx.send(f"🚫 Banned {member.mention}")

@tree.command(name="kick", description="Kick member (Admin)")
@app_commands.describe(member="Member to kick", reason="Reason optional")
async def slash_kick(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
    if not is_admin_inter(interaction):
        return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    await interaction.guild.kick(member, reason=reason)
    await interaction.response.send_message(f"👢 Kicked {member.mention}", ephemeral=False)
    await send_log(interaction.guild, f"[KICK] {member} by {interaction.user}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
    await ctx.guild.kick(member, reason=reason)
    await ctx.send(f"👢 Kicked {member.mention}")

@tree.command(name="mute", description="Mute a member (Manage Roles required)")
@app_commands.describe(member="Member to mute")
async def slash_mute(interaction: discord.Interaction, member: discord.Member):
    perms = interaction.user.guild_permissions
    if not (perms.manage_roles or perms.administrator):
        return await interaction.response.send_message("⚠️ Manage Roles required.", ephemeral=True)
    role = await ensure_muted_role(interaction.guild)
    if not role:
        return await interaction.response.send_message("❌ Can't create muted role.", ephemeral=True)
    await member.add_roles(role)
    await interaction.response.send_message(f"🔇 Muted {member.mention}", ephemeral=False)
    await send_log(interaction.guild, f"[MUTE] {member} by {interaction.user}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx: commands.Context, member: discord.Member):
    role = await ensure_muted_role(ctx.guild)
    await member.add_roles(role)
    await ctx.send(f"🔇 Muted {member.mention}")

@tree.command(name="unmute", description="Unmute a member")
@app_commands.describe(member="Member to unmute")
async def slash_unmute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(interaction.guild.roles, name=MUTED_ROLE_NAME)
    if role and role in member.roles:
        await member.remove_roles(role)
        await interaction.response.send_message(f"🔊 Unmuted {member.mention}", ephemeral=False)
        await send_log(interaction.guild, f"[UNMUTE] {member} by {interaction.user}")
    else:
        await interaction.response.send_message("⚠️ Member not muted.", ephemeral=True)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx: commands.Context, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    if role and role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"🔊 Unmuted {member.mention}")
    else:
        await ctx.send("⚠️ Member not muted.")

@tree.command(name="clear", description="Clear messages (Admin)")
@app_commands.describe(limit="How many to delete (max 100)")
async def slash_clear(interaction: discord.Interaction, limit: int = 10):
    if not is_admin_inter(interaction):
        return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    limit = max(1, min(limit, 100))
    deleted = await interaction.channel.purge(limit=limit)
    await interaction.response.send_message(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)
    await send_log(interaction.guild, f"[CLEAR] {len(deleted)} messages by {interaction.user} in {interaction.channel}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx: commands.Context, limit: int = 10):
    limit = max(1, min(limit, 100))
    deleted = await ctx.channel.purge(limit=limit)
    await ctx.send(f"🧹 Deleted {len(deleted)} messages", delete_after=5)

# say / announce
@tree.command(name="say", description="Bot sends a message to channel (Admin)")
@app_commands.describe(channel="Channel", message="Message text")
async def slash_say(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not is_admin_inter(interaction):
        return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    await channel.send(message)
    await interaction.response.send_message("✅ Sent.", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx: commands.Context, channel: discord.TextChannel, *, message: str):
    await channel.send(message)
    await ctx.send("✅ Sent.", delete_after=5)

# masssend and giveaway already provided as examples earlier (prefix + slash)
# masssend prefix:
@bot.command()
@commands.has_permissions(administrator=True)
async def masssend(ctx: commands.Context, channel: discord.TextChannel, count: int, delay: int, *, message: str):
    count = max(1, min(5, count))
    delay = max(0, delay)
    await ctx.send(f"📤 Sending {count} messages to {channel.mention} ...")
    for _ in range(count):
        await channel.send(message)
        await asyncio.sleep(delay)
    await ctx.send("✅ Done.")

# giveaway prefix:
@bot.command()
async def giveaway_cmd(ctx: commands.Context, channel: discord.TextChannel, duration: int, winners: int, *, prize: str):
    await ctx.send(f"🎉 Giveaway starting in {channel.mention} for **{prize}**")
    asyncio.create_task(run_giveaway(channel, duration, winners, prize, ctx.author.display_name))

async def run_giveaway(channel: discord.TextChannel, duration: int, winners: int, prize: str, host_name: str):
    embed = discord.Embed(title="🎉 GIVEAWAY", description=f"**Prize:** {prize}\nReact with 🎉 to enter. Ends in {duration}s")
    embed.set_footer(text=f"Hosted by {host_name}")
    msg = await channel.send(embed=embed)
    await msg.add_reaction("🎉")
    await asyncio.sleep(duration)
    msg = await channel.fetch_message(msg.id)
    users = set()
    for reaction in msg.reactions:
        if reaction.emoji == "🎉":
            async for u in reaction.users():
                if not u.bot:
                    users.add(u)
    if not users:
        await channel.send("No participants.")
        return
    winners_list = random.sample(list(users), k=min(winners, len(users)))
    await channel.send(f"🏆 Winners: {', '.join(w.mention for w in winners_list)} — Prize: **{prize}**")

# uplevel / level commands (already above for prefix/slash)
@tree.command(name="uplevel", description="Add points/level to a member (Admin)")
@app_commands.describe(member="Member", amount="Amount to add")
async def slash_uplevel(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not is_admin_inter(interaction):
        return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    LEVELS[member.id] = LEVELS.get(member.id, 0) + amount
    await interaction.response.send_message(f"✅ {member.mention} +{amount}. Now: {LEVELS[member.id]}", ephemeral=False)

@bot.command()
@commands.has_permissions(administrator=True)
async def uplevel_cmd(ctx: commands.Context, member: discord.Member, amount: int):
    LEVELS[member.id] = LEVELS.get(member.id, 0) + amount
    await ctx.send(f"✅ {member.mention} +{amount}. Now {LEVELS[member.id]}")

# -------------------------
# DYNAMIC PLACEHOLDERS (SAFE)
# create admin_1..admin_100 and fun_1..fun_50 both as prefix and slash commands
# using function factories so closure captures name correctly
# -------------------------
def make_prefix_admin(name: str):
    async def cmd(ctx: commands.Context, *args):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("⚠️ Admin only.")
            return
        await ctx.send(f"🛠 Placeholder admin `{name}` executed by {ctx.author.mention}. Args: {args}")
    return cmd

def make_slash_admin(name: str):
    async def callback(interaction: discord.Interaction):
        if not is_admin_inter(interaction):
            return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
        await interaction.response.send_message(f"🛠 Placeholder admin `{name}` executed by {interaction.user.mention}", ephemeral=True)
    return callback

def make_prefix_fun(name: str):
    async def cmd(ctx: commands.Context, *args):
        await ctx.send(f"🎲 Placeholder fun `{name}` — args: {args}")
    return cmd

def make_slash_fun(name: str):
    async def callback(interaction: discord.Interaction):
        await interaction.response.send_message(f"🎲 Placeholder fun `{name}`", ephemeral=True)
    return callback

# register admin placeholders
for i in range(1, 101):
    n = f"admin{i}"
    bot.command(name=n)(make_prefix_admin(n))
    # register slash command via tree.add_command using Command object
    cmd = app_commands.Command(name=n, description=f"Placeholder admin command {n}", callback=make_slash_admin(n))
    try:
        tree.add_command(cmd)
    except Exception:
        # ignore if already added (reload)
        pass

# register fun placeholders
for i in range(1, 51):
    n = f"fun{i}"
    bot.command(name=n)(make_prefix_fun(n))
    cmd = app_commands.Command(name=n, description=f"Placeholder fun command {n}", callback=make_slash_fun(n))
    try:
        tree.add_command(cmd)
    except Exception:
        pass

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    bot.run(TOKEN)
