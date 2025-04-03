import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from lingojamtranslate.lingojamtranslate import LingoJamTranslate
import asyncio

class translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bad_translate", description="goofy translator based on lingojam website")
    async def bad_translate(
        self,
        interaction: discord.Interaction,
        text: str,
        lingojam_link: str):
        await interaction.response.defer()
        translator = LingoJamTranslate()
        await interaction.followup.send(content=await translator.translate(text, lingojam_link))

async def setup(bot):
    await bot.add_cog(translate(bot))