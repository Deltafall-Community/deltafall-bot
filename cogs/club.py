import traceback
import textwrap
from rapidfuzz import fuzz, process

import discord
from discord.ext.paginators.button_paginator import ButtonPaginator, PaginatorButton
from discord.ext import commands
from discord import app_commands

from libs.namuclubmanager.clubmanager import Club, ClubLight, ClubError, ClubManager

from typing import List, Optional

paginator_buttons = {
    "FIRST": PaginatorButton(label="", position=0),
    "LEFT": PaginatorButton(label="Back", position=1),
    "PAGE_INDICATOR": PaginatorButton(label="Page N/A / N/A", position=2, disabled=False),
    "RIGHT": PaginatorButton(label="Next", position=3),
    "LAST": PaginatorButton(label="", position=4),
    "STOP": None
}

class EditClubModal(discord.ui.Modal, title='Edit Club'):
    def __init__(self, club_manager: ClubManager,  club_command_obj: 'ClubCommand', club: Club):
        super().__init__()
        self.club_manager = club_manager
        self.club_command_obj = club_command_obj
        self.club = club

        self.description = discord.ui.TextInput(
            label='Description',
            style=discord.TextStyle.long,
            placeholder='The club description...',
            required=False,
            max_length=300,
            default=self.club.description
        )
        self.add_item(self.description)

        self.icon_url = discord.ui.TextInput(
            label='Icon',
            placeholder='Enter the URL for the icon image... (e.g. https://i.imgur.com/0bXMnbm.jpeg)',
            required=False,
            default=self.club.icon_url
        )
        self.add_item(self.icon_url)
    
        self.banner_url = discord.ui.TextInput(
            label='Banner',
            placeholder='Enter the URL for the banner image... (e.g. https://i.imgur.com/2VzYLjT.png)',
            required=False,
            default=self.club.banner_url
        )
        self.add_item(self.banner_url)

    async def on_submit(self, interaction: discord.Interaction):
        club = await self.club_manager.edit_club(interaction, interaction.user, self.description.value, self.icon_url.value, self.banner_url.value)
        if club:
            return await interaction.response.send_message(view=ClubView(club_command=self.club_command_obj, club=club, timeout=None), ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return await interaction.response.send_message("You are not a leader of a club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Something went wrong.', ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)

class CreateClubModal(discord.ui.Modal, title='Create Club'):
    def __init__(self, club_manager: ClubManager, club_command_obj: 'ClubCommand'):
        super().__init__()
        self.club_manager = club_manager
        self.club_command_obj = club_command_obj

        self.name = discord.ui.TextInput(
            label='Name',
            placeholder='Enter club name...',
            max_length=100
        )
        self.add_item(self.name)

        self.description = discord.ui.TextInput(
            label='Description',
            style=discord.TextStyle.long,
            placeholder='The club description...',
            required=False,
            max_length=300
        )
        self.add_item(self.description)

        self.icon_url = discord.ui.TextInput(
            label='Icon',
            placeholder='Enter the URL for the icon image... (e.g. https://i.imgur.com/0bXMnbm.jpeg)',
            required=False
        )
        self.add_item(self.icon_url)

        self.banner_url = discord.ui.TextInput(
            label='Banner',
            placeholder='Enter the URL for the banner image... (e.g. https://i.imgur.com/2VzYLjT.png)',
            required=False
        )
        self.add_item(self.banner_url)

    async def on_submit(self, interaction: discord.Interaction):
        club = await self.club_manager.create_club(interaction, interaction.user, self.name.value, self.description.value, self.icon_url.value, self.banner_url.value)
        if club == ClubError.ALREADY_OWNED:
            return await interaction.response.send_message(content="You have already owned a club.")
        await self.club_command_obj.add_club_to_cache(interaction, club)
        await interaction.response.send_message(view=ClubView(club_command=self.club_command_obj, club=club, timeout=None), allowed_mentions=discord.AllowedMentions.none())

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Something went wrong.', ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)

class ClubAnnounceModal(discord.ui.Modal, title='Club Announce'):
    def __init__(self, club_manager: ClubManager):
        super().__init__()
        self.club_manager = club_manager

        self.message = discord.ui.TextInput(
            label='Message',
            style=discord.TextStyle.long,
            placeholder='The quick brown fox jumps over the lazy dog...',
            required=True,
            max_length=1000
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        club = await self.club_manager.get_club(interaction, interaction.user)
        if club:
            announce_str = f"## `{club.name}` Club Announcement:\n{self.message.value}"
            vaild_members = [user for user in club.users if user.name]
            if vaild_members:
                announce_str += "\n\n-# "
            for user in vaild_members:
                announce_str += user.mention
            return await interaction.response.send_message(announce_str, allowed_mentions=discord.AllowedMentions(users=club.users, everyone=False, roles=False))
        return await interaction.followup.send("You are not a leader of a club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Something went wrong.', ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)

class JoinClubButton(discord.ui.Button):
    def __init__(self, club_command: 'ClubCommand', club: Club, *, style = discord.ButtonStyle.secondary, label = None, disabled = False, custom_id = None, url = None, emoji = None, sku_id = None, id = None):
        self.club_command = club_command
        self.club = club
        super().__init__(style=style, label=label, disabled=disabled, custom_id=custom_id, url=url, emoji=emoji, sku_id=sku_id, id=id)

    async def callback(self, interaction):
        await self.club_command.join_club(interaction, self.club.leader)

class ListClubMemberButton(discord.ui.Button):
    def __init__(self, club: Club, *, style = discord.ButtonStyle.secondary, label = None, disabled = False, custom_id = None, url = None, emoji = None, sku_id = None, id = None):
        self.club = club
        super().__init__(style=style, label=label, disabled=disabled, custom_id=custom_id, url=url, emoji=emoji, sku_id=sku_id, id=id)

    async def callback(self, interaction):
        user_list_embeds=[discord.Embed(description="## Member(s)", color=discord.Color.from_rgb(255,255,255))]
        current_page=0
        for user, index in zip(self.club.users, range(len(self.club.users))):
            if user_list_embeds[current_page].description.count('\n') > 9:
                current_page+=1
            if len(user_list_embeds) < current_page+1:
                user_list_embeds.append(discord.Embed(description="", color=discord.Color.from_rgb(255,255,255)))
            user_list_embeds[current_page].description += f"\n**#{index+1}** - {(lambda s: s.mention if s.name else "*Unknown User*")(user)}"
        paginator = ButtonPaginator(user_list_embeds, author_id=interaction.user.id, buttons=paginator_buttons)
        return await paginator.send(interaction, override_page_kwargs=True, ephemeral=True)

class ClubContainer(discord.ui.Container):
    def __init__(self, club_command: 'ClubCommand', club: Club, children = ..., *, accent_colour = None, accent_color = None, spoiler = False, id = None):
        super().__init__(accent_colour=accent_colour, accent_color=accent_color, spoiler=spoiler, id=id)
        
        self.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(club.banner_url)))
        self.add_item(discord.ui.Section(accessory=discord.ui.Thumbnail(club.icon_url)).add_item(discord.ui.TextDisplay(f"# {club.name}\n{(lambda s: s or "*No description.*")(club.description)}")))
        self.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        vaild_members = [user for user in club.users if user.name]
        extras = ""
        if len(vaild_members) != len(club.users):
            extras += f"\n-# Unknown Member: {len(club.users) - len(vaild_members)}"
        self.add_item(discord.ui.Section(accessory=ListClubMemberButton(club=club, label="List Member(s)", style=discord.ButtonStyle.primary)).add_item(discord.ui.TextDisplay(f"Member: {len(vaild_members)}" + extras)))
        self.add_item(discord.ui.Section(accessory=JoinClubButton(club_command=club_command, club=club, label="Join Club", style=discord.ButtonStyle.success)).add_item(discord.ui.TextDisplay(f"Led By {(lambda s: s.mention if s.name else "*Unknown User*")(club.leader)}")))

class ClubView(discord.ui.LayoutView):
    def __init__(self, club_command: 'ClubCommand', club: Club, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.add_item(ClubContainer(club_command=club_command, club=club))

class ClubCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.club_manager = ClubManager(sqlitecloud_club, True, logger=self.bot.logger) if (sqlitecloud_club := self.bot.config.get("sqlitecloud-club")) else ClubManager("clubs.db", logger=self.bot.logger)
        
        self.club_ping_ctx_menu = app_commands.ContextMenu(
            name='Club Ping',
            callback=self.club_ping,
        )
        self.bot.tree.add_command(self.club_ping_ctx_menu)
        self.clubs_cache = {}

    async def clubs_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        matches = process.extract(
            current,
            [app_commands.Choice(name=f"{textwrap.shorten(club.name, 50)} - {(await self.club_manager.get_member(interaction, club.leader)).name}", value=str(club.leader)) for club in self.clubs_cache[interaction.guild.id]],
            scorer=fuzz.ratio,
            processor=lambda c: getattr(c, "name", str(c)),
        )
        return [club for club, score, _ in matches][:5]

    async def remove_club_from_cache(self, interaction: discord.Interaction):
        if self.clubs_cache.get(interaction.guild.id):
            self.clubs_cache[interaction.guild.id] = [club for club in self.clubs_cache[interaction.guild.id] if club.leader != interaction.user.id]

    async def add_club_to_cache(self, interaction: discord.Interaction, club: Club):
        if not self.clubs_cache.get(interaction.guild.id):
            self.clubs_cache[interaction.guild.id] = []
        self.clubs_cache[interaction.guild.id].append(ClubLight(club.name, club.leader.id, club.description, club.icon_url, club.banner_url))

    async def refresh_clubs_cache(self):
        guilds = await self.club_manager.get_guilds_id()
        for guild in guilds:
            self.clubs_cache[guild] = await self.club_manager.get_guild_clubs_light(guild)

    group = app_commands.Group(name="club", description="club stuff")

    @group.command(name="create", description="creates your club")
    async def createclub(self, interaction: discord.Interaction):
        club_modal = CreateClubModal(self.club_manager, self)
        await interaction.response.send_modal(club_modal)

    @group.command(name="edit", description="edits your club")
    async def editclub(self, interaction: discord.Interaction):
        club = await self.club_manager.get_club(interaction, interaction.user)
        if club:
            club_modal = EditClubModal(self.club_manager, self, club)
            return await interaction.response.send_modal(club_modal)
        return await interaction.response.send_message("You are not a leader of a club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="disband", description="disband/deletes your club")
    async def disbandclub(self, interaction: discord.Interaction):
        await interaction.response.defer()
        delete = await self.club_manager.delete_club(interaction, interaction.user)
        if delete:
            await self.remove_club_from_cache(interaction)
            return await interaction.followup.send("Your club has been successfully disbanded, All of your club members have been kicked out.", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())
        return await interaction.followup.send("You are not a leader of a club.", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="join", description="joins a club")
    @app_commands.autocomplete(search=clubs_autocomplete)
    async def joinclub(self, interaction: discord.Interaction, search: Optional[str], leader: Optional[discord.User]):
        if search:
            leader = await self.club_manager.get_member(interaction, int(search))
        elif not leader:
            return await interaction.response.send_message("Please specify an input.", ephemeral=True)
        await self.join_club(interaction, leader)

    async def join_club(self, interaction: discord.Interaction, leader: discord.User):
        await interaction.response.defer(ephemeral=True)
        if interaction.user == leader:
            return await interaction.followup.send(content="You can't join your own club, Duh.", ephemeral=True)
        club = await self.club_manager.join_club(interaction, interaction.user, leader)
        if club == ClubError.ALREADY_JOINED:
            return await interaction.followup.send(content=f"You have already joined {leader.mention}'s club.", allowed_mentions=discord.AllowedMentions.none(), ephemeral=True)
        elif club:
            return await interaction.followup.send(f"Joined {leader.mention}'s club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return await interaction.followup.send(f"No club was owned by {leader.mention}", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="leave", description="leaves a club")
    @app_commands.autocomplete(search=clubs_autocomplete)
    async def leaveclub(self, interaction: discord.Interaction, search: Optional[str], leader: Optional[discord.User]):
        if search:
            leader = await self.club_manager.get_member(interaction, int(search))
        elif not leader:
            return await interaction.response.send_message("Please specify an input.", ephemeral=True)
        await self.leave_club(interaction, leader)

    async def leave_club(self, interaction: discord.Interaction, leader: discord.User):
        await interaction.response.defer(ephemeral=True)
        club = await self.club_manager.leave_club(interaction, interaction.user, leader)
        if club:
            return await interaction.followup.send(f"You have successfully left {leader.mention}'s club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return await interaction.followup.send(f"You didn't join {leader.mention}'s club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="info", description="gets club info")
    @app_commands.autocomplete(search=clubs_autocomplete)
    async def info(self, interaction: discord.Interaction, search: Optional[str], leader: Optional[discord.User]):
        if search:
            leader = await self.club_manager.get_member(interaction, int(search))
        elif not leader:
            return await interaction.response.send_message("Please specify an input.", ephemeral=True)
        await interaction.response.defer()
        club = await self.club_manager.get_club(interaction, leader)
        if club:
            return await interaction.followup.send(view=ClubView(club_command=self, club=club, timeout=None), allowed_mentions=discord.AllowedMentions.none())
        return await interaction.followup.send(f"No club was owned by {leader.mention}", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="ping", description="ping club members")
    async def ping(self, interaction: discord.Interaction):
        return await self.club_ping(interaction, message=None)

    @group.command(name="announce", description="announces a club message")
    async def announce(self, interaction: discord.Interaction):
        club_announce_modal = ClubAnnounceModal(self.club_manager)
        await interaction.response.send_modal(club_announce_modal)

    @group.command(name="joined_list", description="list clubs you have joined")
    async def joined_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        clubs = await self.club_manager.get_user_clubs(interaction, interaction.user)
        clubs_embeds=[discord.Embed(description="## List of clubs you've joined", color=discord.Color.from_rgb(255,255,255))]
        current_page=0
        if clubs:
            for club in clubs:
                if clubs_embeds[current_page].description.count('\n') > 9:
                    current_page+=1
                if len(clubs_embeds) < current_page+1:
                    clubs_embeds.append(discord.Embed(description="", color=discord.Color.from_rgb(255,255,255)))
                club_desc = (lambda s: s or "*No description.*")(club.description)
                club_leader_mention = (lambda s: s.mention if s.name else "*Unknown User*")(club.leader)
                clubs_embeds[current_page].description += f'\n- **`{club.name}`** - **{textwrap.shorten((club_desc+" ")[:club_desc.find("\n")], 60)}**\n-# ↳ Led by {club_leader_mention} • **Member #{club.users.index(interaction.user)+1}**\n'
        paginator = ButtonPaginator(clubs_embeds, author_id=interaction.user.id, buttons=paginator_buttons)
        return await paginator.send(interaction, override_page_kwargs=True, ephemeral=True)

    @group.command(name="list", description="list clubs in the server")
    async def list_club(self, interaction: discord.Interaction):
        await interaction.response.defer()
        clubs = await self.club_manager.get_guild_clubs(interaction)
        clubs_embeds=[discord.Embed(description="## Clubs", color=discord.Color.from_rgb(255,255,255))]
        current_page=0
        if clubs:
            for club in clubs:
                if clubs_embeds[current_page].description.count('\n') > 9:
                    current_page+=1
                if len(clubs_embeds) < current_page+1:
                    clubs_embeds.append(discord.Embed(description="", color=discord.Color.from_rgb(255,255,255)))
                club_desc = (lambda s: s or "*No description.*")(club.description)
                club_leader_mention = (lambda s: s.mention if s.name else "*Unknown User*")(club.leader)
                clubs_embeds[current_page].description += f'\n- **`{club.name}`** - **{textwrap.shorten((club_desc+" ")[:club_desc.find("\n")], 60)}**\n-# ↳ Led by {club_leader_mention} • **Member Count: {len(club.users)}**\n'
        paginator = ButtonPaginator(clubs_embeds, author_id=interaction.user.id, buttons=paginator_buttons)
        return await paginator.send(interaction)

    async def club_ping(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        club = await self.club_manager.get_club(interaction, interaction.user)
        if club:
            ping_str = f"## `{club.name}` Club Ping:"
            vaild_members = [user for user in club.users if user.name]
            if vaild_members:
                ping_str += "\n-# "
            for user in vaild_members:
                ping_str += user.mention
            if not message:
                await interaction.channel.send(ping_str)
            else:
                await message.reply(ping_str)
            return await interaction.followup.send("Sent Club Ping.")
        return await interaction.followup.send("You are not a leader of a club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):
    club = ClubCommand(bot)
    await club.refresh_clubs_cache()
    await bot.add_cog(club)
