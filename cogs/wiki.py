import discord
from discord.ext import commands
from discord import app_commands
from bs4 import BeautifulSoup
import aiohttp
import mediawiki
import re

from libs.namuwikitextparser import namuwikitextparser, discordformatwikitext

class wiki(commands.Cog):
    def __init__(self, bot):
        self.deltafallwiki = mediawiki.MediaWiki(url="https://deltafall.miraheze.org/w/api.php")
        self.bot = bot

    async def getwikiembed(self, page: mediawiki.MediaWikiPage):
        parser=namuwikitextparser.WikitextParser()
        wiki=await parser.parse(page.wikitext, "https://deltafall.miraheze.org/wiki")
        formattedwiki=await discordformatwikitext.format(wiki[0])
        formattedwiki=f"# [{page.title}]({page.url})\n"+formattedwiki

        title=None
        if "SHORTDESC" in wiki[1]:
            title=wiki[1]["SHORTDESC"][0]
        embed=discord.Embed(title=title, description=formattedwiki, color=0x4034eb)
        images=page.images[:-1]
        if len(images) > 0:
            embed.set_thumbnail(url=images[0])

        return embed

    async def removecitation(self, text):
        return re.sub(r'\[[^\]]*\]', '', text)
    async def getwikiembedCompat(self, url: str):
        # we are parsing the entire html because if we use mediawiki api sometime it doesnt redirect to other sites.

        HTMLcontent = ""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                HTMLcontent = await response.text()
        HTMLcontent = BeautifulSoup(HTMLcontent, features="lxml")

        title = HTMLcontent.body.find("span", attrs={"class": "mw-page-title-main"}).text.strip()
        siteSub = HTMLcontent.body.find("div", attrs={"id": "siteSub"}).text.strip() 
        subtitles = [ (await self.removecitation(title.text)).strip() for title in HTMLcontent.body.find_all("h3") ]
       
        mainContent = HTMLcontent.body.find("div", attrs={"id":"mw-content-text", "class": "mw-body-content"})
        images = []
        previewImage = "https://static.wikitide.net/deltafallwiki/f/f2/Deltafall_Wiki_logo.png"
        for img in mainContent.find_all("img"):
            if "class" in img.attrs and img["class"][0] == "mw-file-element" and img["src"] != "https://upload.wikimedia.org/wikipedia/commons/8/80/Wikipedia-logo-v2.svg":
                images.append(img["src"])
        if len(images) > 0:
            imgUrl = images[0]
            if not imgUrl.startswith('https'):
                imgUrl = "https:" + imgUrl
            previewImage = imgUrl

        parsed = []
        for e in mainContent.find_all("section"):
            content = []
            for n in e.contents:
                match n.name:
                    case "p":
                        t = (await self.removecitation(n.text)).strip()
                        if t != "":
                            content.append(t)
                    case "blockquote":
                        content.append("\n".join([ f"-# - *{await self.removecitation(quote)}*" for quote in n.text.strip().split("\n") ]))
                    case "ul":
                        content.append("\n".join([ f"- {await self.removecitation(quote)}" for quote in n.text.strip().split("\n") ]))

            parsed.append("\n".join(content))

        # formatting

        content=f"# [{title}]({url})"
        content += "\n"+parsed[0]
        for t, i in zip(subtitles, range(len(subtitles))):
            content+="\n## "+t
            content+="\n"+parsed[i+1]

        embed=discord.Embed(title=siteSub, description=content, color=0x4034eb)
        embed.set_thumbnail(url=previewImage)
        return embed

    @app_commands.command(name="wiki", description="deltafall wiki content")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def dfwiki(
        self,
        interaction: discord.Interaction,
        search: str):

        searchresults = self.deltafallwiki.search(search)
        page = self.deltafallwiki.page(searchresults[0])
        embed=None

        try:
            embed = await self.getwikiembed(page)
        except Exception:
            embed = await self.getwikiembedCompat(f"https://deltafall.miraheze.org/wiki/{searchresults[0].replace(" ", "_")}")
        await interaction.response.send_message(embed=embed)
    
async def setup(bot):
    await bot.add_cog(wiki(bot))