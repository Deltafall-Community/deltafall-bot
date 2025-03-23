import discord
from discord.ext import commands
from discord import app_commands
from discord import Embed
from typing import Optional

from namumusic.ytdlpmusicplayer import YTDLPMusicPlayer
from namumusic.ytdlpaudio import PlaybackState
from namumusic.ytdlpaudio import Metadata
from namumusic.ytdlpaudio import YTDLPAudio
from time import strftime
from time import gmtime

import aiohttp
from io import BytesIO
from PIL import Image, ImageStat

class music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guilds = {}

    def get_guild_player(self, voice_client: discord.VoiceClient):
        player = self.guilds.get(voice_client.guild.id)
        if player: return player
        else: player = YTDLPMusicPlayer(voice_client, on_finished=self.on_track_end)
        self.guilds[voice_client.guild.id] = player
        return player

    def delete_guild_player(self, voice_client: discord.VoiceClient):
        self.guilds.pop(voice_client.guild.id)

    group = app_commands.Group(name="music", description="music stuff")
    
    async def on_track_end(self, prev_audio: YTDLPAudio, player: YTDLPMusicPlayer):
        audio = player.get_next_song()
        if audio:
            metadata: Metadata = audio.metadata
            match prev_audio.playback_state:
                case PlaybackState.TRANSITIONING:
                    audio = await player.play_next_song(force=False)
                    embed = Embed(title="🎵 playing now", description=f'trasitioning to playing `{metadata.title} - {metadata.author}` now.')
                case PlaybackState.FINISHED:
                    audio = await player.play_next_song(force=True)
                    embed = Embed(title="🎵 playing now", description=f'`{metadata.title} - {metadata.author}` is playing now.')
            await player.extras.get("channel").send(embed=embed)

    @group.command(name="play", description="song name or the link")
    async def music(self, interaction: discord.Interaction, search: str):
        await interaction.response.defer()
        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect()

        vc = interaction.guild.voice_client
        player = self.get_guild_player(vc)
        player.extras["channel"] = interaction.channel
        try: audio = await player.add_song(search)
        except: return await interaction.followup.send(f'It was not possible to find the song: `{search}`') 
        audio.extras["requester"] = interaction.user
        metadata: Metadata = audio.metadata
        embed = Embed(title="🎵 Song added to the queue.", description=f'`{metadata.title} - {metadata.author}` was added to the queue.')
        await interaction.followup.send(embed=embed)
        await player.play()

    @group.command(name="volume", description="adjust the volume (default 100%)")
    async def volume(self, interaction: discord.Interaction, volume: float):
        vc = interaction.guild.voice_client
        player = self.get_guild_player(vc)
        player.set_volume(volume / 100.0)
        embed = Embed(title="Volume", description=f"The volume has been adjusted to {volume}%.")
        await interaction.response.send_message(embed=embed)
        
    @group.command(name="stop", description="stop everything")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        vc.stop()
        self.delete_guild_player(vc)
        await vc.disconnect()
        embed = Embed(title="⏹️ Music stopped", description="The music has been stopped.")
        await interaction.response.send_message(embed=embed)

    @group.command(name="pause", description="pause music")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        vc.pause()
        embed = Embed(title="⏸️ Music paused", description="The music has been paused")
        await interaction.response.send_message(embed=embed)

    @group.command(name="resume", description="resume music")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        vc.resume()
        embed = Embed(title="▶️ Music Resumed", description="The music has been resumed.")
        await interaction.response.send_message(embed=embed)

    @group.command(name="transition", description="adjust the transition of the song")
    async def transition(self, interaction: discord.Interaction, duration: float, strength: Optional[float]):
        vc = interaction.guild.voice_client
        player = self.get_guild_player(vc)
        player.crossfade_length = min(max(2.0, duration), 12.0)
        if strength:
            strength = min(max(0.1, strength), 9.0)
            player.crossfade_strength = strength
        embed = Embed(title="Transition Set", description=f"Duration: {duration}\nStrength: {strength}")
        await interaction.response.send_message(embed=embed)

    @group.command(name="seek", description="seeks the song position")
    async def seek(self, interaction: discord.Interaction, seconds: float):
        vc = interaction.guild.voice_client
        player = self.get_guild_player(vc)
        player.seek(seconds)
        embed = Embed(title="Seek", description=f"Seeked to {player.current_song.get_position()}")
        await interaction.response.send_message(embed=embed)

    @group.command(name="skip", description="skip song")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        player = self.get_guild_player(vc)
        audio = await player.play_next_song()

        if audio:
            metadata: Metadata = audio.metadata
            embed = Embed(title="⏭️ Song skipped", description=f'Playing the next song in the queue: `{metadata.title}`.')
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("There are no songs in the queue to skip")

    @group.command(name="queue", description="list queue")
    async def queue(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        player = self.get_guild_player(vc)
        queue = player.queue
        if not queue:
            embed = Embed(title="📜 Playlist", description="The queue is empty.")
            await interaction.response.send_message(embed=embed)
        else:
            queue_list = "\n".join([f"- {track.metadata.title}" for track in queue])
            embed = Embed(title="📜 Playlist", description=queue_list)
            await interaction.response.send_message(embed=embed)

    @group.command(name="current_playing", description="what is currently playing")
    async def current_playing(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        player = self.get_guild_player(vc)
        audio = player.current_song
        metadata: Metadata = audio.metadata

        progressbar_length = 30
        progressbar = ""
        currentprogress = int(audio.get_position() / metadata.length * progressbar_length)

        for i in range(progressbar_length):
            if i == currentprogress:
                if vc.is_paused():
                    progressbar += "⏸"
                    continue
                progressbar += "▶"
                continue
            if i > currentprogress:
                progressbar += "⋯"
            else:
                progressbar += "-"

        async with aiohttp.ClientSession() as session:
            async with session.get(metadata.thumbnail_url) as response:
                thumbnail = await response.read()
        artwork = Image.open(BytesIO(thumbnail))
        median = ImageStat.Stat(artwork).median
        embed = Embed(color=discord.Color.from_rgb(median[0], median[1], median[2]), description=f'## [{metadata.title}]({metadata.url})\n-# by [{metadata.author}]({metadata.author_url})\n**{progressbar}**\n- {strftime("%H:%M:%S", gmtime(audio.get_position()))} - {strftime("%H:%M:%S", gmtime(metadata.length))}')
        embed.add_field(name="Requested by:", value=f'`{audio.extras.get("requester").name}`', inline=True)
        next_song = player.get_next_song()
        if next_song:
            embed.add_field(name="Next up:", value=f"`{next_song.metadata.title} - {next_song.metadata.author}`" , inline=True)
        embed.set_thumbnail(url=metadata.thumbnail_url)
        embed.set_image(url=metadata.thumbnail_url)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(music(bot))