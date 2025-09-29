import discord
from discord.ext import commands
from discord import app_commands

from mangadexasync.mangadexasync import MangaDexAsync, Page

class MangaRandom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mgd = MangaDexAsync()

    group = app_commands.Group(name="manga", description="manga stuff")

    @group.command(name="random_page", description="gets a random page from a random manga from mangadex")
    async def random_page(self, interaction: discord.Interaction):
        await interaction.response.defer()
        filters = {
            "contentRating[]": ["safe"]
        }
        
        try:
            page: Page = await self.mgd.get_random_page(True, filters)
        except Exception as e:
            await interaction.followup.send('Something went wrong.')
            self.bot.logger.error(e)

        embed = discord.Embed(description=f"## [{list(page.manga.title.values())[0]}]({"https://mangadex.org/chapter/" + page.chapter.id + "/" + str(page.page)})")
        embed.description += f"\n-# Page: {page.page}"
        if page.chapter.chapter:
            embed.description += f", Chapter: {page.chapter.chapter}"
        if page.chapter.volume:
            embed.description += f", Volume: {page.chapter.volume}"
        embed.set_image(url=page.url)

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MangaRandom(bot))