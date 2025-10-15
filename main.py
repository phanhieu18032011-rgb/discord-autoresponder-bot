# main.py
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
import os
import json
import asyncio

DATA_FILE = "data.json"
DEFAULT_PREFIX = "!"

# ---- Helpers: load/save data (prefixes, autoresponders, warns) ----
def ensure_data():
    if not os.path.exists(DATA_FILE):
        data = {"prefixes": {}, "autoresponders": {}, "warns": {}}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def load_data():
    ensure_data()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# dynamic prefix function
def get_prefix(bot, message):
    if not message.guild:
        return DEFAULT_PREFIX
    data = load_data()
    p = data.get("prefixes", {}).get(str(message.guild.id), DEFAULT_PREFIX)
    return commands.when_mentioned_or(p)(bot, message)

# ---- Flask keep-alive for Render ----
app = Flask(__name__)
@app.route("/")
def home():
    return "✅ Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ---- Bot setup ----
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)
tree = bot.tree

# ---- Utility internal functions ----
async def ensure_muted_role(guild: discord.Guild):
    role = discord.utils.get(guild.roles, name="Muted-by-bot")
    if role is None:
        perms = discord.Permissions(send_messages=False, speak=False)
        role = await guild.create_role(name="Muted-by-bot", permissions=perms, reason="Create mute role")
        for ch in guild.text_channels:
            try:
                await ch.set_permissions(role, send_messages=False)
            except Exception:
                pass
    return role

# ---- On ready: sync tree and load games cog ----
@bot.event
async def on_ready():
    print(f"🤖 Logged in as: {bot.user} ({bot.user.id})")
    try:
        await tree.sync()  # global sync
        print("✅ Slash commands synced globally.")
    except Exception as e:
        print("⚠️ Sync error:", e)
    # load games cog file if exists
    try:
        await bot.load_extension("games")
        print("✅ Loaded games cog.")
    except Exception as e:
        print("⚠️ Could not load games cog:", e)

# ---- Auto-responder: watch messages ----
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # autorespond
    if message.guild:
        data = load_data()
        guild_key = str(message.guild.id)
        ar = data.get("autoresponders", {}).get(guild_key, [])
        for entry in ar:
            trigger = entry.get("trigger", "")
            response = entry.get("response", "")
            if trigger and trigger.lower() in message.content.lower():
                try:
                    await message.channel.send(response)
                except Exception:
                    pass
                break
    await bot.process_commands(message)

# =========================
#  MANAGEMENT (≈20 commands)
#  Each command has both prefix @bot.command and slash @tree.command
# =========================

# 1) ping
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency*1000)}ms")

@tree.command(name="ping", description="Check bot latency")
async def ping_slash(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency*1000)}ms")

# 2) say
@bot.command()
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, text: str):
    await ctx.send(text)

@tree.command(name="say", description="Make the bot say something")
@app_commands.describe(text="Text to say")
async def say_slash(interaction: discord.Interaction, text: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages permission.", ephemeral=True)
        return
    await interaction.response.send_message(text)

# 3) clear
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount+1)
    await ctx.send(f"🧹 Deleted {amount} messages.", delete_after=3)

@tree.command(name="clear", description="Clear messages")
@app_commands.describe(amount="Number of messages to delete")
async def clear_slash(interaction: discord.Interaction, amount: int = 5):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages permission.", ephemeral=True)
        return
    await interaction.response.defer()
    await interaction.channel.purge(limit=amount+1)
    await interaction.followup.send(f"🧹 Deleted {amount} messages.", ephemeral=True)

# 4) kick
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member} — {reason}")

@tree.command(name="kick", description="Kick a member")
@app_commands.describe(member="Member to kick", reason="Reason")
async def kick_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("Need Kick Members permission.", ephemeral=True)
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 Kicked {member} — {reason}")

# 5) ban
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "No reason"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member} — {reason}")

@tree.command(name="ban", description="Ban a member")
@app_commands.describe(member="Member to ban", reason="Reason")
async def ban_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("Need Ban Members permission.", ephemeral=True)
        return
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 Banned {member} — {reason}")

