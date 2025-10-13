# main.py
# Full-feature bot: autoresponder + ~50 admin cmds + ~20 fun cmds + giveaway + uplevel/level + masssend
# Run on Render/GitHub. Put DISCORD_TOKEN into environment.

import os
import asyncio
import random
import threading
import time
from typing import Dict, List, Optional
from flask import Flask

import discord
from discord.ext import commands, tasks
from discord import app_commands

# automode module (anti-spam + banned words)
from automode import handle_auto_mode

# -------------------------
# Config
# -------------------------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise SystemExit("❌ Please set TOKEN env variable")

DEFAULT_PREFIX = "!"
PREFIX = DEFAULT_PREFIX  # temporary in-memory prefix
PORT = int(os.getenv("PORT", 10000))

# -------------------------
# Keep-alive (Flask) for Render web service
# -------------------------
app = Flask("keepalive")

@app.route("/")
def home():
    return "✅ Bot is alive!"

def run_web():
    app.run(host="0.0.0.0", port=PORT)

threading.Thread(target=run_web, daemon=True).start()

# -------------------------
# Bot setup
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

def get_prefix(bot, message):
    return PREFIX

bot = commands.Bot(command_prefix=get_prefix, intents=intents)
tree = bot.tree

# -------------------------
# In-memory storage (RAM)
# -------------------------
AUTORESPONDERS: Dict[str, str] = {}     # trigger -> response (lowercase key)
LEVELS: Dict[int, int] = {}             # user_id -> level
WARNS: Dict[int, int] = {}              # user_id -> warn count
WELCOME_MSG: Dict[int, str] = {}        # guild_id -> template
GOODBYE_MSG: Dict[int, str] = {}
LOG_CHANNEL: Dict[int, int] = {}        # guild_id -> channel_id
MUTER_ROLE_NAME = "Muted"

# -------------------------
# Helpers
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
    role = discord.utils.get(guild.roles, name=MUTER_ROLE_NAME)
    if role:
        return role
    try:
        role = await guild.create_role(name=MUTER_ROLE_NAME, reason="Create Muted role")
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
        print("Failed to create muted role:", e)
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
# Events
# -------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot ready: {bot.user} (id: {bot.user.id})")
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
            await member.guild.system_channel.send(msg)
        except Exception:
            pass
    await send_log(member.guild, f"👋 Member joined: {member} ({member.id})")

@bot.event
async def on_member_remove(member: discord.Member):
    gid = member.guild.id
    if gid in GOODBYE_MSG:
        msg = GOODBYE_MSG[gid].replace("{user}", member.name).replace("{server}", member.guild.name)
        try:
            await member.guild.system_channel.send(msg)
        except Exception:
            pass
    await send_log(member.guild, f"❌ Member left: {member} ({member.id})")

@bot.event
async def on_message(message: discord.Message):
    # automode (anti-spam, banned words)
    try:
        await handle_auto_mode(message)
    except Exception as e:
        print("automode error:", e)

    # autoresponders (in-memory)
    if not message.author.bot:
        txt = message.content.lower()
        for trigger, reply in AUTORESPONDERS.items():
            if trigger in txt:
                try:
                    await message.channel.send(reply)
                except Exception:
                    pass
                break

    await bot.process_commands(message)

# -------------------------
# AUTORESPONDER - Slash
# -------------------------
@tree.command(name="add", description="Add an autoresponder (trigger -> response)")
@app_commands.describe(trigger="Trigger text (substring)", response="Bot's response")
async def slash_add(interaction: discord.Interaction, trigger: str, response: str):
    AUTORESPONDERS[trigger.lower()] = response
    await interaction.response.send_message(f"✅ Added: `{trigger}` → {response}", ephemeral=True)

