import os
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = os.environ["TOKEN"]  # Token Discord lấy từ Render Secrets

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

autoresponses = {}

@bot.tree.command(name="autoresponder", description="Quản lý auto reply")
@app_commands.describe(action="add hoặc remove", keyword="Từ khoá", reply="Câu trả lời (nếu add)")
async def autoresponder(interaction: discord.Interaction, action: str, keyword: str, reply: str = None):
    action = action.lower()
    if action == "add":
        if not reply:
            await interaction.response.send_message("❌ Bạn cần nhập reply khi dùng 'add'.")
            return
        autoresponses[keyword] = reply
        await interaction.response.send_message(f"✅ Đã thêm auto reply cho `{keyword}` → `{reply}`")
    elif action == "remove":
        if keyword in autoresponses:
            del autoresponses[keyword]
            await interaction.response.send_message(f"🗑️ Đã xoá auto reply của `{keyword}`")
        else:
            await interaction.response.send_message(f"⚠️ Không tìm thấy `{keyword}`.")
    else:
        await interaction.response.send_message("❌ Dùng `add` hoặc `remove` thôi nhé.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    for keyword, reply in autoresponses.items():
        if keyword.lower() in message.content.lower():
            await message.channel.send(reply)
            break
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ Bot online: {bot.user}")
    try:
        await bot.tree.sync()
        print("🔧 Slash commands synced.")
    except Exception as e:
        print(f"Sync error: {e}")

bot.run(TOKEN)
