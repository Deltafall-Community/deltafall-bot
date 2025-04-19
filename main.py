import discord
from discord.ext import commands
import os
import logging
import asyncio
import sqlite3
import sys
import json

# dbs

import sqlitecloud
import plyvel
from namuschedule.schedule import Schedule

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        command_prefix = '!'
        super().__init__(command_prefix=command_prefix, intents=intents)

        self.cogsfolder = "cogs"

        # Get bot config from file 
        # this will be accessible through out the whole bot
        with open("config.json", "r") as file: self.config = json.load(file)

        self.token = self.config["token"]
        self.quote_db = self.connect_quote_db()
        self.club_db = self.connect_club_db()
        self.scheduler = None
        self.valentine_lvl_db = plyvel.DB('valentine', create_if_missing=True)

    async def get_scheduler(self):
        if self.config.get("sqlitecloud-schedule"): self.scheduler = await Schedule(self.config["sqlitecloud-schedule"], True)
        else: self.scheduler = await Schedule("schedule.db")

    def connect_quote_db(self):
        try:
            if self.config.get("sqlitecloud-quote"): return sqlitecloud.connect(self.config["sqlitecloud-quote"])
            else: return sqlite3.connect("quotes.db", check_same_thread=False)
        except Exception as e: print(f"Failed to connect to Quote Database.. (Reason: {e})") 

    def connect_club_db(self):
        try:
            if self.config.get("sqlitecloud-club"): return sqlitecloud.connect(self.config["sqlitecloud-club"])
            else: return sqlite3.connect("clubs.db", check_same_thread=False)
        except Exception as e: print(f"Failed to connect to Club Database.. (Reason: {e})") 

    async def load_extensions(self):
        for file in os.listdir(self.cogsfolder):
            if file.endswith(".py"):
                cog_name = f"{self.cogsfolder}.{file[:-3]}"
                await self._load_cog(cog_name)

        logger.info("All cogs loaded successfully.")

    async def _load_cog(self, cog_name):
        try:
            await self.load_extension(cog_name)
            logger.info(f"Loaded {cog_name} cog.")
        except Exception as e:
            logger.error(f"Failed to load cog {cog_name}: {e}")

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
        await bot.load_extensions()
        await bot.start(bot.token)

asyncio.run(main())
