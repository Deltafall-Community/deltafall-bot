import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Union
import asyncio

from petpetgif import petpet

from io import BytesIO
import aiohttp

class PetpetCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def gen_petpet(self, image: BytesIO) -> discord.File:
        # (editor node) code mostly taken from https://pypi.org/project/pet-pet-gif/
        dest = BytesIO() # container to store the petpet gif in memory
        petpet.make(image, dest)
        dest.seek(0) # set the file pointer back to the beginning so it doesn't upload a blank file.
        return discord.File(dest, filename="petpet.gif")

    async def petpet(self, image: Union[BytesIO, str]) -> discord.File:
        if type(image) is str:
            async with aiohttp.ClientSession() as session:
                async with session.get(image) as response:
                    image = BytesIO(await response.read())
        return await asyncio.get_running_loop().run_in_executor(None, self.gen_petpet, image)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.content.lower() == "petpet" and message.reference:
            messager = await message.channel.fetch_message(message.reference.message_id)
            if not await self.bot.setting_manager.get_user_setting(messager.author, ("fun", "petpet")):
                return
            if messager.attachments:
                image_url = messager.attachments[0].url
            else:
                image_url = messager.author.avatar.url
            await message.reply(file=await self.petpet(image_url))

    @app_commands.command(name="petpet", description="petpet")
    async def pet(self, interaction: discord.Interaction, user: Optional[discord.Member], custom_image: Optional[discord.Attachment]):
        img = None
        if user:
            img = user.avatar.url
        if custom_image and custom_image.content_type and custom_image.content_type[:custom_image.content_type.find("/")] == "image":
            img = custom_image.url
        if not img:
            await interaction.response.send_message("Invaild.",ephemeral=True)

        await interaction.response.send_message(file=await self.petpet(img))

async def setup(bot):
    await bot.add_cog(PetpetCommand(bot))