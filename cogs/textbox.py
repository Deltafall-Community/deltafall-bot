import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Union, Type
import asyncio
import aiohttp

from cachetools import TTLCache
from io import BytesIO
from PIL import Image

import math

from libs.namutextbox.textbox import Textbox
from libs.namutextbox.memory_textbox import MemoryTextbox

class TextboxCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pfps_cache = TTLCache(maxsize=100, ttl=300)

    async def as_image_binary(self, images):
        image_binary = BytesIO()
        if len(images) > 1:
            file_format = "webp"
            if len(images) * 100 < 1000:
                frame_duration = 100
            else:
                desired_duration = 1  # seconds
                min_frame_duration = 100  # ms
                max_frames = desired_duration * 1000 // min_frame_duration
                step = max(1, math.ceil((len(images)-1) / max_frames))
                last_img = images[-1]
                images = images[::step]
                images.append(last_img)
                frame_duration = int((desired_duration / (len(images)-1)) * 1000)
            images[0].save(image_binary, file_format, save_all=True, append_images=images[1:], optimize=True, duration=[frame_duration] * (len(images)-1) + [5000], loop=0)
        else:
            file_format = "png"
            images[0].save(image_binary, file_format)

        image_binary.seek(0)
        return (image_binary, file_format)

    def reencode_image(self, image):
        image = Image.open(BytesIO(image))
        image.load()
        reEncodedImage = BytesIO()
        img = image.convert("RGBA")
        img.save(reEncodedImage, format="PNG")
        reEncodedImage.seek(0)
        return Image.open(reEncodedImage)

    async def make_textbox(self, message: discord.Message, textbox: Union[Type[Textbox], Type[MemoryTextbox]] ,reference: Optional[discord.Message] = None):
        pfp = self.pfps_cache.get(message.author.id)
        if not pfp:
            async with aiohttp.ClientSession() as session:
                async with session.get(message.author.avatar.url+"?size=96") as response:
                    pfp = await response.read()
            self.pfps_cache[message.author.id] = pfp

        pfp = await asyncio.get_running_loop().run_in_executor(None, self.reencode_image, pfp)     

        msg = message.clean_content
        asterisk = False
        animated = False
        if msg.lstrip().startswith("[animated]"):
            animated = True
            msg = msg.lstrip()[10:].lstrip()
        if msg.lstrip().startswith("*"):
            asterisk = True
            msg = msg.lstrip()[1:].lstrip()
        
        if textbox is Textbox:
            textbox = Textbox("data/textbox/deltarune.toml", pfp, "data/fonts/determination-mono.ttf", text=msg, asterisk=asterisk, animated=animated)
        else:
            textbox = MemoryTextbox(pfp, "data/fonts/determination-mono.ttf", text=msg, asterisk=asterisk, name=message.author.name, animated=animated)

        image_binary, file_format = await self.as_image_binary(await asyncio.get_running_loop().run_in_executor(None, textbox.render))
    
        await message.channel.send(file=discord.File(fp=image_binary, filename=f"image.{file_format}"), reference=reference)
        if not reference:
            await message.delete()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        
        if message.reference:
            content = message.content.lower()
            if content in ("mtbq", "mtbmq"):
                messager = await message.channel.fetch_message(message.reference.message_id)
                if (messager.author == self.bot.user) or (messager.content == ""):
                    return

                if content == "mtbq":
                    await self.make_textbox(messager, Textbox, messager)

                if content == "mtbmq":
                    await self.make_textbox(messager, MemoryTextbox, messager)

        channels_get = await self.bot.setting_manager.get_guild_setting(message.guild, ("textbox", "channel"))
        if type(channels_get) is not list:
            channels_get = [e] if (e := channels_get) is not None else []

        if message.channel.id in channels_get:
            await self.make_textbox(message, Textbox)

    @app_commands.command(name="textbox", description="makes a textbox")
    @app_commands.choices(style=[
        app_commands.Choice(name="Deltarune", value="deltarune.toml"),
        app_commands.Choice(name="Undertale", value="undertale.toml")])
    @app_commands.choices(font=[
        app_commands.Choice(name="Determination Mono", value="determination-mono.ttf"),
        app_commands.Choice(name="Comic Sans", value="comic-sans.ttf"),
        app_commands.Choice(name="Earthbound", value="earthbound.ttf"),
        app_commands.Choice(name="Minecraft", value="minecraft.ttf"),
        app_commands.Choice(name="Papyrus", value="papyrus.ttf"),
        app_commands.Choice(name="Wingdings", value="wingdings.ttf")])
    @app_commands.choices(animated=[
        app_commands.Choice(name="Yes", value="1"),
        app_commands.Choice(name="No", value="0")])
    @app_commands.choices(portrait=[
        app_commands.Choice(name="ralsei", value="ralsei.webp"),
        app_commands.Choice(name="susie", value="susie.webp"),
        app_commands.Choice(name="sans", value="sans.webp"),
        app_commands.Choice(name="papyrus", value="papyrus.webp"),
        app_commands.Choice(name="queen", value="queen.webp"),
        app_commands.Choice(name="berdly", value="berdly.webp"),
        app_commands.Choice(name="asgore", value="asgore.webp"),
        app_commands.Choice(name="alphys", value="alphys.webp"),
        app_commands.Choice(name="bratty", value="bratty.webp"),
        app_commands.Choice(name="catti", value="catti.webp"),
        app_commands.Choice(name="catty", value="catty.webp")])
    @app_commands.allowed_installs(guilds=True, users=True)
    async def textbox(
        self,
        interaction: discord.Interaction,
        text: str,
        animated: Optional[app_commands.Choice[str]],
        font: Optional[app_commands.Choice[str]],
        style: Optional[app_commands.Choice[str]],
        portrait: Optional[app_commands.Choice[str]],
        custom_portrait: Optional[discord.Attachment]):

        await interaction.response.defer()

        port = None
        if portrait:
            port = f"data/textbox/portraits/{portrait.value}"
        elif custom_portrait:
            async with aiohttp.ClientSession() as session:
                async with session.get(custom_portrait.url) as response:
                    port = await response.read()
        
        if type(port) is str:
            port = await asyncio.get_running_loop().run_in_executor(None, Image.open, port)
        elif type(port) is bytes:
            port = await asyncio.get_running_loop().run_in_executor(None, self.reencode_image, port)
        
        asterisk = False
        if text.lstrip().startswith("*"):
            asterisk = True
            text = text.lstrip()[1:].lstrip()

        if animated:
            animated = bool(int(animated.value))
        if font:
            font = f"data/fonts/{font.value}"
        if style:
            style = f"data/textbox/{style.value}"

        textbox = Textbox(style or "data/textbox/deltarune.toml", port, font or "data/fonts/determination-mono.ttf", text=text, asterisk=asterisk, animated=animated or False)

        image_binary, file_format = await self.as_image_binary(await asyncio.get_running_loop().run_in_executor(None, textbox.render))        
        return await interaction.followup.send(file=discord.File(fp=image_binary, filename=f"image.{file_format}"))

async def setup(bot):
    await bot.add_cog(TextboxCommand(bot))
