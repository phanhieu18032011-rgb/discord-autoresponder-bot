import os
import asyncio
import json
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks
from aiohttp import web

# --------------------
# Configuration (use environment variables / secrets)
# --------------------
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', '0'))  # Discord user ID of the bot owner (for owner-only commands)
# warnings file removed
WARN_FILE = None
KEEP_ALIVE_PORT = int(os.getenv('KEEP_ALIVE_PORT', '8080'))

if not TOKEN:
    raise RuntimeError('DISCORD_TOKEN is not set in environment variables')

# --------------------
# Intents and bot setup
# --------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --------------------
# Helpers: persistence for warnings
# --------------------
def load_warnings():
    return {}

def save_warnings(data):
    pass

warnings_db = {}  # in-memory only

# --------------------
# Permission checks
# --------------------
def is_owner(ctx):
    return ctx.author.id == OWNER_ID

def mod_check():
    async def predicate(ctx):
        # allow if author has kick_members or manage_messages or administrator
        perms = ctx.author.guild_permissions
        return perms.kick_members or perms.ban_members or perms.manage_messages or perms.administrator
    return commands.check(predicate)

# --------------------
# Events
# --------------------
@bot.event
async def on_ready():
    print(f'Bot ready: {bot.user} (ID: {bot.user.id})')
    status_task.start()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('Bạn không có quyền sử dụng lệnh này.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Thiếu tham số bắt buộc cho lệnh.')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('Tham số sai kiểu hoặc không hợp lệ.')
    else:
        # For unexpected errors print to console and notify owner
        print('Unhandled error:', error)
        try:
            owner = await bot.fetch_user(OWNER_ID)
            await owner.send(f'Unhandled error in guild {ctx.guild} command {ctx.command}: {error}')
        except Exception:
            pass

# --------------------
# Status task (keeps bot activity updated)
# --------------------
@tasks.loop(minutes=10)
async def status_task():
    try:
        await bot.change_presence(activity=discord.Game(name=f'Practical moderation | Prefix: !'))
    except Exception:
        pass

# --------------------
# Moderation commands (30 commands) - some commands are grouped or aliased
# --------------------

@bot.command(name='ping')
async def ping(ctx):
    """Kiểm tra kết nối bot"""
    before = datetime.utcnow()
    msg = await ctx.send('Pinging...')
    latency_ms = round(bot.latency * 1000)
    after = datetime.utcnow()
    delta = (after - before).microseconds // 1000
    await msg.edit(content=f'Pong! WebSocket: {latency_ms}ms | Response: {delta}ms')

@bot.command(name='kick')
@mod_check()
async def kick(ctx, member: discord.Member, *, reason: str = 'No reason provided'):
    await member.kick(reason=reason)
    await ctx.send(f'Kicked {member} | {reason}')

@bot.command(name='ban')
@mod_check()
async def ban(ctx, member: discord.Member, *, reason: str = 'No reason provided'):
    await member.ban(reason=reason)
    await ctx.send(f'Banned {member} | {reason}')

@bot.command(name='unban')
@mod_check()
async def unban(ctx, user: discord.User, *, reason: str = 'No reason provided'):
    await ctx.guild.unban(user, reason=reason)
    await ctx.send(f'Unbanned {user} | {reason}')

@bot.command(name='tempban')
@mod_check()
async def tempban(ctx, member: discord.Member, days: int, *, reason: str = 'No reason provided'):
    await member.ban(reason=reason)
    await ctx.send(f'Temporarily banned {member} for {days} day(s) | {reason}')
    await asyncio.sleep(days * 24 * 3600)
    try:
        await ctx.guild.unban(member)
        await ctx.send(f'Lifted tempban for {member}')
    except Exception:
        pass

@bot.command(name='mute')
@mod_check()
async def mute(ctx, member: discord.Member, minutes: int = 0, *, reason: str = 'No reason provided'):
    # create or find role named "Muted"
    role = discord.utils.get(ctx.guild.roles, name='Muted')
    if not role:
        role = await ctx.guild.create_role(name='Muted')
        for ch in ctx.guild.channels:
            try:
                await ch.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
            except Exception:
                pass
    await member.add_roles(role, reason=reason)
    await ctx.send(f'Muted {member} | {reason}')
    if minutes > 0:
        await asyncio.sleep(minutes * 60)
        try:
            await member.remove_roles(role)
            await ctx.send(f'Auto-unmuted {member} after {minutes} minutes')
        except Exception:
            pass

@bot.command(name='unmute')
@mod_check()
async def unmute(ctx, member: discord.Member, *, reason: str = 'No reason provided'):
    role = discord.utils.get(ctx.guild.roles, name='Muted')
    if role:
        await member.remove_roles(role, reason=reason)
    await ctx.send(f'Unmuted {member} | {reason}')

@bot.command(name='purge')
@mod_check()
async def purge(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f'Deleted {len(deleted)} messages.', delete_after=5)

