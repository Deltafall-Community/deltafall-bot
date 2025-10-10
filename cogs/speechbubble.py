import discord
from discord.ext import commands
from discord import app_commands
#from typing import Optional

from io import BytesIO
import requests

from PIL import Image

class speechbubble(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def generatespeechbubble(self, img):
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

    @app_commands.command(name="speechbubble", description="makes a speechbubble")
    async def textbox(self, interaction: discord.Interaction, image: discord.Attachment):
        img = Image.open(BytesIO(requests.get(image.url).content))
        image = await self.generatespeechbubble(img=img)
        await interaction.response.send_message(file=image)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content.lower() == "sb" and message.reference:
            messager = await message.channel.fetch_message(message.reference.message_id)
            if messager.author == self.bot.user:
                return
            if messager.attachments:
                img = Image.open(BytesIO(requests.get(messager.attachments[0].url).content))
                image = await self.generatespeechbubble(img=img)
                await message.channel.send(file=image, reference=message)

async def setup(bot):
    await bot.add_cog(speechbubble(bot))