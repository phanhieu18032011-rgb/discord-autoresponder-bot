# main.py — Multi-tool Discord bot (single-file)
# Requirements: discord.py, flask
# Set environment variable DISCORD_TOKEN with your bot token (DO NOT put token in code)

import os
import asyncio
from automode import handle_auto_mode
import random
import threading
from typing import Dict

from flask import Flask
import discord
from discord.ext import commands
from discord import app_commands

# ----------------------
# Config / Globals
# ----------------------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise SystemExit("❌ Please set TOKEN environment variable before running.")

# default prefix (in-memory, temporary)
PREFIX = "!"
# autoresponders stored in-memory: trigger (lower) -> response
AUTORESPONDERS: Dict[str, str] = {}

# ----------------------
# Keep-alive (Flask) — for Render Web Service
# ----------------------
app = Flask("keepalive")

@app.route("/")
def home():
    return "✅ Bot is alive!"

def run_web():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ----------------------
# Bot setup (both slash and prefix support)
# ----------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # needed for some moderation actions
# dynamic prefix provider reads global PREFIX
def get_prefix(bot, message):
    return PREFIX

bot = commands.Bot(command_prefix=get_prefix, intents=intents)
tree = bot.tree

# ----------------------
# Utilities
# ----------------------
def is_admin_inter(interaction) -> bool:
    try:
        return interaction.user.guild_permissions.administrator
    except Exception:
        return False

def is_admin_ctx(ctx: commands.Context) -> bool:
    try:
        return ctx.author.guild_permissions.administrator
    except Exception:
        return False

async def ensure_muted_role(guild: discord.Guild, bot_member: discord.Member):
    role = discord.utils.get(guild.roles, name="Muted")
    if role:
        return role
    try:
        role = await guild.create_role(name="Muted", reason="Create Muted role for muting")
        for ch in guild.channels:
            try:
                if isinstance(ch, discord.TextChannel):
                    await ch.set_permissions(role, send_messages=False, add_reactions=False)
                elif isinstance(ch, discord.VoiceChannel):
                    await ch.set_permissions(role, speak=False)
            except Exception:
                pass
        return role
    except Exception:
        return None

# ----------------------
# Events
# ----------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (id: {bot.user.id})")
    try:
        synced = await tree.sync()
        print(f"🔁 Synced {len(synced)} slash commands.")
    except Exception as e:
        print("⚠️ Sync error:", e)

@bot.event
async def on_message(message: discord.Message):
    # autoresponder (in-memory)
    if message.author.bot:
        return
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
# Slash Commands — Autoresponder
# ----------------------
@tree.command(name="add", description="Add an autoresponder trigger")
@app_commands.describe(trigger="Trigger text (contains)", response="Bot response")
async def slash_add(interaction: discord.Interaction, trigger: str, response: str):
    AUTORESPONDERS[trigger.lower()] = response
    await interaction.response.send_message(f"✅ Added autoresponder: `{trigger}` → {response}", ephemeral=True)

@tree.command(name="remove", description="Remove an autoresponder trigger")
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
    await interaction.response.send_message(f"📋 Autoresponders:\n{text}", ephemeral=True)

# ----------------------
# Prefix Commands — Autoresponder (mirror)
# ----------------------
@bot.command(name="add")
async def cmd_add(ctx: commands.Context, trigger: str, *, response: str):
    AUTORESPONDERS[trigger.lower()] = response
    await ctx.send(f"✅ Added autoresponder: `{trigger}` → {response}")

@bot.command(name="remove")
async def cmd_remove(ctx: commands.Context, trigger: str):
    if trigger.lower() in AUTORESPONDERS:
        del AUTORESPONDERS[trigger.lower()]
        await ctx.send(f"🗑️ Removed `{trigger}`")
    else:
        await ctx.send("⚠️ Trigger not found.")

@bot.command(name="list")
async def cmd_list(ctx: commands.Context):
    if not AUTORESPONDERS:
        await ctx.send("📭 No autoresponders.")
        return
    text = "\n".join([f"`{k}` → {v}" for k, v in AUTORESPONDERS.items()])
    await ctx.send(f"📋 Autoresponders:\n{text}")

