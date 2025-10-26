import yt_dlp
from typing import List
from urllib.parse import urlparse
from libs.namumusic.metadata import Metadata
from datetime import datetime
from sclib import SoundcloudAPI, Track, Playlist

def parse_from_soundcloud_api(track: Track):
    metadata = Metadata()

    metadata.thumbnail_url=track.artwork_url
    metadata.author=track.artist
    metadata.title=track.title
    metadata.url=track.permalink_url
    metadata.created_on=track.created_at
    if metadata.created_on:
        metadata.created_on = datetime.fromisoformat(metadata.created_on)
    metadata.length=track.duration / 1000

    return metadata

def parse_from_ytdlp_dict(ytdlp_dict: dict, add_stream_url: bool = True):
    metadata = Metadata()

    metadata.thumbnail_url=ytdlp_dict.get("thumbnail")
    metadata.author=ytdlp_dict.get("uploader")
    metadata.author_url=ytdlp_dict.get("uploader_url")
    metadata.title=ytdlp_dict.get("title")
    metadata.created_on=ytdlp_dict.get("timestamp")
    if metadata.created_on:
        metadata.created_on = datetime.fromtimestamp(metadata.created_on)
    metadata.length=ytdlp_dict.get("duration")
    
    # getting url in the "pure" ytdlp dict results in the stream url being fetched
    # so we check the webpage_url first if it exists if not then use url
    # this is because the items in playlist uses url as the attribute
    metadata.url = ytdlp_dict.get("webpage_url") 
    if not metadata.url:
        metadata.url=ytdlp_dict.get("url")
    elif add_stream_url:
        metadata.stream_url=ytdlp_dict.get("url")

    return metadata

def get_metadata(search: str) -> List[Metadata]:
    raw_songs=[]
    songs=[]
    url=None

    soundcloud_api = SoundcloudAPI()
    ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'extract_flat': True} 
    ydl = yt_dlp.YoutubeDL(ydl_opts)
    
    if urlparse(search).netloc != '':
        url = search
    else:
        raw_songs = [ydl.extract_info(f"ytsearch1:{search}", download=False).get("entries")[0]]
    
    extractor=""
    if url:
        extractors = yt_dlp.extractor.gen_extractors()
        for e in extractors:
            if e.suitable(url) and e.IE_NAME != 'generic':
                extractor = (e.IE_NAME+" ")[:e.IE_NAME.find(":")]
        extractor = extractor.lower()
    
    match extractor:
        # normal
        case "youtube" | "bandcamp":
            if not raw_songs:
                yt_dlp_dict = ydl.extract_info(url, download=False)
                entries = yt_dlp_dict.get("entries")
                if entries:
                    raw_songs += entries
                else:
                    raw_songs += [yt_dlp_dict]
        # special case
        case "soundcloud":
            soundcloud_music = soundcloud_api.resolve(url)
            music_type = type(soundcloud_music)
            if music_type is Playlist:
                for track in soundcloud_music.tracks:
                    songs.append(parse_from_soundcloud_api(track))
            elif music_type is Track:
                songs.append(parse_from_soundcloud_api(soundcloud_music))

    for song in raw_songs:
        songs.append(parse_from_ytdlp_dict(song, extractor not in ("bandcamp",)))
    return songs
