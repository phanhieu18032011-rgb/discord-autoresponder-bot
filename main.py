import discord
from discord.ext import commands
import os
import asyncio
import datetime
from flask import Flask
from threading import Thread
import aiohttp  # Added for changeavatar command

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
bot.owner_id = int(os.getenv('OWNER_ID'))  # Added to set owner ID from environment variable

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

t = Thread(target=run_flask)
t.start()

start_time = datetime.datetime.utcnow()

@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')

# Command 1: kick (mod)
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'Kicked {member} for {reason}')

# Command 2: ban (mod)
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'Banned {member} for {reason}')

# Command 3: unban (mod)
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f'Unbanned {user}')

# Command 4: mute (mod)
@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, time: int):
    # Assume mute role exists with ID 1234567890, replace with actual
    mute_role = ctx.guild.get_role(1234567890)
    await member.add_roles(mute_role)
    await ctx.send(f'Muted {member} for {time} minutes')
    await asyncio.sleep(time * 60)
    await member.remove_roles(mute_role)

# Command 5: unmute (mod)
@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    # Assume mute role exists with ID 1234567890, replace with actual
    mute_role = ctx.guild.get_role(1234567890)
    await member.remove_roles(mute_role)
    await ctx.send(f'Unmuted {member}')

# Command 6: warn (mod)
@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason=None):
    await ctx.send(f'Warned {member} for {reason}')
    # Log to mod channel or db, simplified

# Command 7: clear (mod)
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f'Cleared {amount} messages')

# Command 8: slowmode (mod)
@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f'Slowmode set to {seconds} seconds')

# Command 9: lock (mod)
@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send('Channel locked')

# Command 10: unlock (mod)
@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send('Channel unlocked')

# Command 11: addrole (mod)
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f'Added {role} to {member}')

# Command 12: removerole (mod)
@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f'Removed {role} from {member}')

# Command 13: nick (mod)
@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nick(ctx, member: discord.Member, *, new_nick):
    await member.edit(nick=new_nick)
    await ctx.send(f'Changed nick of {member} to {new_nick}')

# Command 14: poll (mod)
@bot.command()
@commands.has_permissions(manage_messages=True)
async def poll(ctx, question, *options):
    if len(options) > 10:
        await ctx.send('Max 10 options')
        return
    msg = await ctx.send(f'Poll: {question}\n' + '\n'.join(f'{i+1}. {opt}' for i, opt in enumerate(options)))
    for i in range(len(options)):
        await msg.add_reaction(str(i+1))

# Command 15: announce (mod)
@bot.command()
@commands.has_permissions(manage_messages=True)
async def announce(ctx, *, message):
    # Assume announce channel ID 1234567890, replace
    channel = bot.get_channel(1234567890)
    await channel.send(message)

# Command 16: timeout (mod)
@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int):
    until = datetime.timedelta(minutes=minutes)
    await member.timeout(until=until)
    await ctx.send(f'Timed out {member} for {minutes} minutes')

# Command 17: untimeout (mod)
@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    await member.timeout(until=None)
    await ctx.send(f'Removed timeout from {member}')

# Command 18: purge (mod)
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f'Purged {amount} messages')

# Command 19: report (mod)
@bot.command()
async def report(ctx, member: discord.Member, *, reason):
    # Assume mod channel ID 1234567890
    channel = bot.get_channel(1234567890)
    await channel.send(f'Report: {member} for {reason} by {ctx.author}')

# Command 20: modlog (mod)
@bot.command()
@commands.has_permissions(manage_messages=True)
async def modlog(ctx, member: discord.Member):
    await ctx.send(f'Mod log for {member}: (simplified, no actual log)')

# Command 21: serverinfo (mod)
@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    await ctx.send(f'Server: {guild.name}, Members: {guild.member_count}, Created: {guild.created_at}')

# Command 22: userinfo (mod)
@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f'User: {member}, Joined: {member.joined_at}, Created: {member.created_at}')

# Command 23: channelinfo (mod)
@bot.command()
async def channelinfo(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await ctx.send(f'Channel: {channel.name}, Created: {channel.created_at}, Position: {channel.position}')

# Command 24: invite (mod)
@bot.command()
@commands.has_permissions(create_instant_invite=True)
async def invite(ctx):
    invite = await ctx.channel.create_invite()
    await ctx.send(f'Invite: {invite.url}')

# Command 25: ping (mod)
@bot.command()
async def ping(ctx):
    await ctx.send(f'Ping: {round(bot.latency * 1000)}ms')

# Command 26: uptime (mod)
@bot.command()
async def uptime(ctx):
    now = datetime.datetime.utcnow()
    delta = now - start_time
    await ctx.send(f'Uptime: {delta}')

# Command 27: helpmod (mod)
@bot.command()
async def helpmod(ctx):
    await ctx.send('List of mod commands: kick, ban, etc. (simplified)')

# Command 28: rules (mod)
@bot.command()
@commands.has_permissions(manage_messages=True)
async def rules(ctx, *, rules_text):
    await ctx.send(f'Rules updated: {rules_text}')

# Command 29: setwelcome (mod)
@bot.command()
@commands.has_permissions(manage_channels=True)
async def setwelcome(ctx, *, message):
    await ctx.send(f'Welcome message set to: {message}')

# Command 30: setgoodbye (mod)
@bot.command()
@commands.has_permissions(manage_channels=True)
async def setgoodbye(ctx, *, message):
    await ctx.send(f'Goodbye message set to: {message}')

# Command 31: dm (owner)
@bot.command()
@commands.is_owner()
async def dm(ctx, member: discord.Member, *, message):
    await member.send(message)
    await ctx.send(f'DM sent to {member}')

# Command 32: say (owner)
@bot.command()
@commands.is_owner()
async def say(ctx, channel: discord.TextChannel, *, message):
    await channel.send(message)
    await ctx.send('Message sent')

# Command 33: shutdown (owner)
@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    await ctx.send('Shutting down')
    await bot.close()

# Command 34: setstatus (owner)
@bot.command()
@commands.is_owner()
async def setstatus(ctx, *, status):
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(status))
    await ctx.send(f'Status set to {status}')

# Command 35: setactivity (owner)
@bot.command()
@commands.is_owner()
async def setactivity(ctx, *, activity):
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=activity))
    await ctx.send(f'Activity set to {activity}')

# Command 36: changename (owner)
@bot.command()
@commands.is_owner()
async def changename(ctx, *, new_name):
    await bot.user.edit(username=new_name)
    await ctx.send(f'Name changed to {new_name}')

# Command 37: changeavatar (owner)
@bot.command()
@commands.is_owner()
async def changeavatar(ctx, url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return await ctx.send('Failed')
            data = await resp.read()
            await bot.user.edit(avatar=data)
    await ctx.send('Avatar changed')

# Command 38: eval (owner)
@bot.command()
@commands.is_owner()
async def eval(ctx, *, code):
    try:
        result = eval(code)
        await ctx.send(f'Result: {result}')
    except Exception as e:
        await ctx.send(f'Error: {e}')

# Command 39: exec (owner)
@bot.command()
@commands.is_owner()
async def exec(ctx, *, code):
    try:
        exec(code)
        await ctx.send('Executed')
    except Exception as e:
        await ctx.send(f'Error: {e}')

# Command 40: broadcast (owner)
@bot.command()
@commands.is_owner()
async def broadcast(ctx, *, message):
    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                await channel.send(message)
                break
            except:
                pass
    await ctx.send('Broadcast sent')

bot.run(os.getenv('TOKEN'))