# ----------------------
# Moderation — Slash
# ----------------------
@tree.command(name="ban", description="Ban a user (Admin only)")
@app_commands.describe(member="Member to ban", reason="Reason (optional)")
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Administrator only.", ephemeral=True); return
    try:
        await interaction.guild.ban(member, reason=reason)
        await interaction.response.send_message(f"🚫 Banned {member.mention}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@tree.command(name="unban", description="Unban a user by ID (Admin only)")
@app_commands.describe(user_id="User ID to unban")
async def slash_unban(interaction: discord.Interaction, user_id: str):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Administrator only.", ephemeral=True); return
    try:
        uid = int(user_id)
        user = await bot.fetch_user(uid)
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ Unbanned {user}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@tree.command(name="mute", description="Mute a user (Manage Roles required)")
@app_commands.describe(member="Member to mute", reason="Reason (optional)")
async def slash_mute(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    perms = interaction.user.guild_permissions
    if not (perms.manage_roles or perms.administrator):
        await interaction.response.send_message("⚠️ Manage Roles or Administrator required.", ephemeral=True); return
    bot_member = interaction.guild.get_member(bot.user.id)
    if not bot_member.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ Bot needs Manage Roles permission.", ephemeral=True); return
    role = await ensure_muted_role(interaction.guild, bot_member)
    if not role:
        await interaction.response.send_message("❌ Can't create Muted role.", ephemeral=True); return
    try:
        await member.add_roles(role, reason=reason)
        await interaction.response.send_message(f"🔇 Muted {member.mention}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@tree.command(name="unmute", description="Unmute a user")
@app_commands.describe(member="Member to unmute")
async def slash_unmute(interaction: discord.Interaction, member: discord.Member):
    perms = interaction.user.guild_permissions
    if not (perms.manage_roles or perms.administrator):
        await interaction.response.send_message("⚠️ Manage Roles or Administrator required.", ephemeral=True); return
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not role:
        await interaction.response.send_message("⚠️ Muted role not found.", ephemeral=True); return
    try:
        await member.remove_roles(role)
        await interaction.response.send_message(f"🔊 Unmuted {member.mention}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@tree.command(name="lock", description="Lock current channel (Admin only)")
@app_commands.describe(channel="Channel to lock (omit for current channel)")
async def slash_lock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Administrator only.", ephemeral=True); return
    ch = channel or interaction.channel
    try:
        await ch.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(f"🔒 Locked {ch.mention}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@tree.command(name="unlock", description="Unlock channel (Admin only)")
@app_commands.describe(channel="Channel to unlock (omit for current channel)")
async def slash_unlock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Administrator only.", ephemeral=True); return
    ch = channel or interaction.channel
    try:
        await ch.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message(f"🔓 Unlocked {ch.mention}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

# ----------------------
# Moderation — Prefix counterparts
# ----------------------
@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def pfx_ban(ctx: commands.Context, member: discord.Member, *, reason: str = None):
    await ctx.guild.ban(member, reason=reason)
    await ctx.send(f"🚫 Banned {member.mention}")

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def pfx_unban(ctx: commands.Context, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"✅ Unbanned {user}")

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def pfx_mute(ctx: commands.Context, member: discord.Member):
    role = await ensure_muted_role(ctx.guild, ctx.guild.get_member(bot.user.id))
    await member.add_roles(role)
    await ctx.send(f"🔇 Muted {member.mention}")

@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def pfx_unmute(ctx: commands.Context, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if role:
        await member.remove_roles(role)
        await ctx.send(f"🔊 Unmuted {member.mention}")
    else:
        await ctx.send("⚠️ Muted role not found.")

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def pfx_lock(ctx: commands.Context, channel: discord.TextChannel = None):
    ch = channel or ctx.channel
    await ch.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 Locked {ch.mention}")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def pfx_unlock(ctx: commands.Context, channel: discord.TextChannel = None):
    ch = channel or ctx.channel
    await ch.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 Unlocked {ch.mention}")

# ----------------------
# Giveaway (reaction-based) — Slash & Prefix
# ----------------------
async def run_giveaway(channel: discord.TextChannel, duration: int, winners: int, prize: str, host):
    embed = discord.Embed(title="🎉 Giveaway!", description=f"**Prize:** {prize}\nReact with 🎉 to enter.\nEnds in {duration} seconds.", color=0x00ff00)
    embed.set_footer(text=f"Hosted by {host}")
    msg = await channel.send(embed=embed)
    await msg.add_reaction("🎉")
    await asyncio.sleep(duration)
    msg = await channel.fetch_message(msg.id)  # refetch
    users = set()
    for reaction in msg.reactions:
        if reaction.emoji == "🎉":
            async for user in reaction.users():
                if not user.bot:
                    users.add(user)
    if not users:
        await channel.send("No participants — giveaway canceled.")
        return []
    winners_list = random.sample(list(users), k=min(winners, len(users)))
    mention_text = ", ".join(w.mention for w in winners_list)
    await channel.send(f"🏆 Congratulations {mention_text}! You won **{prize}**")
    return winners_list

@tree.command(name="giveaway", description="Start a giveaway (Admin only)")
@app_commands.describe(channel="Channel to post", duration="Duration in seconds", winners="Number of winners", prize="Prize text")
async def slash_giveaway(interaction: discord.Interaction, channel: discord.TextChannel, duration: int, winners: int, prize: str):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    await interaction.response.send_message(f"🎉 Giveaway started in {channel.mention} for **{prize}** — ends in {duration}s", ephemeral=True)
    await run_giveaway(channel, duration, winners, prize, interaction.user.display_name)

@bot.command(name="giveaway")
@commands.has_permissions(administrator=True)
async def pfx_giveaway(ctx: commands.Context, channel: discord.TextChannel, duration: int, winners: int, *, prize: str):
    await ctx.send(f"🎉 Giveaway started in {channel.mention} for **{prize}** — ends in {duration}s")
    await run_giveaway(channel, duration, winners, prize, ctx.author.display_name)

# ----------------------
# Mass send (safe)
# ----------------------
@tree.command(name="masssend", description="Send message multiple times (Admin only, max 10000)")
@app_commands.describe(channel="Channel to send", message="Message", count="1-5", delay="Seconds between messages")
async def slash_masssend(interaction: discord.Interaction, channel: discord.TextChannel, message: str, count: int = 1, delay: int = 1):
    if not is_admin_inter(interaction):
        await interaction.response.send_message("⚠️ Admin only.", ephemeral=True); return
    count = max(1, min(count, 10000))
    delay = max(0, delay)
    await interaction.response.send_message(f"📤 Sending {count} messages to {channel.mention}...", ephemeral=True)
    for _ in range(count):
        await channel.send(message)
        await asyncio.sleep(delay)
    await interaction.followup.send("✅ Done.", ephemeral=True)

@bot.command(name="masssend")
@commands.has_permissions(administrator=True)
async def pfx_masssend(ctx: commands.Context, channel: discord.TextChannel, count: int, delay: int, *, message: str):
    count = max(1, min(count, 10000))
    delay = max(0, delay)
    await ctx.send(f"📤 Sending {count} messages to {channel.mention}...")
    for _ in range(count):
        await channel.send(message)
        await asyncio.sleep(delay)
    await ctx.send("✅ Done.")

# ----------------------
# Prefix management: /prefix (slash) and !prefix (prefix)
# ----------------------
@tree.command(name="prefix", description="Change bot command prefix (temporary)")
@app_commands.describe(new_prefix="New prefix (1-3 chars)")
async def slash_prefix(interaction: discord.Interaction, new_prefix: str):
    global PREFIX
    if len(new_prefix) > 3:
        await interaction.response.send_message("⚠️ Prefix max 3 chars.", ephemeral=True); return
    PREFIX = new_prefix
    await interaction.response.send_message(f"✅ Prefix set to `{PREFIX}` (temporary, will reset on restart).", ephemeral=True)

@bot.command(name="prefix")
@commands.has_permissions(administrator=True)
async def pfx_prefix(ctx: commands.Context, new_prefix: str):
    global PREFIX
    if len(new_prefix) > 3:
        await ctx.send("⚠️ Prefix max 3 chars."); return
    PREFIX = new_prefix
    await ctx.send(f"✅ Prefix set to `{PREFIX}` (temporary).")

# ----------------------
# Utility: ping/info
# ----------------------
@tree.command(name="ping", description="Check bot latency")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency*1000)} ms", ephemeral=True)

@bot.command(name="ping")
async def pfx_ping(ctx: commands.Context):
    await ctx.send(f"Pong! {round(bot.latency*1000)} ms")

@tree.command(name="info", description="Bot info")
async def slash_info(interaction: discord.Interaction):
    await interaction.response.send_message(f"Bot: {bot.user}\nPrefix (temp): `{PREFIX}`", ephemeral=True)

# =============== GẮN AUTO MODE ===============
@bot.event
async def on_message(message):
    await handle_auto_mode(message)  # ✅ xử lý spam & từ cấm
    await bot.process_commands(message)

# ----------------------
# Run bot
# ----------------------
bot.run(TOKEN)
