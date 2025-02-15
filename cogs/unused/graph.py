#import wavelink
import discord
from discord.ext import commands
from discord import app_commands
from discord import Embed
from wavelink import Queue

#from time import strftime
#from time import gmtime
import datetime
import re
import json

#from io import BytesIO
#import requests
#from PIL import Image, ImageStat

class graph(commands.Cog):
    def __init__(self, bot):
        self.lastmessage_time = None
        self.allemoji = {}
        self.bot = bot

    @commands.command()
    async def history(self, ctx):
        json.dump(self.allemoji, open("data/emoji.json", 'w'), indent=2)
        #entireting = r'(<.*?>)'
        justtheemojiname = r'<:(.*?):\d+>'
        if ctx.author.id == 899113384660844634:
            if not self.lastmessage_time:
                async for message in ctx.channel.history(limit=500, oldest_first=True):
                    finds = re.findall(justtheemojiname, message.content)
                    for emoji in finds:
                        if emoji in self.allemoji:
                            self.allemoji[emoji] += 1
                        else:
                            self.allemoji[emoji] = 1
                    self.lastmessage_time = message.created_at
                return await self.history(ctx)

            async for message in ctx.channel.history(limit=500, after=self.lastmessage_time):
                finds = re.findall(justtheemojiname, message.content)
                for emoji in finds:
                    if emoji in self.allemoji:
                        self.allemoji[emoji] += 1
                    else:
                        self.allemoji[emoji] = 1
                self.lastmessage_time = message.created_at
            return await self.history(ctx)



async def setup(bot):
    await bot.add_cog(graph(bot))