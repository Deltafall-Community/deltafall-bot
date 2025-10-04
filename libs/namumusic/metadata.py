from dataclasses import dataclass
from datetime import datetime

@dataclass
class Metadata:
    url: str = None
    stream_url: str = None
    title: str = None
    author: str = None
    author_url: str = None
    thumbnail_url: str = None
    created_on: datetime = None
    length: float = None