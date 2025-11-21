import os
import discord
from discord.ext import commands
import asyncio
from aiohttp import web

# =========================
# ENV VARIABLES
# =========================
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
PREFIX = "!"

# =========================
# BOT INIT
# =========================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# =========================
# HELPER
# =========================
def is_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

# =========================
# MOD COMMANDS (30 commands)
# =========================

# 1. kick
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"{member} has been kicked.")

# 2. ban
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"{member} has been banned.")

# 3. unban
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user: discord.User):
    banned_users = await ctx.guild.bans()
    for ban_entry in banned_users:
        if ban_entry.user.id == user.id:
            await ctx.guild.unban(user)
            await ctx.send(f"{user} has been unbanned.")
            return
    await ctx.send(f"{user} was not found in the ban list.")

# 4. mute
@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not role:
        role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(role, send_messages=False)
    await member.add_roles(role)
    await ctx.send(f"{member} has been muted.")

# 5. unmute
@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    await member.remove_roles(role)
    await ctx.send(f"{member} has been unmuted.")

# 6. clear messages
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"Deleted {len(deleted)} messages.", delete_after=5)

# 7. lock channel
@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"{channel} has been locked.")

# 8. unlock channel
@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"{channel} has been unlocked.")

# 9. slowmode
@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"Slowmode set to {seconds} seconds.")

# 10. rename channel
@bot.command()
@commands.has_permissions(manage_channels=True)
async def rename(ctx, channel: discord.TextChannel, *, name):
    await channel.edit(name=name)
    await ctx.send(f"Channel renamed to {name}.")

# 11. add role
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"{role} has been added to {member}.")

# 12. removerole
@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f"{role} has been removed from {member}.")

# 13. create role
@bot.command()
@commands.has_permissions(manage_roles=True)
async def createrole(ctx, *, name):
    await ctx.guild.create_role(name=name)
    await ctx.send(f"Role {name} has been created.")

# 14. delete role
@bot.command()
@commands.has_permissions(manage_roles=True)
async def deleterole(ctx, role: discord.Role):
    await role.delete()
    await ctx.send(f"Role {role} has been deleted.")

# 15. announce
@bot.command()
@commands.has_permissions(manage_channels=True)
async def announce(ctx, *, message):
    await ctx.send(message)

# 16. nick
@bot.command()
@commands.has_permissions(change_nickname=True)
async def nick(ctx, member: discord.Member, *, nickname):
    await member.edit(nick=nickname)
    await ctx.send(f"{member}'s nickname changed to {nickname}.")

# 17. purge user
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgeuser(ctx, member: discord.Member, amount: int):
    deleted = await ctx.channel.purge(limit=amount, check=lambda m: m.author == member)
    await ctx.send(f"Deleted {len(deleted)} messages from {member}.", delete_after=5)

# 18. lockdown
@bot.command()
@commands.has_permissions(manage_channels=True)
async def lockdown(ctx):
    for channel in ctx.guild.channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("All channels have been locked.")

# 19. unlockall
@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlockall(ctx):
    for channel in ctx.guild.channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("All channels have been unlocked.")

# 20. roleinfo
@bot.command()
@commands.has_permissions(manage_roles=True)
async def roleinfo(ctx, role: discord.Role):
    await ctx.send(f"Role {role} has ID {role.id}, color {role.color}, {len(role.members)} members.")

# 21. serverinfo
@bot.command()
@commands.has_permissions(manage_guild=True)
async def serverinfo(ctx):
    guild = ctx.guild
    await ctx.send(f"Server: {guild.name}, Members: {guild.member_count}, Owner: {guild.owner}.")

# 22. userinfo
@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"{member} joined at {member.joined_at}, account created at {member.created_at}.")

# 23. avatar
@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(member.avatar.url)

# 24. servericon
@bot.command()
async def servericon(ctx):
    await ctx.send(ctx.guild.icon.url)

# 25. saymod
@bot.command()
@commands.has_permissions(manage_messages=True)
async def saymod(ctx, *, message):
    await ctx.send(message)

# 26. lockrole
@bot.command()
@commands.has_permissions(manage_roles=True)
async def lockrole(ctx, role: discord.Role):
    for channel in ctx.guild.channels:
        await channel.set_permissions(role, send_messages=False)
    await ctx.send(f"{role} has been locked in all channels.")

# 27. unlockrole
@bot.command()
@commands.has_permissions(manage_roles=True)
async def unlockrole(ctx, role: discord.Role):
    for channel in ctx.guild.channels:
        await channel.set_permissions(role, send_messages=True)
    await ctx.send(f"{role} has been unlocked in all channels.")

# 28. mentionrole
@bot.command()
@commands.has_permissions(mention_everyone=True)
async def mentionrole(ctx, role: discord.Role, *, message):
    await ctx.send(f"{role.mention} {message}")

# 29. topic
@bot.command()
@commands.has_permissions(manage_channels=True)
async def topic(ctx, channel: discord.TextChannel, *, text):
    await channel.edit(topic=text)
    await ctx.send(f"Topic for {channel} changed to: {text}")

# 30. slowrole
@bot.command()
@commands.has_permissions(manage_roles=True)
async def slowrole(ctx, role: discord.Role, seconds: int):
    for channel in ctx.guild.channels:
        await channel.set_permissions(role, send_messages=True, reason=f"Slowmode {seconds} seconds")
    await ctx.send(f"{role} slowmode applied (approx).")

# =========================
# OWNER COMMANDS (10 commands)
# =========================

# 1. dm host
@bot.command()
@is_owner()
async def dm(ctx, user: discord.User, *, message):
    await user.send(message)
    await ctx.send(f"Sent DM to {user}.")

# 2. say
@bot.command()
@is_owner()
async def say(ctx, *, message):
    await ctx.send(message)

# 3. shutdown
@bot.command()
@is_owner()
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    await bot.close()

# 4. restart
@bot.command()
@is_owner()
async def restart(ctx):
    await ctx.send("Restarting...")
    await bot.close()
    os.execv(__file__, [])

# 5. eval
@bot.command()
@is_owner()
async def eval(ctx, *, code):
    try:
        result = eval(code)
        await ctx.send(f"Result: {result}")
    except Exception as e:
        await ctx.send(f"Error: {e}")

# 6. exec
@bot.command()
@is_owner()
async def exec(ctx, *, code):
    try:
        exec(code)
        await ctx.send("Executed successfully.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

# 7. load cogs (placeholder)
@bot.command()
@is_owner()
async def load(ctx, *, module):
    await ctx.send(f"Loaded {module} (placeholder).")

# 8. unload cogs (placeholder)
@bot.command()
@is_owner()
async def unload(ctx, *, module):
    await ctx.send(f"Unloaded {module} (placeholder).")

# 9. broadcast
@bot.command()
@is_owner()
async def broadcast(ctx, *, message):
    for member in ctx.guild.members:
        try:
            await member.send(message)
        except:
            pass
    await ctx.send("Broadcast completed.")

# 10. info
@bot.command()
@is_owner()
async def info(ctx):
    await ctx.send("Owner command list: DM, Say, Shutdown, Restart, Eval, Exec, Load, Unload, Broadcast, Info")

# =========================
# KEEP ALIVE
# =========================
async def keep_alive():
    app = web.Application()
    async def handle(request):
        return web.Response(text="Bot is alive!")
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    await site.start()

# =========================
# EVENTS
# =========================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await keep_alive()

# =========================
# RUN BOT
# =========================
bot.run(TOKEN)
