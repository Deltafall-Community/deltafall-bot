from typing import Callable
from enum import Enum
from typing import Awaitable
from typing import Any
from typing import Optional
from dataclasses import dataclass
from asyncinit import asyncinit
from datetime import datetime
import math
import asyncio
from concurrent.futures import ThreadPoolExecutor
import traceback
import threading
import aiohttp

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
    IDLE = 0
    LOADING = 1
    FINISHED = 2
    FAILED = 3

class PlaybackState(Enum):
    NOT_PLAYING = 1
    PLAYING = 2
    TRANSITIONING = 3
    FINISHED = 4

# needs to be asynchronous since yt-dlp blocks the main thread.
@asyncinit
class YTDLPAudio(discord.AudioSource):
    async def __init__(self,
                       url: str|dict,
                       streamable: bool = True,
                       cache_on_init: bool = True,
                       on_finished: Callable[['YTDLPAudio'], Awaitable[Any]] = None,
                       on_loading_finished: Callable[['YTDLPAudio'], Awaitable[Any]] = None,
                       on_read: Callable[['YTDLPAudio', bytes], bytes] = None,
                       on_clean_up: Callable[['YTDLPAudio'], None] = None):
        self.metadata = Metadata()
        self.extras = {}

        self.playback_state = PlaybackState.NOT_PLAYING
        self.loop = False
        self.streamable = streamable
        
        self.on_clean_up = on_clean_up
        self.on_finished = on_finished
        self.on_loading_finished = on_loading_finished
        self.on_read = on_read
        self.status = Status.IDLE

        self.event_loop = asyncio.get_running_loop()
        if type(url) == dict: self.stream_url = self.parse_from_ytdlp_dict(url)
        else:
            if streamable: self.stream_url = await self.event_loop.run_in_executor(None, self.get_source_url, url)
            else: self.stream_url = url

        if not streamable:
            self.metadata.title = urlparse(url).path.split("/")[-1]
            self.metadata.author = "Discord Attachment"

        self.packet_index = 0
        self.packets = []
        self.total_rms = 0

        if cache_on_init: await self.start_caching()
        
    async def start_caching(self) -> None:
        self.status = Status.LOADING
        samples_per_second = 48000
        channels = 2

        if self.streamable:
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
        else:
            try:
                self.ffmpeg_process = (
                    ffmpeg
                    .input('pipe:')
                    .output('pipe:', format="s16le", ar=str(samples_per_second), ac=channels)
                    .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True, quiet=True)
                )
            except ffmpeg.Error:
                self.status = Status.FAILED
                return

        self.lock = threading.Lock()
        executor = ThreadPoolExecutor()
        if not self.streamable: self.event_loop.create_task(self.input_ffmpeg())
        self.event_loop.run_in_executor(executor, self.read_ffmpeg)
        # wait for the data the reach 1 second of audio (else the read function will end immediately)
        await self.event_loop.run_in_executor(None, self.wait_for_enough_data)
        self.status = Status.FINISHED
        await self.on_loading_finished(self)

    def finished(self, wait: bool = True) -> None:
        if self.on_finished:
            # since this function gets run by discord.py on the different thread
            # we have to use `run_coroutine_threadsafe`
            future=asyncio.run_coroutine_threadsafe(self.on_finished(self), self.event_loop)
            if wait:
                try: future.result()
                except Exception: traceback.print_exc()
    
    def read_event(self, packet: bytes) -> Optional[bytes]:
        if self.on_read: return self.on_read(self, packet)

    def wait_for_enough_data(self) -> None:
        while len(self.packets) < 50: pass

    async def input_ffmpeg(self) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.stream_url) as response:
                async for byte in response.content:
                    self.ffmpeg_process.stdin.write(byte)
    def read_ffmpeg(self) -> None:
        while True:
            pcm = self.ffmpeg_process.stdout.read(3840)
            if not pcm: break
            if len(pcm) < 3840:pcm += b"\x00" * (3840 - len(pcm))
            with self.lock:
                self.packets.append(pcm)
                self.metadata.length = len(self.packets)*0.02
                self.total_rms += audioop.rms(pcm, 2)

    def get_source_url(self, search: str) -> str:
        ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True , 'quiet': True} 
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        
        if urlparse(search).netloc != '': info = ydl.extract_info(search, download=False)
        else: info = ydl.extract_info(f"ytsearch1:{search}", download=False).get("entries")[0]

        return self.parse_from_ytdlp_dict(info)


    def parse_from_ytdlp_dict(self, ytdlp_dict: dict):
        self.metadata.thumbnail_url=ytdlp_dict.get("thumbnail")
        self.metadata.author=ytdlp_dict.get("uploader")
        self.metadata.author_url=ytdlp_dict.get("uploader_url")
        self.metadata.title=ytdlp_dict.get("title")
        self.metadata.url=ytdlp_dict.get("webpage_url")
        created_on=ytdlp_dict.get("timestamp")
        if created_on: self.metadata.created_on = datetime.fromtimestamp(created_on)

        platform = ytdlp_dict.get("extractor")
        if platform: platform = platform.lower()

        match platform:
            case "youtube" | "soundcloud" | "bandcamp":
                lastaudiobitrate = 0
                for f in ytdlp_dict['formats']:
                    if f.get('acodec') != 'none':
                        bitrate = f.get('abr')
                        if bitrate and bitrate > lastaudiobitrate:
                            url = f['url']
                            lastaudiobitrate = bitrate
            
        return url

    def read(self) -> bytes:
        if not self.packet_index: self.playback_state = PlaybackState.NOT_PLAYING # there must be a better way to to this

        self.packet_index += 1
        if self.packet_index > len(self.packets):
            if self.playback_state == PlaybackState.FINISHED: return b''
            if not self.loop:
                if not self.playback_state == PlaybackState.TRANSITIONING:
                    self.playback_state = PlaybackState.FINISHED
                    self.finished()
                self.playback_state = PlaybackState.FINISHED
                if self.on_clean_up: self.on_clean_up(self)
                return b''
            self.packet_index = 0

        packet = self.packets[self.packet_index-1]


        # leave it to the user to motifiy the packet
        # e.g. c\ustom effects   
        try:
            motified_packet = self.read_event(packet)
            if motified_packet: packet = motified_packet
        except Exception: traceback.print_exc()

        return packet

    def is_opus(self):
        return False

    def get_position(self) -> float:
        return self.packet_index * 0.02

    def set_loop(self, bool: bool) -> None:
        self.loop = bool

    def seek(self, position: int):
        while len(self.packets) * 0.02 < position: pass
        self.packet_index = (math.floor(position / 0.02))