# 6) unban
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"✅ Unbanned {user}")

@tree.command(name="unban", description="Unban by user ID")
@app_commands.describe(user_id="User ID to unban")
async def unban_slash(interaction: discord.Interaction, user_id: int):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("Need Ban Members permission.", ephemeral=True)
        return
    user = await bot.fetch_user(user_id)
    await interaction.guild.unban(user)
    await interaction.response.send_message(f"✅ Unbanned {user}")

# 7) lock / unlock (channel send_messages permission for @everyone)
@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    overwrites = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrites.send_messages = False
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrites)
    await ctx.send("🔒 Channel locked.")

@tree.command(name="lock", description="Lock current channel")
async def lock_slash(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Need Manage Channels permission.", ephemeral=True)
        return
    overwrites = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrites.send_messages = False
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrites)
    await interaction.response.send_message("🔒 Channel locked.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    overwrites = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrites.send_messages = True
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrites)
    await ctx.send("🔓 Channel unlocked.")

@tree.command(name="unlock", description="Unlock current channel")
async def unlock_slash(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Need Manage Channels permission.", ephemeral=True)
        return
    overwrites = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrites.send_messages = True
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrites)
    await interaction.response.send_message("🔓 Channel unlocked.")

# 8) mute / unmute (uses Muted-by-bot role)
@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason: str = "No reason"):
    role = await ensure_muted_role(ctx.guild)
    await member.add_roles(role, reason=reason)
    await ctx.send(f"🔇 {member} has been muted. Reason: {reason}")

@tree.command(name="mute", description="Mute a member")
@app_commands.describe(member="Member to mute", reason="Reason")
async def mute_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("Need Manage Roles permission.", ephemeral=True)
        return
    role = await ensure_muted_role(interaction.guild)
    await member.add_roles(role, reason=reason)
    await interaction.response.send_message(f"🔇 {member} has been muted. Reason: {reason}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted-by-bot")
    if role:
        await member.remove_roles(role)
        await ctx.send(f"🔊 {member} has been unmuted.")
    else:
        await ctx.send("No mute role found.")

@tree.command(name="unmute", description="Unmute a member")
@app_commands.describe(member="Member to unmute")
async def unmute_slash(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("Need Manage Roles permission.", ephemeral=True)
        return
    role = discord.utils.get(interaction.guild.roles, name="Muted-by-bot")
    if role:
        await member.remove_roles(role)
        await interaction.response.send_message(f"🔊 {member} has been unmuted.")
    else:
        await interaction.response.send_message("No mute role found.", ephemeral=True)

# 9) warn
@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason: str = "None"):
    data = load_data()
    gw = data.setdefault("warns", {})
    gk = str(ctx.guild.id)
    gw.setdefault(gk, {})
    gw[gk].setdefault(str(member.id), []).append(reason)
    save_data(data)
    await ctx.send(f"⚠️ Warned {member}. Reason: {reason}")

@tree.command(name="warn", description="Warn a member")
@app_commands.describe(member="Member to warn", reason="Reason")
async def warn_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "None"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("Need Kick Members permission.", ephemeral=True)
        return
    data = load_data()
    gw = data.setdefault("warns", {})
    gk = str(interaction.guild.id)
    gw.setdefault(gk, {})
    gw[gk].setdefault(str(member.id), []).append(reason)
    save_data(data)
    await interaction.response.send_message(f"⚠️ Warned {member}. Reason: {reason}")

# 10) role add/remove
@bot.command()
@commands.has_permissions(manage_roles=True)
async def role_add(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"✅ Added role {role.name} to {member}.")

