from enum import Enum
from dataclasses import field
from dataclasses import dataclass
from typing import List, Optional
import traceback
import asyncio
import textwrap
from rapidfuzz import fuzz, process

import discord
from discord.ext.paginators.button_paginator import ButtonPaginator, PaginatorButton
from discord.ext import commands
from discord import app_commands
from discord import Embed

class ClubError(Enum):
    ALREADY_JOINED = 1
    ALREADY_OWNED = 2

paginator_buttons = {
    "FIRST": PaginatorButton(label="", position=0),
    "LEFT": PaginatorButton(label="Back", position=1),
    "PAGE_INDICATOR": PaginatorButton(label="Page N/A / N/A", position=2, disabled=False),
    "RIGHT": PaginatorButton(label="Next", position=3),
    "LAST": PaginatorButton(label="", position=4),
    "STOP": None
}

@dataclass
class ClubData:
    name: str
    leader: discord.User
    description: str = None
    icon_url: str = "https://deltafall-community.github.io/resources/deltafall-logo-old.png"
    banner_url: str = "https://deltafall-community.github.io/resources/titieless_splash_screen.png"
    users: List[discord.User] = field(default_factory=list)

@dataclass
class ClubDataLight:
    name: str
    leader: int
    description: str = None
    icon_url: str = "https://deltafall-community.github.io/resources/deltafall-logo-old.png"
    banner_url: str = "https://deltafall-community.github.io/resources/titieless_splash_screen.png"

class DummyUser(discord.User):
    def __init__(self, id, name, discriminator, bot=False, avatar=None):
        mock_state = type('MockState', (object,), {'_get_websocket': lambda: None, '_get_guild': lambda x: None})()
        mock_data = {
            'id': str(id),
            'username': name,
            'discriminator': discriminator,
            'bot': bot,
            'avatar': avatar,
        }
        super().__init__(state=mock_state, data=mock_data)

async def get_member(interaction: discord.Interaction, id: int):
    # look in the cache first, if member doesn't exist try fetching it.
    member=interaction.guild.get_member(id)
    if not member:
        member = await interaction.client.fetch_user(id)
    if not member:
        return DummyUser(id, None, "0001")
    return member

async def populate_club(interaction: discord.Interaction, club: tuple, connection):
    leader = await get_member(interaction, club[1])
    return ClubData(club[0], leader, club[2], club[3], club[4], await get_club_users(interaction, connection, leader))

def db_get_table_clubs(connection, table):
    cur = connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}clubs'(name, leader, description, icon_url, banner_url)")
    return cur.execute(f"""
        SELECT * FROM '{table}clubs'
    """).fetchall()
async def get_guild_clubs(interaction: discord.Interaction, connection):
    table = interaction.guild.id
    event_loop = asyncio.get_running_loop()
    clubs = await event_loop.run_in_executor(None, db_get_table_clubs, connection, table)    
    return [await populate_club(interaction, club, connection) for club in clubs]
async def get_guild_clubs_light(connection, id: int):
    event_loop = asyncio.get_running_loop()
    clubs = await event_loop.run_in_executor(None, db_get_table_clubs, connection, id)    
    return [ClubDataLight(club[0], club[1], club[2], club[3], club[4]) for club in clubs]

def db_get_club(connection, table, leader: discord.User):
    cur = connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}clubs'(name, leader, description, icon_url, banner_url)")
    return cur.execute(f"""
        SELECT * FROM '{table}clubs' WHERE leader = ?
    """, (leader.id,)).fetchone()
async def get_club(interaction: discord.Interaction, connection, leader: discord.User):
    table = interaction.guild.id
    event_loop = asyncio.get_running_loop()
    club = await event_loop.run_in_executor(None, db_get_club, connection, table, leader)    
    if club:
        return ClubData(club[0], interaction.guild.get_member(club[1]), club[2], club[3], club[4], await get_club_users(interaction, connection, leader))

