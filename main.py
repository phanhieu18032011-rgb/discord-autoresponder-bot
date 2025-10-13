# main.py
# Full-feature Discord bot (single-run RAM storage)
# - autoresponder (/add /remove /list) in-memory
# - ~25 admin commands (ban/unban/kick/mute/unmute/lock/unlock/clear/warn/tempban/tempmute/role add/remove/announce/say/slowmode/nickname/userinfo/serverinfo/avatar/poll/nuke/massban/masskick/etc.)
# - giveaway (reaction-based)
# - uplevel (admin can add level to member)
# - massend (safe limit)
# - both slash commands and prefix commands supported
# - automode import for anti-spam & banned words
# - keep-alive Flask for Render

import os, asyncio, random, threading, time
from typing import Dict, List
from flask import Flask
import discord
from discord.ext import commands, tasks
from discord import app_commands

# import automode module (must be in same repo)
from automode import handle_auto_mode

# ----------------------
# CONFIG
# ----------------------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise SystemExit("❌ Please set TOKEN environment variable.")

DEFAULT_PREFIX = "!"
PREFIX = DEFAULT_PREFIX  # temporary in-memory
PORT = int(os.getenv("PORT", 10000))

# ----------------------
# Keep-alive Flask (for Render Web Service)
# ----------------------
app = Flask("keepalive")
@app.route("/")
def home():
    return "✅ Bot is alive!"

def run_web():
    app.run(host="0.0.0.0", port=PORT)

threading.Thread(target=run_web, daemon=True).start()

# ----------------------
# Bot setup
# ----------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

def get_prefix(bot, message):
    return PREFIX

bot = commands.Bot(command_prefix=get_prefix, intents=intents)
tree = bot.tree

# ----------------------
# In-memory storages
# ----------------------
AUTORESPONDERS: Dict[str, str] = {}     # trigger_lower -> response
LEVELS: Dict[int, int] = {}             # user_id -> level (int)
WARNS: Dict[int, int] = {}              # user_id -> warns count
TEMP_TASKS = []                         # list of background tasks if needed

# ----------------------
# Helpers
# ----------------------
def is_admin_inter(interaction: discord.Interaction) -> bool:
    try:
        return interaction.user.guild_permissions.administrator
    except:
        return False

def is_admin_ctx(ctx: commands.Context) -> bool:
    try:
        return ctx.author.guild_permissions.administrator
    except:
        return False

async def ensure_muted_role(guild: discord.Guild):
    role = discord.utils.get(guild.roles, name="Muted")
    if role:
        return role
    try:
        role = await guild.create_role(name="Muted", reason="Create Muted role")
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
        print("Failed create Muted role:", e)
        return None

# ----------------------
# Events
# ----------------------
@bot.event
async def on_ready():
    print(f"✅ Bot ready: {bot.user} (id: {bot.user.id})")
    try:
        synced = await tree.sync()
        print(f"🔁 Synced {len(synced)} slash commands")
    except Exception as e:
        print("Slash sync error:", e)

@bot.event
async def on_message(message: discord.Message):
    # call automode (spam/bad words)
    try:
        await handle_auto_mode(message)
    except Exception as e:
        print("automode error:", e)

    # autoresponders
    if not message.author.bot:
        content = message.content.lower()
        for trigger, reply in AUTORESPONDERS.items():
            if trigger in content:
                try:
                    await message.channel.send(reply)
                except Exception:
                    pass
                break

    await bot.process_commands(message)

# ----------------------
# Slash Autoresponder
# ----------------------
@tree.command(name="add", description="Add an autoresponder (trigger -> response)")
@app_commands.describe(trigger="Trigger text (contains)", response="Bot response")
async def slash_add(interaction: discord.Interaction, trigger: str, response: str):
    AUTORESPONDERS[trigger.lower()] = response
    await interaction.response.send_message(f"✅ Added autoresponder: `{trigger}` → {response}", ephemeral=True)

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
    lines = [f"`{k}` → {v}" for k,v in AUTORESPONDERS.items()]
    text = "\n".join(lines)
    if len(text) > 1900:
        fname = "autoresponders.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(text)
        await interaction.response.send_message("📄 List is long, file attached.", file=discord.File(fname), ephemeral=True)
    else:
        await interaction.response.send_message(f"📋 {text}", ephemeral=True)