@tree.command(name="role_add", description="Add role to member")
@app_commands.describe(member="Target member", role="Role to add")
async def role_add_slash(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("Need Manage Roles permission.", ephemeral=True)
        return
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ Added role {role.name} to {member}.")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def role_remove(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f"✅ Removed role {role.name} from {member}.")

@tree.command(name="role_remove", description="Remove role from member")
@app_commands.describe(member="Target member", role="Role to remove")
async def role_remove_slash(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("Need Manage Roles permission.", ephemeral=True)
        return
    await member.remove_roles(role)
    await interaction.response.send_message(f"✅ Removed role {role.name} from {member}.")

# 11) slowmode
@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int = 0):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏱️ Slowmode set to {seconds}s")

@tree.command(name="slowmode", description="Set channel slowmode")
@app_commands.describe(seconds="Seconds")
async def slowmode_slash(interaction: discord.Interaction, seconds: int = 0):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Need Manage Channels permission.", ephemeral=True)
        return
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"⏱️ Slowmode set to {seconds}s")

# 12) prefix add (set server prefix)
@bot.command(name="prefix_add")
@commands.has_permissions(manage_guild=True)
async def prefix_add(ctx, new_prefix: str):
    data = load_data()
    data.setdefault("prefixes", {})[str(ctx.guild.id)] = new_prefix
    save_data(data)
    await ctx.send(f"✅ Prefix set to `{new_prefix}` for this server.")

@tree.command(name="prefix_add", description="Set server prefix")
@app_commands.describe(new_prefix="New prefix for server")
async def prefix_add_slash(interaction: discord.Interaction, new_prefix: str):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Guild permission.", ephemeral=True)
        return
    data = load_data()
    data.setdefault("prefixes", {})[str(interaction.guild.id)] = new_prefix
    save_data(data)
    await interaction.response.send_message(f"✅ Prefix set to `{new_prefix}` for this server.")

# 13/14) autoresponder add / remove / list
@bot.command(name="autorespond_add")
@commands.has_permissions(manage_guild=True)
async def autorespond_add(ctx, trigger: str, *, response: str):
    data = load_data()
    ar = data.setdefault("autoresponders", {})
    gk = str(ctx.guild.id)
    ar.setdefault(gk, []).append({"trigger": trigger, "response": response})
    save_data(data)
    await ctx.send(f"✅ Added autoresponder: when message contains `{trigger}` -> reply `{response}`")

@tree.command(name="autorespond_add", description="Add autoresponder")
@app_commands.describe(trigger="Trigger (substring)", response="Response text")
async def autorespond_add_slash(interaction: discord.Interaction, trigger: str, response: str):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Guild permission.", ephemeral=True)
        return
    data = load_data()
    ar = data.setdefault("autoresponders", {})
    gk = str(interaction.guild.id)
    ar.setdefault(gk, []).append({"trigger": trigger, "response": response})
    save_data(data)
    await interaction.response.send_message(f"✅ Added autoresponder for `{trigger}`")

@bot.command(name="autorespond_list")
@commands.has_permissions(manage_guild=True)
async def autorespond_list(ctx):
    data = load_data()
    ar = data.get("autoresponders", {}).get(str(ctx.guild.id), [])
    if not ar:
        await ctx.send("No autoresponders set.")
        return
    msg = "Autoresponders:\n"
    for i, e in enumerate(ar, 1):
        msg += f"{i}. `{e.get('trigger')}` -> `{e.get('response')}`\n"
    await ctx.send(msg)

