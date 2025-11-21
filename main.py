# main.py
import discord
from discord.ext import commands
import os
import requests
from flask import Flask
import threading

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

maintenance_mode = False

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

def is_owner():
    async def predicate(ctx):
        return ctx.author.id == int(os.getenv('OWNER_ID'))
    return commands.check(predicate)

@bot.check
async def check_maintenance(ctx):
    if maintenance_mode and ctx.author.id != int(os.getenv('OWNER_ID')):
        await ctx.send('maintenance mode on.')
        return False
    return True

@bot.event
async def on_ready():
    print(f'Logged: {bot.user}')

# Lenh 1: kick
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'kicker {member.mention}')

# Lenh 2: ban
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'banner {member.mention}')

# Lenh 3: unban
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member):
    async for ban_entry in ctx.guild.bans():
        user = ban_entry.user
        if str(user) == member:
            await ctx.guild.unban(user)
            await ctx.send(f'unbanner {user.mention}')
            return

# Lenh 4: mute
@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, speak=False, send_messages=False)
    await member.add_roles(muted_role, reason=reason)
    await ctx.send(f'muter {member.mention}')

# Lenh 5: unmute
@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    await member.remove_roles(muted_role)
    await ctx.send(f'unmuter {member.mention}')

# Lenh 6: warn
@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason):
    await ctx.send(f'warner {member.mention} {reason}')

# Lenh 7: warnings
@bot.command()
@commands.has_permissions(kick_members=True)
async def warnings(ctx, member: discord.Member):
    await ctx.send(f'warnings {member.mention}: 0')

# Lenh 8: clearwarns
@bot.command()
@commands.has_permissions(kick_members=True)
async def clearwarns(ctx, member: discord.Member):
    await ctx.send(f'clearwarns {member.mention}')

# Lenh 9: clear
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f'clear {amount}')

# Lenh 10: slowmode
@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f'slowmode {seconds}')

# Lenh 11: lock
@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send('lock channel')

# Lenh 12: unlock
@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send('unlock channel')

# Lenh 13: addrole
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f'addrole {role.name} {member.mention}')

# Lenh 14: removerole
@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f'removerole {role.name} {member.mention}')

# Lenh 15: nickname
@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nickname(ctx, member: discord.Member, *, nick):
    await member.edit(nick=nick)
    await ctx.send(f'nickname {member.mention} {nick}')

# Lenh 16: ping
@bot.command()
async def ping(ctx):
    await ctx.send(f'ping {round(bot.latency * 1000)}ms')

# Lenh 17: serverinfo
@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    await ctx.send(f'serverinfo {guild.name} {guild.member_count} {guild.id}')

# Lenh 18: userinfo
@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    await ctx.send(f'userinfo {member.name} {member.id} {member.created_at}')

# Lenh 19: channelinfo
@bot.command()
async def channelinfo(ctx):
    channel = ctx.channel
    await ctx.send(f'channelinfo {channel.name} {channel.id} {channel.type}')

# Lenh 20: roleinfo
@bot.command()
async def roleinfo(ctx, role: discord.Role):
    await ctx.send(f'roleinfo {role.name} {role.id} {len(role.members)}')

# Lenh 21: purgeuser
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgeuser(ctx, member: discord.Member, amount: int = 10):
    def check(m):
        return m.author == member
    await ctx.channel.purge(limit=amount, check=check)
    await ctx.send(f'purgeuser {member.mention} {amount}')

# Lenh 22: purgebot
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgebot(ctx, amount: int = 10):
    def check(m):
        return m.author.bot
    await ctx.channel.purge(limit=amount, check=check)
    await ctx.send(f'purgebot {amount}')

# Lenh 23: purgecontains
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgecontains(ctx, text: str, amount: int = 10):
    def check(m):
        return text in m.content
    await ctx.channel.purge(limit=amount, check=check)
    await ctx.send(f'purgecontains {text} {amount}')

# Lenh 24: purgestarts
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgestarts(ctx, text: str, amount: int = 10):
    def check(m):
        return m.content.startswith(text)
    await ctx.channel.purge(limit=amount, check=check)
    await ctx.send(f'purgestarts {text} {amount}')

# Lenh 25: purgeends
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgeends(ctx, text: str, amount: int = 10):
    def check(m):
        return m.content.endswith(text)
    await ctx.channel.purge(limit=amount, check=check)
    await ctx.send(f'purgeends {text} {amount}')

# Lenh 26: whois
@bot.command()
async def whois(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    await ctx.send(f'whois {member.name} {member.id} {member.created_at}')

# Lenh 27: avatar
@bot.command()
async def avatar(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    await ctx.send(member.display_avatar.url)

# Lenh 28: modlog
@bot.command()
@commands.has_permissions(administrator=True)
async def modlog(ctx):
    await ctx.send('modlog setup')

# Lenh 29: case
@bot.command()
@commands.has_permissions(kick_members=True)
async def case(ctx, case_id: int):
    await ctx.send(f'case {case_id} details')

# Lenh 30: botinfo
@bot.command()
async def botinfo(ctx):
    await ctx.send(f'botinfo {bot.user} {round(bot.latency * 1000)}ms {len(bot.guilds)}')

# Lenh 31: dm
@bot.command()
@is_owner()
async def dm(ctx, member: discord.Member, *, message):
    try:
        await member.send(message)
        await ctx.send(f'dm {member.mention}')
    except:
        await ctx.send('dm failed')

# Lenh 32: say
@bot.command()
@is_owner()
async def say(ctx, *, message):
    await ctx.message.delete()
    await ctx.send(message)

# Lenh 33: servers
@bot.command()
@is_owner()
async def servers(ctx):
    server_list = '\n'.join([f'{g.name}: {g.id}' for g in bot.guilds[:10]])
    await ctx.send(f'servers {len(bot.guilds)}\n{server_list}')

# Lenh 34: leave
@bot.command()
@is_owner()
async def leave(ctx, guild_id: int):
    guild = bot.get_guild(guild_id)
    if guild:
        await guild.leave()
        await ctx.send(f'leave {guild.name}')

# Lenh 35: broadcast
@bot.command()
@is_owner()
async def broadcast(ctx, *, message):
    success = 0
    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                await channel.send(message)
                success += 1
                break
            except:
                continue
    await ctx.send(f'broadcast {success}')

# Lenh 36: setavatar
@bot.command()
@is_owner()
async def setavatar(ctx, url: str):
    try:
        response = requests.get(url)
        await bot.user.edit(avatar=response.content)
        await ctx.send('setavatar done')
    except:
        await ctx.send('setavatar failed')

# Lenh 37: setname
@bot.command()
@is_owner()
async def setname(ctx, *, name: str):
    try:
        await bot.user.edit(username=name)
        await ctx.send(f'setname {name}')
    except:
        await ctx.send('setname failed')

# Lenh 38: maintenance
@bot.command()
@is_owner()
async def maintenance(ctx, mode: str):
    global maintenance_mode
    if mode.lower() == 'on':
        maintenance_mode = True
        await ctx.send('maintenance on')
    elif mode.lower() == 'off':
        maintenance_mode = False
        await ctx.send('maintenance off')

# Lenh 39: eval
@bot.command()
@is_owner()
async def eval(ctx, *, code):
    try:
        result = eval(code)
        await ctx.send(f'eval {result}')
    except Exception as e:
        await ctx.send(f'eval error {e}')

# Lenh 40: shutdown
@bot.command()
@is_owner()
async def shutdown(ctx):
    await ctx.send('shutdown')
    await bot.close()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f'error {str(error)}')

keep_alive()
bot.run(os.getenv('TOKEN'))
