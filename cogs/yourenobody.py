import discord
from discord.utils import get
from discord.ext import commands
import time
from discord.ext import tasks
import os

import time
import datetime

from dataclasses import dataclass
@dataclass
class Flags:
    isCreatedRecently: bool = False
    isUsingDefaultAvatar: bool = False
    hasNotSetDisplayName: bool = False
    hasNoBadges: bool = False
    hasBeenFlaggedAsSpammer: bool = False

class yourenobody(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guildid = 1198291214672347308
        self.channelid = 1245885709240373309
        
    async def getEmoji(self, bool: bool) -> str:
        if bool: return "✅"
        else: return "❌"

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.User):
        if member.guild.id != self.guildid:
            return
        
        flags = Flags()

        if (datetime.datetime.now(datetime.timezone.utc).timestamp() - time.mktime(member.created_at.timetuple())) < 604800: flags.isCreatedRecently = True
        if member.public_flags.spammer:
            flags.hasBeenFlaggedAsSpammer = True
            if len(member.public_flags.all()) - 1 < 1: flags.hasNoBadges = True
        elif len(member.public_flags.all()) < 1: flags.hasNoBadges = True
        if not member.avatar or (member.avatar and member.avatar.url == member.default_avatar.url): flags.isUsingDefaultAvatar = True
        if not member.global_name or (member.global_name and member.global_name == member.name): flags.hasNotSetDisplayName = True

        totalScore = 0

        if flags.isCreatedRecently: totalScore += 30
        if flags.isUsingDefaultAvatar: totalScore += 30
        if flags.hasNotSetDisplayName: totalScore += 20
        if flags.hasBeenFlaggedAsSpammer: totalScore += 10
        if flags.hasNoBadges: totalScore += 10

        summaryString = f"""```
[{await self.getEmoji(flags.isCreatedRecently)}] (+30) created their account in the last 7 days
[{await self.getEmoji(flags.isUsingDefaultAvatar)}] (+30) has not changed their profile picture
[{await self.getEmoji(flags.hasNotSetDisplayName)}] (+20) has the default display name
[{await self.getEmoji(flags.hasBeenFlaggedAsSpammer)}] (+10) flagged "likely a spammer" by discord
[{await self.getEmoji(flags.hasNoBadges)}] (+10) has no badges
```"""
        
        extraMsg = "All clears"
        if totalScore >= 50: extraMsg = f"This guy (<@{member.id}>) is looking real suspicious, no? <@&1211135690503495740> <@&1220416159573213264>"

        if totalScore >= 50:
            channel=discord.utils.get(member.guild.channels, id=self.channelid)
            embed=discord.Embed(title="", description=f"# User Suspicious Score Summary\n{summaryString}\n### Total: {totalScore}\n{extraMsg}", color=0x4034eb)
            await channel.send(content=extraMsg, embed=embed)

async def setup(bot):
    await bot.add_cog(yourenobody(bot))