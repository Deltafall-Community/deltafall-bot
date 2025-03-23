from typing import Callable
from typing import Optional
from typing import List
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import asyncio
import math

import audioop
import time
from namumusic.mixer import Mixer
from namumusic.ytdlpaudio import PlaybackState
from namumusic.ytdlpaudio import YTDLPAudio
import discord

class YTDLPMusicPlayer():
    def __init__(self,
                vc: discord.VoiceClient,
                on_start: Callable[['YTDLPMusicPlayer'], None] = None,
                on_finished: Callable[[YTDLPAudio, 'YTDLPMusicPlayer'], None] = None,
                volume: float = 1.0):
        self.extras = {}

        self.volume = volume

        self.on_start = on_start
        self.on_finished = on_finished

        self.crossfade = True
        self.crossfade_length = 6.0
        self.crossfade_strength = 3.0

        self.mixer = Mixer()
        self.vc = vc
        self.queue: List[YTDLPAudio] = [] # maybe use deque?
        self.current_song: YTDLPAudio = None

    async def finished(self, audio) -> None:
        if self.on_finished: await self.on_finished(audio, self)

    def clean_up(self, audio) -> None:
        self.queue.remove(audio)
        if not self.queue: self.vc.stop()

    async def loaded(self, audio) -> None:
        if self.current_song and self.current_song.playback_state == PlaybackState.FINISHED: await self.play(audio)

    def easeInOutSine(self, x: float) -> float:
        return (-(math.cos(math.pi * x) - 1) / 2)**self.crossfade_strength

    def on_audio_read(self, audio: YTDLPAudio, packet: bytes) -> bytes:
        # normalize the audio
        scale_factor = 6000 / (audio.total_rms / len(audio.packets))
        packet = audioop.mul(packet, 2, scale_factor)
        
        if self.crossfade:
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

        self.mixer.add_audio_source("music", self.current_song)
        
        if not self.vc.is_playing(): self.vc.play(self.mixer, fec=False, signal_type="music", bitrate=512)
        if self.on_start: await self.on_start(self)
        return self.current_song

    async def add_song(self, url: str) -> YTDLPAudio:
        audio = await YTDLPAudio(url, on_finished=self.finished, on_loading_finished=self.loaded, on_read=self.on_audio_read, on_clean_up=self.clean_up)
        self.queue.append(audio)
        if (len(self.queue) > 1 and self.queue[1].playback_state == PlaybackState.NOT_PLAYING and self.queue[0].playback_state == PlaybackState.TRANSITIONING):
            self.current_song.finished(wait=False)
        return audio

    async def play_next_song(self, force=True) -> YTDLPAudio:
        next_song = self.get_next_song()
        if not next_song: return None
        if force:
            self.mixer.remove_audio_source("music", self.current_song)
            self.queue.remove(self.current_song)
        return await self.play(next_song)