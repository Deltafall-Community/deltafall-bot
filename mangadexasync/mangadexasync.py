from MangaDexPy import MangaDex, Manga, Chapter, Group, Author, Cover
from MangaDexPy import INCLUDE_ALL, APIError, NoResultsError, NetworkChapter
from typing import Type, List, Union, Dict, Optional
from dataclasses import dataclass
from mangadexasync.util import convert_requests_to_aiohttp, aiohttp_to_requests_response
import MangaDexPy
import random
import asyncio
import json

async def retrieve_pages(cli: MangaDex, url: str, obj: Type[Union[Manga, Chapter, Group, Author, Cover]],
                    limit: int = 0, call_limit: int = 500,
                    params: dict = None) -> List[Union[Manga, Chapter, Group, Author, Cover]]:
    params = params or {}
    data = []
    offset = 0
    resp = None
    remaining = True
    if "limit" in params:
        params.pop("limit")
    if "offset" in params:
        params.pop("offset")
    while remaining:
        p = {"limit": limit if limit <= call_limit and limit != 0 else call_limit, "offset": offset}
        p = {**p, **params}
        async with convert_requests_to_aiohttp(cli.session) as session:
            req = await session.get(url, params=p)
        if req.status == 200:
            resp = await req.json()
            data += [x for x in resp["data"]]
        elif req.status == 204:
            pass
        else:
            raise APIError(await aiohttp_to_requests_response(req))
        if limit and len(data) >= limit:
            break
        if resp is not None:
            remaining = resp["total"] > offset + call_limit
            offset += call_limit
        else:
            remaining = False
        if remaining:
            asyncio.sleep(cli.rate_limit)
    if not data:
        raise NoResultsError()
    return [obj(x, cli) for x in data]

async def read_chapter(cli: MangaDex, ch: Chapter, force_443: bool = False) -> NetworkChapter:
    """Pulls a chapter from the MD@H Network."""
    data = {"forcePort443": json.dumps(force_443)}
    async with convert_requests_to_aiohttp(cli.session) as session:
        req = await session.get(f"{cli.api}/at-home/server/{ch.id}", params=data)
    if req.status == 200:
        resp = await req.json()
        return NetworkChapter(resp, ch, cli)
    else:
        raise APIError(await aiohttp_to_requests_response(req))

@dataclass
class Page:
    url: str
    page: int
    manga: Manga
    chapter: Chapter

class MangaDexAsync():
    def __init__(self):
        self.cli = MangaDexPy.MangaDex()
        self.tags_cache: Dict[str, str] = {}

    async def get_tags(self) -> Dict[str, str]:
        async with convert_requests_to_aiohttp(self.cli.session) as session:
            req = await session.get(f"{self.cli.api}/manga/tag")
        if req.status == 200:
            resp = await req.json()
            tags = {}
            for tag in resp["data"]:
                tags[tag.get("attributes").get("name").get("en")] = tag.get("id")
            return tags
        raise NoResultsError()

    async def refresh_tags_cache(self):
        self.tags_cache = await self.get_tags()

    def get_tag_id_from_str(self, tag: str) -> Optional[str]:
        return self.tags_cache.get(tag)

    async def get_random_manga(self, filters: dict = {}, includes: List[str] = [], call_limit: int = 100) -> Manga:
        includes = INCLUDE_ALL if not includes else includes
        if includes:
            filters |= {"includes[]": includes}
        called = 0
        while called < call_limit:
            called += 1
            async with convert_requests_to_aiohttp(self.cli.session) as session:
                req = await session.get(f"{self.cli.api}/manga/random", params=filters)
            if req.status == 200:
                resp = await req.json()
                return Manga(resp["data"], self.cli)
        raise NoResultsError()

    async def get_random_page(self, light: bool, filters: dict = {}, call_limit: int = 100) -> Page:
        called = 0
        while called < call_limit:
            called += 1
            try:
                manga = await self.get_random_manga(filters)
                chapters = await retrieve_pages(self.cli, f"{self.cli.api}/manga/{manga.id}/feed", Chapter, limit=50, call_limit=100)
            except MangaDexPy.NoResultsError:
                continue

            eng_chapters = [c for c in chapters if c.language == "en"]
            if eng_chapters:
                chapter: Chapter = random.sample(eng_chapters, 1)[0]
            else:
                chapter: Chapter = random.sample(chapters, 1)[0]
            net = await read_chapter(self.cli, chapter)
            pages = net.pages_redux if light else net.pages
            if len(pages) < 1:
                continue
            page_idx = random.randint(0, len(pages)-1)
            
            return Page(pages[page_idx], page_idx+1, manga, chapter)
        raise NoResultsError()