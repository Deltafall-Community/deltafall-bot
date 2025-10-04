import discord
from discord.ext import commands
import os
import logging
import asyncio
import sqlite3
import sys
import json
import time

# dbs

import sqlitecloud
import plyvel

from libs.namuscheduler.scheduler import Scheduler
from libs.namuphishingdetection.phishingdetector import PhishingDetector

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

default_config_content = """{
    "token": "",
    "prefix": "!",
    "sqlitecloud-quote": "",
    "sqlitecloud-club": ""
}
"""

# get bot config from file 
# this will be accessible through out the whole bot
try:
    config = json.load(open("config.json", "r"))
except FileNotFoundError:
    file = open("config.json", "x")
    file.write(default_config_content)
    file.close()
    logger.info("A new config file has been created (config.json), Please include your bot token in the config file.")
    sys.exit()

if not config.get("token"):
    logger.error("Invaild token.")
    sys.exit()

class Bot(commands.Bot):
    def __init__(self):
        self.config = config
        self.cogsfolder = "cogs"

        self.token = self.config["token"]
        self.quote_db = self.connect_quote_db()
        self.scheduler = None
        self.phishing_detector = None
        self.valentine_lvl_db = plyvel.DB('valentine', create_if_missing=True)

        self.logger = logger
        super().__init__(command_prefix=prefix if (prefix := self.config.get("prefix")) else "!", intents=discord.Intents.all())

    async def get_phishing_detector(self):
        self.phishing_detector = await PhishingDetector(logger)

    async def get_scheduler(self):
        self.scheduler = await Scheduler(sqlitecloud_schedule, True) if (sqlitecloud_schedule := self.config.get("sqlitecloud-schedule")) else await Scheduler("schedule.db")

    def connect_quote_db(self):
        try:
            if self.config.get("sqlitecloud-quote"):
                return sqlitecloud.connect(self.config["sqlitecloud-quote"])
            else:
                return sqlite3.connect("quotes.db", check_same_thread=False)
        except Exception as e:
            logger.error(f"Failed to connect to Quote Database.. (Reason: {e})") 

    async def load_extensions(self):
        for file in os.listdir(self.cogsfolder):
            if file.endswith(".py"):
                cog_name = f"{self.cogsfolder}.{file[:-3]}"
                await self._load_cog(cog_name)

        logger.info("All cogs loaded successfully.")

    async def _load_cog(self, cog_name):
        start = time.time_ns()
        try:
            await self.load_extension(cog_name)
            logger.info(f"Loaded {cog_name} ({(1e-9 * (time.time_ns() - start)):.4f}s)")
        except Exception as e:
            logger.error(f"Failed to load {cog_name}: {e}")

bot = Bot()

@bot.command()
async def reload(ctx, cog):
    if await bot.is_owner(ctx.author):
        try:
            await bot.reload_extension(f"{bot.cogsfolder}.{cog}")
            await ctx.send(f"Reloaded {cog}")
            logger.info(f"{cog} cog reloaded by {ctx.author.name}.")
        except Exception as e:
            await ctx.send(f"Failed to reload {cog}")
            logger.error(f"Failed to reload cog {cog}: {e}")

@bot.command()
async def sync(ctx):
    if await bot.is_owner(ctx.author):
        try:
            synced = await bot.tree.sync()
            await ctx.send(f"Synced {len(synced)} command(s).")
            logger.info(f"Commands synced by {ctx.author.name}.")
        except Exception as e:
            await ctx.send("Failed to sync commands.")
            logger.error(f"Failed to sync commands: {e}")

@bot.listen()
async def on_ready():
    logger.info(f"Logged in as {bot.user}")

async def main():
    async with bot:
        await bot.get_scheduler()
        await bot.get_phishing_detector()
        await bot.load_extensions()
        await bot.start(bot.token)

asyncio.run(main())