def db_get_club_users(connection, table, leader: discord.User):
    cur = connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}users'(user, leader)")
    return cur.execute(f"""
        SELECT * FROM '{table}users' WHERE leader = ?
    """, (leader.id,)).fetchall()
async def get_club_users(interaction: discord.Interaction, connection, leader: discord.User):
    table = interaction.guild.id
    event_loop = asyncio.get_running_loop()
    users = await event_loop.run_in_executor(None, db_get_club_users, connection, table, leader)    
    return [await get_member(interaction, user[0]) for user in users]

def db_get_user_clubs(connection, table, user: discord.User):
    cur = connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}users'(user, leader)")
    return cur.execute(f"""
        SELECT * FROM '{table}users' WHERE user = ?
    """, (user.id,)).fetchall()
async def get_user_clubs(interaction: discord.Interaction,connection, user: discord.User):
    table = interaction.guild.id
    event_loop = asyncio.get_running_loop()
    clubs = await event_loop.run_in_executor(None, db_get_user_clubs, connection, table, user)
    if clubs:
        return [await get_club(interaction, connection, interaction.guild.get_member(club[1])) for club in clubs]

def db_join_club(connection, table, user: discord.User, leader: discord.User):
    cur = connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}users'(user, leader)")
    cur.execute(f"""
        INSERT INTO '{table}users' VALUES
            (?, ?)
        """, (user.id, leader.id))
    connection.commit()
async def join_club(interaction: discord.Interaction, connection, user: discord.User, leader: discord.User):
    club = await get_club(interaction, connection, leader)
    table = interaction.guild.id
    if club:
        if interaction.user in club.users:
            return ClubError.ALREADY_JOINED
        
        event_loop = asyncio.get_running_loop()
        await event_loop.run_in_executor(None, db_join_club, connection, table, user, leader)
        return club

def db_create_club(connection, table, club):
    cur = connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}clubs'(name, leader, description, icon_url, banner_url)")
    cur.execute(f"""
        INSERT INTO '{table}clubs' VALUES
            (?, ?, ?, ?, ?)
        """, (club.name, club.leader.id, club.description, club.icon_url, club.banner_url))
    connection.commit()
async def create_club(interaction: discord.Interaction, connection, leader: discord.User, name: str, desc: str = None, icon_url: str = None, banner_url: str = None):
    owned_club = await get_club(interaction, connection, leader)
    if owned_club:
        return ClubError.ALREADY_OWNED
    
    table = interaction.guild.id
    event_loop = asyncio.get_running_loop()
    club = ClubData(name, leader)
    if desc:
        club.description = desc
    if icon_url:
        club.icon_url = icon_url
    if banner_url:
        club.banner_url = banner_url
    await event_loop.run_in_executor(None, db_create_club, connection, table, club)

    return club

def db_edit_club(connection, table, club):
    cur = connection.cursor()
    cur.execute(f"""
        UPDATE '{table}clubs' SET description = ?, icon_url = ?, banner_url = ? WHERE leader = ?
    """, (club.description, club.icon_url, club.banner_url, club.leader.id,))
    connection.commit()
async def edit_club(interaction: discord.Interaction, connection, leader: discord.User, desc: str = None, icon_url: str = None, banner_url: str = None):
    club = await get_club(interaction, connection, leader)
    if club:
        table = interaction.guild.id
        if desc:
            club.description = desc
        if icon_url:
            club.icon_url = icon_url
        if banner_url:
            club.banner_url = banner_url
        event_loop = asyncio.get_running_loop()
        await event_loop.run_in_executor(None, db_edit_club, connection, table, club)        

    return club

def db_delete_club(connection, table, leader: discord.User):
    cur = connection.cursor()
    cur.execute(f"""
        DELETE FROM '{table}clubs'
        WHERE leader = ?""", (leader.id,))
    cur.execute(f"""
        DELETE FROM '{table}users'
        WHERE leader = ?""", (leader.id,))
    connection.commit()
