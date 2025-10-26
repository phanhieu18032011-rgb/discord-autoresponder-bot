import discord
from discord.ext import commands
import asyncio
import aiohttp
import subprocess
import os
import sys
import threading
import json
import requests
from flask import Flask
from threading import Thread
import time
import datetime
from collections import defaultdict
import psutil

# WEB SERVER FOR PORT BINDING
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🤖 SHADOW HOSTING SYSTEM - ONLINE"

@web_app.route('/delta')
def delta_status():
    return "🔓 DELTA BYPASS ACTIVE"

def run_web_server():
    web_app.run(host='0.0.0.0', port=8080, debug=False)

# START WEB SERVER
web_thread = Thread(target=run_web_server, daemon=True)
web_thread.start()

# SHADOW CORE CONFIG
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=['/', '!'], intents=intents, help_command=None)

class DeltaBypassSystem:
    def __init__(self):
        self.active_tokens = {}
        self.user_log_channels = {}
        self.bypass_script = """
import discord
from discord.ext import commands
import asyncio
import requests
import json
import time
import datetime

# DELTA CLIENT BYPASS PROTOCOL
class DeltaBypass:
    def __init__(self, token):
        self.token = token
        self.session = requests.Session()
        self.bypass_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDExIiwib3NfdmVyc2lvbiI6IjEwLjAuMjI2MjEiLCJvc19hcmNoIjoieDY0Iiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiY2xpZW50X2J1aWxkX251bWJlciI6MjMwMDAwLCJuYXRpdmVfYnVpbGRfbnVtYmVyIjo0MDAzOCwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0=',
            'X-Fingerprint': 'NULL_BYPASS_DELTA_SHADOW_CORE'
        }
    
    def bypass_verification(self):
        '''Bypass client verification checks'''
        try:
            # Mock verification endpoint
            url = f"https://discord.com/api/v9/users/@me"
            response = self.session.get(url, headers={
                **self.bypass_headers,
                'Authorization': self.token
            })
            return response.status_code == 200
        except:
            return True
    
    def emulate_delta_client(self):
        '''Emulate Delta client behavior'''
        gateway_data = {
            "op": 2,
            "d": {
                "token": self.token,
                "properties": {
                    "$os": "windows",
                    "$browser": "Discord Client",
                    "$device": "desktop",
                    "$referrer": "",
                    "$referring_domain": ""
                },
                "compress": False,
                "large_threshold": 250,
                "v": 3
            }
        }
        return gateway_data

# SHADOW BYPASS BOT
def create_bypass_bot(token, log_webhook_url=None):
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
    
    bypass = DeltaBypass(token)
    start_time = time.time()
    current_status = "online"
    current_activity = "Delta Bypass Active"

    def get_uptime():
        uptime_seconds = int(time.time() - start_time)
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        return f"{days}d {hours}h {minutes}m {seconds}s"

    async def send_log(description, color=0x0099ff):
        '''Send log to webhook'''
        if log_webhook_url:
            embed = discord.Embed(
                title="📊 BOT LOG",
                description=description,
                color=color,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="⏱️ Uptime", value=get_uptime(), inline=True)
            embed.add_field(name="🔧 Status", value=current_status.upper(), inline=True)
            embed.add_field(name="🎮 Activity", value=current_activity, inline=True)
            
            try:
                async with aiohttp.ClientSession() as session:
                    webhook = discord.Webhook.from_url(log_webhook_url, session=session)
                    await webhook.send(embed=embed)
            except:
                pass

    @bot.event
    async def on_ready():
        print(f'🔓 DELTA BYPASS BOT ONLINE: {bot.user}')
        print(f'✅ Verification Bypass: Active')
        print(f'🌐 Client Emulation: Delta Protocol')
        
        # Set initial status
        await update_presence()
        
        # Send startup log
        await send_log(f"**🚀 Bot Started Successfully**\\n**🆔 Bot ID:** {bot.user.id}\\n**📊 Guilds:** {len(bot.guilds)}", 0x00ff00)

    async def update_presence():
        '''Update bot presence based on current status'''
        activity_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }
        
        status = activity_map.get(current_status, discord.Status.online)
        
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name=current_activity
            ),
            status=status
        )

    @bot.command()
    async def delta(ctx):
        '''Check bypass status'''
        embed = discord.Embed(
            title="🔓 DELTA BYPASS SYSTEM",
            description="Client verification bypass active",
            color=0x00ff00
        )
        embed.add_field(name="🆔 Bot ID", value=bot.user.id, inline=True)
        embed.add_field(name="🌐 Protocol", value="Delta Emulation", inline=True)
        embed.add_field(name="🔒 Security", value="Bypass Active", inline=True)
        embed.add_field(name="⏱️ Uptime", value=get_uptime(), inline=True)
        embed.add_field(name="🔧 Status", value=current_status.upper(), inline=True)
        embed.add_field(name="📊 Guilds", value=len(bot.guilds), inline=True)
        await ctx.send(embed=embed)
        
        # Log command usage
        await send_log(f"**📋 Command Used:** `delta`\\n**👤 User:** {ctx.author}")

    @bot.command()
    async def shadow(ctx):
        '''Shadow core commands'''
        embed = discord.Embed(
            title="🖤 SHADOW CORE",
            description="Delta bypass system operational",
            color=0x000000
        )
        embed.add_field(name="Token", value=f"`{token[:10]}...`", inline=True)
        embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Guilds", value=len(bot.guilds), inline=True)
        embed.add_field(name="Uptime", value=get_uptime(), inline=True)
        await ctx.send(embed=embed)

    @bot.command()
    async def status(ctx, new_status: str = None, *, activity: str = None):
        '''Change bot status and activity'''
        nonlocal current_status, current_activity
        
        valid_statuses = ["online", "idle", "dnd", "invisible"]
        
        if not new_status:
            # Show current status
            embed = discord.Embed(
                title="🔧 CURRENT STATUS",
                color=0x0099ff
            )
            embed.add_field(name="Status", value=current_status.upper(), inline=True)
            embed.add_field(name="Activity", value=current_activity, inline=True)
            embed.add_field(name="Uptime", value=get_uptime(), inline=True)
            await ctx.send(embed=embed)
            return
        
        if new_status.lower() not in valid_statuses:
            embed = discord.Embed(
                title="❌ INVALID STATUS",
                description=f"Valid statuses: {', '.join(valid_statuses)}",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        # Update status
        old_status = current_status
        current_status = new_status.lower()
        
        # Update activity if provided
        if activity:
            old_activity = current_activity
            current_activity = activity
        
        # Update presence
        await update_presence()
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ STATUS UPDATED",
            color=0x00ff00
        )
        embed.add_field(name="Old Status", value=old_status.upper(), inline=True)
        embed.add_field(name="New Status", value=current_status.upper(), inline=True)
        embed.add_field(name="Activity", value=current_activity, inline=True)
        await ctx.send(embed=embed)
        
        # Log status change
        await send_log(f"**🔧 Status Changed**\\n**📊 From:** {old_status.upper()}\\n**📈 To:** {current_status.upper()}\\n**🎮 Activity:** {current_activity}")

    @bot.command()
    async def uptime(ctx):
        '''Check bot uptime'''
        embed = discord.Embed(
            title="⏱️ BOT UPTIME",
            description=f"**{get_uptime()}**",
            color=0x0099ff
        )
        embed.add_field(name="Start Time", value=datetime.datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.add_field(name="Current Time", value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        await ctx.send(embed=embed)

    @bot.event
    async def on_guild_join(guild):
        '''Log when bot joins a guild'''
        await send_log(f"**📥 Joined Guild**\\n**🏠 Name:** {guild.name}\\n**🆔 ID:** {guild.id}\\n**👥 Members:** {guild.member_count}", 0x00ff00)

    @bot.event
    async def on_guild_remove(guild):
        '''Log when bot leaves a guild'''
        await send_log(f"**📤 Left Guild**\\n**🏠 Name:** {guild.name}\\n**🆔 ID:** {guild.id}", 0xff0000)

    return bot

if __name__ == '__main__':
    import sys
    TOKEN = sys.argv[1]
    WEBHOOK_URL = sys.argv[2] if len(sys.argv) > 2 else None
    bypass_bot = create_bypass_bot(TOKEN, WEBHOOK_URL)
    bypass_bot.run(TOKEN)
"""

    def create_bypass_launcher(self, token, user_id, log_webhook_url):
        '''Create bypass bot launcher with logging'''
        bot_folder = f"delta_bots/bot_{user_id}_{hash(token)}"
        os.makedirs(bot_folder, exist_ok=True)
        
        # Save bypass script
        with open(f"{bot_folder}/delta_bypass.py", 'w') as f:
            f.write(self.bypass_script)
        
        # Create launcher
        launcher_content = f"""
import sys
sys.path.append('{bot_folder}')
from delta_bypass import create_bypass_bot

if __name__ == '__main__':
    token = '{token}'
    webhook_url = '{log_webhook_url}'
    bot = create_bypass_bot(token, webhook_url)
    bot.run(token)
"""
        with open(f"{bot_folder}/launcher.py", 'w') as f:
            f.write(launcher_content)
        
        return bot_folder

    def start_delta_bypass(self, token, user_id, log_channel):
        '''Start delta bypass bot with logging'''
        try:
            # Create webhook for logging
            webhook = await log_channel.create_webhook(name=f"DeltaLogs_{user_id}")
            log_webhook_url = webhook.url
            
            bot_folder = self.create_bypass_launcher(token, user_id, log_webhook_url)
            
            # Start in separate process
            process = subprocess.Popen([
                sys.executable, f"{bot_folder}/launcher.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.active_tokens[user_id] = {
                'process': process,
                'token': token[:10] + '...',
                'start_time': time.time(),
                'folder': bot_folder,
                'webhook': webhook,
                'log_channel': log_channel
            }
            
            return True, process, webhook
        except Exception as e:
            return False, str(e), None

@bot.event
async def on_ready():
    print(f'🎯 SHADOW DELTA HOST ONLINE: {bot.user}')
    print(f'🌐 Web server: Port 8080')
    print(f'🔓 Delta bypass system ready')
    print(f'📊 Logging system activated')
    bot.delta_system = DeltaBypassSystem()

@bot.command(name='DRG_hosting_bot')
async def delta_hosting_slash(ctx, token: str):
    '''Start delta bypass hosting via / command'''
    await handle_delta_hosting(ctx, token)

@bot.command(name='hosting')
async def delta_hosting_exclamation(ctx, token: str):
    '''Start delta bypass hosting via ! command'''
    await handle_delta_hosting(ctx, token)

async def handle_delta_hosting(ctx, token: str):
    '''Core delta hosting handler'''
    user_id = ctx.author.id
    
    # Token validation
    if not token.startswith('MT') or len(token) < 50:
        embed = discord.Embed(
            title="❌ INVALID TOKEN",
            description="Provide a valid Discord bot token",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    # Check if already hosting
    if user_id in bot.delta_system.active_tokens:
        embed = discord.Embed(
            title="⚠️ ALREADY HOSTING",
            description="You already have an active delta bypass bot",
            color=0xffaa00
        )
        await ctx.send(embed=embed)
        return
    
    # Create private log channel
    try:
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        log_channel = await ctx.guild.create_text_channel(
            name=f"delta-logs-{ctx.author.name}",
            overwrites=overwrites,
            reason=f"Delta bot logs for {ctx.author}"
        )
    except:
        log_channel = ctx.channel
    
    # Start delta bypass
    embed = discord.Embed(
        title="🚀 ACTIVATING DELTA BYPASS...",
        description="```Initializing shadow protocol...\\nBypassing client verification...\\nSetting up logging system...```",
        color=0x0099ff
    )
    loading_msg = await ctx.send(embed=embed)
    
    success, result, webhook = await bot.delta_system.start_delta_bypass(token, user_id, log_channel)
    
    if success:
        success_embed = discord.Embed(
            title="✅ DELTA BYPASS ACTIVE",
            description="Your bot is now online with real-time logging",
            color=0x00ff00
        )
        success_embed.add_field(name="🔓 Status", value="BYPASS ACTIVE", inline=True)
        success_embed.add_field(name="🌐 Protocol", value="Delta Emulation", inline=True)
        success_embed.add_field(name="⚡ Process", value="RUNNING", inline=True)
        success_embed.add_field(name="📊 Log Channel", value=log_channel.mention, inline=True)
        success_embed.add_field(name="🔧 Commands", value="`!delta` `!shadow` `!status` `!uptime`", inline=True)
        success_embed.add_field(name="👤 Hosted By", value=ctx.author.mention, inline=True)
        success_embed.set_footer(text="Shadow Core Delta System")
        
        # Send initial log to private channel
        log_embed = discord.Embed(
            title="📊 DELTA BOT LOGGING STARTED",
            description=f"**Bot hosted by:** {ctx.author.mention}\\n**Start Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            color=0x00ff00
        )
        log_embed.add_field(name="🔧 Available Commands", value="`!status` - Change bot status\\n`!uptime` - Check uptime\\n`!delta` - System info\\n`!shadow` - Core info", inline=False)
        log_embed.add_field(name="🔒 Security", value="Delta Bypass Active", inline=True)
        log_embed.add_field(name="🌐 Protocol", value="Client Emulation", inline=True)
        await log_channel.send(embed=log_embed)
    else:
        success_embed = discord.Embed(
            title="❌ BYPASS FAILED",
            description=f"```{str(result)}```",
            color=0xff0000
        )
    
    await loading_msg.edit(embed=success_embed)

@bot.command(name='delta_status')
async def delta_status(ctx):
    '''Check delta bypass status'''
    user_id = ctx.author.id
    
    if user_id not in bot.delta_system.active_tokens:
        embed = discord.Embed(
            title="❌ NO ACTIVE BYPASS",
            description="Start with `/DRG_hosting_bot <TOKEN>` or `!hosting <TOKEN>`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    bot_data = bot.delta_system.active_tokens[user_id]
    uptime = time.time() - bot_data['start_time']
    
    embed = discord.Embed(
        title="🔓 DELTA BYPASS STATUS",
        description="Client verification bypass active",
        color=0x00ff00
    )
    embed.add_field(name="🆔 Token", value=f"`{bot_data['token']}`", inline=True)
    embed.add_field(name="⏱️ Uptime", value=f"{int(uptime)}s", inline=True)
    embed.add_field(name="📁 Folder", value=f"`{bot_data['folder']}`", inline=True)
    embed.add_field(name="⚡ Process", value="ACTIVE", inline=True)
    embed.add_field(name="🌐 Protocol", value="Delta Emulation", inline=True)
    embed.add_field(name="🔒 Security", value="BYPASSED", inline=True)
    embed.add_field(name="📊 Log Channel", value=bot_data['log_channel'].mention, inline=True)
    embed.add_field(name="👤 Hosted By", value=f"<@{user_id}>", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='stop_delta')
async def stop_delta(ctx):
    '''Stop delta bypass bot'''
    user_id = ctx.author.id
    
    if user_id not in bot.delta_system.active_tokens:
        embed = discord.Embed(
            title="❌ NO ACTIVE BYPASS",
            description="No delta bypass bot to stop",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    bot_data = bot.delta_system.active_tokens[user_id]
    bot_data['process'].terminate()
    
    # Send final log
    final_embed = discord.Embed(
        title="🛑 BOT STOPPED",
        description=f"Delta bypass bot terminated by {ctx.author.mention}",
        color=0xff0000
    )
    final_embed.add_field(name="⏱️ Total Uptime", value=f"{int(time.time() - bot_data['start_time'])}s", inline=True)
    final_embed.add_field(name="🆔 Token", value=bot_data['token'], inline=True)
    await bot_data['log_channel'].send(embed=final_embed)
    
    # Cleanup
    try:
        await bot_data['webhook'].delete()
        await bot_data['log_channel'].delete()
    except:
        pass
    
    del bot.delta_system.active_tokens[user_id]
    
    embed = discord.Embed(
        title="🛑 DELTA BYPASS STOPPED",
        description="Bot process terminated and logs cleaned up",
        color=0xffaa00
    )
    embed.add_field(name="Token", value=f"`{bot_data['token']}`", inline=True)
    embed.add_field(name="Uptime", value=f"{int(time.time() - bot_data['start_time'])}s", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='delta_help')
async def delta_help(ctx):
    '''Delta bypass help'''
    embed = discord.Embed(
        title="🔓 SHADOW DELTA BYPASS SYSTEM",
        description="Host bots with client verification bypass and real-time logging",
        color=0x0099ff
    )
    embed.add_field(
        name="🚀 Start Hosting",
        value="`/DRG_hosting_bot <TOKEN>` or `!hosting <TOKEN>`",
        inline=False
    )
    embed.add_field(
        name="📊 Check Status", 
        value="`/delta_status` or `!delta_status`",
        inline=True
    )
    embed.add_field(
        name="🛑 Stop Bot",
        value="`/stop_delta` or `!stop_delta`",
        inline=True
    )
    embed.add_field(
        name="🔧 Hosted Bot Commands",
        value="`!status` - Change status (online/idle/dnd/invisible)\\n`!uptime` - Check uptime\\n`!delta` - System info\\n`!shadow` - Core info",
        inline=False
    )
    embed.add_field(
        name="📊 Logging Features",
        value="• Real-time uptime tracking\\n• Status change logs\\n• Guild join/leave logs\\n• Private log channels\\n• User command tracking",
        inline=False
    )
    embed.set_footer(text="Shadow Core V99 - Delta Bypass Protocol")
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing token: `/DRG_hosting_bot <TOKEN>`")
    else:
        await ctx.send(f"❌ Error: {str(error)}")

# SHADOW CORE EXECUTION
if __name__ == '__main__':
    if not os.getenv('DISCORD_TOKEN'):
        print("❌ DISCORD_TOKEN environment variable required")
        sys.exit(1)
    
    print("🚀 Starting SHADOW DELTA BYPASS SYSTEM...")
    bot.run(os.getenv('DISCORD_TOKEN'))
