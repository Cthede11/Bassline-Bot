import sys
import os
import discord
import asyncio
from discord.ext import commands
from src.config.settings import DISCORD_TOKEN
from src.commands.play import PlayCommand

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    if bot.user.name != "BasslineBot":
        await bot.user.edit(username="BasslineBot")


async def main():
    async with bot:
        await bot.add_cog(PlayCommand(bot))
        await bot.start(DISCORD_TOKEN)

asyncio.run(main())
