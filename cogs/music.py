from typing import Optional
from time import strftime
from time import gmtime

import discord
from discord.ext import commands
from discord import app_commands
from discord.ext.paginators.button_paginator import ButtonPaginator, PaginatorButton

from libs.namumusic.ytdlpmusicplayer import YTDLPMusicPlayer
from libs.namumusic.ytdlpaudio import PlaybackState, Metadata, YTDLPAudio

import aiohttp
from io import BytesIO
from PIL import Image, ImageStat

class music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guilds = {}

    def get_guild_player(self, voice_client: discord.VoiceClient):
        player = self.guilds.get(voice_client.guild.id)
        if player:
            return player
        else:
            player = YTDLPMusicPlayer(voice_client, on_finished=self.on_track_end, on_start=self.on_track_start)
        self.guilds[voice_client.guild.id] = player
        return player

    def delete_guild_player(self, voice_client: discord.VoiceClient):
        player = self.guilds.get(voice_client.guild.id)
        if player:
            player.self_clean_up()
            self.guilds.pop(voice_client.guild.id)

    group = app_commands.Group(name="music", description="music stuff")
    
    async def on_track_start(self, audio: YTDLPAudio, player: YTDLPMusicPlayer):
        metadata: Metadata = audio.metadata
        match audio.playback_state:
            case PlaybackState.TRANSITIONING:
                embed = discord.Embed(description=f'## 🎵 Playing now\nTrasitioning to playing `{metadata.title} - {metadata.author}` now.')
            case PlaybackState.PLAYING:
                embed = discord.Embed(description=f'## 🎵 Playing now\n`{metadata.title} - {metadata.author}` is playing now.')
        await player.extras.get("channel").send(embed=embed)

    async def on_track_end(self, prev_audio: YTDLPAudio, player: YTDLPMusicPlayer):
        audio = player.get_next_song()
        if audio:
            match prev_audio.playback_state:
                case PlaybackState.TRANSITIONING:
                    audio = await player.play_next_song(force=False)
                case PlaybackState.FINISHED:
                    audio = await player.play_next_song()

    @group.command(name="play", description="song name or the link")
    async def music(self, interaction: discord.Interaction, search: Optional[str], file: Optional[discord.Attachment]):
        await interaction.response.defer()
        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect()

        vc = interaction.guild.voice_client
        player = self.get_guild_player(vc)
        player.extras["channel"] = interaction.channel
        if file and file.content_type[:file.content_type.find("/")] == "audio":
            audios = await player.add_song(file.url, streamable=False)
            #except: return await interaction.followup.send(f'It was not possible to play the attachment.')
        elif search:
            audios = await player.add_song(search)
            #except: return await interaction.followup.send(f'It was not possible to find the song: `{search}`') 
        else:
            return await interaction.followup.send("You have to specify an audio source. ")
        for audio in audios:
            audio.extras["requester"] = interaction.user
        metadata: Metadata = audios[0].metadata
        embed = discord.Embed(description=f'## 🎵 Song added to the queue.\n`{metadata.title} - {metadata.author}` was added to the queue.')
        await interaction.followup.send(embed=embed)
        if not vc.is_playing():
            await player.play()

    @group.command(name="volume", description="adjust the volume (default 100%)")
    async def volume(self, interaction: discord.Interaction, volume: float):
        vc = interaction.guild.voice_client
        player = self.get_guild_player(vc)
        player.set_volume(volume / 100.0)
        embed = discord.Embed(description=f"## Volume\n The volume has been adjusted to {volume}%.")
        await interaction.response.send_message(embed=embed)
        
    @group.command(name="stop", description="stop everything")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        vc.stop()
        self.delete_guild_player(vc)
        await vc.disconnect()
        embed = discord.Embed(description="## ⏹️ Music Stopped\nThe music has been stopped.")
        await interaction.response.send_message(embed=embed)

    @group.command(name="pause", description="pause music")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        vc.pause()
        embed = discord.Embed(description="## ⏸️ Music Paused\nThe music has been paused")
        await interaction.response.send_message(embed=embed)

    @group.command(name="resume", description="resume music")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        vc.resume()
        embed = discord.Embed(description="## ▶️ Music Resumed\nThe music has been resumed.")
        await interaction.response.send_message(embed=embed)

    @group.command(name="transition", description="adjust the transition of the song")
    @app_commands.choices(enabled=[
        app_commands.Choice(name="Yes", value=1),
        app_commands.Choice(name="No", value=0)])
    async def transition(self, interaction: discord.Interaction, enabled: app_commands.Choice[int], duration: Optional[float], strength: Optional[float]):
        vc = interaction.guild.voice_client
        player = self.get_guild_player(vc)
        player.crossfade = bool(enabled.value)
        if duration:
            player.crossfade_length = min(max(2.0, duration), 12.0)
        if strength:
            strength = min(max(0.1, strength), 9.0)
            player.crossfade_strength = strength
        embed = discord.Embed(description=f"## Transition Set\nEnabled: {player.crossfade}\nDuration: {player.crossfade_length}\nStrength: {player.crossfade_strength}")
        await interaction.response.send_message(embed=embed)

    @group.command(name="skip", description="skip song")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        player = self.get_guild_player(vc)
        audio = await player.play_next_song()

        if audio:
            metadata: Metadata = audio.metadata
            embed = discord.Embed(description=f'## ⏭️ Song skipped\nPlaying the next song in the queue: `{metadata.title}`.')
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("There are no songs in the queue to skip")

    @group.command(name="queue", description="list queue")
    async def queue(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        player = self.get_guild_player(vc)
        queue = player.queue
        if not queue:
            embed = discord.Embed(description="## 📜 Playlist\nThe queue is empty.")
            await interaction.response.send_message(embed=embed)
        else:
            playlist_embeds = [discord.Embed(description="## 📜 Playlist")]
            current_page=0
            for num, track in zip(range(len(queue)), queue):
                if playlist_embeds[current_page].description.count('\n') > 15:
                    current_page+=1
                if len(playlist_embeds) < current_page+1:
                    playlist_embeds.append(discord.Embed(description="", color=discord.Color.from_rgb(255,255,255)))
                if not num:
                    if vc.is_paused():
                        num = f'- ⏸ {strftime("%H:%M:%S", gmtime(track.get_position()))} - {strftime("%H:%M:%S", gmtime(track.metadata.length))}\n  - '
                    else:
                        num = f'- ▶ {strftime("%H:%M:%S", gmtime(track.get_position()))} - {strftime("%H:%M:%S", gmtime(track.metadata.length))}\n  - '
                else:
                    num=f"{num}. "
                playlist_embeds[current_page].description += f'\n{num}**{track.metadata.title}**\n-# ↳ {track.metadata.author} • Requested by: {track.extras.get("requester").mention}\n'
            custom_buttons = {
                "FIRST": PaginatorButton(label=":First Page", position=0),
                "LEFT": PaginatorButton(label="Back", position=1),
                "PAGE_INDICATOR": PaginatorButton(label="Page N/A / N/A", position=2, disabled=False),
                "RIGHT": PaginatorButton(label="Next", position=3),
                "LAST": PaginatorButton(label="Last Page:", position=4),
                "STOP": None
            }
            paginator = ButtonPaginator(playlist_embeds, author_id=interaction.user.id, buttons=custom_buttons)
            return await paginator.send(interaction)

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

        embed = discord.Embed(description=f'## [{metadata.title}]({metadata.url})\n-# by [{metadata.author}]({metadata.author_url})\n**{progressbar}**\n- {strftime("%H:%M:%S", gmtime(audio.get_position()))} - {strftime("%H:%M:%S", gmtime(metadata.length))}')
        if metadata.thumbnail_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(metadata.thumbnail_url) as response:
                    thumbnail = await response.read()
            artwork = Image.open(BytesIO(thumbnail))
            median = ImageStat.Stat(artwork).median
            embed.color=discord.Color.from_rgb(median[0], median[1], median[2])
            embed.set_image(url=metadata.thumbnail_url)
        embed.add_field(name="Requested by:", value=f'`{audio.extras.get("requester").name}`', inline=True)
        next_song = player.get_next_song()
        if next_song:
            embed.add_field(name="Next up:", value=f"`{next_song.metadata.title} - {next_song.metadata.author}`" , inline=True)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(music(bot))