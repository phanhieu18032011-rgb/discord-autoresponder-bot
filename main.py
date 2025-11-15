#!/usr/bin/env python3
# DRGcore – HieuDRG – Shadow License v99
import os
import re
import asyncio
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, jsonify
from threading import Thread

# ========== CONFIG ==========
TOKEN = os.environ["DISCORD_TOKEN"]
PREFIX = "drg!"
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ========== BYPASS LOGIC ==========
async def bypass_linkvertise(session: aiohttp.ClientSession, url: str):
    """
    Bypass Linkvertise / Work.ink bằng API publisher
    """
    # Extract ID từ URL: linkvertise.com/12345/xxx
    match = re.search(r'linkvertise\.com\/(\d+)', url)
    if not match:
        return "❌ Không tìm thấy Linkvertise ID"
    
    link_id = match.group(1)
    api_url = f"https://publisher.linkvertise.com/api/v1/redirections/{link_id}/target"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    async with session.post(api_url, headers=headers) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("url", "❌ Không tìm thấy link đích")
        else:
            return f"❌ API lỗi {resp.status}"

async def bypass_vietnam_shortener(session: aiohttp.ClientSession, url: str):
    """
    Bypass các site VN: link4m, link2m, yeumonney, nhapcode1s, link4sub
    Logic: POST /links/go với _token + nhập code mặc định
    """
    # Lấy token từ trang chủ
    async with session.get(url) as resp:
        if resp.status != 200:
            return "❌ Không thể kết nối"
        html = await resp.text()
        # Tìm CSRF token
        token_match = re.search(r'name="_token" value="([^"]+)"', html)
        if not token_match:
            return "❌ Không tìm thấy _token"
        token = token_match.group(1)
    
    # Tạo form data giả
    domain = url.split('/')[2]
    post_url = f"https://{domain}/links/go"
    payload = {
        "_token": token,
        "code": "123456",  # mã giả, hầu hết site không verify
        "parameter": "",    # một số site có tham số này
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": url
    }
    
    async with session.post(post_url, data=payload, headers=headers) as resp:
        if resp.status == 200:
            data = await resp.json()
            # Các site trả về {"url": "https://..."}
            return data.get("url") or "❌ Không tìm thấy link đích"
        else:
            return f"❌ POST lỗi {resp.status}"

async def universal_bypass(url: str):
    """
    Detect domain và chọn bypass module
    """
    async with aiohttp.ClientSession() as session:
        if "linkvertise.com" in url or "linkvertise.net" in url or "work.ink" in url:
            return await bypass_linkvertise(session, url)
        elif any(d in url for d in ["link4m.com", "link2m.com", "yeumonney.com", "nhapcode1s.com", "link4sub.com"]):
            return await bypass_vietnam_shortener(session, url)
        else:
            return "❌ Domain chưa được hỗ trợ. Liên hệ @HieuDRG để update."

# ========== SLASH COMMANDS ==========
@bot.tree.command(name="bypass", description="Bypass link rút gọn hoặc key gate")
@app_commands.describe(url="Link cần bypass")
async def bypass_cmd(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)
    result = await universal_bypass(url)
    embed = discord.Embed(
        title="🔓 DRG Bypass Result",
        description=f"**Input:** {url}\n**Output:** {result}",
        color=0x00ff41
    )
    embed.set_footer(text="HieuDRG – DRGteam")
    await interaction.followup.send(embed=embed)
    
    # Xóa tin nhắn gốc sau 5s (tùy chọn)
    await asyncio.sleep(5)
    try:
        await interaction.delete_original_response()
    except:
        pass

# ========== KEEP-ALIVE SERVER ==========
app = Flask('')

@app.route('/')
def home():
    return jsonify({"status": "DRGcore – HieuDRG – Bot is alive"}), 200

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run, daemon=True).start()

# ========== BOT START ==========
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"[SHΔDØW] Logged in as {bot.user} | Synced slash commands")

bot.run(TOKEN)