async def delete_club(interaction: discord.Interaction, connection, leader: discord.User):
    owned_club = await get_club(interaction, connection, leader)
    if not owned_club:
        return None

    table = interaction.guild.id
    event_loop = asyncio.get_running_loop()
    await event_loop.run_in_executor(None, db_delete_club, connection, table, leader)        

    return True

def db_leave_club(connection, table, user: discord.User, leader: discord.User):
    cur = connection.cursor()
    cur.execute(f"""
        DELETE FROM '{table}users'
        WHERE user = ? AND leader = ?""", (user.id,leader.id,))
    connection.commit()
async def leave_club(interaction: discord.Interaction, connection, user: discord.User, leader: discord.User):
    club = await get_club(interaction, connection, leader)
    if club:
        if interaction.user not in club.users:
            return None
        
        table = interaction.guild.id
        event_loop = asyncio.get_running_loop()
        await event_loop.run_in_executor(None, db_leave_club, connection, table, user, leader)

        return True

def db_get_guilds(connection):
    cur = connection.cursor()
    return cur.execute("""SELECT name FROM sqlite_master WHERE type='table'""").fetchall()
async def get_guilds_id(connection):
    event_loop = asyncio.get_running_loop()
    guilds = await event_loop.run_in_executor(None, db_get_guilds, connection)
    return list(set([int(id) for guild in guilds if (id := ''.join(c for c in guild[0] if c.isdigit())) != '']))

