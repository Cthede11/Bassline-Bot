import sys
import os
import discord
import asyncio
from discord.ext import commands
from src.config.settings import DISCORD_TOKEN
from src.commands.play import PlayCommand
from src.commands.playlist_command import PlaylistCommand

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
        
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Missing playlist name.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("⚠️ Bad argument. Try quoting the playlist name.")
    else:
        await ctx.send(f"❌ Unexpected error: {error}")


async def main():
    async with bot:
        await bot.add_cog(PlayCommand(bot))
        await bot.add_cog(PlaylistCommand(bot))
        await bot.start(DISCORD_TOKEN)

asyncio.run(main())
