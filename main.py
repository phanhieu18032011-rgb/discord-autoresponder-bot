import os
import threading
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands

# ====== CẤU HÌNH ======
TOKEN = os.getenv("TOKEN")  # lấy token từ biến môi trường
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ====== FLASK WEB APP ======
app = Flask(__name__)

@app.route("/")
def home():
    return "<h2>✅ Flask & Discord Bot đang hoạt động trên Render!</h2>"

# Thread để chạy Flask song song với bot
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ====== SỰ KIỆN BOT ======
@bot.event
async def on_ready():
    print(f"🤖 Bot đã đăng nhập thành công: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔧 Đã đồng bộ {len(synced)} lệnh slash (/).")
    except Exception as e:
        print(f"❌ Lỗi sync: {e}")

# ====== LỆNH /say ======
@bot.tree.command(name="say", description="Bot gửi tin nhắn bạn nhập")
@app_commands.describe(
    message="Nội dung muốn bot gửi",
    channel="(Tùy chọn) Kênh để gửi tin nhắn"
)
async def say(interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
    target_channel = channel or interaction.channel
    try:
        await target_channel.send(message)
        await interaction.response.send_message(
            f"✅ Đã gửi tin nhắn tới {target_channel.mention}", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

# ====== CHẠY FLASK VÀ BOT ======
if __name__ == "__main__":
    if not TOKEN:
        print("❌ Thiếu token! Hãy set biến môi trường TOKEN.")
    else:
        # Chạy Flask song song bằng luồng riêng
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.start()

        # Chạy bot Discord
        bot.run(TOKEN)
