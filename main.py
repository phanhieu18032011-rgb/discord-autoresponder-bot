import os, asyncio, threading
from flask import Flask
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise SystemExit("❌ Bạn chưa đặt biến môi trường DISCORD_TOKEN trên Render!")

# Flask keep alive cho Render
app = Flask(__name__)
@app.route("/")
def home(): return "✅ Bot is alive!"
def run_web():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
threading.Thread(target=run_web, daemon=True).start()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
responses = {}

def is_admin(inter):
    try: return inter.user.guild_permissions.administrator
    except: return False

# Slash commands
@tree.command(name="add", description="Thêm auto responder")
@app_commands.describe(trigger="Từ khóa", reply="Phản hồi")
async def add(inter, trigger: str, reply: str):
    responses[trigger.lower()] = reply
    await inter.response.send_message(f"✅ Đã thêm `{trigger}` → `{reply}`", ephemeral=True)

@tree.command(name="remove", description="Xóa auto responder")
@app_commands.describe(trigger="Từ khóa")
async def remove(inter, trigger: str):
    if trigger.lower() in responses:
        del responses[trigger.lower()]
        await inter.response.send_message(f"🗑️ Đã xóa `{trigger}`", ephemeral=True)
    else:
        await inter.response.send_message("⚠️ Không tìm thấy trigger.", ephemeral=True)

@tree.command(name="list", description="Xem danh sách auto responder")
async def list_cmd(inter):
    if not responses:
        await inter.response.send_message("📭 Danh sách trống.", ephemeral=True)
    else:
        text = "\n".join([f"`{k}` → {v}" for k, v in responses.items()])
        await inter.response.send_message(f"📋 Danh sách:\n{text}", ephemeral=True)

# Moderation
@tree.command(name="ban", description="Ban người dùng (Admin only)")
async def ban(inter, member: discord.Member, reason: str = "Không có lý do"):
    if not is_admin(inter):
        return await inter.response.send_message("⚠️ Chỉ admin mới dùng được.", ephemeral=True)
    await inter.guild.ban(member, reason=reason)
    await inter.response.send_message(f"🚫 Đã ban {member.mention}.")

@tree.command(name="unban", description="Unban người dùng theo ID (Admin only)")
async def unban(inter, user_id: str):
    if not is_admin(inter):
        return await inter.response.send_message("⚠️ Chỉ admin mới dùng được.", ephemeral=True)
    user = await bot.fetch_user(int(user_id))
    await inter.guild.unban(user)
    await inter.response.send_message(f"✅ Đã unban {user}.")

async def ensure_muted_role(guild):
    role = discord.utils.get(guild.roles, name="Muted")
    if not role:
        role = await guild.create_role(name="Muted", reason="Tạo role Muted")
        for ch in guild.channels:
            try:
                await ch.set_permissions(role, send_messages=False, speak=False)
            except: pass
    return role

@tree.command(name="mute", description="Mute người dùng (Admin only)")
async def mute(inter, member: discord.Member):
    if not is_admin(inter):
        return await inter.response.send_message("⚠️ Chỉ admin mới dùng được.", ephemeral=True)
    role = await ensure_muted_role(inter.guild)
    await member.add_roles(role)
    await inter.response.send_message(f"🔇 Đã mute {member.mention}")

@tree.command(name="unmute", description="Unmute người dùng (Admin only)")
async def unmute(inter, member: discord.Member):
    if not is_admin(inter):
        return await inter.response.send_message("⚠️ Chỉ admin mới dùng được.", ephemeral=True)
    role = discord.utils.get(inter.guild.roles, name="Muted")
    if role:
        await member.remove_roles(role)
        await inter.response.send_message(f"🔊 Đã unmute {member.mention}")
    else:
        await inter.response.send_message("⚠️ Không có role Muted.", ephemeral=True)

@tree.command(name="masssend", description="Gửi tin nhắn nhiều lần (Admin only, max 100)")
async def masssend(inter, channel: discord.TextChannel, message: str, count: int = 1):
    if not is_admin(inter):
        return await inter.response.send_message("⚠️ Chỉ admin mới dùng được.", ephemeral=True)
    count = min(max(count, 1), 100)
    await inter.response.send_message(f"📤 Đang gửi {count} tin nhắn tới {channel.mention}...", ephemeral=True)
    for i in range(count):
        await channel.send(message)
        await asyncio.sleep(1)
    await inter.followup.send(f"✅ Đã gửi xong {count} tin nhắn!", ephemeral=True)

# Auto reply
@bot.event
async def on_message(message):
    if message.author.bot: return
    for k, v in responses.items():
        if k in message.content.lower():
            await message.channel.send(v)
            break
    await bot.process_commands(message)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot đã sẵn sàng: {bot.user}")

bot.run(TOKEN)

