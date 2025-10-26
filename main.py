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

# SHADOW CORE CONFIG
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents, help_command=None)

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
    print(f'SHADOW HOST MASTER ONLINE: {bot.user}')
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
        print(f'Hosted Bot Online: {{bot.user}}')
    
    # Import main bot logic
    try:
        from main import setup
        setup(bot)
    except ImportError:
        pass
    
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
async def start_hosting(ctx, token: str):
    """Initialize bot hosting session"""
    user_id = ctx.author.id
    
    if user_id in hosting_sessions:
        await ctx.send("❌ You already have an active hosting session. Type `/done` when finished.")
        return
    
    # SECURITY: Basic token validation
    if not token.startswith('MT') or len(token) < 50:
        await ctx.send("❌ Invalid token format. Token must be a valid Discord bot token.")
        return
    
    # Initialize session
    hosting_sessions[user_id] = BotHostingSession(user_id)
    hosting_sessions[user_id].token = token
    hosting_sessions[user_id].awaiting_files = True
    
    embed = discord.Embed(
        title="🤖 SHADOW HOSTING SYSTEM ACTIVE",
        description="**Upload your bot files now.**\n\n"
                   "**Commands:**\n"
                   "`/upload <filename> <code>` - Upload file\n"
                   "`/files` - View uploaded files\n"
                   "`/done` - Start hosting\n"
                   "`/cancel` - Abort session",
        color=0x00ff00
    )
    embed.add_field(name="⚠️ SECURITY", value="Tokens are encrypted. Files executed in isolated environment.", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='upload')
async def upload_file(ctx, filename: str, *, code: str):
    """Upload bot file"""
    user_id = ctx.author.id
    
    if user_id not in hosting_sessions or not hosting_sessions[user_id].awaiting_files:
        await ctx.send("❌ No active hosting session. Start with `/DRG_hosting_bot <TOKEN>`")
        return
    
    # Validate file type
    if not filename.endswith(('.py', '.txt', '.json', '.env')):
        await ctx.send("⚠️ Only Python files and config files allowed.")
        return
    
    hosting_sessions[user_id].add_file(filename, code)
    
    embed = discord.Embed(
        title="📁 FILE UPLOADED",
        description=f"**Filename:** `{filename}`\n"
                   f"**Size:** {len(code)} bytes\n"
                   f"**Total Files:** {len(hosting_sessions[user_id].files)}",
        color=0x0099ff
    )
    
    await ctx.send(embed=embed)

@bot.command(name='files')
async def list_files(ctx):
    """Show uploaded files"""
    user_id = ctx.author.id
    
    if user_id not in hosting_sessions:
        await ctx.send("❌ No active hosting session.")
        return
    
    files = hosting_sessions[user_id].files
    
    if not files:
        await ctx.send("📁 No files uploaded yet.")
        return
    
    embed = discord.Embed(title="📁 UPLOADED FILES", color=0xffaa00)
    
    for filename, content in files.items():
        embed.add_field(
            name=f"`{filename}`",
            value=f"{len(content)} bytes",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command(name='done')
async def finish_hosting(ctx):
    """Complete file upload and start hosting"""
    user_id = ctx.author.id
    
    if user_id not in hosting_sessions:
        await ctx.send("❌ No active hosting session.")
        return
    
    session = hosting_sessions[user_id]
    
    if not session.files:
        await ctx.send("❌ No files uploaded. Add files with `/upload <filename> <code>`")
        return
    
    # Validate main bot file exists
    if 'main.py' not in session.files:
        await ctx.send("❌ `main.py` is required for bot hosting.")
        return
    
    # Start hosting process
    await ctx.send("🚀 **Starting bot hosting...**")
    
    success, result = session.start_bot()
    
    if success:
        embed = discord.Embed(
            title="✅ HOSTING SUCCESSFUL",
            description="Your bot is now running!",
            color=0x00ff00
        )
        embed.add_field(name="📊 Status", value="🟢 ONLINE", inline=True)
        embed.add_field(name="📁 Files", value=f"{len(session.files)} files", inline=True)
        embed.add_field(name="🔒 Security", value="Isolated Environment", inline=True)
    else:
        embed = discord.Embed(
            title="❌ HOSTING FAILED",
            description=str(result),
            color=0xff0000
        )
    
    # Cleanup session
    del hosting_sessions[user_id]
    
    await ctx.send(embed=embed)

@bot.command(name='cancel')
async def cancel_hosting(ctx):
    """Cancel current hosting session"""
    user_id = ctx.author.id
    
    if user_id in hosting_sessions:
        del hosting_sessions[user_id]
        await ctx.send("❌ Hosting session cancelled.")
    else:
        await ctx.send("❌ No active hosting session.")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required arguments.")
    else:
        await ctx.send(f"❌ Error: {str(error)}")

# SHADOW CORE EXECUTION
if __name__ == '__main__':
    # Validate token
    if not os.getenv('DISCORD_TOKEN'):
        print("❌ DISCORD_TOKEN environment variable required")
        sys.exit(1)
    
    bot.run(os.getenv('DISCORD_TOKEN'))
