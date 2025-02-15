import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from bs4 import BeautifulSoup
import aiohttp
import re


class wiki(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="wiki", description="deltafall wiki content")
    async def dfwiki(
        self,
        interaction: discord.Interaction,
        page: str):

        url = f"https://deltafall.miraheze.org/wiki/{page.replace(" ", "_")}"

        HTMLcontent = ""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                HTMLcontent = await response.text()
        HTMLcontent = BeautifulSoup(HTMLcontent, features="html.parser")

        title = HTMLcontent.body.find("span", attrs={"class": "mw-page-title-main"}).text.strip()
        siteSub = HTMLcontent.body.find("div", attrs={"id": "siteSub"}).text.strip() 
        subtitles = [ (await self.removecitation(title.text)).strip() for title in HTMLcontent.body.find_all("h3") ]
       
        mainContent = HTMLcontent.body.find("div", attrs={"id":"mw-content-text", "class": "mw-body-content"})
        images = []
        previewImage = None
        for img in mainContent.find_all("img"):
            if "class" in img.attrs and img["class"][0] == "mw-file-element" and img["src"] != "https://upload.wikimedia.org/wikipedia/commons/8/80/Wikipedia-logo-v2.svg": images.append(img["src"])
        if len(images) > 0:
            imgUrl = images[0]
            if not imgUrl.startswith('https'): imgUrl = "https:" + imgUrl
            previewImage = imgUrl


        parsed = []
        for e in mainContent.find_all("section"):
            #index = int(e["id"][16:])
            content = []
            for n in e.contents:
                match n.name:
                    case "p":
                        t = (await self.removecitation(n.text)).strip()
                        if t != "": content.append(t)
                    case "blockquote":
                        content.append("\n".join([ f"- {await self.removecitation(quote)}" for quote in n.text.strip().split("\n") ]))
            parsed.append("\n".join(content))

        content=f"# [{title}]({url})"
        content += "\n"+parsed[0]
        for t, i in zip(subtitles, range(len(subtitles))):
            content+="\n## "+t
            content+="\n"+parsed[i+1]

        embed=discord.Embed(title=siteSub, description=content, color=0x4034eb)
        embed.set_thumbnail(url=previewImage)
        await interaction.response.send_message(embed=embed)

    async def removecitation(self, text):
        return re.sub(r'\[[^\]]*\]', '', text)

async def setup(bot):
    await bot.add_cog(wiki(bot))