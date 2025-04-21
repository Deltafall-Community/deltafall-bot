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

from namumusic.metadata import Metadata

class Status(Enum):
    IDLE = 0
    LOADING = 1
    CACHING = 2
    FINISHED = 3
    FAILED = 4

class PlaybackState(Enum):
    NOT_PLAYING = 1
    PLAYING = 2
    TRANSITIONING = 3
    FINISHED = 4

# needs to be asynchronous since yt-dlp blocks the main thread.
@asyncinit
class YTDLPAudio(discord.AudioSource):
    async def __init__(self,
                       url: str|Metadata,
                       streamable: bool = True,
                       cache_on_init: bool = True,
                       on_start: Callable[['YTDLPAudio'], Awaitable[Any]] = None,
                       on_finished: Callable[['YTDLPAudio'], Awaitable[Any]] = None,
                       on_loading_finished: Callable[['YTDLPAudio'], Awaitable[Any]] = None,
                       on_failed: Callable[['YTDLPAudio'], Awaitable[Any]] = None,
                       on_read: Callable[['YTDLPAudio', bytes], bytes] = None,
                       on_clean_up: Callable[['YTDLPAudio'], None] = None):
        self.extras = {}

        self.playback_state = PlaybackState.NOT_PLAYING
        self.loop = False
        self.streamable = streamable
        
        self.on_clean_up = on_clean_up
        self.on_start = on_start
        self.on_finished = on_finished
        self.on_loading_finished = on_loading_finished
        self.on_failed = on_failed
        self.on_read = on_read
        self.status = Status.IDLE

        self.executor = ThreadPoolExecutor()
        self.read_ffmpeg_future = None
        self.event_loop = asyncio.get_running_loop()
        if type(url) == Metadata: self.metadata = url
        else:
            self.metadata = Metadata()
            if streamable: self.metadata.stream_url = await self.event_loop.run_in_executor(None, self.get_source_url, url)
            else: self.metadata.stream_url = url

        if not streamable:
            self.metadata.title = urlparse(url).path.split("/")[-1]
            self.metadata.author = "Discord Attachment"

        self.packet_index = 0
        self.packets = []
        self.total_rms = 0

        if cache_on_init: await self.start_caching()
        
    async def start_caching(self, reset_stream_url: bool = False) -> None:
        self.status = Status.LOADING
        samples_per_second = 48000
        channels = 2
        
        if reset_stream_url: self.metadata.stream_url = None
        if not self.metadata.stream_url: self.metadata.stream_url = await self.event_loop.run_in_executor(None, self.get_source_url, self.metadata.url) 
        
        if self.streamable:
            self.ffmpeg_process = (
                ffmpeg
                .input(self.metadata.stream_url)
                .output('pipe:', format="s16le", ar=str(samples_per_second), ac=channels, loglevel="fatal")
                .run_async(pipe_stdout=True, pipe_stderr=True, quiet=True)
            )
        else:
            self.ffmpeg_process = (
                ffmpeg
                .input('pipe:')
                .output('pipe:', format="s16le", ar=str(samples_per_second), ac=channels, v=0)
                .run_async(pipe_stdin=True, pipe_stderr=True, pipe_stdout=True, quiet=True)
            )

        self.lock = threading.Lock()
        if not self.streamable: self.event_loop.create_task(self.input_ffmpeg())
        self.read_ffmpeg_future = self.event_loop.run_in_executor(self.executor, self.read_ffmpeg)
        # wait for the data the reach 1 second of audio (else the read function will end immediately)
        while len(self.packets) < 50:
            if self.status == Status.FAILED: break
            await asyncio.sleep(1.0)
        if self.status != Status.FAILED and self.on_loading_finished:
            await self.on_loading_finished(self)
            self.status = Status.CACHING

    def start(self, wait: bool = True) -> None:
        if self.start:
            # since this function gets run by discord.py on the different thread
            # we have to use `run_coroutine_threadsafe`
            future=asyncio.run_coroutine_threadsafe(self.on_start(self), self.event_loop)
            if wait:
                try: future.result()
                except Exception: traceback.print_exc()
    def finished(self, wait: bool = True) -> None:
        if self.on_finished:
            # since this function gets run by discord.py on the different thread
            # we have to use `run_coroutine_threadsafe`
            future=asyncio.run_coroutine_threadsafe(self.on_finished(self), self.event_loop)
            if wait:
                try: future.result()
                except Exception: traceback.print_exc()
    
    def clean_up(self):
        self.ffmpeg_process.terminate()
        if self.read_ffmpeg_future: self.read_ffmpeg_future.cancel()
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.packets.clear()

        if self.on_clean_up: self.on_clean_up(self)

    def failed(self) -> None:
        if self.on_failed:
            future=asyncio.run_coroutine_threadsafe(self.on_failed(self), self.event_loop)
            try: future.result()
            except Exception: traceback.print_exc()

    def read_event(self, packet: bytes) -> Optional[bytes]:
        if self.on_read: return self.on_read(self, packet)

    async def input_ffmpeg(self) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.metadata.stream_url) as response:
                async for byte in response.content:
                    try: self.ffmpeg_process.stdin.write(byte)
                    except: break
        self.ffmpeg_process.stdin.close()
    def read_ffmpeg(self) -> None:
        end_silence=None
        while True:
            pcm = self.ffmpeg_process.stdout.read(3840)
            if not pcm: break
            if len(pcm) < 3840:pcm += b"\x00" * (3840 - len(pcm))
            with self.lock:
                # discord only accepts mono audio so doing this actually saves some memory
                pcm = audioop.tomono(pcm, 2, 0.5, 0.5) 
                rms = audioop.rms(pcm, 2)
                self.packets.append(pcm)
                if rms < 500: end_silence=len(self.packets)
                else: end_silence=None
                self.total_rms += rms
        if self.packets:
            if end_silence: self.packets=self.packets[:end_silence]
            self.metadata.length = len(self.packets)*0.02
            self.status = Status.FINISHED
        else:
            self.failed()
            self.status = Status.FAILED

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
        self.metadata.length=ytdlp_dict.get("duration")

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
        if not self.status in (Status.CACHING, Status.FINISHED):
            self.playback_state = PlaybackState.NOT_PLAYING
            return

        self.packet_index += 1
        if self.packet_index > len(self.packets):
            if self.playback_state == PlaybackState.FINISHED: return b''
            if not self.loop:
                if not self.playback_state == PlaybackState.TRANSITIONING:
                    self.playback_state = PlaybackState.FINISHED
                    self.finished()
                self.playback_state = PlaybackState.FINISHED
                self.clean_up()
                return b''
            self.packet_index = 0

        packet = audioop.tostereo(self.packets[self.packet_index-1], 2, 1.0, 1.0)
        # discord.py for some reason does not like mono audio so we have to convert it back to stereo

        # leave it to the user to motifiy the packet
        # e.g. custom effects
        try:
            motified_packet = self.read_event(packet)
            if motified_packet: packet = motified_packet
        except Exception: traceback.print_exc()

        # this gets sent here because the `PlaybackState` doesnt get applied until the player sets it 
        if self.packet_index == 1: self.start(False)

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