@tree.command(name="remove", description="Remove an autoresponder by trigger")
@app_commands.describe(trigger="Trigger text to remove")
async def slash_remove(interaction: discord.Interaction, trigger: str):
    if trigger.lower() in AUTORESPONDERS:
        del AUTORESPONDERS[trigger.lower()]
        await interaction.response.send_message(f"🗑️ Removed `{trigger}`", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Trigger not found.", ephemeral=True)

@tree.command(name="list", description="List autoresponders")
async def slash_list(interaction: discord.Interaction):
    if not AUTORESPONDERS:
        await interaction.response.send_message("📭 No autoresponders.", ephemeral=True)
        return
    text = "\n".join([f"`{k}` → {v}" for k, v in AUTORESPONDERS.items()])
    if len(text) > 1900:
        fname = "autoresponders.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(text)
        await interaction.response.send_message("📄 List attached.", file=discord.File(fname), ephemeral=True)
    else:
        await interaction.response.send_message(f"📋 {text}", ephemeral=True)

# -------------------------
# AUTORESPONDER - Prefix mirrors
# -------------------------
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
# MANY ADMIN COMMANDS (slash) — a large set (~50)
# For safety, dangerous ops are admin-only and some mass ops limited
# -------------------------
@tree.command(name="ban", description="Ban a user (Admin only)")
@app_commands.describe(member="Member to ban", reason="Reason (optional)")
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    await interaction.guild.ban(member, reason=reason)
    await interaction.response.send_message(f"🚫 Banned {member.mention}", ephemeral=False)
    await send_log(interaction.guild, f"[BAN] {member} by {interaction.user} — {reason}")

@tree.command(name="unban", description="Unban by user id (Admin only)")
@app_commands.describe(user_id="User ID to unban")
async def slash_unban(interaction: discord.Interaction, user_id: str):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    try:
        uid = int(''.join(ch for ch in user_id if ch.isdigit()))
        user = await bot.fetch_user(uid)
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ Unbanned {user}", ephemeral=False)
        await send_log(interaction.guild, f"[UNBAN] {user} by {interaction.user}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@tree.command(name="kick", description="Kick a user (Admin only)")
@app_commands.describe(member="Member to kick", reason="Reason optional")
async def slash_kick(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    await interaction.guild.kick(member, reason=reason)
    await interaction.response.send_message(f"👢 Kicked {member.mention}", ephemeral=False)
    await send_log(interaction.guild, f"[KICK] {member} by {interaction.user} — {reason}")

@tree.command(name="warn", description="Warn a member (Admin only)")
@app_commands.describe(member="Member", reason="Reason optional")
async def slash_warn(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    uid = member.id
    WARNS[uid] = WARNS.get(uid, 0) + 1
    await interaction.response.send_message(f"⚠️ {member.mention} warned ({WARNS[uid]}). Reason: {reason or 'None'}", ephemeral=False)
    await send_log(interaction.guild, f"[WARN] {member} by {interaction.user}: {reason}")

@tree.command(name="warns", description="Show warn count for a user")
@app_commands.describe(member="Member (omit for yourself)")
async def slash_warns(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    m = member or interaction.user
    await interaction.response.send_message(f"{m.mention} has {WARNS.get(m.id,0)} warn(s).", ephemeral=True)

@tree.command(name="resetwarns", description="Reset warns for a user (Admin only)")
@app_commands.describe(member="Member")
async def slash_resetwarns(interaction: discord.Interaction, member: discord.Member):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    WARNS[member.id] = 0
    await interaction.response.send_message(f"✅ Reset warns for {member.mention}", ephemeral=True)
    await send_log(interaction.guild, f"[RESETWARNS] {member} by {interaction.user}")

@tree.command(name="mute", description="Mute a member (Manage roles or admin)")
@app_commands.describe(member="Member", reason="Reason optional")
async def slash_mute(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
    perms = interaction.user.guild_permissions
    if not (perms.manage_roles or perms.administrator): return await interaction.response.send_message("⚠️ Manage Roles required.", ephemeral=True)
    role = await ensure_muted_role(interaction.guild)
    if not role: return await interaction.response.send_message("❌ Can't create muted role.", ephemeral=True)
    await member.add_roles(role, reason=reason)
    await interaction.response.send_message(f"🔇 Muted {member.mention}", ephemeral=False)
    await send_log(interaction.guild, f"[MUTE] {member} by {interaction.user} — {reason}")

@tree.command(name="unmute", description="Unmute a member")
@app_commands.describe(member="Member")
async def slash_unmute(interaction: discord.Interaction, member: discord.Member):
    perms = interaction.user.guild_permissions
    if not (perms.manage_roles or perms.administrator): return await interaction.response.send_message("⚠️ Manage Roles required.", ephemeral=True)
    role = discord.utils.get(interaction.guild.roles, name=MUTER_ROLE_NAME)
    if role and role in member.roles:
        await member.remove_roles(role)
        await interaction.response.send_message(f"🔊 Unmuted {member.mention}", ephemeral=False)
        await send_log(interaction.guild, f"[UNMUTE] {member} by {interaction.user}")
    else:
        await interaction.response.send_message("⚠️ Member not muted.", ephemeral=True)

@tree.command(name="tempmute", description="Temp mute seconds (Admin/Manage Roles)")
@app_commands.describe(member="Member", seconds="Seconds", reason="Reason optional")
async def slash_tempmute(interaction: discord.Interaction, member: discord.Member, seconds: int, reason: Optional[str] = None):
    perms = interaction.user.guild_permissions
    if not (perms.manage_roles or perms.administrator): return await interaction.response.send_message("⚠️ Manage Roles required.", ephemeral=True)
    role = await ensure_muted_role(interaction.guild)
    await member.add_roles(role)
    await interaction.response.send_message(f"🔇 Temp-muted {member.mention} for {seconds}s", ephemeral=False)
    async def unmute_later(m, r, d):
        await asyncio.sleep(d)
        try:
            await m.remove_roles(r)
        except:
            pass
    bot.loop.create_task(unmute_later(member, role, seconds))

@tree.command(name="clear", description="Purge messages in channel")
@app_commands.describe(limit="How many messages to delete (max 100)")
async def slash_clear(interaction: discord.Interaction, limit: int = 10):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    limit = max(1, min(limit, 100))
    deleted = await interaction.channel.purge(limit=limit)
    await interaction.response.send_message(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)
    await send_log(interaction.guild, f"[CLEAR] {len(deleted)} messages by {interaction.user} in {interaction.channel}")

@tree.command(name="lock", description="Lock a channel (Admin only)")
@app_commands.describe(channel="Channel to lock (omit for current)")
async def slash_lock(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    ch = channel or interaction.channel
    await ch.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(f"🔒 Locked {ch.mention}", ephemeral=False)
    await send_log(interaction.guild, f"[LOCK] {ch} by {interaction.user}")

@tree.command(name="unlock", description="Unlock a channel (Admin only)")
@app_commands.describe(channel="Channel to unlock (omit for current)")
async def slash_unlock(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    ch = channel or interaction.channel
    await ch.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message(f"🔓 Unlocked {ch.mention}", ephemeral=False)
    await send_log(interaction.guild, f"[UNLOCK] {ch} by {interaction.user}")

@tree.command(name="say", description="Bot say message (Admin only)")
@app_commands.describe(channel="Channel", message="Message")
async def slash_say(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    await channel.send(message)
    await interaction.response.send_message("✅ Sent.", ephemeral=True)

@tree.command(name="announce", description="Announce embed (Admin only)")
@app_commands.describe(channel="Channel", message="Message")
async def slash_announce(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    embed = discord.Embed(description=message, color=0x00ff00)
    await channel.send(embed=embed)
    await interaction.response.send_message("✅ Announced.", ephemeral=True)

@tree.command(name="slowmode", description="Set slowmode seconds for a channel")
@app_commands.describe(seconds="Seconds", channel="Channel (omit for current)")
async def slash_slowmode(interaction: discord.Interaction, seconds: int, channel: Optional[discord.TextChannel] = None):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    ch = channel or interaction.channel
    try:
        await ch.edit(slowmode_delay=max(0, seconds))
        await interaction.response.send_message(f"⏱️ Slowmode set to {seconds}s for {ch.mention}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ {e}", ephemeral=True)

@tree.command(name="nickname", description="Change a member's nickname (Admin only)")
@app_commands.describe(member="Member", nickname="New nickname")
async def slash_nickname(interaction: discord.Interaction, member: discord.Member, nickname: str):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    try:
        await member.edit(nick=nickname)
        await interaction.response.send_message(f"✅ Nick changed for {member.mention}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ {e}", ephemeral=True)

@tree.command(name="userinfo", description="Get user info")
@app_commands.describe(member="Member (omit for yourself)")
async def slash_userinfo(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    m = member or interaction.user
    embed = discord.Embed(title=str(m), description=f"ID: {m.id}")
    embed.add_field(name="Joined", value=str(m.joined_at))
    embed.set_thumbnail(url=m.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="serverinfo", description="Server info")
async def slash_serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=g.name, description=f"ID: {g.id}")
    embed.add_field(name="Members", value=str(g.member_count))
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="roleadd", description="Add role to user (Admin)")
@app_commands.describe(member="Member", role="Role")
async def slash_roleadd(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ Added {role.name} to {member.mention}", ephemeral=True)

@tree.command(name="roleremove", description="Remove role from user (Admin)")
@app_commands.describe(member="Member", role="Role")
async def slash_roleremove(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    await member.remove_roles(role)
    await interaction.response.send_message(f"✅ Removed {role.name} from {member.mention}", ephemeral=True)

@tree.command(name="createrole", description="Create a role (Admin)")
@app_commands.describe(name="Role name")
async def slash_createrole(interaction: discord.Interaction, name: str):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    role = await interaction.guild.create_role(name=name)
    await interaction.response.send_message(f"✅ Created role {role.name}", ephemeral=True)

@tree.command(name="deleterole", description="Delete a role (Admin)")
@app_commands.describe(role="Role to delete")
async def slash_deleterole(interaction: discord.Interaction, role: discord.Role):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    await role.delete()
    await interaction.response.send_message(f"✅ Deleted role {role.name}", ephemeral=True)

@tree.command(name="setwelcome", description="Set welcome message template (Admin)")
@app_commands.describe(channel="Channel (system channel will be used)", message="Message template, use {user} and {server}")
async def slash_setwelcome(interaction: discord.Interaction, message: str):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    WELCOME_MSG[interaction.guild.id] = message
    await interaction.response.send_message("✅ Welcome message set (temporary)", ephemeral=True)

@tree.command(name="setgoodbye", description="Set goodbye message template (Admin)")
@app_commands.describe(message="Message template, use {user} and {server}")
async def slash_setgoodbye(interaction: discord.Interaction, message: str):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    GOODBYE_MSG[interaction.guild.id] = message
    await interaction.response.send_message("✅ Goodbye message set (temporary)", ephemeral=True)

@tree.command(name="setlog", description="Set moderation log channel (Admin)")
@app_commands.describe(channel="Channel")
async def slash_setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    LOG_CHANNEL[interaction.guild.id] = channel.id
    await interaction.response.send_message(f"✅ Log channel set to {channel.mention}", ephemeral=True)

# mass operations with safety limits
@tree.command(name="massban", description="Ban multiple users (Admin only, limited to 10)")
@app_commands.describe(users="Space separated mentions or IDs (max 10)")
async def slash_massban(interaction: discord.Interaction, users: str):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    parts = users.split()
    if len(parts) > 10:
        return await interaction.response.send_message("⚠️ Max 10 users per operation.", ephemeral=True)
    failed = []
    for p in parts:
        try:
            uid = int(''.join(ch for ch in p if ch.isdigit()))
            user = await bot.fetch_user(uid)
            await interaction.guild.ban(user)
        except Exception:
            failed.append(p)
    await interaction.response.send_message(f"✅ massban done. failed: {failed}", ephemeral=True)

@tree.command(name="masskick", description="Kick multiple users (Admin only, max 10)")
@app_commands.describe(users="Space separated mentions or IDs (max 10)")
async def slash_masskick(interaction: discord.Interaction, users: str):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    parts = users.split()
    if len(parts) > 10:
        return await interaction.response.send_message("⚠️ Max 10 users per operation.", ephemeral=True)
    failed = []
    for p in parts:
        try:
            uid = int(''.join(ch for ch in p if ch.isdigit()))
            member = interaction.guild.get_member(uid)
            if member:
                await interaction.guild.kick(member)
        except Exception:
            failed.append(p)
    await interaction.response.send_message(f"✅ masskick done. failed: {failed}", ephemeral=True)

# -------------------------
# Giveaway and uplevel/level
# -------------------------
async def run_giveaway(channel: discord.TextChannel, duration: int, winners: int, prize: str, host_name: str):
    embed = discord.Embed(title="🎉 GIVEAWAY", description=f"**Prize:** {prize}\nReact with 🎉 to enter.\nEnds in {duration}s", color=0x2ecc71)
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
        return []
    winners_list = random.sample(list(users), k=min(winners, len(users)))
    await channel.send(f"🏆 Winners: {', '.join(w.mention for w in winners_list)} — Prize: **{prize}**")
    return winners_list

@tree.command(name="giveaway", description="Start giveaway (Admin only)")
@app_commands.describe(channel="Channel", duration="Seconds", winners="Number of winners", prize="Prize text")
async def slash_giveaway(interaction: discord.Interaction, channel: discord.TextChannel, duration: int, winners: int, prize: str):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    await interaction.response.send_message(f"🎉 Giveaway started in {channel.mention}", ephemeral=True)
    bot.loop.create_task(run_giveaway(channel, duration, winners, prize, interaction.user.display_name))

@tree.command(name="uplevel", description="Add level/points to member (Admin only)")
@app_commands.describe(member="Member", amount="Amount (int)")
async def slash_uplevel(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    LEVELS[member.id] = LEVELS.get(member.id, 0) + amount
    await interaction.response.send_message(f"✅ {member.mention} gained {amount}. Now: {LEVELS[member.id]}", ephemeral=False)

@tree.command(name="level", description="Check member level")
@app_commands.describe(member="Member (optional)")
async def slash_level(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    m = member or interaction.user
    await interaction.response.send_message(f"{m.mention} level: {LEVELS.get(m.id,0)}", ephemeral=True)

# -------------------------
# Masssend (safe) - slash
# -------------------------
@tree.command(name="masssend", description="Send message multiple times (Admin only, max 100000)")
@app_commands.describe(channel="Channel", message="Message", count="1-100000", delay="Seconds >=1")
async def slash_masssend(interaction: discord.Interaction, channel: discord.TextChannel, message: str, count: int = 1, delay: int = 1):
    if not is_admin_inter(interaction): return await interaction.response.send_message("⚠️ Admin only.", ephemeral=True)
    count = max(1, min(count,100000))
    delay = max(0, delay)
    await interaction.response.send_message(f"📤 Sending {count} messages to {channel.mention}...", ephemeral=True)
    for _ in range(count):
        await channel.send(message)
        await asyncio.sleep(delay)
    await interaction.followup.send("✅ Done.", ephemeral=True)

# -------------------------
# Prefix admin equivalents (examples)
# -------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
    await ctx.guild.ban(member, reason=reason)
    await ctx.send(f"🚫 Banned {member.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def kick(ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
    await ctx.guild.kick(member, reason=reason)
    await ctx.send(f"👢 Kicked {member.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def uplevel(ctx: commands.Context, member: discord.Member, amount: int):
    LEVELS[member.id] = LEVELS.get(member.id, 0) + amount
    await ctx.send(f"✅ {member.mention} level +{amount}. Now {LEVELS[member.id]}")

@bot.command()
@commands.has_permissions(administrator=True)
async def masssend_cmd(ctx: commands.Context, channel: discord.TextChannel, count: int, delay: int, *, message: str):
    count = max(1, min(count,5))
    delay = max(1, delay)
    await ctx.send(f"📤 Sending {count} messages to {channel.mention}...")
    for _ in range(count):
        await channel.send(message)
        await asyncio.sleep(delay)
    await ctx.send("✅ Done.")

# -------------------------
# Misc / fun commands (slash + prefix where applicable)
# -------------------------
@tree.command(name="ping", description="Bot latency")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency*1000)} ms", ephemeral=True)

@bot.command()
async def ping(ctx: commands.Context):
    await ctx.send(f"Pong! {round(bot.latency*1000)} ms")

@tree.command(name="info", description="Bot info")
async def slash_info(interaction: discord.Interaction):
    await interaction.response.send_message(f"Bot: {bot.user}\nPrefix (temp): `{PREFIX}`", ephemeral=True)

@tree.command(name="invite", description="Invite link for this bot")
async def slash_invite(interaction: discord.Interaction):
    app_id = bot.user.id
    link = f"https://discord.com/oauth2/authorize?client_id={app_id}&scope=bot%20applications.commands&permissions=8"
    await interaction.response.send_message(link, ephemeral=True)

@tree.command(name="roll", description="Roll a dice (sides)")
@app_commands.describe(sides="Number of sides")
async def slash_roll(interaction: discord.Interaction, sides: int = 6):
    await interaction.response.send_message(f"🎲 {random.randint(1, max(1,sides))}", ephemeral=True)

@tree.command(name="rand", description="Random number between min and max")
@app_commands.describe(minimum="Min", maximum="Max")
async def slash_rand(interaction: discord.Interaction, minimum: int, maximum: int):
    await interaction.response.send_message(str(random.randint(minimum, maximum)), ephemeral=True)

@tree.command(name="choose", description="Choose from comma-separated options")
@app_commands.describe(options="a,b,c,...")
async def slash_choose(interaction: discord.Interaction, options: str):
    opts = [o.strip() for o in options.split(",") if o.strip()]
    if not opts: return await interaction.response.send_message("No options", ephemeral=True)
    await interaction.response.send_message(random.choice(opts), ephemeral=True)

@tree.command(name="joke", description="Tell a joke")
async def slash_joke(interaction: discord.Interaction):
    jokes = ["Why did the chicken cross... to get to the other side.", "I would tell you a UDP joke but you might not get it."]
    await interaction.response.send_message(random.choice(jokes), ephemeral=True)

@tree.command(name="avatar", description="Get avatar of a user")
@app_commands.describe(member="Member (omit for yourself)")
async def slash_avatar(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    m = member or interaction.user
    await interaction.response.send_message(m.display_avatar.url, ephemeral=True)

# -------------------------
# Prefix misc examples
# -------------------------
@bot.command()
async def roll(ctx: commands.Context, sides: int = 6):
    await ctx.send(f"🎲 {random.randint(1, max(1,sides))}")

@bot.command()
async def rand(ctx: commands.Context, minimum: int, maximum: int):
    await ctx.send(str(random.randint(minimum, maximum)))

@bot.command()
async def choose(ctx: commands.Context, *, options: str):
    opts = [o.strip() for o in options.split(",") if o.strip()]
    if not opts:
        return await ctx.send("No options")
    await ctx.send(random.choice(opts))

@bot.command()
async def joke(ctx: commands.Context):
    await ctx.send(random.choice(["Joke A","Joke B","Joke C"]))

# -------------------------
# Prefix management
# -------------------------
@tree.command(name="prefix", description="Change bot command prefix (temporary)")
@app_commands.describe(new_prefix="New prefix (1-3 chars)")
async def slash_prefix(interaction: discord.Interaction, new_prefix: str):
    global PREFIX
    if len(new_prefix) > 3:
        return await interaction.response.send_message("Prefix max 3 chars.", ephemeral=True)
    PREFIX = new_prefix
    await interaction.response.send_message(f"✅ Prefix set to `{PREFIX}` (temporary).", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def prefix(ctx: commands.Context, new_prefix: str):
    global PREFIX
    if len(new_prefix) > 3:
        return await ctx.send("Prefix max 3 chars.")
    PREFIX = new_prefix
    await ctx.send(f"✅ Prefix set to `{PREFIX}` (temporary).")

# -------------------------
# Run
# -------------------------
bot.run(TOKEN)
