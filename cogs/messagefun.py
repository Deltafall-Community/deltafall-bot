import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random

class messagefun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.allusermessage = {899113384660844634: []}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        #if "@someone" in message.content.lower():
        #    members = message.guild.members
        #    await message.channel.send(f'<@{members[random.randint(0, len(members) - 1)].id}>', reference=message)
        if message.content.lower() == "nerdify":
            messager = await message.channel.fetch_message(message.reference.message_id)
            await message.channel.send(f'ermm akshually {messager.content} - 🤓☝️`{messager.author}`', reference=message, allowed_mentions=discord.AllowedMentions.none())
        if message.channel.id == 1198291381018443906 and message.author.id in [1170229788435304481, 1222177374142070835] and message.attachments:
            await message.add_reaction("⭐")
        if "miku" in message.content.lower():
            await message.reply("i'm thinking miku miku oo ee oo")

async def setup(bot):
    await bot.add_cog(messagefun(bot))