@bot.command(name='nick')
@mod_check()
async def nick(ctx, member: discord.Member, *, nickname: str = None):
    await member.edit(nick=nickname)
    await ctx.send(f'Changed nickname for {member} to {nickname}')

@bot.command(name='warn')
@mod_check()
async def warn(ctx, member: discord.Member, *, reason: str = 'Vi phạm'):
    guild_id = str(ctx.guild.id)
    member_id = str(member.id)
    guild_warns = warnings_db.setdefault(guild_id, {})
    user_warns = guild_warns.setdefault(member_id, [])
    entry = {'by': ctx.author.id, 'reason': reason, 'time': datetime.utcnow().isoformat()}
    user_warns.append(entry)
    save_warnings(warnings_db)
    await ctx.send(f'Warned {member}. Total warns: {len(user_warns)}')

@bot.command(name='warns')
@mod_check()
async def warns(ctx, member: discord.Member = None):
    member = member or ctx.author
    guild_id = str(ctx.guild.id)
    member_id = str(member.id)
    guild_warns = warnings_db.get(guild_id, {})
    user_warns = guild_warns.get(member_id, [])
    if not user_warns:
        await ctx.send(f'No warns for {member}.')
        return
    lines = []
    for i, w in enumerate(user_warns, 1):
        lines.append(f"{i}. By: {w['by']} Reason: {w['reason']} Time: {w['time']}")
    await ctx.send('\n'.join(lines))

@bot.command(name='clearwarns')
@mod_check()
async def clearwarns(ctx, member: discord.Member):
    guild_id = str(ctx.guild.id)
    member_id = str(member.id)
    guild_warns = warnings_db.get(guild_id, {})
    if member_id in guild_warns:
        del guild_warns[member_id]
        save_warnings(warnings_db)
    await ctx.send(f'Cleared warns for {member}.')

@bot.command(name='addrole')
@mod_check()
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f'Added role {role.name} to {member}')

@bot.command(name='removerole')
@mod_check()
async def removerole(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f'Removed role {role.name} from {member}')