# ----------------------
# Prefix Autoresponder (mirror)
# ----------------------
@bot.command(name="add")
async def pfx_add(ctx: commands.Context, trigger: str, *, response: str):
    AUTORESPONDERS[trigger.lower()] = response
    await ctx.send(f"✅ Added autoresponder: `{trigger}` → {response}")

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
    text = "\n".join([f"`{k}` → {v}" for k,v in AUTORESPONDERS.items()])
    await ctx.send(f"📋 {text}")

# ----------------------
# Moderation commands (slash)
# ----------------------
@tree.command(name="ban", description="Ban a user (Admin only)")
@app_commands.describe(member="Member to ban", reason="Reason")
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    try:
        await interaction.guild.ban(member, reason=reason)
        await interaction.response.send_message(f"🚫 Banned {member.mention}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@tree.command(name="unban", description="Unban user by ID (Admin only)")
@app_commands.describe(user_id="User ID to unban")
async def slash_unban(interaction: discord.Interaction, user_id: str):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    try:
        uid = int(user_id)
        user = await bot.fetch_user(uid)
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ Unbanned {user}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@tree.command(name="kick", description="Kick a member (Admin only)")
@app_commands.describe(member="Member to kick", reason="Reason optional")
async def slash_kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    try:
        await interaction.guild.kick(member, reason=reason)
        await interaction.response.send_message(f"👢 Kicked {member.mention}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@tree.command(name="mute", description="Mute a member (Manage Roles required)")
@app_commands.describe(member="Member to mute", reason="Reason optional")
async def slash_mute(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    perms = interaction.user.guild_permissions
    if not (perms.manage_roles or perms.administrator):
        await interaction.response.send_message("⚠️ Manage Roles required.", ephemeral=True); return
    bot_member = interaction.guild.get_member(bot.user.id)
    if not bot_member.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ Bot needs Manage Roles perm.", ephemeral=True); return
    role = await ensure_muted_role(interaction.guild)
    if not role:
        await interaction.response.send_message("❌ Can't create Muted role.", ephemeral=True); return
    await member.add_roles(role, reason=reason)
    await interaction.response.send_message(f"🔇 Muted {member.mention}", ephemeral=False)

@tree.command(name="unmute", description="Unmute a member")
@app_commands.describe(member="Member to unmute")
async def slash_unmute(interaction: discord.Interaction, member: discord.Member):
    perms = interaction.user.guild_permissions
    if not (perms.manage_roles or perms.administrator):
        await interaction.response.send_message("⚠️ Manage Roles required.", ephemeral=True); return
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not role:
        await interaction.response.send_message("⚠️ Muted role not found.", ephemeral=True); return
    await member.remove_roles(role)
    await interaction.response.send_message(f"🔊 Unmuted {member.mention}", ephemeral=False)

@tree.command(name="lock", description="Lock a channel (Admin only)")
@app_commands.describe(channel="Channel to lock (omit for current)")
async def slash_lock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    ch = channel or interaction.channel
    await ch.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(f"🔒 Locked {ch.mention}", ephemeral=False)

@tree.command(name="unlock", description="Unlock a channel (Admin only)")
@app_commands.describe(channel="Channel to unlock (omit for current)")
async def slash_unlock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    ch = channel or interaction.channel
    await ch.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message(f"🔓 Unlocked {ch.mention}", ephemeral=False)

@tree.command(name="clear", description="Clear messages in channel (Admin only)")
@app_commands.describe(limit="Number of messages to delete")
async def slash_clear(interaction: discord.Interaction, limit: int = 10):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    deleted = await interaction.channel.purge(limit=limit)
    await interaction.response.send_message(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)

@tree.command(name="warn", description="Warn a member (Admin only)")
@app_commands.describe(member="Member to warn", reason="Reason optional")
async def slash_warn(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    uid = member.id
    WARNS[uid] = WARNS.get(uid, 0) + 1
    await interaction.response.send_message(f"⚠️ {member.mention} warned ({WARNS[uid]}). Reason: {reason or 'None'}", ephemeral=False)

@tree.command(name="tempban", description="Temp ban (seconds) (Admin only)")
@app_commands.describe(member="Member", seconds="Duration in seconds", reason="Reason optional")
async def slash_tempban(interaction: discord.Interaction, member: discord.Member, seconds: int, reason: str = None):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    await interaction.guild.ban(member, reason=reason)
    await interaction.response.send_message(f"🚫 Temp-banned {member.mention} for {seconds}s", ephemeral=False)
    async def unban_later(guild, uid, delay):
        await asyncio.sleep(delay)
        try:
            user = await bot.fetch_user(uid)
            await guild.unban(user)
        except Exception:
            pass
    bot.loop.create_task(unban_later(interaction.guild, member.id, seconds))

@tree.command(name="tempmute", description="Temp mute seconds (Admin only)")
@app_commands.describe(member="Member", seconds="Seconds", reason="Reason optional")
async def slash_tempmute(interaction: discord.Interaction, member: discord.Member, seconds: int, reason: str = None):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    role = await ensure_muted_role(interaction.guild)
    await member.add_roles(role)
    await interaction.response.send_message(f"🔇 Temp-muted {member.mention} for {seconds}s", ephemeral=False)
    async def unmute_later(m, r, d):
        await asyncio.sleep(d)
        try:
            await m.remove_roles(r)
        except Exception:
            pass
    bot.loop.create_task(unmute_later(member, role, seconds))

@tree.command(name="say", description="Make bot say something (Admin only)")
@app_commands.describe(channel="Channel", message="Message")
async def slash_say(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    await channel.send(message)
    await interaction.response.send_message("✅ Sent.", ephemeral=True)

@tree.command(name="announce", description="Announce message to channel (Admin only)")
@app_commands.describe(channel="Channel", message="Message")
async def slash_announce(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    embed = discord.Embed(description=message, color=0x00ff00)
    await channel.send(embed=embed)
    await interaction.response.send_message("✅ Announced.", ephemeral=True)

@tree.command(name="slowmode", description="Set channel slowmode seconds (Admin only)")
@app_commands.describe(channel="Channel (omit for current)", seconds="Seconds")
async def slash_slowmode(interaction: discord.Interaction, seconds: int, channel: discord.TextChannel = None):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    ch = channel or interaction.channel
    try:
        await ch.edit(slowmode_delay=seconds)
        await interaction.response.send_message(f"⏱️ Slowmode set to {seconds}s for {ch.mention}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@tree.command(name="nickname", description="Change a member's nickname (Admin only)")
@app_commands.describe(member="Member", nickname="New nickname")
async def slash_nickname(interaction: discord.Interaction, member: discord.Member, nickname: str):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    try:
        await member.edit(nick=nickname)
        await interaction.response.send_message(f"✅ Nick changed for {member.mention}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@tree.command(name="userinfo", description="Get user info")
@app_commands.describe(member="Member (omit for yourself)")
async def slash_userinfo(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    embed = discord.Embed(title=str(m), description=f"ID: {m.id}")
    embed.add_field(name="Joined", value=str(m.joined_at))
    embed.set_thumbnail(url=m.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="serverinfo", description="Get server info")
async def slash_serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=g.name, description=f"ID: {g.id}")
    embed.add_field(name="Members", value=str(g.member_count))
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="roleadd", description="Add a role to a user (Admin only)")
@app_commands.describe(member="Member", role="Role to add")
async def slash_roleadd(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ Added {role.name} to {member.mention}", ephemeral=True)

@tree.command(name="roleremove", description="Remove a role from a user (Admin only)")
@app_commands.describe(member="Member", role="Role to remove")
async def slash_roleremove(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    await member.remove_roles(role)
    await interaction.response.send_message(f"✅ Removed {role.name} from {member.mention}", ephemeral=True)

@tree.command(name="avatar", description="Get a member's avatar")
@app_commands.describe(member="Member (omit for yourself)")
async def slash_avatar(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    await interaction.response.send_message(m.display_avatar.url, ephemeral=True)

@tree.command(name="poll", description="Create a poll (Admin only)")
@app_commands.describe(question="Question text", options="Comma-separated options (2-5)")
async def slash_poll(interaction: discord.Interaction, question: str, options: str):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    opts = [o.strip() for o in options.split(",") if o.strip()]
    if len(opts) < 2 or len(opts) > 5:
        await interaction.response.send_message("⚠️ Options must be 2–5.", ephemeral=True); return
    embed = discord.Embed(title=question, description="\n".join(f"{i+1}. {o}" for i,o in enumerate(opts)))
    msg = await interaction.channel.send(embed=embed)
    emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"][:len(opts)]
    for e in emojis:
        await msg.add_reaction(e)
    await interaction.response.send_message("📊 Poll created.", ephemeral=True)

@tree.command(name="nuke", description="Purge channel (Admin only, CAREFUL)")
async def slash_nuke(interaction: discord.Interaction):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    await interaction.response.send_message("🔁 Purging messages...", ephemeral=True)
    await interaction.channel.purge(limit=None)

@tree.command(name="massban", description="Ban multiple users by mention/IDs (Admin only)")
@app_commands.describe(users="Space separated user IDs or mentions")
async def slash_massban(interaction: discord.Interaction, users: str):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    parts = users.split()
    failed = []
    for p in parts:
        try:
            uid = int(''.join(ch for ch in p if ch.isdigit()))
            user = await bot.fetch_user(uid)
            await interaction.guild.ban(user)
        except Exception as e:
            failed.append(p)
    await interaction.response.send_message(f"✅ Done. Failed: {failed}", ephemeral=True)

@tree.command(name="masskick", description="Kick multiple users (Admin only)")
@app_commands.describe(users="Space separated user IDs or mentions")
async def slash_masskick(interaction: discord.Interaction, users: str):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    parts = users.split()
    failed = []
    for p in parts:
        try:
            uid = int(''.join(ch for ch in p if ch.isdigit()))
            member = interaction.guild.get_member(uid)
            if member:
                await interaction.guild.kick(member)
        except Exception as e:
            failed.append(p)
    await interaction.response.send_message(f"✅ Done. Failed: {failed}", ephemeral=True)

# ----------------------
# Giveaway
# ----------------------
async def run_giveaway(channel: discord.TextChannel, duration: int, winners: int, prize: str, host_name: str):
    embed = discord.Embed(title="🎉 GIVEAWAY", description=f"**Prize:** {prize}\nReact with 🎉 to join.\nEnds in {duration}s", color=0x2ecc71)
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
@app_commands.describe(channel="Channel", duration="Duration sec", winners="Number winners", prize="Prize text")
async def slash_giveaway(interaction: discord.Interaction, channel: discord.TextChannel, duration: int, winners: int, prize: str):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    await interaction.response.send_message(f"🎉 Giveaway started in {channel.mention}", ephemeral=True)
    bot.loop.create_task(run_giveaway(channel, duration, winners, prize, interaction.user.display_name))

# ----------------------
# Uplevel (admin can add level to user)
# ----------------------
@tree.command(name="uplevel", description="Add XP/level to member (Admin only)")
@app_commands.describe(member="Member", amount="Amount of levels/points to add (int)")
async def slash_uplevel(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only", ephemeral=True); return
    uid = member.id
    LEVELS[uid] = LEVELS.get(uid, 0) + amount
    await interaction.response.send_message(f"✅ {member.mention} gained {amount} level(s). Now: {LEVELS[uid]}", ephemeral=False)

@tree.command(name="level", description="Check member level")
@app_commands.describe(member="Member (optional)")
async def slash_level(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    lvl = LEVELS.get(m.id, 0)
    await interaction.response.send_message(f"{m.mention} level: {lvl}", ephemeral=True)

# ----------------------
# Masssend (safe)
# ----------------------
@tree.command(name="masssend", description="Send message multiple times (Admin only, max 50000)")
@app_commands.describe(channel="Channel", message="Message", count="1-50000", delay="seconds >=1")
async def slash_masssend(interaction: discord.Interaction, channel: discord.TextChannel, message: str, count: int = 1, delay: int = 1):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    count = max(1, min(count, 50000))
    delay = max(0, delay)
    await interaction.response.send_message(f"📤 Sending {count} messages to {channel.mention}...", ephemeral=True)
    for _ in range(count):
        await channel.send(message)
        await asyncio.sleep(delay)
    await interaction.followup.send("✅ Done", ephemeral=True)

# ----------------------
# Prefix commands (examples for some admin actions)
# ----------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def prefix(ctx: commands.Context, new_prefix: str = None):
    global PREFIX
    if not new_prefix:
        await ctx.send(f"Prefix: `{PREFIX}`")
    else:
        if len(new_prefix) > 3:
            await ctx.send("⚠️ Prefix max 3 chars.")
            return
        PREFIX = new_prefix
        await ctx.send(f"✅ Prefix set to `{PREFIX}` (temporary)")

@bot.command()
@commands.has_permissions(administrator=True)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = None):
    await ctx.guild.ban(member, reason=reason)
    await ctx.send(f"🚫 Banned {member.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = None):
    await ctx.guild.kick(member, reason=reason)
    await ctx.send(f"👢 Kicked {member.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def tempmute(ctx: commands.Context, member: discord.Member, seconds: int):
    role = await ensure_muted_role(ctx.guild)
    await member.add_roles(role)
    await ctx.send(f"🔇 Temp-muted {member.mention} for {seconds}s")
    async def unmute_later(m, r, d):
        await asyncio.sleep(d)
        try:
            await m.remove_roles(r)
        except Exception:
            pass
    bot.loop.create_task(unmute_later(member, role, seconds))

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
    await ctx.send("✅ Done")

# ----------------------
# Run
# ----------------------
bot.run(TOKEN)