class EditClubModal(discord.ui.Modal, title='Edit Club'):
    def __init__(self, connection, club_obj: 'Club', club: ClubData):
        super().__init__()
        self.connection = connection
        self.club_obj = club_obj
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
        club = await edit_club(interaction, self.connection, interaction.user, self.description.value, self.icon_url.value, self.banner_url.value)
        if club:
            return await interaction.response.send_message(view=ClubView(club_obj=self.club_obj, club=club, timeout=None), ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return await interaction.response.send_message("You are not a leader of a club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Something went wrong.', ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)

class CreateClubModal(discord.ui.Modal, title='Create Club'):
    def __init__(self, connection, club_obj: 'Club'):
        super().__init__()
        self.connection = connection
        self.club_obj = club_obj

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
        club = await create_club(interaction, self.connection, interaction.user, self.name.value, self.description.value, self.icon_url.value, self.banner_url.value)
        if club == ClubError.ALREADY_OWNED:
            return await interaction.response.send_message(content="You have already owned a club.")
        await self.club_obj.add_club_to_cache(interaction, club)
        await interaction.response.send_message(view=ClubView(club_obj=self.club_obj, club=club, timeout=None), allowed_mentions=discord.AllowedMentions.none())

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Something went wrong.', ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)

class ClubAnnounceModal(discord.ui.Modal, title='Club Announce'):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection

        self.message = discord.ui.TextInput(
            label='Message',
            style=discord.TextStyle.long,
            placeholder='The quick brown fox jumps over the lazy dog...',
            required=True,
            max_length=1000
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        club = await get_club(interaction, self.connection, interaction.user)
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
    def __init__(self, club_obj: 'Club', club: ClubData, *, style = discord.ButtonStyle.secondary, label = None, disabled = False, custom_id = None, url = None, emoji = None, sku_id = None, id = None):
        self.club_obj = club_obj
        self.club = club
        super().__init__(style=style, label=label, disabled=disabled, custom_id=custom_id, url=url, emoji=emoji, sku_id=sku_id, id=id)

    async def callback(self, interaction):
        await self.club_obj.join_club(interaction, self.club.leader)

class ListClubMemberButton(discord.ui.Button):
    def __init__(self, club: ClubData, *, style = discord.ButtonStyle.secondary, label = None, disabled = False, custom_id = None, url = None, emoji = None, sku_id = None, id = None):
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
    def __init__(self, club_obj: 'Club', club: ClubData, children = ..., *, accent_colour = None, accent_color = None, spoiler = False, id = None):
        super().__init__(accent_colour=accent_colour, accent_color=accent_color, spoiler=spoiler, id=id)
        
        self.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(club.banner_url)))
        self.add_item(discord.ui.Section(accessory=discord.ui.Thumbnail(club.icon_url)).add_item(discord.ui.TextDisplay(f"# {club.name}\n{(lambda s: s or "*No description.*")(club.description)}")))
        self.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        vaild_members = [user for user in club.users if user.name]
        extras = ""
        if len(vaild_members) != len(club.users):
            extras += f"\n-# Unknown Member: {len(club.users) - len(vaild_members)}"
        self.add_item(discord.ui.Section(accessory=ListClubMemberButton(club=club, label="List Member(s)", style=discord.ButtonStyle.primary)).add_item(discord.ui.TextDisplay(f"Member: {len(vaild_members)}" + extras)))
        self.add_item(discord.ui.Section(accessory=JoinClubButton(club_obj=club_obj, club=club, label="Join Club", style=discord.ButtonStyle.success)).add_item(discord.ui.TextDisplay(f"Led By {(lambda s: s.mention if s.name else "*Unknown User*")(club.leader)}")))

class ClubView(discord.ui.LayoutView):
    def __init__(self, club_obj: 'Club', club: ClubData, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.add_item(ClubContainer(club_obj=club_obj, club=club))

class Club(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.club_ping_ctx_menu = app_commands.ContextMenu(
            name='Club Ping',
            callback=self.club_ping,
        )
        self.bot.tree.add_command(self.club_ping_ctx_menu)
        self.clubs_cache = {}

    def check_connection(self):
        try:
            cur = self.bot.club_db.cursor()
            cur.execute("""SELECT 1""")
        except Exception as ex:
            print(f"Reconnecting to Club Database... (Reason: {repr(ex)})")
            self.bot.club_db = self.bot.connect_club_db()
            return self.check_connection()
        return self.bot.club_db
                
    async def get_connection(self):
        self.event_loop = asyncio.get_running_loop()
        return await self.event_loop.run_in_executor(None, self.check_connection)

    async def clubs_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        matches = process.extract(
            current,
            [app_commands.Choice(name=f"{club.name} - {(await get_member(interaction, club.leader)).name}", value=str(club.leader)) for club in self.clubs_cache[interaction.guild.id]],
            scorer=fuzz.ratio,
            processor=lambda c: getattr(c, "name", str(c)),
        )
        return [club for club, score, _ in matches][:5]

    async def remove_club_from_cache(self, interaction: discord.Interaction):
        if self.clubs_cache.get(interaction.guild.id):
            self.clubs_cache[interaction.guild.id] = [club for club in self.clubs_cache[interaction.guild.id] if club.leader != interaction.user.id]

    async def add_club_to_cache(self, interaction: discord.Interaction, club: ClubData):
        if not self.clubs_cache.get(interaction.guild.id):
            self.clubs_cache[interaction.guild.id] = []
        self.clubs_cache[interaction.guild.id].append(ClubDataLight(club.name, club.leader.id, club.description, club.icon_url, club.banner_url))

    async def refresh_clubs_cache(self):
        guilds = await get_guilds_id(await self.get_connection())
        for guild in guilds:
            self.clubs_cache[guild] = await get_guild_clubs_light(await self.get_connection(), guild)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.refresh_clubs_cache()

    group = app_commands.Group(name="club", description="club stuff")

    @group.command(name="create", description="creates your club")
    async def createclub(self, interaction: discord.Interaction):
        club_modal = CreateClubModal(await self.get_connection(), self)
        await interaction.response.send_modal(club_modal)

    @group.command(name="edit", description="edits your club")
    async def editclub(self, interaction: discord.Interaction):
        club = await get_club(interaction, await self.get_connection(), interaction.user)
        if club:
            club_modal = EditClubModal(await self.get_connection(), self, club)
            return await interaction.response.send_modal(club_modal)
        return await interaction.response.send_message("You are not a leader of a club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="disband", description="disband/deletes your club")
    async def disbandclub(self, interaction: discord.Interaction):
        await interaction.response.defer()
        delete = await delete_club(interaction, await self.get_connection(), interaction.user)
        if delete:
            await self.remove_club_from_cache(interaction)
            return await interaction.followup.send("Your club has been successfully disbanded, All of your club members have been kicked out.", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())
        return await interaction.followup.send("You are not a leader of a club.", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="join", description="joins a club")
    @app_commands.autocomplete(search=clubs_autocomplete)
    async def joinclub(self, interaction: discord.Interaction, search: Optional[str], leader: Optional[discord.User]):
        if search:
            leader = await get_member(interaction, int(search))
        elif not leader:
            return await interaction.response.send_message("Please specify an input.", ephemeral=True)
        await self.join_club(interaction, leader)

    async def join_club(self, interaction: discord.Interaction, leader: discord.User):
        await interaction.response.defer(ephemeral=True)
        if interaction.user == leader:
            return await interaction.followup.send(content="You can't join your own club, Duh.", ephemeral=True)
        club = await join_club(interaction, await self.get_connection(), interaction.user, leader)
        if club == ClubError.ALREADY_JOINED:
            return await interaction.followup.send(content=f"You have already joined {leader.mention}'s club.", allowed_mentions=discord.AllowedMentions.none(), ephemeral=True)
        elif club:
            return await interaction.followup.send(f"Joined {leader.mention}'s club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return await interaction.followup.send(f"No club was owned by {leader.mention}", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="leave", description="leaves a club")
    @app_commands.autocomplete(search=clubs_autocomplete)
    async def leaveclub(self, interaction: discord.Interaction, search: Optional[str], leader: Optional[discord.User]):
        if search:
            leader = await get_member(interaction, int(search))
        elif not leader:
            return await interaction.response.send_message("Please specify an input.", ephemeral=True)
        await self.leave_club(interaction, leader)

    async def leave_club(self, interaction: discord.Interaction, leader: discord.User):
        await interaction.response.defer(ephemeral=True)
        club = await leave_club(interaction, await self.get_connection(), interaction.user, leader)
        if club:
            return await interaction.followup.send(f"You have successfully left {leader.mention}'s club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return await interaction.followup.send(f"You didn't join {leader.mention}'s club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="info", description="gets club info")
    @app_commands.autocomplete(search=clubs_autocomplete)
    async def info(self, interaction: discord.Interaction, search: Optional[str], leader: Optional[discord.User]):
        if search:
            leader = await get_member(interaction, int(search))
        elif not leader:
            return await interaction.response.send_message("Please specify an input.", ephemeral=True)
        await interaction.response.defer()
        club = await get_club(interaction, await self.get_connection(), leader)
        if club:
            return await interaction.followup.send(view=ClubView(club_obj=self, club=club, timeout=None), allowed_mentions=discord.AllowedMentions.none())
        return await interaction.followup.send(f"No club was owned by {leader.mention}", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="ping", description="ping club members")
    async def ping(self, interaction: discord.Interaction):
        return await self.club_ping(interaction, message=None)

    @group.command(name="announce", description="announces a club message")
    async def announce(self, interaction: discord.Interaction):
        club_announce_modal = ClubAnnounceModal(await self.get_connection())
        await interaction.response.send_modal(club_announce_modal)

    @group.command(name="joined_list", description="list clubs you have joined")
    async def joined_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        clubs = await get_user_clubs(interaction, await self.get_connection(), interaction.user)
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
        clubs = await get_guild_clubs(interaction, await self.get_connection())
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
        club = await get_club(interaction, await self.get_connection(), interaction.user)
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
    await bot.add_cog(Club(bot))