@bot.command(name='lock')
@mod_check()
async def lock(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send(f'Locked {channel.mention}')

@bot.command(name='unlock')
@mod_check()
async def unlock(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = None
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send(f'Unlocked {channel.mention}')

@bot.command(name='slowmode')
@mod_check()
async def slowmode(ctx, seconds: int, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.edit(slowmode_delay=seconds)
    await ctx.send(f'Set slowmode to {seconds} seconds in {channel.mention}')

@bot.command(name='prune')
@mod_check()
async def prune(ctx, user: discord.Member, amount: int = 100):
    def is_user(m):
        return m.author.id == user.id
    deleted = await ctx.channel.purge(limit=amount, check=is_user)
    await ctx.send(f'Deleted {len(deleted)} messages from {user}', delete_after=5)

@bot.command(name='announce')
@mod_check()
async def announce(ctx, channel: discord.TextChannel, *, message: str):
    await channel.send(message)
    await ctx.send('Announcement sent.', delete_after=5)

@bot.command(name='slowban')
@mod_check()
async def slowban(ctx, member: discord.Member, delay_seconds: int = 5, *, reason: str = 'No reason'):
    await ctx.send(f'Banning {member} in {delay_seconds} seconds')
    await asyncio.sleep(delay_seconds)
    await member.ban(reason=reason)
    await ctx.send(f'Banned {member}')

@bot.command(name='clear')
@mod_check()
async def clear(ctx, amount: int = 1):
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f'Deleted {len(deleted)} messages.', delete_after=5)

@bot.command(name='serverinfo')
async def serverinfo(ctx):
    g = ctx.guild
    text = (
        f'Guild: {g.name}\n'
        f'ID: {g.id}\n'
        f'Members: {g.member_count}\n'
        f'Owner: {g.owner}\n'
        f'Created at: {g.created_at}\n'
    )
    await ctx.send(text)

@bot.command(name='userinfo')
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    text = (
        f'User: {member}\n'
        f'ID: {member.id}\n'
        f'Joined at: {member.joined_at}\n'
        f'Created at: {member.created_at}\n'
        f'Roles: {len(member.roles)-1}\n'
    )
    await ctx.send(text)

# Add small convenience aliases to reach roughly 30 moderation/admin operations
# alias commands: ban, unban, kick, mute, unmute, purge, prune, clear, warn, warns, clearwarns,
# addrole, removerole, nick, lock, unlock, slowmode, serverinfo, userinfo, announce, tempban, tempmute,
# slowban, ping, prune, kickban (alias to ban+kick), roleinfo, membercount

@bot.command(name='kickban')
@mod_check()
async def kickban(ctx, member: discord.Member, *, reason: str = 'No reason'):
    await member.kick(reason=reason)
    await member.ban(reason=reason)
    await ctx.send(f'Kickbanned {member} | {reason}')

@bot.command(name='roleinfo')
@mod_check()
async def roleinfo(ctx, role: discord.Role):
    await ctx.send(f'Role: {role.name} ID: {role.id} Members: {len(role.members)}')

@bot.command(name='membercount')
async def membercount(ctx):
    await ctx.send(f'Member count: {ctx.guild.member_count}')

# --------------------
# Owner-only commands (9 commands)
# --------------------

@bot.command(name='shutdown')
async def shutdown(ctx):
    if not is_owner(ctx):
        return await ctx.send('Chỉ owner mới dùng được lệnh này.')
    await ctx.send('Shutting down...')
    await bot.close()

@bot.command(name='restart')
async def restart(ctx):
    if not is_owner(ctx):
        return await ctx.send('Chỉ owner mới dùng được lệnh này.')
    await ctx.send('Restarting...')
    await bot.close()

@bot.command(name='dm_host')
async def dm_host(ctx, *, message: str):
    if not is_owner(ctx):
        return await ctx.send('Chỉ owner mới dùng được lệnh này.')
    try:
        owner = await bot.fetch_user(OWNER_ID)
        await owner.send(f'Message from bot owner via dm_host command:\n{message}')
        await ctx.send('Đã gửi tin nhắn tới host.')
    except Exception as e:
        await ctx.send(f'Gửi thất bại: {e}')

@bot.command(name='evalpy')
async def evalpy(ctx, *, code: str):
    if not is_owner(ctx):
        return await ctx.send('Chỉ owner mới dùng được lệnh này.')
    # Warning: executing code is dangerous. This command only for the bot owner.
    try:
        local = {'bot': bot, 'ctx': ctx, 'discord': discord, 'asyncio': asyncio}
        exec(f'async def __ex():\n' + '\n'.join(f'    {line}' for line in code.split('\n')), local)
        result = await local['__ex']()
        await ctx.send(f'Eval result: {result}')
    except Exception as e:
        await ctx.send(f'Eval error: {e}')

@bot.command(name='pull_logs')
async def pull_logs(ctx):
    if not is_owner(ctx):
        return await ctx.send('Chỉ owner mới dùng được lệnh này.')
    await ctx.send('Không còn file logs để gửi. warnings.json đã bị loại bỏ.')
    # Sends the warnings file as an example of pulling logs
    try:
        await ctx.send(file=discord.File(WARN_FILE))
    except Exception as e:
        await ctx.send(f'Gửi logs thất bại: {e}')

@bot.command(name='setgame')
async def setgame(ctx, *, text: str):
    if not is_owner(ctx):
        return await ctx.send('Chỉ owner mới dùng được lệnh này.')
    await bot.change_presence(activity=discord.Game(name=text))
    await ctx.send('Updated presence.')

@bot.command(name='evalraw')
async def evalraw(ctx, *, code: str):
    if not is_owner(ctx):
        return await ctx.send('Chỉ owner mới dùng được lệnh này.')
    try:
        result = eval(code)
        await ctx.send(f'Eval result: {result}')
    except Exception as e:
        await ctx.send(f'Eval error: {e}')

@bot.command(name='sendraw')
async def sendraw(ctx, channel_id: int, *, message: str):
    if not is_owner(ctx):
        return await ctx.send('Chỉ owner mới dùng được lệnh này.')
    ch = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
    await ch.send(message)
    await ctx.send('Sent message.')

@bot.command(name='reload_warnings')
async def reload_warnings(ctx):
    if not is_owner(ctx):
        return await ctx.send('Chỉ owner mới dùng được lệnh này.')
    global warnings_db
    warnings_db = load_warnings()
    await ctx.send('Reloaded warnings from disk.')

# That is 9 owner-only commands: shutdown, restart, dm_host, evalpy, pull_logs, setgame, evalraw, sendraw, reload_warnings

# --------------------
# Minimal help command
# --------------------
@bot.command(name='help')
async def help_cmd(ctx):
    lines = [
        'Commands overview:',
        'Moderation (examples): kick, ban, unban, tempban, mute, unmute, purge, prune, warn, warns, clearwarns, addrole, removerole, nick, lock, unlock, slowmode, announce, kickban, roleinfo, membercount, serverinfo, userinfo',
        'Owner only: shutdown, restart, dm_host, evalpy, pull_logs, setgame, evalraw, sendraw, reload_warnings',
        'Prefix: !'
    ]
    await ctx.send('\n'.join(lines))

# --------------------
# Keep-alive web server for Render / GitHub Pages / Uptime monitoring
# --------------------
async def handle_ping(request):
    return web.Response(text='OK')

async def start_webserver():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', KEEP_ALIVE_PORT)
    await site.start()
    print(f'Keep-alive web server started on port {KEEP_ALIVE_PORT}')

# --------------------
# Run both webserver and bot
# --------------------
async def main():
    await start_webserver()
    await bot.start(TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Interrupted')
