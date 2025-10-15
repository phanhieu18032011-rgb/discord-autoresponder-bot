# games.py
import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1) Guess number (prefix)
    @commands.command(name="guess")
    async def guess_cmd(self, ctx):
        number = random.randint(1, 20)
        await ctx.send("🎯 I thought of a number between 1 and 20. Guess it!")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=15)
            if int(msg.content) == number:
                await ctx.send("✅ Correct!")
            else:
                await ctx.send(f"❌ Wrong. The number was {number}.")
        except asyncio.TimeoutError:
            await ctx.send(f"⌛ Timeout. The number was {number}.")

    # slash version
    @app_commands.command(name="guess", description="Guess a number 1-20")
    async def guess_slash(self, interaction: discord.Interaction):
        number = random.randint(1, 20)
        await interaction.response.send_message("🎯 I thought of a number between 1 and 20. Reply with your guess in chat (15s).")
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel and m.content.isdigit()
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=15)
            if int(msg.content) == number:
                await interaction.followup.send("✅ Correct!")
            else:
                await interaction.followup.send(f"❌ Wrong. The number was {number}.")
        except asyncio.TimeoutError:
            await interaction.followup.send(f"⌛ Timeout. The number was {number}.")

    # 2) Rock Paper Scissors (prefix)
    @commands.command(name="rps")
    async def rps_cmd(self, ctx, choice: str):
        choice = choice.lower()
        bot_choice = random.choice(["rock", "paper", "scissors"])
        result = "Tie!"
        if choice == bot_choice:
            result = "Tie!"
        elif (choice, bot_choice) in [("rock","scissors"), ("scissors","paper"), ("paper","rock")]:
            result = "You win!"
        else:
            result = "You lose!"
        await ctx.send(f"I chose **{bot_choice}** — {result}")

    @app_commands.command(name="rps", description="Play rock paper scissors")
    @app_commands.describe(choice="rock/paper/scissors")
    async def rps_slash(self, interaction: discord.Interaction, choice: str):
        choice = choice.lower()
        bot_choice = random.choice(["rock", "paper", "scissors"])
        result = "Tie!"
        if choice == bot_choice:
            result = "Tie!"
        elif (choice, bot_choice) in [("rock","scissors"), ("scissors","paper"), ("paper","rock")]:
            result = "You win!"
        else:
            result = "You lose!"
        await interaction.response.send_message(f"I chose **{bot_choice}** — {result}")

    # 3) Dice (prefix)
    @commands.command(name="dice")
    async def dice_cmd(self, ctx):
        await ctx.send(f"🎲 You rolled: {random.randint(1,6)}")

    @app_commands.command(name="dice", description="Roll a dice")
    async def dice_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🎲 You rolled: {random.randint(1,6)}")

    # 4) Hangman-like (very simple) (prefix)
    @commands.command(name="hangman")
    async def hangman_cmd(self, ctx):
        words = ["python", "discord", "render", "github"]
        word = random.choice(words)
        hidden = ["_"] * len(word)
        tries = 6
        await ctx.send(f"Hangman: {' '.join(hidden)} — {tries} tries. Send single letters.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and len(m.content) == 1
        while tries > 0 and "_" in hidden:
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send("Timeout! Game ended.")
                return
            ch = msg.content.lower()
            if ch in word:
                for i, c in enumerate(word):
                    if c == ch:
                        hidden[i] = ch
                await ctx.send("Good! " + " ".join(hidden))
            else:
                tries -= 1
                await ctx.send(f"Wrong! {tries} tries left.")
        if "_" not in hidden:
            await ctx.send(f"You won! Word: {word}")
        else:
            await ctx.send(f"You lost! Word: {word}")

    @app_commands.command(name="hangman", description="Simple hangman game")
    async def hangman_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("Use the chat to play a short hangman (you must reply with single letters).")
        # reuse prefix function via simulating a direct message loop is complex for slash; keep simple
        await interaction.followup.send("Please use the prefix command `hangman` for full interactive mode.", ephemeral=True)

    # 5) Blackjack (very simple)
    @commands.command(name="blackjack")
    async def blackjack_cmd(self, ctx):
        user = random.randint(15, 25)
        botv = random.randint(15, 25)
        if user > 21:
            res = "You busted!"
        elif botv > 21 or user > botv:
            res = "You win!"
        elif user == botv:
            res = "Tie!"
        else:
            res = "You lose!"
        await ctx.send(f"🃏 You: {user} | Bot: {botv} — {res}")

    @app_commands.command(name="blackjack", description="Simple blackjack")
    async def blackjack_slash(self, interaction: discord.Interaction):
        user = random.randint(15, 25)
        botv = random.randint(15, 25)
        if user > 21:
            res = "You busted!"
        elif botv > 21 or user > botv:
            res = "You win!"
        elif user == botv:
            res = "Tie!"
        else:
            res = "You lose!"
        await interaction.response.send_message(f"🃏 You: {user} | Bot: {botv} — {res}")

async def setup(bot):
    await bot.add_cog(Games(bot))
