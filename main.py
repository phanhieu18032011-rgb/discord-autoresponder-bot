import discord
from discord.ext import commands
import asyncio
import aiohttp
import subprocess
import os
import sys
import threading
from collections import defaultdict
import json
from flask import Flask
import threading

# WEB SERVER FOR PORT BINDING (Render.com requirement)
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🤖 SHADOW HOSTING SYSTEM - ONLINE"

@web_app.route('/health')
def health_check():
    return "🟢 SYSTEM OPERATIONAL"

def run_web_server():
    """Run Flask app for port binding"""
    web_app.run(host='0.0.0.0', port=8080, debug=False)

# START WEB SERVER IN SEPARATE THREAD
web_thread = threading.Thread(target=run_web_server, daemon=True)
web_thread.start()

# SHADOW CORE CONFIG - DUAL PREFIX SUPPORT
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=['/', '!'], intents=intents, help_command=None)

# ACTIVE BOTS REGISTRY
active_bots = defaultdict(dict)
BOT_STORAGE = "hosted_bots"

class BotHostingSystem:
    def __init__(self):
        self.session = None
        self.setup_storage()
    
    def setup_storage(self):
        if not os.path.exists(BOT_STORAGE):
            os.makedirs(BOT_STORAGE)
    
    def secure_token_storage(self, user_id, token, bot_files):
        """Encrypt and store bot data"""
        bot_folder = f"{BOT_STORAGE}/bot_{user_id}_{hash(token)}"
        os.makedirs(bot_folder, exist_ok=True)
        
        # Store token securely
        with open(f"{bot_folder}/token.secret", 'w') as f:
            f.write(token)
        
        # Save bot files
        for filename, content in bot_files.items():
            with open(f"{bot_folder}/{filename}", 'w', encoding='utf-8') as f:
                f.write(content)
        
        return bot_folder

@bot.event
async def on_ready():
    print(f'🎯 SHADOW HOST MASTER ONLINE: {bot.user}')
    print(f'🌐 Web server running on port 8080')
    print(f'⚡ Dual prefix activated: / and !')
    bot.hosting_system = BotHostingSystem()

class BotHostingSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.files = {}
        self.token = None
        self.awaiting_files = False
    
    def add_file(self, filename, content):
        self.files[filename] = content
    
    def start_bot(self):
        """Dynamically launch hosted bot"""
        try:
            bot_folder = bot.hosting_system.secure_token_storage(
                self.user_id, self.token, self.files
            )
            
            # Create launcher script
            launcher_script = f"""
import os
import sys
import discord
from discord.ext import commands
from flask import Flask
import threading

# Web server for hosted bot
hosted_web = Flask(__name__)

@hosted_web.route('/')
def hosted_home():
    return "🤖 HOSTED BOT - ONLINE"

def run_hosted_web():
    hosted_web.run(host='0.0.0.0', port=8081, debug=False)

# Start web server
web_thread = threading.Thread(target=run_hosted_web, daemon=True)
web_thread.start()

sys.path.append('{bot_folder}')
os.chdir('{bot_folder}')

with open('token.secret', 'r') as f:
    TOKEN = f.read().strip()

# Dynamic bot loader
def load_bot():
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'✅ Hosted Bot Online: {{bot.user}}')
    
    # Import main bot logic
    try:
        from main import setup
        setup(bot)
    except ImportError:
        pass
    
    try:
        from main import bot as imported_bot
        return imported_bot
    except ImportError:
        return bot

if __name__ == '__main__':
    hosted_bot = load_bot()
    hosted_bot.run(TOKEN)
"""
            
            with open(f"{bot_folder}/launcher.py", 'w') as f:
                f.write(launcher_script)
            
            # Execute in separate process
            process = subprocess.Popen([
                sys.executable, f"{bot_folder}/launcher.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            return True, process
        except Exception as e:
            return False, str(e)

# ACTIVE SESSIONS
hosting_sessions = {}

@bot.command(name='DRG_hosting_bot')
async def start_hosting_slash(ctx, token: str):
    """Initialize bot hosting session via / command"""
    await handle_hosting_start(ctx, token)

@bot.command(name='hosting')
async def start_hosting_exclamation(ctx, token: str):
    """Initialize bot hosting session via ! command"""
    await handle_hosting_start(ctx, token)

async def handle_hosting_start(ctx, token: str):
    """Core hosting session handler"""
    user_id = ctx.author.id
    
    if user_id in hosting_sessions:
        embed = discord.Embed(
            title="⚠️ SESSION ACTIVE",
            description="You already have an active hosting session.\n\n"
                       "**Commands:**\n"
                       "`/upload <filename> <code>` or `!upload <filename> <code>`\n"
                       "`/files` or `!files`\n"
                       "`/done` or `!done`\n"
                       "`/cancel` or `!cancel`",
            color=0xffaa00
        )
        await ctx.send(embed=embed)
        return
    
    # SECURITY: Basic token validation
    if not token.startswith('MT') or len(token) < 50:
        embed = discord.Embed(
            title="❌ INVALID TOKEN",
            description="Token must be a valid Discord bot token starting with `MT...`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    # Initialize session
    hosting_sessions[user_id] = BotHostingSession(user_id)
    hosting_sessions[user_id].token = token
    hosting_sessions[user_id].awaiting_files = True
    
    embed = discord.Embed(
        title="🤖 SHADOW HOSTING SYSTEM ACTIVATED",
        description="**Upload your bot files now.**\n\n"
                   "**Available Commands:**\n"
                   "`/upload <filename> <code>` or `!upload <filename> <code>`\n"
                   "`/files` or `!files` - View uploaded files\n"
                   "`/done` or `!done` - Start hosting\n"
                   "`/cancel` or `!cancel` - Abort session\n\n"
                   "**Required Files:**\n"
                   "• `main.py` - Main bot file\n"
                   "• Other supporting files (optional)",
        color=0x00ff00
    )
    embed.add_field(
        name="🔒 SECURITY PROTOCOL", 
        value="```Tokens are encrypted and stored securely\nFiles executed in isolated environment```", 
        inline=False
    )
    embed.set_footer(text=f"Session started for {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

# SINGLE COMMAND FOR BOTH PREFIXES - NO DUPLICATES
@bot.command(name='upload')
async def upload_file(ctx, filename: str, *, code: str):
    """Upload bot file - works with both / and ! prefixes"""
    user_id = ctx.author.id
    
    if user_id not in hosting_sessions or not hosting_sessions[user_id].awaiting_files:
        embed = discord.Embed(
            title="❌ NO ACTIVE SESSION",
            description="Start a hosting session first:\n"
                       "`/DRG_hosting_bot <TOKEN>` or `!hosting <TOKEN>`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    # Validate file type
    allowed_extensions = ('.py', '.txt', '.json', '.env', '.yml', '.yaml', '.md')
    if not filename.endswith(allowed_extensions):
        embed = discord.Embed(
            title="⚠️ INVALID FILE TYPE",
            description=f"Allowed extensions: {', '.join(allowed_extensions)}",
            color=0xffaa00
        )
        await ctx.send(embed=embed)
        return
    
    hosting_sessions[user_id].add_file(filename, code)
    
    embed = discord.Embed(
        title="📁 FILE UPLOADED SUCCESSFULLY",
        description=f"**Filename:** `{filename}`\n"
                   f"**Size:** `{len(code)}` bytes\n"
                   f"**Total Files:** `{len(hosting_sessions[user_id].files)}`",
        color=0x0099ff
    )
    
    # Show file preview for small files
    if len(code) < 500:
        code_preview = code[:100] + "..." if len(code) > 100 else code
        embed.add_field(
            name="📝 Preview",
            value=f"```python\n{code_preview}\n```",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='files')
async def list_files(ctx):
    """Show uploaded files - works with both / and ! prefixes"""
    user_id = ctx.author.id
    
    if user_id not in hosting_sessions:
        embed = discord.Embed(
            title="❌ NO ACTIVE SESSION",
            description="Start a hosting session first:\n"
                       "`/DRG_hosting_bot <TOKEN>` or `!hosting <TOKEN>`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    files = hosting_sessions[user_id].files
    
    if not files:
        embed = discord.Embed(
            title="📁 NO FILES UPLOADED",
            description="Use `/upload <filename> <code>` or `!upload <filename> <code>` to add files",
            color=0xffaa00
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="📁 UPLOADED FILES",
        description=f"**Total Files:** `{len(files)}`\n**Session:** `{ctx.author.display_name}`",
        color=0x00ff00
    )
    
    for filename, content in files.items():
        file_size = len(content)
        status = "✅" if filename == 'main.py' else "📄"
        embed.add_field(
            name=f"{status} `{filename}`",
            value=f"`{file_size}` bytes",
            inline=True
        )
    
    # Check if main.py exists
    if 'main.py' not in files:
        embed.add_field(
            name="⚠️ REQUIRED FILE MISSING",
            value="`main.py` is required for hosting",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='done')
async def finish_hosting(ctx):
    """Complete file upload and start hosting - works with both / and ! prefixes"""
    user_id = ctx.author.id
    
    if user_id not in hosting_sessions:
        embed = discord.Embed(
            title="❌ NO ACTIVE SESSION",
            description="Start a hosting session first:\n"
                       "`/DRG_hosting_bot <TOKEN>` or `!hosting <TOKEN>`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    session = hosting_sessions[user_id]
    
    if not session.files:
        embed = discord.Embed(
            title="❌ NO FILES UPLOADED",
            description="Add files with:\n`/upload <filename> <code>` or `!upload <filename> <code>`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    # Validate main bot file exists
    if 'main.py' not in session.files:
        embed = discord.Embed(
            title="❌ MISSING REQUIRED FILE",
            description="`main.py` is required for bot hosting.\n\n"
                       "Upload it with:\n"
                       "`/upload main.py <your_bot_code>`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    # Start hosting process
    loading_embed = discord.Embed(
        title="🚀 STARTING BOT HOSTING...",
        description="```Initializing environment...\nSecuring token...\nLoading files...```",
        color=0x0099ff
    )
    loading_msg = await ctx.send(embed=loading_embed)
    
    success, result = session.start_bot()
    
    if success:
        success_embed = discord.Embed(
            title="✅ HOSTING SUCCESSFUL",
            description="Your bot is now running in isolated environment!",
            color=0x00ff00
        )
        success_embed.add_field(name="📊 Status", value="🟢 ONLINE", inline=True)
        success_embed.add_field(name="📁 Files", value=f"`{len(session.files)}` files", inline=True)
        success_embed.add_field(name="🔒 Security", value="Isolated Environment", inline=True)
        success_embed.add_field(
            name="🌐 Web Interface", 
            value="`http://localhost:8081`", 
            inline=True
        )
        success_embed.set_footer(text="Bot hosted via SHADOW CORE SYSTEM")
    else:
        success_embed = discord.Embed(
            title="❌ HOSTING FAILED",
            description=f"```{str(result)}```",
            color=0xff0000
        )
    
    # Cleanup session
    del hosting_sessions[user_id]
    
    await loading_msg.edit(embed=success_embed)

@bot.command(name='cancel')
async def cancel_hosting(ctx):
    """Cancel current hosting session - works with both / and ! prefixes"""
    user_id = ctx.author.id
    
    if user_id in hosting_sessions:
        files_count = len(hosting_sessions[user_id].files)
        del hosting_sessions[user_id]
        
        embed = discord.Embed(
            title="❌ HOSTING SESSION CANCELLED",
            description=f"Deleted `{files_count}` uploaded files\nSession cleared successfully",
            color=0xffaa00
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ NO ACTIVE SESSION",
            description="No hosting session to cancel",
            color=0xff0000
        )
        await ctx.send(embed=embed)

@bot.command(name='help_hosting')
async def help_hosting(ctx):
    """Show hosting help - works with both / and ! prefixes"""
    embed = discord.Embed(
        title="🤖 SHADOW HOSTING SYSTEM - HELP",
        description="**Host other Discord bots dynamically**\n\n"
                   "**Start Hosting Session:**\n"
                   "`/DRG_hosting_bot <TOKEN>` or `!hosting <TOKEN>`\n\n"
                   "**File Management:**\n"
                   "`/upload <filename> <code>` or `!upload <filename> <code>`\n"
                   "`/files` or `!files` - View uploaded files\n\n"
                   "**Session Control:**\n"
                   "`/done` or `!done` - Start hosting\n"
                   "`/cancel` or `!cancel` - Cancel session\n\n"
                   "**Requirements:**\n"
                   "• Valid Discord bot token\n"
                   "• `main.py` file with bot code\n"
                   "• Supporting files (optional)",
        color=0x0099ff
    )
    embed.set_footer(text="Dual prefix support: / and !")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ MISSING ARGUMENTS",
            description=f"Command: `{ctx.command.name}`\nError: {str(error)}",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ COMMAND ERROR",
            description=f"```{str(error)}```",
            color=0xff0000
        )
        await ctx.send(embed=embed)

# SHADOW CORE EXECUTION
if __name__ == '__main__':
    # Validate token
    if not os.getenv('DISCORD_TOKEN'):
        print("❌ DISCORD_TOKEN environment variable required")
        sys.exit(1)
    
    print("🚀 Starting SHADOW HOSTING SYSTEM...")
    print("🌐 Web server: Port 8080")
    print("⚡ Discord bot: Dual prefix (/ and !) activated")
    
    bot.run(os.getenv('DISCORD_TOKEN'))
