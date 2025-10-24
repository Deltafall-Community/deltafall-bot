import discord
from discord.ext import commands
from discord import app_commands

from libs.mangadexasync.mangadexasync import MangaDexAsync, Page, Manga

class MangaRandom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mgd = MangaDexAsync()
        self.group.allowed_installs = discord.app_commands.AppInstallationType(guild=True, user=True)

    group = app_commands.Group(name="manga", description="manga stuff")

    @group.command(name="random", description="gets a random manga from mangadex")
    async def random(self, interaction: discord.Interaction):
        await interaction.response.defer()
        filters = {
            "contentRating[]": ["safe"],
            "excludedTags[]": [self.mgd.get_tag_id_from_str("Gore"), self.mgd.get_tag_id_from_str("Sexual Violence"), self.mgd.get_tag_id_from_str("Boys' Love"), self.mgd.get_tag_id_from_str("Girls' Love"), self.mgd.get_tag_id_from_str("Loli")]
        }
        
        try:
            manga: Manga = await self.mgd.get_random_manga(filters)
        except Exception as e:
            self.bot.logger.error(e, exc_info=True)
            return await interaction.followup.send('Something went wrong.')

        embed = discord.Embed(description=f"## [{list(manga.title.values())[0]}]({"https://mangadex.org/title/" + manga.id})")
        embed.description += f"\n{list(manga.desc.values())[0]}"
        embed.set_image(url=manga.cover.url)

        await interaction.followup.send(embed=embed)

    @group.command(name="random_page", description="gets a random page from a random manga from mangadex")
    async def random_page(self, interaction: discord.Interaction):
        await interaction.response.defer()
        filters = {
            "contentRating[]": ["safe"],
            "excludedTags[]": [self.mgd.get_tag_id_from_str("Gore"), self.mgd.get_tag_id_from_str("Sexual Violence"), self.mgd.get_tag_id_from_str("Boys' Love"), self.mgd.get_tag_id_from_str("Girls' Love"), self.mgd.get_tag_id_from_str("Loli")]
        }
        
        try:
            page: Page = await self.mgd.get_random_page(True, filters)
        except Exception as e:
            self.bot.logger.error(e, exc_info=True)
            return await interaction.followup.send('Something went wrong.')

        embed = discord.Embed(description=f"## [{list(page.manga.title.values())[0]}]({"https://mangadex.org/chapter/" + page.chapter.id + "/" + str(page.page)})")
        embed.description += f"\n-# Page: {page.page}"
        if page.chapter.chapter:
            embed.description += f", Chapter: {page.chapter.chapter}"
        if page.chapter.volume:
            embed.description += f", Volume: {page.chapter.volume}"
        embed.set_image(url=page.url)

        await interaction.followup.send(embed=embed)

async def setup(bot):
    mr = MangaRandom(bot)
    await mr.mgd.refresh_tags_cache()
    await bot.add_cog(mr)