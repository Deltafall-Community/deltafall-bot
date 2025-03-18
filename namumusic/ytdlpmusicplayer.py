from typing import Callable
from typing import Awaitable
from typing import Optional

from namumusic.ytdlpaudio import YTDLPAudio
import discord

class YTDLPMusicPlayer():
    def __init__(self,
                vc: discord.VoiceClient,
                on_start: Callable[['YTDLPMusicPlayer'], None] = None,
                on_finished: Callable[['YTDLPMusicPlayer'], None] = None):
        self.extras = {}

        self.on_start = on_start
        self.on_finished = on_finished

        self.vc = vc
        self.queue = [] # maybe use deque?
        self.current_song: YTDLPAudio = None
    
    async def finished(self, audio) -> None:
        if self.on_finished: await self.on_finished(self)

    async def loaded(self, audio) -> None:
        if self.current_song and self.current_song.is_finished: await self.play(audio)

    async def set_loop(self, bool: bool) -> None:
        for ac in self.queue: ac.set_loop(bool)

    async def seek(self, pos: int) -> None:
        self.current_song.seek(pos)

    async def set_volume(self, vol: float) -> None:
        for ac in self.queue: ac.set_volume(vol)

    async def play(self, audio_source: Optional[YTDLPAudio] = None) -> YTDLPAudio:
        self.vc.stop()
        if not audio_source:
            if self.current_song and self.current_song.is_finished:
                self.queue.remove(self.current_song)
                self.current_song=await self.get_next_song()
            else: self.current_song=self.queue[0]
        else:
            self.queue.remove(self.current_song)
            self.current_song=audio_source

        if not self.current_song: return None
        self.vc.play(self.current_song, fec=False, signal_type="music", bitrate=512)
        if self.on_start: await self.on_start(self)

        return self.current_song

    async def get_next_song(self) -> YTDLPAudio:
        if len(self.queue) > 1: return self.queue[1]
        return None

    async def add_song(self, url: str) -> YTDLPAudio:
        audio = await YTDLPAudio(url, on_finished=self.finished, on_loading_finished=self.loaded)
        self.queue.append(audio)
        return audio

    async def play_next_song(self) -> YTDLPAudio:
        next_song = await self.get_next_song()
        if not next_song: return None
        return await self.play(next_song)