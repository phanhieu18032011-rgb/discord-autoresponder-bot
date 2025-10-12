import os
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
import threading

# --- Web server để giữ bot online ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run).start()

# --- Cấu hình bot ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# --- Lưu trữ phản hồi tự động ---
autoresponders = {}  # key: từ khóa, value: phản hồi

# --- Sự kiện khi bot sẵn sàng ---
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")
    try:
        synced = await tree.sync()
        print(f"📁 Đã sync {len(synced)} lệnh slash.")
    except Exception as e:
        print(f"❌ Lỗi sync lệnh: {e}")

# --- Slash command: /add ---
@tree.command(name="add", description="Thêm phản hồi tự động")
@app_commands.describe(trigger="Từ khóa kích hoạt", response="Phản hồi của bot")
async def add(interaction: discord.Interaction, trigger: str, response: str):
    autoresponders[trigger.lower()] = response
    await interaction.response.send_message(f"✅ Đã thêm auto-response: **{trigger} → {response}**")

# --- Slash command: /remove ---
@tree.command(name="remove", description="Xóa phản hồi tự động")
@app_commands.describe(trigger="Từ khóa muốn xóa")
async def remove(interaction: discord.Interaction, trigger: str):
    if trigger.lower() in autoresponders:
        del autoresponders[trigger.lower()]
        await interaction.response.send_message(f"🗑️ Đã xóa auto-response cho từ khóa **{trigger}**")
    else:
        await interaction.response.send_message(f"⚠️ Không tìm thấy từ khóa **{trigger}**")

# --- Slash command: /list ---
@tree.command(name="list", description="Xem danh sách auto-response")
async def list_responses(interaction: discord.Interaction):
    if autoresponders:
        msg = "\n".join([f"- **{k}** → {v}" for k, v in autoresponders.items()])
    else:
        msg = "Hiện chưa có auto-response nào!"
    await interaction.response.send_message(msg)

# --- Sự kiện: tin nhắn thường ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()
    for trigger, response in autoresponders.items():
        if trigger in content:
            await message.channel.send(response)
            break

    await bot.process_commands(message)

# --- Chạy bot ---
TOKEN = os.environ["TOKEN"]  # Lấy token từ Render secrets
bot.run(TOKEN)
