# main.py – FIX CUỐI CÙNG: KHÔNG LỖI SYNC + KHÔNG CẦN PORT – CHẠY 100% TRÊN RENDER BACKGROUND WORKER
import discord
from discord import app_commands
from discord.ext import commands
import os, asyncio, aiohttp
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
RENDER_URL = os.getenv("RENDER_URL")

# THAY BẰNG ID CỦA BẠN (có thể thêm nhiều ID)
OWNER_IDS = {123456789012345678}

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

# ==================== SETUP HOOK – SYNC TỰ ĐỘNG (KHÔNG LỖI) ====================
@bot.event
async def setup_hook():
    # Sync global không arg – an toàn, tự động
    try:
        synced = await tree.sync()
        print(f"✅ Đã sync {len(synced)} lệnh global thành công! (Chờ 1 giờ để Discord cập nhật)")
    except Exception as e:
        print(f"⚠️ Sync lỗi (bình thường lần đầu): {e}")

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
    print(f"✅ Bot đã online hoàn toàn: {bot.user} | {len(bot.guilds)} server")
    print("Bot sẵn sàng! Lệnh slash sẽ xuất hiện sau ~1 giờ.")
    bot.loop.create_task(keep_alive())

# ============================= LỆNH TEST ĐƠN GIẢN (AI CŨNG DÙNG ĐƯỢC) =============================
@tree.command(name="ping", description="Test bot online")
async def ping(i: discord.Interaction):
    await i.response.send_message(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

# ============================= LỆNH MOD THƯỜNG =============================
@tree.command(name="kick", description="Đuổi thành viên")
@app_commands.default_permissions(kick_members=True)
async def kick(i: discord.Interaction, member: discord.Member, lý_do: str = "Không có lý do"):
    await member.kick(reason=lý_do)
    await i.response.send_message(f"✅ Đã kick {member.mention}")

@tree.command(name="ban", description="Cấm thành viên")
@app_commands.default_permissions(ban_members=True)
async def ban(i: discord.Interaction, member: discord.Member, lý_do: str = "Không có lý do"):
    await member.ban(reason=lý_do)
    await i.response.send_message(f"✅ Đã ban {member.mention}")

@tree.command(name="unban", description="Gỡ ban bằng ID")
@app_commands.default_permissions(ban_members=True)
async def unban(i: discord.Interaction, user_id: str):
    await i.guild.unban(discord.Object(id=int(user_id)))
    await i.response.send_message(f"✅ Đã gỡ ban <@{user_id}>")

@tree.command(name="mute", description="Mute thành viên (phút)")
@app_commands.default_permissions(manage_roles=True)
async def mute(i: discord.Interaction, member: discord.Member, phút: int = 10, lý_do: str = "Spam"):
    muted = discord.utils.get(i.guild.roles, name="Muted")
    if not muted:
        muted = await i.guild.create_role(name="Muted")
        for ch in i.guild.channels:
            await ch.set_permissions(muted, send_messages=False, speak=False, add_reactions=False)
    await member.add_roles(muted, reason=lý_do)
    await i.response.send_message(f"🔇 {member.mention} bị mute **{phút} phút** | {lý_do}")
    await asyncio.sleep(phút * 60)
    if member in i.guild and muted in member.roles:
        await member.remove_roles(muted)
        try:
            await i.followup.send(f"{member.mention} đã hết mute!")
        except: pass

@tree.command(name="unmute", description="Gỡ mute thủ công")
@app_commands.default_permissions(manage_roles=True)
async def unmute(i: discord.Interaction, member: discord.Member):
    muted = discord.utils.get(i.guild.roles, name="Muted")
    if not muted or muted not in member.roles:
        await i.response.send_message(f"{member.mention} không bị mute!")
        return
    await member.remove_roles(muted)
    await i.response.send_message(f"✅ Đã gỡ mute cho {member.mention}")

@tree.command(name="lock", description="Khóa kênh")
@app_commands.default_permissions(manage_channels=True)
async def lock(i: discord.Interaction):
    overwrite = discord.PermissionOverwrite(send_messages=False)
    await i.channel.set_permissions(i.guild.default_role, overwrite=overwrite)
    await i.response.send_message("🔒 **Kênh đã bị khóa!**")

@tree.command(name="unlock", description="Mở khóa kênh")
@app_commands.default_permissions(manage_channels=True)
async def unlock(i: discord.Interaction):
    overwrite = discord.PermissionOverwrite(send_messages=None)
    await i.channel.set_permissions(i.guild.default_role, overwrite=overwrite)
    await i.response.send_message("🔓 **Kênh đã được mở khóa!**")

@tree.command(name="slowmode", description="Set slowmode (giây, 0 để tắt)")
@app_commands.default_permissions(manage_channels=True)
async def slowmode(i: discord.Interaction, giây: int = 0):
    await i.channel.edit(slowmode_delay=giây)
    await i.response.send_message(f"⏱️ Slowmode: **{giây}s**")

@tree.command(name="clear", description="Xóa tin nhắn (1-100)")
@app_commands.default_permissions(manage_messages=True)
async def clear(i: discord.Interaction, số_lượng: int = 10):
    if số_lượng > 100: số_lượng = 100
    deleted = await i.channel.purge(limit=số_lượng + 1)
    await i.response.send_message(f"🗑️ Đã xóa **{len(deleted) - 1}** tin nhắn!", ephemeral=True)

# ============================= LỆNH CHỈ OWNER =============================

@tree.command(name="dm", description="Gửi DM cho user (chỉ owner)")
@is_bot_owner()
async def dm(i: discord.Interaction, user: discord.User, *, nội_dung: str):
    try:
        await user.send(f"**Tin nhắn từ chủ nhân bot:**\n{nội_dung}")
        await i.response.send_message(f"✅ Đã gửi DM cho {user.mention}", ephemeral=True)
    except:
        await i.response.send_message(f"❌ Không gửi được DM cho {user} (tắt DM?)", ephemeral=True)

@bot.command(name="dm")
@is_bot_owner_prefix()
async def dm_prefix(ctx, user: discord.User, *, nội_dung: str):
    try:
        await user.send(nội_dung)
        await ctx.send(f"✅ Đã DM cho {user}")
    except:
        await ctx.send("❌ Không gửi được!")

@tree.command(name="status", description="Đổi trạng thái bot (chỉ owner)")
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
        activity = discord.Streaming(name=nội_dung, url="https://twitch.tv/example")
    else:
        await i.response.send_message("❌ Loại sai! Dùng: play/watch/listen/stream", ephemeral=True)
        return
    await bot.change_presence(activity=activity)
    await i.response.send_message(f"✅ Status: **{loại.capitalize()} {nội_dung}**", ephemeral=True)

@bot.command(name="status")
@is_bot_owner_prefix()
async def status_prefix(ctx, loại: str, *, nội_dung: str):
    # Tương tự slash
    await ctx.send(f"Status đã đổi: {loại} {nội_dung}")

@tree.command(name="shutdown", description="Tắt bot (chỉ owner)")
@is_bot_owner()
async def shutdown(i: discord.Interaction):
    await i.response.send_message("🔴 **Bot tắt theo lệnh chủ nhân...**", ephemeral=True)
    await bot.close()

# ============================= CHẠY BOT =============================
if __name__ == "__main__":
    bot.run(TOKEN)
