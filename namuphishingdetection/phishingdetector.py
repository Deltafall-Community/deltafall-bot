import aiosqlite
import asyncinit
import aiohttp
import asyncio
import json
import urllib.parse
import re

@asyncinit.asyncinit
class PhishingDetector():
    async def __init__(self):
        self.loop = asyncio.get_running_loop()
        self.db = await aiosqlite.connect("phishing.db")
        await self.db.execute(f"CREATE TABLE IF NOT EXISTS phishing(url TEXT UNIQUE)")

    async def check_url(self, url: str):
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.netloc:
            cursor = await self.db.execute("""SELECT * FROM phishing WHERE url = ?""", (parsed_url.netloc,))
            phish_url = await cursor.fetchone()
            if phish_url: return True
        return False

    async def check_string(self, string: str):
        for url in re.findall(r"(https?:\/\/.*)", string):
            if await self.check_url(url): return True

    async def update_db(self, db, url: str):
        await db.execute("""
        INSERT OR IGNORE INTO phishing(url) VALUES(?)
        """, (url,))

    async def update(self):       
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.github.com/repos/romainmarcoux/malicious-domains/git/trees/main?recursive=0') as resp:
                repo = json.loads(await resp.text())
                tree = repo.get("tree")
                sha = repo.get("sha")

        try: open("phishing_sha", "x")
        except: pass
        file = open("phishing_sha", "r")
        old_sha = file.read().strip()
        if old_sha != sha:
            print("PhishingDetector: Updating Database...")
            tasks = []
            
            for file in tree:
                path=file.get("path")
                if path.startswith("full-domains"):
                    async with aiohttp.ClientSession(raise_for_status=True) as session:
                        async with session.get(f"https://raw.githubusercontent.com/romainmarcoux/malicious-domains/refs/heads/main/{path}") as r:
                            async for line in r.content:
                                tasks.append(self.loop.create_task(self.update_db(self.db, line.decode().strip())))
            await asyncio.gather(*tasks)
            await self.db.commit()
            print("PhishingDetector: Up to Date.")
        file = open("phishing_sha", "w")
        file.write(sha)