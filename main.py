import discord
from discord import app_commands
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64
import os
import asyncio
import json
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import requests
import random

# Flask app for keep alive
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is alive and running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# Khởi động Flask server
keep_alive()

# Lấy token từ environment variable
TOKEN = os.environ.get('TOKEN')

if not TOKEN:
    print("❌ Lỗi: Không tìm thấy TOKEN!")
    exit(1)

# Cấu hình Discord
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Lưu trữ session
encryption_sessions = {}

# Biến để theo dõi trạng thái bot
bot_start_time = datetime.now()

class AESEncryption:
    @staticmethod
    def generate_key_from_password(password: str, salt: bytes = None) -> tuple:
        """Tạo khóa từ mật khẩu sử dụng PBKDF2"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt

    @staticmethod
    def encrypt_aes_gcm(data: bytes, password: str) -> dict:
        """Mã hóa AES-256-GCM"""
        salt = os.urandom(16)
        key, salt = AESEncryption.generate_key_from_password(password, salt)
        iv = os.urandom(12)
        
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return {
            'ciphertext': base64.urlsafe_b64encode(ciphertext).decode(),
            'iv': base64.urlsafe_b64encode(iv).decode(),
            'salt': base64.urlsafe_b64encode(salt).decode(),
            'tag': base64.urlsafe_b64encode(encryptor.tag).decode()
        }

# Hàm ping để giữ bot alive
async def ping_server():
    while True:
        try:
            # Tự ping chính nó để giữ active
            requests.get('https://your-bot-name.onrender.com', timeout=5)
            print(f"🔄 Keep-alive ping at {datetime.now().strftime('%H:%M:%S')}")
        except:
            print("⚠️  Không thể ping server")
        await asyncio.sleep(300)  # Ping mỗi 5 phút

@client.event
async def on_ready():
    print(f'✅ Bot {client.user} đã sẵn sàng!')
    print(f'📊 Đang chạy trên {len(client.guilds)} server(s)')
    print(f'⏰ Bot khởi động lúc: {bot_start_time}')
    
    await tree.sync()
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/mahoa | !mahoa"))
    
    # Bắt đầu task keep-alive
    client.loop.create_task(ping_server())

# Slash Command /mahoa
@tree.command(name="mahoa", description="Mã hóa source code với AES-256-GCM")
async def mahoa_slash(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    encryption_sessions[user_id] = {
        'step': 'waiting_source',
        'created_at': datetime.now(),
        'type': 'slash'
    }
    
    embed = discord.Embed(
        title="🔐 **MÃ HÓA SOURCE CODE**",
        description="**Vui lòng gửi source code của bạn để tiến hành mã hóa**",
        color=0x5865F2,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="📤 Cách gửi:",
        value="• Gửi code trực tiếp trong tin nhắn\n• Hoặc attach file (.txt, .py, .js, .java, .cpp, v.v.)",
        inline=False
    )
    embed.add_field(
        name="🔒 Thuật toán:",
        value="AES-256-GCM với PBKDF2",
        inline=True
    )
    embed.add_field(
        name="⏱️ Thời hạn:",
        value="5 phút",
        inline=True
    )
    embed.set_footer(text="Hệ thống mã hóa bảo mật cao")
    
    await interaction.response.send_message(embed=embed)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Prefix Command !mahoa
    if message.content.startswith('!mahoa'):
        user_id = message.author.id
        
        encryption_sessions[user_id] = {
            'step': 'waiting_source',
            'created_at': datetime.now(),
            'type': 'prefix'
        }
        
        embed = discord.Embed(
            title="🔐 **MÃ HÓA SOURCE CODE**",
            description="**Vui lòng gửi source code của bạn để tiến hành mã hóa**",
            color=0x5865F2,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="📤 Cách gửi:",
            value="• Gửi code trực tiếp trong tin nhắn\n• Hoặc attach file (.txt, .py, .js, .java, .cpp, v.v.)",
            inline=False
        )
        embed.add_field(
            name="🔒 Thuật toán:",
            value="AES-256-GCM với PBKDF2",
            inline=True
        )
        embed.add_field(
            name="⏱️ Thời hạn:",
            value="5 phút",
            inline=True
        )
        embed.set_footer(text="Hệ thống mã hóa bảo mật cao")
        
        await message.reply(embed=embed)

    # Xử lý source code từ người dùng
    elif message.author.id in encryption_sessions:
        user_id = message.author.id
        session = encryption_sessions[user_id]
        
        # Kiểm tra timeout
        if datetime.now() - session['created_at'] > timedelta(minutes=5):
            del encryption_sessions[user_id]
            await message.reply("❌ **Session đã hết hạn!** Vui lòng sử dụng lệnh lại.")
            return

        if session['step'] == 'waiting_source':
            try:
                # Lấy source code
                source_content = ""
                file_used = False
                
                if message.attachments:
                    for attachment in message.attachments:
                        valid_extensions = ['.txt', '.py', '.js', '.java', '.cpp', '.c', '.html', '.css', '.php', '.md', '.json', '.xml']
                        if any(attachment.filename.endswith(ext) for ext in valid_extensions):
                            file_content = await attachment.read()
                            source_content = file_content.decode('utf-8')
                            file_used = True
                            break
                    else:
                        await message.reply("❌ **Không tìm thấy file văn bản hợp lệ!**")
                        return
                else:
                    source_content = message.content

                if not source_content.strip():
                    await message.reply("❌ **Source code không được để trống!**")
                    return

                # Lưu source và chuyển sang bước mật khẩu
                session['source_content'] = source_content
                session['step'] = 'waiting_password'
                session['file_used'] = file_used
                
                embed = discord.Embed(
                    title="🔑 **THIẾT LẬP MẬT KHẨU**",
                    description="Vui lòng nhập mật khẩu để mã hóa:",
                    color=0xF1C40F
                )
                embed.add_field(
                    name="💡 Yêu cầu:",
                    value="• Mật khẩu mạnh (tối thiểu 4 ký tự)\n• **LƯU Ý:** Không thể khôi phục nếu quên mật khẩu!",
                    inline=False
                )
                embed.add_field(
                    name="📊 Kích thước source:",
                    value=f"{len(source_content):,} ký tự",
                    inline=True
                )
                embed.add_field(
                    name="📁 Loại:",
                    value="File" if file_used else "Text",
                    inline=True
                )
                
                await message.reply(embed=embed)
                
            except Exception as e:
                await message.reply(f"❌ **Lỗi xử lý:** {str(e)}")
                if user_id in encryption_sessions:
                    del encryption_sessions[user_id]

        elif session['step'] == 'waiting_password':
            password = message.content.strip()
            
            if len(password) < 4:
                await message.reply("❌ **Mật khẩu quá ngắn!** Tối thiểu 4 ký tự.")
                return
            
            # Thông báo đang mã hóa
            processing_msg = await message.reply("🛡️ **Đang mã hóa source code với AES-256-GCM...**")
            
            try:
                # Mã hóa source code
                source_bytes = session['source_content'].encode('utf-8')
                encrypted_data = AESEncryption.encrypt_aes_gcm(source_bytes, password)
                
                # Tạo file kết quả
                result_data = {
                    'encryption_info': {
                        'algorithm': 'AES-256-GCM',
                        'key_derivation': 'PBKDF2-SHA256-100000',
                        'created_at': datetime.now().isoformat(),
                        'data_size': len(source_bytes),
                        'original_type': 'file' if session['file_used'] else 'text'
                    },
                    'encrypted_data': encrypted_data
                }
                
                result_json = json.dumps(result_data, indent=2)
                
                # Tạo filename với timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                encrypted_file = discord.File(
                    fp=discord.BytesIO(result_json.encode('utf-8')),
                    filename=f"encrypted_source_{timestamp}.secure"
                )
                
                # Embed kết quả
                embed = discord.Embed(
                    title="✅ **MÃ HÓA THÀNH CÔNG**",
                    description="Source code của bạn đã được mã hóa bảo mật!",
                    color=0x2ECC71,
                    timestamp=datetime.now()
                )
                embed.add_field(
                    name="🔐 Thuật toán",
                    value="AES-256-GCM",
                    inline=True
                )
                embed.add_field(
                    name="📊 Kích thước gốc",
                    value=f"{len(source_bytes):,} bytes",
                    inline=True
                )
                embed.add_field(
                    name="🔑 Bảo mật",
                    value="PBKDF2 100,000 iterations",
                    inline=True
                )
                embed.add_field(
                    name="💾 File output",
                    value=f"encrypted_source_{timestamp}.secure",
                    inline=False
                )
                embed.add_field(
                    name="📝 Lưu ý quan trọng",
                    value="• **LƯU LẠI MẬT KHẨU** để giải mã sau này\n• Không thể khôi phục nếu mất mật khẩu\n• File chứa dữ liệu mã hóa an toàn",
                    inline=False
                )
                embed.set_footer(text="Hệ thống mã hóa AES-256-GCM")
                
                # Gửi kết quả
                try:
                    await message.author.send(
                        content=f"🔐 **Source code đã được mã hóa thành công!**\n**Mật khẩu bạn dùng:** ||{password}||\n\n*Lưu ý: Giữ kín mật khẩu này để bảo vệ dữ liệu*",
                        embed=embed,
                        file=encrypted_file
                    )
                    await processing_msg.edit(content="✅ **Mã hóa hoàn tất! Source code đã mã hóa đã được gửi đến tin nhắn riêng của bạn.**")
                except discord.Forbidden:
                    await processing_msg.edit(content="❌ **Không thể gửi tin nhắn riêng!** Vui lòng bật DM với bot và thử lại.")
                
            except Exception as e:
                await processing_msg.edit(content=f"❌ **Lỗi mã hóa:** {str(e)}")
            
            finally:
                # Dọn dẹp session
                if user_id in encryption_sessions:
                    del encryption_sessions[user_id]

    # Lệnh hủy
    elif message.content.startswith('!huy'):
        user_id = message.author.id
        if user_id in encryption_sessions:
            del encryption_sessions[user_id]
            await message.reply("❌ **Đã hủy session mã hóa hiện tại.**")

    # Lệnh kiểm tra trạng thái bot
    elif message.content.startswith('!status'):
        uptime = datetime.now() - bot_start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed = discord.Embed(
            title="🤖 **TRẠNG THÁI BOT**",
            color=0x7289DA,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="🟢 Trạng thái",
            value="Online ✅",
            inline=True
        )
        embed.add_field(
            name="⏰ Uptime",
            value=f"{hours}h {minutes}m {seconds}s",
            inline=True
        )
        embed.add_field(
            name="📊 Servers",
            value=f"{len(client.guilds)} server(s)",
            inline=True
        )
        embed.add_field(
            name="🛠️ Tính năng",
            value="Mã hóa AES-256-GCM",
            inline=True
        )
        embed.add_field(
            name="🔗 Hosting",
            value="Render + Keep Alive",
            inline=True
        )
        embed.set_footer(text=f"Bot ID: {client.user.id}")
        
        await message.reply(embed=embed)

# Xử lý lỗi
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    print(f"Lỗi slash command: {error}")
    if isinstance(error, app_commands.CommandNotFound):
        return
    
    try:
        await interaction.response.send_message("❌ Có lỗi xảy ra khi thực hiện lệnh!", ephemeral=True)
    except:
        pass

# Chạy bot
if __name__ == "__main__":
    try:
        print("🚀 Đang khởi động bot mã hóa với Keep Alive...")
        print("📡 Flask server đang chạy trên port 8080")
        client.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Token không hợp lệ! Kiểm tra DISCORD_BOT_TOKEN.")
    except Exception as e:
        print(f"❌ Lỗi khởi động: {e}")
