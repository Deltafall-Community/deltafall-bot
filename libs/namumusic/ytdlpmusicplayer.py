from typing import Callable
from typing import Optional
from typing import List
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import asyncio
import math

import audioop
import time
import yt_dlp
from urllib.parse import urlparse 
from libs.namumusic.mixer import Mixer
from libs.namumusic.ytdlpaudio import PlaybackState, YTDLPAudio, Status
from libs.namumusic.metadatagetter import get_metadata
import discord

class YTDLPMusicPlayer():
    def __init__(self,
                vc: discord.VoiceClient,
                on_start: Callable[[YTDLPAudio, 'YTDLPMusicPlayer'], None] = None,
                on_finished: Callable[[YTDLPAudio, 'YTDLPMusicPlayer'], None] = None,
                volume: float = 1.0):
        self.extras = {}

        self.volume = volume

        self.on_start = on_start
        self.on_finished = on_finished

        self.crossfade = True
        self.crossfade_length = 2.0
        self.crossfade_strength = 3.0

        self.mixer = Mixer()
        self.vc = vc
        self.queue: List[YTDLPAudio] = [] # maybe use deque?
        self.current_song: YTDLPAudio = None

    async def finished(self, audio) -> None:
        if self.on_finished: await self.on_finished(audio, self)

    def self_clean_up(self):
        for song in self.queue: song.clean_up()

    def clean_up(self, audio) -> None:
        try: self.queue.remove(audio)
        except Exception as e: print(f"Player {id(self)} Exception While Removing From Queue: {e}")
        if not self.queue: self.vc.stop()

    async def loaded(self, audio: YTDLPAudio) -> None:
        if self.current_song and self.current_song.playback_state == PlaybackState.FINISHED: await self.play(audio)

    async def start(self, audio: YTDLPAudio) -> None:
        if self.on_start: await self.on_start(audio, self)

    async def failed(self, audio: YTDLPAudio) -> None:
        await audio.start_caching(reset_stream_url=True)
        if audio.status == Status.FAILED:
            if audio == self.current_song: await self.play_next_song()
            else: self.current_song.clean_up()

    def easeInOutSine(self, x: float) -> float:
        return (-(math.cos(math.pi * x) - 1) / 2)**self.crossfade_strength

    def on_audio_read(self, audio: YTDLPAudio, packet: bytes) -> bytes:
        # normalize the audio
        scale_factor = 6000 / (audio.total_rms / len(audio.packets))
        packet = audioop.mul(packet, 2, scale_factor)
        
        # this entire thing manages the playbackstate of the audio
        if audio.metadata.length and self.crossfade:
            current_time = audio.get_position()
            time_left = audio.metadata.length - current_time
            if time_left <= self.crossfade_length:
                if len(self.mixer.get_channel("music")) < 2 and not audio.playback_state == PlaybackState.TRANSITIONING:
                    audio.playback_state = PlaybackState.TRANSITIONING
                    audio.finished(wait=False)
                if time_left <= 0: packet = audioop.mul(packet, 2, 0)
                else: packet = audioop.mul(packet, 2, self.easeInOutSine(time_left / self.crossfade_length) )
            
            elif current_time <= self.crossfade_length:
                packet = audioop.mul(packet, 2, self.easeInOutSine(current_time / self.crossfade_length) )
                audio.playback_state = PlaybackState.TRANSITIONING
            
            else: audio.playback_state = PlaybackState.PLAYING
        else: audio.playback_state = PlaybackState.PLAYING

        # set overall volume
        packet = audioop.mul(packet, 2, self.volume)

        return packet

    def get_next_song(self) -> YTDLPAudio:
        if len(self.queue) > 1: return self.queue[1]
        return None

    def set_volume(self, volume: float) -> None:
        self.volume = volume

    def set_loop(self, bool: bool) -> None:
        for ac in self.queue: ac.set_loop(bool)

    def seek(self, pos: int) -> None:
        self.current_song.seek(pos)

    async def play(self, audio_source: Optional[YTDLPAudio] = None) -> YTDLPAudio:
        if not audio_source:
            if self.current_song: self.current_song = self.get_next_song()
            else: self.current_song=self.queue[0]
        else: self.current_song = audio_source
        if not self.current_song: return None

        loop = asyncio.get_running_loop()
        for audio in self.queue[1:][:3]:
            if audio.status == Status.IDLE: loop.create_task(audio.start_caching())
        if self.current_song == Status.IDLE: await self.current_song.start_caching()

        self.mixer.add_audio_source("music", self.current_song)
        
        if not self.vc.is_playing(): self.vc.play(self.mixer, fec=False, signal_type="music", bitrate=512)
        return self.current_song

    async def add_song(self, url: str, streamable: bool = True) -> YTDLPAudio:
        loop = asyncio.get_running_loop()
        audios = []
        if streamable:
            entries = await loop.run_in_executor(None, get_metadata, url)
            for entry in entries: audios.append(await YTDLPAudio(entry, streamable=streamable, cache_on_init=len(self.queue)+len(audios)<=1, on_start=self.start, on_finished=self.finished, on_loading_finished=self.loaded, on_read=self.on_audio_read, on_clean_up=self.clean_up, on_failed=self.failed))
        else: audios = [await YTDLPAudio(url, streamable=streamable, cache_on_init=len(self.queue)+len(audios)<=1, on_start=self.start, on_finished=self.finished, on_loading_finished=self.loaded, on_read=self.on_audio_read, on_clean_up=self.clean_up, on_failed=self.failed)]
        self.queue += audios
        if (len(self.queue) > 1 and self.queue[1].playback_state == PlaybackState.NOT_PLAYING and self.queue[0].playback_state == PlaybackState.TRANSITIONING):
            self.current_song.finished(wait=False)
        return audios

    async def play_next_song(self, force=True) -> YTDLPAudio:
        next_song = self.get_next_song()
        if not next_song: return None
        if force and self.current_song.playback_state != PlaybackState.FINISHED:
            try:
                self.current_song.clean_up()
                self.mixer.remove_audio_source("music", self.current_song)
            except Exception as e: print(f"Player {id(self)} Exception While Removing From Mixer & Queue: {e}")
        return await self.play(next_song)