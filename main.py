# main.py – ĐÃ THÊM LỆNH ĐỔI TRẠNG THÁI BOT (chỉ owner dùng)
import discord
from discord import app_commands
from discord.ext import commands
import os, asyncio, aiohttp
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
RENDER_URL = os.getenv("RENDER_URL")

# THAY BẰNG ID CỦA BẠN (có thể thêm nhiều ID)
OWNER_IDS = {1333333136037249057}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
tree = bot.tree

# ==================== CHỈ OWNER DÙNG ====================
def is_bot_owner():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id not in OWNER_IDS:
            await interaction.response.send_message("❌ Chỉ chủ nhân bot mới dùng được lệnh này!", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

def is_bot_owner_prefix():
    def predicate(ctx):
        return ctx.author.id in OWNER_IDS
    return commands.check(predicate)

# ==================== KEEP ALIVE ====================
async def keep_alive():
    if RENDER_URL:
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.get(RENDER_URL): pass
                except: pass
                await asyncio.sleep(600)

@bot.event
async def on_ready():
    await tree.sync(global=True)   # ĐÃ FIX lỗi global_ → global=True
    print(f"Bot đã online: {bot.user}")
    bot.loop.create_task(keep_alive())

# ============================= LỆNH MOD THƯỜNG =============================
@tree.command(name="kick")
@app_commands.default_permissions(kick_members=True)
async def kick(i: discord.Interaction, member: discord.Member, lý_do: str = "Không có lý do"):
    await member.kick(reason=lý_do)
    await i.response.send_message(f"✅ Đã kick {member.mention}")

@tree.command(name="ban")
@app_commands.default_permissions(ban_members=True)
async def ban(i: discord.Interaction, member: discord.Member, lý_do: str = "Không có lý do"):
    await member.ban(reason=lý_do)
    await i.response.send_message(f"✅ Đã ban {member.mention}")

@tree.command(name="unban")
@app_commands.default_permissions(ban_members=True)
async def unban(i: discord.Interaction, user_id: str):
    await i.guild.unban(discord.Object(id=int(user_id)))
    await i.response.send_message(f"✅ Đã gỡ ban <@{user_id}>")

@tree.command(name="mute")
@app_commands.default_permissions(manage_roles=True)
async def mute(i: discord.Interaction, member: discord.Member, phút: int = 10):
    muted = discord.utils.get(i.guild.roles, name="Muted")
    if not muted:
        muted = await i.guild.create_role(name="Muted")
        for ch in i.guild.channels:
            await ch.set_permissions(muted, send_messages=False, speak=False)
    await member.add_roles(muted)
    await i.response.send_message(f"🔇 {member.mention} bị mute {phút} phút")
    await asyncio.sleep(phút*60)
    await member.remove_roles(muted)

@tree.command(name="unmute")
@app_commands.default_permissions(manage_roles=True)
async def unmute(i: discord.Interaction, member: discord.Member):
    muted = discord.utils.get(i.guild.roles, name="Muted")
    if muted and muted in member.roles:
        await member.remove_roles(muted)
        await i.response.send_message(f"✅ Đã gỡ mute cho {member.mention}")
    else:
        await i.response.send_message("Người này không bị mute!")

@tree.command(name="lock")
@app_commands.default_permissions(manage_channels=True)
async def lock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False)
    await i.response.send_message("🔒 Kênh đã bị khóa!")

@tree.command(name="unlock")
@app_commands.default_permissions(manage_channels=True)
async def unlock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=None)
    await i.response.send_message("🔓 Kênh đã mở khóa!")

@tree.command(name="clear")
@app_commands.default_permissions(manage_messages=True)
async def clear(i: discord.Interaction, số_lượng: int = 50):
    await i.channel.purge(limit= số_lượng + 1)
    await i.response.send_message(f"🗑️ Đã xóa {số_lượng} tin!", ephemeral=True)

# ============================= LỆNH CHỈ OWNER =============================

# === MỚI: ĐỔI TRẠNG THÁI BOT ===
@tree.command(name="status", description="⚡ Đổi trạng thái bot (chỉ owner)")
@is_bot_owner()
async def status(i: discord.Interaction, loại: str, *, nội_dung: str):
    loại = loại.lower()
    if loại == "play":
        activity = discord.Game(name=nội_dung)
    elif loại == "watch":
        activity = discord.Activity(type=discord.ActivityType.watching, name=nội_dung)
    elif loại == "listen":
        activity = discord.Activity(type=discord.ActivityType.listening, name=nội_dung)
    elif loại == "stream":
        activity = discord.Streaming(name=nội_dung, url="https://twitch.tv/yourchannel")
    else:
        await i.response.send_message("❌ Loại không hợp lệ! Dùng: play / watch / listen / stream")
        return
    
    await bot.change_presence(activity=activity)
    await i.response.send_message(f"✅ Đã đổi trạng thái → **{loại.capitalize()} {nội_dung}**", ephemeral=True)

# lệnh prefix !status (cũng chỉ owner)
@bot.command()
@is_bot_owner_prefix()
async def status(ctx, loại: str, *, nội_dung: str):
    await status(ctx, loại=loại, nội_dung=nội_dung)  # gọi lại lệnh slash

# các lệnh owner khác
@tree.command(name="dm", description="Gửi tin riêng")
@is_bot_owner()
async def dm(i: discord.Interaction, user: discord.User, *, nội_dung: str):
    try:
        await user.send(nội_dung)
        await i.response.send_message(f"✅ Đã gửi DM cho {user}", ephemeral=True)
    except:
        await i.response.send_message("❌ Không gửi được DM!", ephemeral=True)

@tree.command(name="shutdown", description="Tắt bot")
@is_bot_owner()
async def shutdown(i: discord.Interaction):
    await i.response.send_message("🔴 Bot tắt đây chủ nhân...")
    await bot.close()

# ============================= CHẠY BOT =============================
bot.run(TOKEN)
