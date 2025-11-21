# main.py
import discord
from discord.ext import commands
import os
import requests
from flask import Flask
import threading
import logging

# Cau hinh logging
logging.basicConfig(level=logging.INFO)

# Cau hinh bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)

# Maintenance mode
maintenance_mode = False

# Keep alive server
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def keep_alive():
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

# Owner check
def is_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id == int(os.getenv('OWNER_ID', 0))
    return discord.app_commands.check(predicate)

# Error handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    logging.error(f"Error: {error}")
    await ctx.send(f"error {str(error)}")

@bot.event
async def on_ready():
    logging.info(f'Bot ready: {bot.user}')
    logging.info(f'Servers: {len(bot.guilds)}')
    # Clear slash commands to prevent errors
    try:
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
    except:
        pass

# === 30 LENH MOD QUAN LI (PREFIX) ===

# Lệnh 1: kick
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'kick {member.mention}')

# Lệnh 2: ban
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'ban {member.mention}')

# Lệnh 3: unban
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member: str):
    async for ban_entry in ctx.guild.bans():
        user = ban_entry.user
        if str(user) == member:
            await ctx.guild.unban(user)
            await ctx.send(f'unban {user.mention}')
            return
    await ctx.send('user not found')

# Lệnh 4: mute
@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, speak=False, send_messages=False)
    await member.add_roles(muted_role, reason=reason)
    await ctx.send(f'mute {member.mention}')

# Lệnh 5: unmute
@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    await member.remove_roles(muted_role)
    await ctx.send(f'unmute {member.mention}')

# Lệnh 6: warn
@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason: str):
    await ctx.send(f'warn {member.mention} {reason}')

# Lệnh 7: warnings
@bot.command()
@commands.has_permissions(kick_members=True)
async def warnings(ctx, member: discord.Member):
    await ctx.send(f'warnings {member.mention} 0')

# Lệnh 8: clearwarns
@bot.command()
@commands.has_permissions(kick_members=True)
async def clearwarns(ctx, member: discord.Member):
    await ctx.send(f'clearwarns {member.mention}')

# Lệnh 9: clear
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f'clear {amount}')

# Lệnh 10: slowmode
@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f'slowmode {seconds}')

# Lệnh 11: lock
@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send('lock channel')

# Lệnh 12: unlock
@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send('unlock channel')

# Lệnh 13: addrole
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f'addrole {role.name} {member.mention}')

# Lệnh 14: removerole
@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f'removerole {role.name} {member.mention}')

# Lệnh 15: nickname
@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nickname(ctx, member: discord.Member, *, nick: str):
    await member.edit(nick=nick)
    await ctx.send(f'nickname {member.mention} {nick}')

# Lệnh 16: ping
@bot.command()
async def ping(ctx):
    await ctx.send(f'ping {round(bot.latency * 1000)}ms')

# Lệnh 17: serverinfo
@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    await ctx.send(f'serverinfo {guild.name} {guild.member_count} {guild.id}')

# Lệnh 18: userinfo
@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    await ctx.send(f'userinfo {member.name} {member.id} {member.created_at}')

# Lệnh 19: channelinfo
@bot.command()
async def channelinfo(ctx):
    channel = ctx.channel
    await ctx.send(f'channelinfo {channel.name} {channel.id} {channel.type}')

# Lệnh 20: roleinfo
@bot.command()
async def roleinfo(ctx, role: discord.Role):
    await ctx.send(f'roleinfo {role.name} {role.id} {len(role.members)}')

# Lệnh 21: purgeuser
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgeuser(ctx, member: discord.Member, amount: int = 10):
    def check(m):
        return m.author == member
    await ctx.channel.purge(limit=amount, check=check)
    await ctx.send(f'purgeuser {member.mention} {amount}')

# Lệnh 22: purgebot
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgebot(ctx, amount: int = 10):
    def check(m):
        return m.author.bot
    await ctx.channel.purge(limit=amount, check=check)
    await ctx.send(f'purgebot {amount}')

# Lệnh 23: purgecontains
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgecontains(ctx, text: str, amount: int = 10):
    def check(m):
        return text in m.content
    await ctx.channel.purge(limit=amount, check=check)
    await ctx.send(f'purgecontains {text} {amount}')

# Lệnh 24: purgestarts
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgestarts(ctx, text: str, amount: int = 10):
    def check(m):
        return m.content.startswith(text)
    await ctx.channel.purge(limit=amount, check=check)
    await ctx.send(f'purgestarts {text} {amount}')

# Lệnh 25: purgeends
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgeends(ctx, text: str, amount: int = 10):
    def check(m):
        return m.content.endswith(text)
    await ctx.channel.purge(limit=amount, check=check)
    await ctx.send(f'purgeends {text} {amount}')

