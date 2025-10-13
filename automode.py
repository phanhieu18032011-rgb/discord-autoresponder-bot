import asyncio
import discord
from discord.ext import commands

# Danh sách từ cấm
BANNED_WORDS = ["chửi", "spam", "xxx", "ngu", "vl"]  # bạn có thể thêm tùy ý
# Giới hạn spam
SPAM_LIMIT = 5  # số tin trong 5 giây
TIME_FRAME = 5  # thời gian tính spam

# Lưu tạm tin nhắn người dùng
user_messages = {}

async def check_anti_spam(message: discord.Message):
    user_id = message.author.id
    now = message.created_at.timestamp()

    # Ghi nhận lịch sử tin nhắn
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(now)

    # Xóa tin cũ hơn TIME_FRAME
    user_messages[user_id] = [t for t in user_messages[user_id] if now - t < TIME_FRAME]

    # Nếu vượt giới hạn → cảnh cáo
    if len(user_messages[user_id]) >= SPAM_LIMIT:
        await message.delete()
        await message.channel.send(
            f"{message.author.mention}, bạn đang spam quá nhanh! ⚠️", delete_after=5
        )
        user_messages[user_id] = []


async def check_banned_words(message: discord.Message):
    for word in BANNED_WORDS:
        if word.lower() in message.content.lower():
            await message.delete()
            await message.channel.send(
                f"{message.author.mention}, từ **'{word}'** bị cấm! 🚫", delete_after=5
            )
            break


# Hàm khởi động module
async def handle_auto_mode(message: discord.Message):
    if message.author.bot:
        return

    await check_anti_spam(message)
    await check_banned_words(message)
