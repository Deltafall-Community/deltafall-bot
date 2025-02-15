import discord
from discord.utils import get
from discord.ext import commands
import time
from discord.ext import tasks
import os

import time
import datetime

class yourenobody(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guildid = 1198291214672347308
        
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == self.guildid:
            print(time.time() - time.mktime(member.created_at.timetuple()))
            if time.time() - time.mktime(member.created_at.timetuple()) < 172800:
                channel = discord.utils.get(member.guild.channels, id=1311950927527149568)
                await channel.send(f"<@{member.id}> erm this guy might be an alt <@&1211135690503495740><@&1220416159573213264> can u take a look at this?")
            #print(member.guild.roles

async def setup(bot):
    await bot.add_cog(yourenobody(bot))