from typing import Callable
from enum import Enum
from typing import Awaitable
from typing import Any
from dataclasses import dataclass
from asyncinit import asyncinit
from datetime import datetime
import math
import asyncio
from concurrent.futures import ThreadPoolExecutor
import traceback
import threading

import discord
import yt_dlp
from urllib.parse import urlparse
import ffmpeg
import audioop

@dataclass
class Metadata:
    url: str = None
    title: str = None
    author: str = None
    author_url: str = None
    thumbnail_url: str = None
    created_on: datetime = None
    length: float = None

class Status(Enum):
    LOADING = 1
    FINISHED = 2
    FAILED = 3

# needs to be asynchronous since yt-dlp blocks the main thread.
@asyncinit
class YTDLPAudio(discord.AudioSource):
    async def __init__(self,
                       url: str,
                       on_finished: Callable[['YTDLPAudio'], Awaitable[Any]] = None,
                       on_loading_finished: Callable[['YTDLPAudio'], Awaitable[Any]] = None,
                       volume: float = 1.0):
        self.metadata = Metadata()
        self.extras = {}

        self.is_finished = False
        self.loop = False
        self.volume = volume
        
        self.on_finished = on_finished
        self.on_loading_finished = on_loading_finished
        self.status = Status.LOADING

        self.event_loop = asyncio.get_event_loop()
        self.stream_url = await self.event_loop.run_in_executor(None, self.get_source_url, url)

        # start ffmpeg decoding & storing in background
        samples_per_second = 48000
        channels = 2

        try:
            self.ffmpeg_process = (
                ffmpeg
                .input(self.stream_url)
                .output('pipe:', format="s16le", ar=str(samples_per_second), ac=channels)
                .run_async(pipe_stdout=True, pipe_stderr=True, quiet=True)
            )
        except ffmpeg.Error:
            self.status = Status.FAILED
            return

        self.packet_index = 0
        self.packets = []
        self.total_rms = 0

        self.lock = threading.Lock()
        executor = ThreadPoolExecutor()
        await self.event_loop.run_in_executor(executor, self.read_ffmpeg)

        await self.on_loading_finished(self)

    def read_ffmpeg(self) -> None:
        while True:
            pcm = self.ffmpeg_process.stdout.read(3840)
            if not pcm: break
            if len(pcm) < 3840:pcm += b"\x00" * (3840 - len(pcm))
            with self.lock:
                self.packets.append(pcm)
                self.total_rms += audioop.rms(pcm, 2)

    def get_source_url(self, search: str) -> str:
        ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True , 'quiet': True} 
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        
        if urlparse(search).netloc != '': info = ydl.extract_info(search, download=False)
        else: info = ydl.extract_info(f"ytsearch1:{search}", download=False).get("entries")[0]

        self.metadata.thumbnail_url=info.get("thumbnail")
        self.metadata.author=info.get("uploader")
        self.metadata.author_url=info.get("uploader_url")
        self.metadata.title=info.get("title")
        self.metadata.url=info.get("webpage_url")
        created_on=info.get("timestamp")
        if created_on: self.metadata.created_on = datetime.fromtimestamp(created_on)
        self.metadata.length=info.get("duration")

        platform = info.get("extractor")
        if platform: platform = platform.lower()

        match platform:
            case "youtube" | "soundcloud" | "bandcamp":
                lastaudiobitrate = 0
                for f in info['formats']:
                    if f.get('acodec') != 'none':
                        bitrate = f.get('abr')
                        if bitrate and bitrate > lastaudiobitrate:
                            url = f['url']
                            lastaudiobitrate = bitrate
            
        return url

    async def finished(self) -> None:
        if self.on_finished: await self.on_finished(self)
    
    def read(self) -> bytes:
        packets_count = len(self.packets)
        self.packet_index += 1
        if self.packet_index > packets_count:
            if self.is_finished: return b''
            if not self.loop:
                # since this function gets run by discord.py on the different thread
                # we have to use `run_coroutine_threadsafe`   
                future=asyncio.run_coroutine_threadsafe(self.finished(), self.event_loop)
                try: future.result()
                except Exception: traceback.print_exc()
                self.is_finished = True
                return b''
            self.packet_index = 0
        packet = self.packets[self.packet_index-1]
        
        # normalize the audio
        scale_factor = 6500 / (self.total_rms / packets_count)
        packet = audioop.mul(packet, 2, scale_factor)
        
        # set overall volume
        packet = audioop.mul(packet, 2, self.volume)
        
        return packet

    def is_opus(self):
        return False

    def get_position(self) -> float:
        return self.packet_index * 0.02

    def set_volume(self, volume: float) -> None:
        self.volume = volume

    def set_loop(self, bool: bool) -> None:
        self.loop = bool

    def seek(self, position: int):
        while len(self.packets) * 0.02 < position: pass
        self.packet_index = (math.floor(position / 0.02))