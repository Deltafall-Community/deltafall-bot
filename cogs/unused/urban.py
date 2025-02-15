import discord
from discord.ext import commands
from discord import app_commands
from pyurbandict import UrbanDict
#from typing import Optional

#from io import BytesIO
#import requests
import random

class urban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="urban", description="gets the urban")
    async def urbanc(
        self,
        interaction: discord.Interaction,
        word: str):

        r = UrbanDict(word).search()
        if not len(r) > 0:
            return await interaction.response.send_message("no results found :(",ephemeral=True)
        r = r[random.randint(0, len(r))]
        embed=discord.Embed(title=r.word, description=r.definition, color=0x62a0ea)
        embed.add_field(name="By", value=r.author, inline=True)
        embed.add_field(name="Like(s)/Dislike(s)", value=f"👍 {r.thumbs_up} / 👎 {r.thumbs_down}", inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(urban(bot))