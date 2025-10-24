import discord
from discord.ext import commands
from discord import app_commands
from typing import Union
import asyncio

from io import BytesIO
import aiohttp

from PIL import Image

class SpeechBubbleCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def gen_speechbubble(self, img: BytesIO):
        img = Image.open(img)
        bg = Image.new("RGB", (img.size[0], img.size[1]))
        bg.putalpha(0)
        speechbubble = Image.open("data/speechbubble/speechbubble.png").resize((img.size[0], int(img.size[1] / 4)))
        base = Image.new("RGB", (img.size[0], img.size[1]), (255,255,255)).convert('L')
        base.paste(speechbubble, (0,0))
        img = Image.composite(img,bg,base)
        with BytesIO() as image_binary:
            img.save(image_binary, 'PNG')
            image_binary.seek(0)
            return discord.File(fp=image_binary, filename='image.png')

    async def speechbubble(self, image: Union[BytesIO, str]) -> discord.File:
        if type(image) is str:
            async with aiohttp.ClientSession() as session:
                async with session.get(image) as response:
                    image = BytesIO(await response.read())
        return await asyncio.get_running_loop().run_in_executor(None, self.gen_speechbubble, image)

    @app_commands.command(name="speechbubble", description="makes a speechbubble")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def speechbubble_command(self, interaction: discord.Interaction, image: discord.Attachment):
        if not (image and image.content_type and image.content_type[:image.content_type.find("/")] == "image"):
            return await interaction.response.send_message("Invaild.",ephemeral=True)
        await interaction.response.send_message(file=await self.speechbubble(image.url))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.content.lower() == "sb" and message.reference:
            messager = await message.channel.fetch_message(message.reference.message_id)
            if messager.author == self.bot.user:
                return
            if messager.attachments:
                img = messager.attachments[0]
                if img and img.content_type and img.content_type[:img.content_type.find("/")] == "image":
                    await message.reply(file=await self.speechbubble(img.url))

async def setup(bot):
    await bot.add_cog(SpeechBubbleCommand(bot))