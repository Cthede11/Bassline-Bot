import discord
import yt_dlp as youtube_dl


async def join_voice_channel(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        return await channel.connect()
    else:
        await ctx.send("You need to be in a voice channel to use this command.")
        return None

async def play_song(voice_client, search_query, return_source=False):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch10',
        'noplaylist': True,
        'extract_flat': False,
        'cookiefile': 'src/utils/cookies.txt',
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"{search_query} full song", download=False)

        # If this is a playlist or search result, get the first valid entry
        if 'entries' in info:
            entries = info['entries']
            selected = next((e for e in entries if e.get("duration", 0) >= 90), None)
        else:
            selected = info if info.get("duration", 0) >= 90 else None

        if not selected:
            raise Exception(f"No suitable result for: {search_query}")

        stream_url = selected['url']
        print(f"🔗 Streaming from: {stream_url}")
        print(f"🎵 Title: {selected.get('title')} ({selected.get('duration')}s)")

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }

        source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_options)

        if return_source:
            return source
        else:
            voice_client.play(source)