import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
import random
import os

# ==== Flask để giữ bot sống trên Render ====
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==== Cấu hình bot ====
TOKEN = os.getenv("TOKEN") or "YOUR_TOKEN_HERE"
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
tree = bot.tree

# ==== Khi bot online ====
@bot.event
async def on_ready():
    print(f"🤖 Bot đã đăng nhập: {bot.user}")
    try:
        await tree.sync()
        print("✅ Slash commands đã sync toàn cầu.")
    except Exception as e:
        print(f"Lỗi sync: {e}")

# ==== Prefix Commands ====
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")

@bot.command()
async def say(ctx, *, text):
    await ctx.send(text)

@bot.command()
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Đã xoá {amount} tin nhắn.", delete_after=3)

# ==== 5 Mini Games ====

# 1️⃣ Đoán số
@bot.command()
async def đoánsố(ctx):
    number = random.randint(1, 10)
    await ctx.send("🎯 Tôi đã nghĩ 1 số từ 1–10, đoán đi!")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    msg = await bot.wait_for("message", check=check)
    if msg.content.isdigit() and int(msg.content) == number:
        await ctx.send("✅ Chính xác!")
    else:
        await ctx.send(f"❌ Sai rồi, số đúng là {number}.")

# 2️⃣ Oẳn tù tì
@bot.command()
async def oẳntùtì(ctx, chọn: str):
    chọn = chọn.lower()
    bot_chọn = random.choice(["kéo", "búa", "bao"])
    if chọn == bot_chọn:
        kq = "⚖️ Hoà!"
    elif (chọn, bot_chọn) in [("kéo","bao"),("búa","kéo"),("bao","búa")]:
        kq = "🏆 Bạn thắng!"
    else:
        kq = "😢 Bạn thua!"
    await ctx.send(f"🤖 Tôi chọn **{bot_chọn}** — {kq}")

# 3️⃣ Xúc xắc
@bot.command()
async def xúcxắc(ctx):
    await ctx.send(f"🎲 Kết quả: {random.randint(1,6)}")

# 4️⃣ Đoán chữ
@bot.command()
async def đoánchữ(ctx):
    words = ["python", "discord", "render", "github"]
    word = random.choice(words)
    hidden = "_" * len(word)
    await ctx.send(f"Từ cần đoán: `{hidden}` (gợi ý: {len(word)} chữ)")

# 5️⃣ Blackjack
@bot.command()
async def blackjack(ctx):
    user = random.randint(15, 25)
    botnum = random.randint(15, 25)
    if user > 21:
        result = "Bạn quá 21, thua!"
    elif botnum > 21 or user > botnum:
        result = "Bạn thắng!"
    elif user == botnum:
        result = "Hoà!"
    else:
        result = "Bot thắng!"
    await ctx.send(f"🃏 Bạn: {user} | Bot: {botnum}\n{result}")

# ==== Slash Commands ====
@tree.command(name="ping", description="Kiểm tra độ trễ bot")
async def ping_slash(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")

@tree.command(name="say", description="Bot lặp lại lời bạn")
async def say_slash(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(text)

# ==== Chạy bot ====
keep_alive()
bot.run(TOKEN)

