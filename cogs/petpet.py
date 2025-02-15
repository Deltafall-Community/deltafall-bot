import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from petpetgif import petpet

from io import BytesIO
import requests

class petpetc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def generatepetpet(self, image):
        # (editor node) code mostly taken from https://pypi.org/project/pet-pet-gif/
        dest = BytesIO() # container to store the petpet gif in memory
        petpet.make(image, dest)
        dest.seek(0) # set the file pointer back to the beginning so it doesn't upload a blank file.
        return discord.File(dest, filename="petpet.gif")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if message.content.lower() == "petpet":
            messager = await message.channel.fetch_message(message.reference.message_id)
            img = BytesIO(requests.get(messager.author.avatar.url).content)
            image = await self.generatepetpet(image=img)
            await message.channel.send(file=image, reference=message)

    @app_commands.command(name="petpet", description="petpet")
    async def pet(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member],
        custom_image: Optional[discord.Attachment]):

        if not user and not custom_image:
            await interaction.response.send_message("bro select one thing god damn",ephemeral=True)
        if user:
            img = BytesIO(requests.get(user.avatar.url).content)
        if custom_image:
            img = BytesIO(requests.get(custom_image.url).content)
        
        image = await self.generatepetpet(image=img)
        await interaction.response.send_message(file=image)

async def setup(bot):
    await bot.add_cog(petpetc(bot))