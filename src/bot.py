import sys
import os
import discord
import asyncio
import traceback 
from discord.ext import commands
from src.config.settings import DISCORD_TOKEN
from src.commands.play import PlayCommand 
from src.commands.playlist_command import PlaylistCommand 
from src.utils.music import music_manager # Import music_manager
from src.utils.discord_voice import LogColors, log # For logging

intents = discord.Intents.default()
intents.message_content = True 
intents.guilds = True
intents.voice_states = True # Essential for on_voice_state_update

class BasslineBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or("!bl "), intents=intents)

    async def setup_hook(self):
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
    try:
        activity = discord.Activity(type=discord.ActivityType.listening, name="/play | !bl help")
        await bot.change_presence(activity=activity)
        print("🎧 Bot activity set to 'Listening to /play | !bl help'")
    except Exception as e:
        print(f"⚠️ Failed to set bot activity: {e}")

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """
    Handles voice state updates, especially for the bot itself.
    If the bot is disconnected from a voice channel, it clears its music state for that guild.
    """
    if member.id == bot.user.id: # Check if the update is for the bot itself
        guild_id = member.guild.id
        if before.channel is not None and after.channel is None:
            # Bot was in a channel (before.channel) and now is not in any channel (after.channel is None)
            # This means the bot was disconnected (manually, kicked, or left via command/idle timeout)
            log_prefix = f"[VOICE_STATE_UPDATE Guild: {guild_id}] "
            log(log_prefix + "BOT_DISCONNECTED", f"Bot disconnected from voice channel '{before.channel.name}'. Clearing music state.", LogColors.YELLOW)
            
            # Stop any active player for this guild if it somehow still exists
            vc = music_manager.voice_clients.get(guild_id)
            if vc and (vc.is_playing() or vc.is_paused()):
                vc.stop()
                log(log_prefix + "BOT_DISCONNECTED", "Stopped active player.", LogColors.YELLOW)
            
            music_manager.clear_guild_state(guild_id) # Clear queue, now_playing, etc.
            
            # Optionally send a message to a relevant text channel
            # This part needs a good way to find the "last active" or a default channel.
            # For now, just logging. If you have a system for tracking last interaction channel, use it.
            # Example:
            # last_interaction_channel_id = music_manager.get_last_interaction_channel(guild_id)
            # if last_interaction_channel_id:
            #     text_channel = bot.get_channel(last_interaction_channel_id)
            #     if text_channel:
            #         try:
            #             await text_channel.send("I've been disconnected from the voice channel. Playback stopped and queue cleared.")
            #         except discord.Forbidden:
            #             log(log_prefix + "BOT_DISCONNECTED_MSG_FAIL", "No permission to send disconnect message.", LogColors.YELLOW)
            #         except Exception as e:
            #             log(log_prefix + "BOT_DISCONNECTED_MSG_ERROR", f"Error sending disconnect message: {e}", LogColors.YELLOW)


async def main():
    async with bot: 
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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🤖 Bot shutting down by KeyboardInterrupt...")
    except Exception as e: 
        print(f"💥 A critical error occurred: {e}")
        traceback.print_exc()
