# main.py – ĐÃ THÊM /unmute và /dm (chỉ owner dùng dm)
# → Lệnh quản lý bình thường: ai có quyền server đều dùng
# → Lệnh nguy hiểm + dm: CHỈ OWNER BOT MỚI DÙNG ĐƯỢC

import discord
from discord import app_commands
from discord.ext import commands
import os, asyncio, aiohttp, traceback
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
RENDER_URL = os.getenv("RENDER_URL")

# THAY BẰNG ID CỦA BẠN (có thể thêm nhiều ID cách nhau dấu phẩy)
OWNER_IDS = {1333333136037249057}  

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
tree = bot.tree

# ==================== CHECK OWNER (chỉ cho lệnh nguy hiểm + dm) ====================
def is_bot_owner():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id not in OWNER_IDS:
            await interaction.response.send_message("Chỉ chủ nhân bot mới dùng được lệnh này!", ephemeral=True)
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
    await tree.sync(global_=True)
    print(f"Bot đã online: {bot.user} | {len(bot.guilds)} server")
    bot.loop.create_task(keep_alive())

# ============================= LỆNH THƯỜNG – AI CÓ QUYỀN SERVER ĐỀU DÙNG ĐƯỢC =============================

@tree.command(name="kick", description="Đuổi thành viên")
@app_commands.default_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, lý_do: str = "Không có lý do"):
    await member.kick(reason=lý_do)
    await interaction.response.send_message(f"Đã kick {member.mention} | {lý_do}")

@tree.command(name="ban", description="Cấm thành viên")
@app_commands.default_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, lý_do: str = "Không có lý do"):
    await member.ban(reason=lý_do)
    await interaction.response.send_message(f"Đã ban {member.mention} | {lý_do}")

@tree.command(name="unban", description="Gỡ ban bằng ID")
@app_commands.default_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str):
    await interaction.guild.unban(discord.Object(id=int(user_id)))
    await interaction.response.send_message(f"Đã gỡ ban cho <@{user_id}>")

@tree.command(name="mute", description="Mute thành viên (phút)")
@app_commands.default_permissions(manage_roles=True)
async def mute(interaction: discord.Interaction, member: discord.Member, phút: int = 10, lý_do: str = "Spam"):
    muted = discord.utils.get(interaction.guild.roles, name="Muted")
    if not muted:
        muted = await interaction.guild.create_role(name="Muted")
        for ch in interaction.guild.channels:
            await ch.set_permissions(muted, send_messages=False, speak=False, add_reactions=False)
    await member.add_roles(muted, reason=lý_do)
    await interaction.response.send_message(f"{member.mention} đã bị mute **{phút} phút** | {lý_do}")
    await asyncio.sleep(phút * 60)
    if muted in member.roles:
        await member.remove_roles(muted)
        try:
            await interaction.followup.send(f"{member.mention} đã hết thời gian mute!")
        except: pass

# === MỚI: LỆNH UNMUTE (ai có quyền manage_roles đều dùng được) ===
@tree.command(name="unmute", description="Gỡ mute thủ công cho thành viên")
@app_commands.default_permissions(manage_roles=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    muted = discord.utils.get(interaction.guild.roles, name="Muted")
    if not muted:
        await interaction.response.send_message("Không tìm thấy role Muted!")
        return
    if muted not in member.roles:
        await interaction.response.send_message(f"{member.mention} không bị mute!")
        return
    await member.remove_roles(muted)
    await interaction.response.send_message(f"Đã gỡ mute cho {member.mention}!")

@tree.command(name="lock", description="Khóa kênh")
@app_commands.default_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("**Kênh đã bị khóa!**")

@tree.command(name="unlock", description="Mở khóa kênh")
@app_commands.default_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
    await interaction.response.send_message("**Kênh đã được mở khóa!**")

@tree.command(name="slowmode", description="Set slowmode (giây)")
@app_commands.default_permissions(manage_channels=True)
async def slowmode(interaction: discord.Interaction, giây: int):
    await interaction.channel.edit(slowmode_delay=giây)
    await interaction.response.send_message(f"Slowmode: **{giây}s**")

@tree.command(name="clear", description="Xóa tin nhắn")
@app_commands.default_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, số_lượng: int = 50):
    await interaction.channel.purge(limit=min(số_lượng + 1, 200))
    await interaction.response.send_message(f"Đã xóa **{số_lượng}** tin nhắn!", ephemeral=True)

# ============================= LỆNH NGUY HIỂM – CHỈ OWNER BOT DÙNG =============================

# === MỚI: LỆNH DM (chỉ owner dùng được) ===
@tree.command(name="dm", description="Gửi tin nhắn riêng cho bất kỳ ai")
@is_bot_owner()
async def dm(interaction: discord.Interaction, user: discord.User, *, nội_dung: str):
    try:
        await user.send(f"**Tin nhắn từ chủ nhân bot:**\n\n{nội_dung}")
        await interaction.response.send_message(f"Đã gửi DM thành công cho {user} (`{user.id}`)", ephemeral=True)
    except:
        await interaction.response.send_message(f"Không gửi được DM cho {user} (có thể tắt tin nhắn riêng)", ephemeral=True)

# Lệnh prefix dm (cũng chỉ owner)
@bot.command(name="dm")
@is_bot_owner_prefix()
async def dm_prefix(ctx, user: discord.User, *, nội_dung):
    try:
        await user.send(f"Tin nhắn từ chủ nhân bot:\n{nội_dung}")
        await ctx.send(f"Đã DM cho {user}")
    except:
        await ctx.send("Không gửi được!")

@tree.command(name="shutdown", description="Tắt bot")
@is_bot_owner()
async def shutdown(interaction: discord.Interaction):
    await interaction.response.send_message("**Bot đang tắt...**")
    await bot.close()

@tree.command(name="eval", description="Chạy code Python")
@is_bot_owner()
async def eval_cmd(interaction: discord.Interaction, *, code: str):
    await interaction.response.defer(ephemeral=True)
    try:
        result = eval(code)
        await interaction.followup.send(f"```py\n{result}\n```", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"```py\n{traceback.format_exc()}\n```", ephemeral=True)

@tree.command(name="spam", description="Spam tin (max 20)")
@is_bot_owner()
async def spam(interaction: discord.Interaction, số_lượng: int, *, nội_dung: str):
    await interaction.response.defer(ephemeral=True)
    for _ in range(min(số_lượng, 20)):
        await interaction.channel.send(nội_dung)
        await asyncio.sleep(1.2)
    await interaction.followup.send("Spam xong!", ephemeral=True)

@tree.command(name="status", description="Đổi status bot")
@is_bot_owner()
async def status(interaction: discord.Interaction, loại: str, *, nội_dung: str):
    activities = {
        "play": discord.Game(name=nội_dung),
        "watch": discord.Activity(type=discord.ActivityType.watching, name=nội_dung),
        "listen": discord.Activity(type=discord.ActivityType.listening, name=nội_dung),
        "stream": discord.Streaming(name=nội_dung, url="https://twitch.tv/pewdiepie")
    }
    await bot.change_presence(activity=activities.get(loại.lower()))
    await interaction.response.send_message(f"Status đã đổi: {loại} {nội_dung}")

# ============================= CHẠY BOT =============================
bot.run(TOKEN)
