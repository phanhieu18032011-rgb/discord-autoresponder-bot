import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiohttp
from aiohttp import web

# =========================
# ENV
# =========================
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
PREFIX = "!"

# =========================
# BOT INIT
# =========================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
tree = bot.tree

# =========================
# KEEP ALIVE SERVER
# =========================
async def handle_root(request):
    return web.Response(text="Bot alive")

async def start_keep_alive():
    app = web.Application()
    app.router.add_get('/', handle_root)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("KEEP_ALIVE_PORT", "8080")))
    await site.start()

# =========================
# HELPERS
# =========================
def is_owner_ctx(ctx):
    return ctx.author.id == OWNER_ID

def is_owner_inter(interaction):
    return interaction.user.id == OWNER_ID

# ==============================
# 30 PREFIX MOD COMMANDS (!)
# ==============================
# 1
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    await ctx.send(f"Kicked {member} Reason: {reason}")

# 2
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await ctx.send(f"Banned {member} Reason: {reason}")

# 3
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user: str):
    banned = await ctx.guild.bans()
    name, discrim = user.split("#")
    for entry in banned:
        if entry.user.name == name and entry.user.discriminator == discrim:
            await ctx.guild.unban(entry.user)
            return await ctx.send(f"Unbanned {entry.user}")
    await ctx.send("User not found")

# 4
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount+1)
    await ctx.send(f"Cleared {amount} messages")

# 5
@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("Channel locked")

# 6
@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("Channel unlocked")

# 7
@bot.command()
async def ping(ctx):
    await ctx.send(f"Ping {round(bot.latency*1000)} ms")

# 8
@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nick(ctx, member: discord.Member, *, name):
    await member.edit(nick=name)
    await ctx.send("Nickname updated")

# 9
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send("Role added")

# 10
@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send("Role removed")

# 11
@bot.command()
async def server(ctx):
    g = ctx.guild
    await ctx.send(f"Server name: {g.name} Members: {g.member_count}")

# 12
@bot.command()
async def user(ctx, member: discord.Member=None):
    member = member or ctx.author
    await ctx.send(f"User: {member} ID: {member.id}")

# 13
@bot.command()
async def avatar(ctx, member: discord.Member=None):
    member = member or ctx.author
    await ctx.send(member.display_avatar.url)

# 14
@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"Slowmode {seconds}s")

# 15
@bot.command()
@commands.has_permissions(manage_guild=True)
async def setname(ctx, *, name):
    await ctx.guild.edit(name=name)
    await ctx.send("Server name updated")

# 16
@bot.command()
@commands.has_permissions(manage_channels=True)
async def topic(ctx, *, text):
    await ctx.channel.edit(topic=text)
    await ctx.send("Topic updated")

# 17
@bot.command()
async def id(ctx, member: discord.Member=None):
    member = member or ctx.author
    await ctx.send(str(member.id))

# 18
@bot.command()
async def channelid(ctx):
    await ctx.send(str(ctx.channel.id))

# 19
@bot.command()
async def serverid(ctx):
    await ctx.send(str(ctx.guild.id))

# 20
@bot.command()
async def roleid(ctx, role: discord.Role):
    await ctx.send(str(role.id))

# 21
@bot.command()
@commands.has_permissions(manage_messages=True)
async def pin(ctx):
    ref = ctx.message.reference
    if not ref:
        return await ctx.send("Reply to pin")
    msg = await ctx.channel.fetch_message(ref.message_id)
    await msg.pin()
    await ctx.send("Pinned")

# 22
@bot.command()
@commands.has_permissions(manage_messages=True)
async def unpin(ctx):
    ref = ctx.message.reference
    if not ref:
        return await ctx.send("Reply to unpin")
    msg = await ctx.channel.fetch_message(ref.message_id)
    await msg.unpin()
    await ctx.send("Unpinned")

# 23
@bot.command()
async def uptime(ctx):
    await ctx.send("Bot running")

# 24
@bot.command()
async def members(ctx):
    await ctx.send(f"Members: {ctx.guild.member_count}")

# 25
@bot.command()
@commands.has_permissions(kick_members=True)
async def softban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await member.unban()
    await ctx.send(f"Softbanned {member}")

# 26
@bot.command()
async def bots(ctx):
    count = sum(1 for m in ctx.guild.members if m.bot)
    await ctx.send(f"Bots: {count}")

# 27
@bot.command()
async def humans(ctx):
    count = sum(1 for m in ctx.guild.members if not m.bot)
    await ctx.send(f"Humans: {count}")

# 28
@bot.command()
async def pingrole(ctx, role: discord.Role):
    await ctx.send(role.mention)

# 29
@bot.command()
@commands.has_permissions(manage_channels=True)
async def clone(ctx):
    ch = await ctx.channel.clone()
    await ctx.send(f"Cloned {ch.name}")

# 30
@bot.command()
async def info(ctx):
    await ctx.send("Moderation bot active")

# ==========================
# OWNER SLASH COMMANDS (9)
# ==========================
@tree.command(name="shutdown", description="Shutdown bot")
async def shutdown(interaction):
    if not is_owner_inter(interaction):
        return await interaction.response.send_message("Owner only")
    await interaction.response.send_message("Shutting down")
    await bot.close()

@tree.command(name="restart", description="Restart bot")
async def restart(interaction):
    if not is_owner_inter(interaction):
        return await interaction.response.send_message("Owner only")
    await interaction.response.send_message("Restarting")
    await bot.close()

@tree.command(name="dm_host", description="DM host owner")
async def dm_host(interaction, message: str):
    if not is_owner_inter(interaction):
        return await interaction.response.send_message("Owner only")
    user = bot.get_user(OWNER_ID)
    if user:
        await user.send(message)
    await interaction.response.send_message("Sent")

@tree.command(name="evalpy", description="Eval python")
async def evalpy(interaction, code: str):
    if not is_owner_inter(interaction):
        return await interaction.response.send_message("Owner only")
    try:
        result = eval(code)
        await interaction.response.send_message(str(result))
    except Exception as e:
        await interaction.response.send_message(str(e))

@tree.command(name="evalraw", description="Exec python code")
async def evalraw(interaction, code: str):
    if not is_owner_inter(interaction):
        return await interaction.response.send_message(