# Lệnh 26: whois
@bot.command()
async def whois(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    await ctx.send(f'whois {member.name} {member.id}')

# Lệnh 27: avatar
@bot.command()
async def avatar(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    await ctx.send(f'avatar {member.display_avatar.url}')

# Lệnh 28: modlog
@bot.command()
@commands.has_permissions(administrator=True)
async def modlog(ctx):
    await ctx.send('modlog placeholder')

# Lệnh 29: case
@bot.command()
@commands.has_permissions(kick_members=True)
async def case(ctx, case_id: int):
    await ctx.send(f'case {case_id} placeholder')

# Lệnh 30: botinfo
@bot.command()
async def botinfo(ctx):
    await ctx.send(f'botinfo {bot.user} {round(bot.latency * 1000)}ms {len(bot.guilds)}')

# === 10 LENH SLASH CHO OWNER ===

# Lệnh 31: dm
@bot.tree.command(name='dm', description='dm user')
@is_owner()
async def dm_slash(interaction: discord.Interaction, member: discord.Member, message: str):
    try:
        await member.send(message)
        await interaction.response.send_message(f'dm {member.mention}', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'dm failed {str(e)}', ephemeral=True)

# Lệnh 32: say
@bot.tree.command(name='say', description='say message')
@is_owner()
async def say_slash(interaction: discord.Interaction, message: str):
    await interaction.response.send_message('done', ephemeral=True)
    await interaction.channel.send(message)

# Lệnh 33: servers
@bot.tree.command(name='servers', description='list servers')
@is_owner()
async def servers_slash(interaction: discord.Interaction):
    server_list = '\n'.join([f'{g.name}: {g.id}' for g in bot.guilds[:10]])
    await interaction.response.send_message(f'servers {len(bot.guilds)}\n{server_list}', ephemeral=True)

# Lệnh 34: leave
@bot.tree.command(name='leave', description='leave server')
@is_owner()
async def leave_slash(interaction: discord.Interaction, guild_id: str):
    guild = bot.get_guild(int(guild_id))
    if guild:
        await guild.leave()
        await interaction.response.send_message(f'leave {guild.name}', ephemeral=True)
    else:
        await interaction.response.send_message('guild not found', ephemeral=True)

# Lệnh 35: broadcast
@bot.tree.command(name='broadcast', description='broadcast message')
@is_owner()
async def broadcast_slash(interaction: discord.Interaction, message: str):
    await interaction.response.send_message('broadcasting', ephemeral=True)
    success = 0
    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                await channel.send(message)
                success += 1
                break
            except:
                continue
    await interaction.followup.send(f'broadcast {success} servers', ephemeral=True)

# Lệnh 36: setavatar
@bot.tree.command(name='setavatar', description='set bot avatar')
@is_owner()
async def setavatar_slash(interaction: discord.Interaction, url: str):
    try:
        response = requests.get(url, timeout=10)
        await bot.user.edit(avatar=response.content)
        await interaction.response.send_message('setavatar done', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'setavatar failed {str(e)}', ephemeral=True)

# Lệnh 37: setname
@bot.tree.command(name='setname', description='set bot username')
@is_owner()
async def setname_slash(interaction: discord.Interaction, name: str):
    try:
        await bot.user.edit(username=name)
        await interaction.response.send_message(f'setname {name}', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'setname failed {str(e)}', ephemeral=True)

# Lệnh 38: maintenance
@bot.tree.command(name='maintenance', description='toggle maintenance')
@is_owner()
async def maintenance_slash(interaction: discord.Interaction, mode: str):
    global maintenance_mode
    if mode.lower() == 'on':
        maintenance_mode = True
        await interaction.response.send_message('maintenance on', ephemeral=True)
    elif mode.lower() == 'off':
        maintenance_mode = False
        await interaction.response.send_message('maintenance off', ephemeral=True)
    else:
        await interaction.response.send_message('usage on/off', ephemeral=True)

# Lệnh 39: eval
@bot.tree.command(name='eval', description='evaluate code')
@is_owner()
async def eval_slash(interaction: discord.Interaction, code: str):
    try:
        result = eval(code)
        await interaction.response.send_message(f'eval {result}', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'eval error {e}', ephemeral=True)

# Lệnh 40: shutdown
@bot.tree.command(name='shutdown', description='shutdown bot')
@is_owner()
async def shutdown_slash(interaction: discord.Interaction):
    await interaction.response.send_message('shutdown', ephemeral=True)
    await bot.close()

# Chay bot
if __name__ == '__main__':
    keep_alive()
    token = os.getenv('TOKEN')
    if not token:
        print("TOKEN not found in environment variables!")
        exit(1)
    bot.run(token)
