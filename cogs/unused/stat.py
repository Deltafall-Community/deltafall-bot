import discord
from discord.ext import commands
from discord import app_commands
import os
#import json

class stat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="stat", description="gets the deltafall server stat")
    async def stat(self, interaction: discord.Interaction):
        connection = self.bot.quote_db
        cur = connection.cursor()
        try:
            quotescount = cur.execute(f"SELECT COUNT() FROM '{interaction.guild.id}'").fetchone()[0]
        except:
            quotescount = "Unknown"
        embed=discord.Embed(title="Deltatistics", description=f"There are {quotescount} quote(s) added so far in this server.", color=0x57e389)
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):
    await bot.add_cog(stat(bot))
