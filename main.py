# main.py
import discord
from discord.ext import commands, tasks
import os
import asyncio
from flask import Flask
from threading import Thread

# --------------------
# KEEP ALIVE SERVER
# --------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --------------------
# BOT SETUP
# --------------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Load token from environment variable (set in Render secrets)
TOKEN = os.environ.get('DISCORD_TOKEN')

# --------------------
# MODERATION COMMANDS (30)
# --------------------

# 1. kick
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"{member} was kicked. Reason: {reason}")

# 2. ban
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"{member} was banned. Reason: {reason}")

# 3. unban
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member):
    banned_users = await ctx.guild.bans()
    member_name, member_discriminator = member.split('#')
    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (member_name, member_discriminator):
            await ctx.guild.unban(user)
            await ctx.send(f"{user} was unbanned")
            return

# 4. mute
@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not role:
        role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(role, speak=False, send_messages=False)
    await member.add_roles(role)
    await ctx.send(f"{member} has been muted")

# 5. unmute
@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    await member.remove_roles(role)
    await ctx.send(f"{member} has been unmuted")

# 6. clear
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"Deleted {amount} messages", delete_after=5)

# 7. warn
@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason=None):
    await ctx.send(f"{member} was warned. Reason: {reason}")

# 8. lockdown
@bot.command()
@commands.has_permissions(manage_channels=True)
async def lockdown(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"{channel} is now in lockdown mode")

# 9. unlock
@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"{channel} is now unlocked")

# 10. slowmode
@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.edit(slowmode_delay=seconds)
    await ctx.send(f"Slowmode set to {seconds} seconds")

# 11. announce
@bot.command()
@commands.has_permissions(manage_channels=True)
async def announce(ctx, *, message):
    await ctx.send(f"Announcement: {message}")

# 12. addrole
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"Added {role} to {member}")

# 13. removerole
@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f"Removed {role} from {member}")

# 14. createtext
@bot.command()
@commands.has_permissions(manage_channels=True)
async def createtext(ctx, name):
    await ctx.guild.create_text_channel(name)
    await ctx.send(f"Text channel {name} created")

# 15. createvoice
@bot.command()
@commands.has_permissions(manage_channels=True)
async def createvoice(ctx, name):
    await ctx.guild.create_voice_channel(name)
    await ctx.send(f"Voice channel {name} created")

# 16. deletechannel
@bot.command()
@commands.has_permissions(manage_channels=True)
async def deletechannel(ctx, channel: discord.TextChannel):
    await channel.delete()
    await ctx.send(f"{channel} deleted")

# 17. nickname
@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nickname(ctx, member: discord.Member, *, name):
    await member.edit(nick=name)
    await ctx.send(f"{member}'s nickname changed to {name}")

# 18. whois
@bot.command()
async def whois(ctx, member: discord.Member):
    await ctx.send(f"{member} info: ID: {member.id}, Name: {member.name}, Joined: {member.joined_at}")

# 19. serverinfo
@bot.command()
async def serverinfo(ctx):
    await ctx.send(f"Server: {ctx.guild.name}, Members: {ctx.guild.member_count}, Owner: {ctx.guild.owner}")

# 20. membercount
@bot.command()
async def membercount(ctx):
    await ctx.send(f"Member count: {ctx.guild.member_count}")

# 21. avatar
@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(member.avatar.url)

# 22. roleinfo
@bot.command()
async def roleinfo(ctx, role: discord.Role):
    await ctx.send(f"Role: {role.name}, ID: {role.id}, Members: {len(role.members)}")

# 23. listroles
@bot.command()
async def listroles(ctx):
    roles = [role.name for role in ctx.guild.roles]
    await ctx.send("Roles: " + ", ".join(roles))

# 24. channels
@bot.command()
async def channels(ctx):
    ch_list = [ch.name for ch in ctx.guild.channels]
    await ctx.send("Channels: " + ", ".join(ch_list))

# 25. bans
@bot.command()
@commands.has_permissions(ban_members=True)
async def bans(ctx):
    banned_users = await ctx.guild.bans()
    await ctx.send(f"Banned users: {[user.user.name for user in banned_users]}")

# 26. boosts
@bot.command()
async def boosts(ctx):
    await ctx.send(f"Server boosts: {ctx.guild.premium_subscription_count}")

# 27. emojis
@bot.command()
async def emojis(ctx):
    await ctx.send(f"Emojis: {[emoji.name for emoji in ctx.guild.emojis]}")

# 28. ping
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")

# 29. info
@bot.command()
async def info(ctx):
    await ctx.send(f"Bot Name: {bot.user.name}, ID: {bot.user.id}")

# 30. invite
@bot.command()
async def invite(ctx):
    await ctx.send("Bot invite: [your bot invite link here]")

# --------------------
# OWNER ONLY COMMANDS (10)
# --------------------
OWNER_ID = int(os.environ.get("OWNER_ID", 0))

def is_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

# 1. dm
@bot.command()
@is_owner()
async def dm(ctx, member: discord.Member, *, message):
    await member.send(message)
    await ctx.send(f"Message sent to {member}")

# 2. say
@bot.command()
@is_owner()
async def say(ctx, *, message):
    await ctx.send(message)

# 3. load
@bot.command()
@is_owner()
async def load(ctx, extension):
    bot.load_extension(extension)
    await ctx.send(f"Loaded {extension}")

# 4. unload
@bot.command()
@is_owner()
async def unload(ctx, extension):
    bot.unload_extension(extension)
    await ctx.send(f"Unloaded {extension}")

# 5. reload
@bot.command()
@is_owner()
async def reload(ctx, extension):
    bot.reload_extension(extension)
    await ctx.send(f"Reloaded {extension}")

# 6. shutdown
@bot.command()
@is_owner()
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    await bot.close()

# 7. eval
@bot.command()
@is_owner()
async def eval(ctx, *, code):
    try:
        result = eval(code)
        await ctx.send(f"Result: {result}")
    except Exception as e:
        await ctx.send(f"Error: {e}")

# 8. exec
@bot.command()
@is_owner()
async def exec(ctx, *, code):
    try:
        exec(code)
        await ctx.send("Code executed")
    except Exception as e:
        await ctx.send(f"Error: {e}")

# 9. restart
@bot.command()
@is_owner()
async def restart(ctx):
    await ctx.send("Restarting bot...")
    await bot.close()
    os.system("python main.py")

# 10. secret
@bot.command()
@is_owner()
async def secret(ctx):
    await ctx.send("This is an owner-only secret command")

# --------------------
# RUN BOT
# --------------------
keep_alive()
bot.run(TOKEN)
