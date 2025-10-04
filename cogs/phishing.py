import discord
from discord.ext import tasks, commands
from discord import app_commands
from libs.namuphishingdetection.phishingdetector import PhishingDetector
import asyncio

class phishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guildid = 1198291214672347308
        self.check_update.start()

    @tasks.loop(seconds=3600.0)
    async def check_update(self):
        await self.bot.phishing_detector.update()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        
        if message.guild.id == self.guildid:
            phishing_detector: PhishingDetector = self.bot.phishing_detector
            if await phishing_detector.check_string(message.content):
                await message.reply("PHISHING LINK(S) DETECTED!!! <@&1211135690503495740> <@&1220416159573213264>")
        

async def setup(bot):
    await bot.add_cog(phishing(bot))