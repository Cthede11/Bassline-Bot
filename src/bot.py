import sys
import os
import discord
import asyncio
import traceback # For catching exceptions in main
from discord.ext import commands
# from discord import app_commands # app_commands is part of discord.ext.commands.Bot.tree
from src.config.settings import DISCORD_TOKEN

# Assuming your cogs are correctly imported
from src.commands.play import PlayCommand # Ensure this path is correct
from src.commands.playlist_command import PlaylistCommand # Ensure this path is correct

# Define intents clearly
intents = discord.Intents.default()
intents.message_content = True # Only if you need it for non-slash command features
intents.guilds = True
intents.voice_states = True
# intents.messages = True # Only if you need to read general message history beyond commands

class BasslineBot(commands.Bot):
    def __init__(self):
        # Using when_mentioned_or with a prefix like "!" allows for potential text commands later
        # For a slash-command-only bot, command_prefix is less critical but good to define.
        super().__init__(command_prefix=commands.when_mentioned_or("!bl "), intents=intents)

    async def setup_hook(self):
        # This is the primary place to load extensions (cogs) and sync commands.
        try:
            await self.add_cog(PlayCommand(self))
            print("⚙️ PlayCommand Cog Loaded Successfully")
        except Exception as e:
            print(f"❌ Failed to load PlayCommand Cog: {e}")
            traceback.print_exc()

        try:
            await self.add_cog(PlaylistCommand(self))
            print("⚙️ PlaylistCommand Cog Loaded Successfully")
        except Exception as e:
            print(f"❌ Failed to load PlaylistCommand Cog: {e}")
            traceback.print_exc()
        
        # Sync the command tree.
        # For global commands, this might take a bit to propagate (up to an hour sometimes).
        # For faster testing, you can sync to a specific guild:
        # GUILD_ID = 123456789012345678 # Replace with your test guild ID
        # test_guild = discord.Object(id=GUILD_ID)
        # self.tree.copy_global_to(guild=test_guild)
        # try:
        #     await self.tree.sync(guild=test_guild)
        #     print(f"🛠️ Synced commands to guild {GUILD_ID}")
        # except Exception as e:
        #     print(f"❌ Failed to sync commands to guild {GUILD_ID}: {e}")
        
        # Sync global commands
        try:
            await self.tree.sync()
            print("🌐 Synced global slash commands.")
        except Exception as e:
            print(f"❌ Failed to sync global slash commands: {e}")
            traceback.print_exc()


bot = BasslineBot()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"🤖 {bot.user.name} is online and ready in {len(bot.guilds)} server(s)!")
    # Command syncing is now handled in setup_hook.
    # Setting bot activity:
    try:
        activity = discord.Activity(type=discord.ActivityType.listening, name="/play | !bl help")
        await bot.change_presence(activity=activity)
        print("🎧 Bot activity set to 'Listening to /play | !bl help'")
    except Exception as e:
        print(f"⚠️ Failed to set bot activity: {e}")

async def main():
    async with bot: # This handles bot.close() automatically
        if DISCORD_TOKEN is None:
            print("❌ DISCORD_TOKEN is not set. Please check your .env file or environment variables.")
            return
        try:
            await bot.start(DISCORD_TOKEN)
        except discord.LoginFailure:
            print("❌ Failed to log in: Improper token has been passed.")
        except Exception as e:
            print(f"💥 An error occurred while starting the bot: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    # Setup for asyncio loop on Windows if needed for some libraries, though usually not for discord.py itself
    # if sys.platform == "win32":
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🤖 Bot shutting down by KeyboardInterrupt...")
    except Exception as e: # Catch-all for errors during asyncio.run if main() itself raises before bot starts
        print(f"💥 A critical error occurred: {e}")
        traceback.print_exc()
