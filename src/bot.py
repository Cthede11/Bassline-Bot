import sys
import os
import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from src.config.settings import DISCORD_TOKEN

from src.commands.play import PlayCommand
from src.commands.playlist_command import PlaylistCommand

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.voice_states = True

class BasslineBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        await self.add_cog(PlayCommand(self))
        await self.add_cog(PlaylistCommand(self))
        await self.tree.sync()
        print("🌐 Synced global slash commands")

bot = BasslineBot()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.tree.clear_commands()
    await bot.tree.sync()
    print("🔄 Cleared and re-synced commands")
    print("🎵 BasslineBot is online and ready!")

async def main():
    async with bot:
        await bot.start(DISCORD_TOKEN)

asyncio.run(main())
