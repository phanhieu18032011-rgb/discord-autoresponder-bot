import os
import discord
from discord.ext import commands
from flask import Flask
import threading

# --- Web server ảo để Render giữ bot online ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run).start()

# --- Bot Discord ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập thành công: {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

TOKEN = os.environ["TOKEN"]  # Lấy token từ Render Secrets
bot.run(TOKEN)