@tree.command(name="autorespond_list", description="List autoresponders")
async def autorespond_list_slash(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Guild permission.", ephemeral=True)
        return
    data = load_data()
    ar = data.get("autoresponders", {}).get(str(interaction.guild.id), [])
    if not ar:
        await interaction.response.send_message("No autoresponders set.", ephemeral=True)
        return
    msg = "Autoresponders:\n"
    for i, e in enumerate(ar, 1):
        msg += f"{i}. `{e.get('trigger')}` -> `{e.get('response')}`\n"
    await interaction.response.send_message(msg, ephemeral=True)

@bot.command(name="autorespond_remove")
@commands.has_permissions(manage_guild=True)
async def autorespond_remove(ctx, index: int):
    data = load_data()
    entries = data.get("autoresponders", {}).get(str(ctx.guild.id), [])
    if 1 <= index <= len(entries):
        removed = entries.pop(index-1)
        save_data(data)
        await ctx.send(f"✅ Removed autoresponder: `{removed.get('trigger')}`")
    else:
        await ctx.send("Invalid index.")

@tree.command(name="autorespond_remove", description="Remove autoresponder by index")
@app_commands.describe(index="Index from /autorespond_list")
async def autorespond_remove_slash(interaction: discord.Interaction, index: int):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Guild permission.", ephemeral=True)
        return
    data = load_data()
    entries = data.get("autoresponders", {}).get(str(interaction.guild.id), [])
    if 1 <= index <= len(entries):
        removed = entries.pop(index-1)
        save_data(data)
        await interaction.response.send_message(f"✅ Removed autoresponder: `{removed.get('trigger')}`")
    else:
        await interaction.response.send_message("Invalid index.", ephemeral=True)

# 15) info
@bot.command()
async def info(ctx):
    await ctx.send(f"Bot: {bot.user}\nServers: {len(bot.guilds)}")

@tree.command(name="info", description="Bot info")
async def info_slash(interaction: discord.Interaction):
    await interaction.response.send_message(f"Bot: {bot.user}\nServers: {len(bot.guilds)}")

# 16) help (simple)
@bot.command()
async def help(ctx):
    txt = (
        "Basic commands: ping, say, clear, kick, ban, unban, lock, unlock, mute, unmute, warn,\n"
        "role_add, role_remove, slowmode, prefix_add, autorespond_add/list/remove, info\n"
        "Games are in /games (or use prefix commands; see commands list)."
    )
    await ctx.send(txt)

@tree.command(name="help", description="Show help")
async def help_slash(interaction: discord.Interaction):
    txt = (
        "Basic commands: ping, say, clear, kick, ban, unban, lock, unlock, mute, unmute, warn,\n"
        "role_add, role_remove, slowmode, prefix_add, autorespond_add/list/remove, info\n"
        "Games are in /games (or use prefix commands)."
    )
    await interaction.response.send_message(txt, ephemeral=True)

# 17) prefix show
@bot.command()
async def prefix(ctx):
    data = load_data()
    pref = data.get("prefixes", {}).get(str(ctx.guild.id), DEFAULT_PREFIX)
    await ctx.send(f"Prefix for this server: `{pref}`")

@tree.command(name="prefix", description="Show current prefix")
async def prefix_slash(interaction: discord.Interaction):
    data = load_data()
    pref = data.get("prefixes", {}).get(str(interaction.guild.id), DEFAULT_PREFIX)
    await interaction.response.send_message(f"Prefix for this server: `{pref}`", ephemeral=True)

# 18) whois (member info)
@bot.command()
async def whois(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"{member} — joined: {member.joined_at} — created: {member.created_at}")

@tree.command(name="whois", description="Member info")
@app_commands.describe(member="Member to inspect")
async def whois_slash(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    await interaction.response.send_message(f"{member} — joined: {member.joined_at} — created: {member.created_at}", ephemeral=True)

# 19) placeholder admin command (demonstration)
@bot.command()
@commands.has_permissions(administrator=True)
async def admin_cmd(ctx, *, text: str = "hi"):
    await ctx.send(f"Admin command executed: {text}")

@tree.command(name="admin_cmd", description="Placeholder admin command")
@app_commands.describe(text="Text")
async def admin_cmd_slash(interaction: discord.Interaction, text: str = "hi"):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Need Administrator permission.", ephemeral=True)
        return
    await interaction.response.send_message(f"Admin command executed: {text}")

# 20) shutdown (owner only)
@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    await bot.close()

@tree.command(name="shutdown", description="Shutdown bot (owner only)")
async def shutdown_slash(interaction: discord.Interaction):
    app_owner = await bot.application_info()
    if interaction.user.id != app_owner.owner.id:
        await interaction.response.send_message("Only bot owner can run this.", ephemeral=True)
        return
    await interaction.response.send_message("Shutting down...")
    await bot.close()

# =========================
#  Load token and run
# =========================
if __name__ == "__main__":
    ensure_data()
    TOKEN = os.getenv("TOKEN") or "YOUR_TOKEN_HERE"
    keep_alive()
    bot.run(TOKEN)

