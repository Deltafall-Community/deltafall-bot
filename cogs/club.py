from typing import Optional
from enum import Enum
from dataclasses import field
from dataclasses import dataclass
from typing import List
import traceback
import asyncio

import discord
from discord.ext import commands
from discord import app_commands
from discord import Embed

class ClubError(Enum):
    ALREADY_JOINED = 1
    ALREADY_OWNED = 2

@dataclass
class ClubData:
    name: str
    leader: discord.User
    description: str = None
    icon_url: str = "https://deltafall-community.github.io/resources/deltafall-logo-old.png"
    banner_url: str = "https://deltafall-community.github.io/resources/titieless_splash_screen.png"
    users: List[discord.User] = field(default_factory=list)

async def create_club_embed(club: ClubData):
    club_desc = lambda s: s or "*-# No description.*"
    embed = Embed(color=discord.Color.from_rgb(255, 255, 255), description=f'## {club.name}\n-# Led by {club.leader.mention}\n{club_desc(club.description)}\n')
    embed.add_field(name="Member count:", value=len(club.users), inline=True)
    embed.add_field(name="Join:", value=f"`/club join leader:@{club.leader.name}`", inline=True)
    embed.set_thumbnail(url=club.icon_url)
    embed.set_image(url=club.banner_url)
    return embed

def db_get_club(connection, table, leader: discord.User):
    cur = connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}clubs'(name, leader, description, icon_url, banner_url)")
    return cur.execute(f"""
        SELECT *, leader FROM '{table}clubs' WHERE leader = ?
    """, (leader.id,)).fetchone()
async def get_club(interaction: discord.Interaction, connection, leader: discord.User):
    table = interaction.guild.id
    event_loop = asyncio.get_event_loop()
    club = await event_loop.run_in_executor(None, db_get_club, connection, table, leader)    
    if club: return ClubData(club[0], interaction.guild.get_member(club[1]), club[2], club[3], club[4], await get_club_users(interaction, connection, leader))

def db_get_club_users(connection, table, leader: discord.User):
    cur = connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}users'(user, leader)")
    return cur.execute(f"""
        SELECT *, leader FROM '{table}users' WHERE leader = ?
    """, (leader.id,)).fetchall()
async def get_club_users(interaction: discord.Interaction, connection, leader: discord.User):
    table = interaction.guild.id
    discord_users = []
    event_loop = asyncio.get_event_loop()
    users = await event_loop.run_in_executor(None, db_get_club_users, connection, table, leader)    
    for user in users: discord_users.append(interaction.guild.get_member(user[0]))
    return discord_users

def db_get_user_club(connection, table, user: discord.User):
    cur = connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}users'(user, leader)")
    return cur.execute(f"""
        SELECT *, user FROM '{table}users' WHERE user = ?
    """, (user.id,)).fetchone()
async def get_user_club(interaction: discord.Interaction,connection, user: discord.User):
    table = interaction.guild.id
    event_loop = asyncio.get_event_loop()
    club = await event_loop.run_in_executor(None, db_get_club_users, connection, table, user)
    if club: return await get_club(interaction, connection, interaction.guild.get_member(club[1]))

def db_join_club(connection, table, user: discord.User, leader: discord.User):
    cur = connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}users'(user, leader)")
    cur.execute(f"""
        INSERT INTO '{table}users' VALUES
            (?, ?)
        """, (user.id, leader.id))
    connection.commit()
async def join_club(interaction: discord.Interaction, connection, user: discord.User, leader: discord.User):
    joined_club = await get_user_club(interaction, connection, user)
    
    if joined_club: return ClubError.ALREADY_JOINED

    club = await get_club(interaction, connection, leader)
    table = interaction.guild.id
    if club:
        event_loop = asyncio.get_event_loop()
        return await event_loop.run_in_executor(None, db_join_club, connection, table, user, leader)

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
    if owned_club: return ClubError.ALREADY_OWNED
    
    table = interaction.guild.id
    event_loop = asyncio.get_event_loop()
    club = ClubData(name, leader)
    if desc: club.description = desc
    if icon_url: club.icon_url = icon_url
    if banner_url: club.banner_url = banner_url
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
        if desc: club.description = desc
        if icon_url: club.icon_url = icon_url
        if banner_url: club.banner_url = banner_url
        event_loop = asyncio.get_event_loop()
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
    if not owned_club: return None

    table = interaction.guild.id
    event_loop = asyncio.get_event_loop()
    await event_loop.run_in_executor(None, db_delete_club, connection, table, leader)        

    return True

def db_leave_club(connection, table, user: discord.User):
    cur = connection.cursor()
    cur.execute(f"""
        DELETE FROM '{table}users'
        WHERE user = ?""", (user.id,))
    connection.commit()
async def leave_club(interaction: discord.Interaction, connection, user: discord.User):
    joined_club = await get_user_club(interaction, connection, user)
    if not joined_club: return None

    table = interaction.guild.id
    event_loop = asyncio.get_event_loop()
    await event_loop.run_in_executor(None, db_leave_club, connection, table, user)

    return True

class EditClubModal(discord.ui.Modal, title='Edit Club'):
    description = discord.ui.TextInput(
        label='Description',
        style=discord.TextStyle.long,
        placeholder='The club description...',
        required=False,
        max_length=300,
    )

    icon_url = discord.ui.TextInput(
        label='Icon',
        placeholder='Enter the URL for the icon image... (e.g. https://i.imgur.com/0bXMnbm.jpeg)',
        required=False,
    )
    banner_url = discord.ui.TextInput(
        label='Banner',
        placeholder='Enter the URL for the banner image... (e.g. https://i.imgur.com/2VzYLjT.png)',
        required=False,
    )

    def __init__(self, connection):
        super().__init__()
        self.connection = connection

    async def on_submit(self, interaction: discord.Interaction):
        club = await edit_club(interaction, self.connection, interaction.user, self.description.value, self.icon_url.value, self.banner_url.value)
        if club: return await interaction.response.send_message(embed=await create_club_embed(club))
        return await interaction.response.send_message(f"You are not a leader of a club.", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Something went wrong.', ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)

class CreateClubModal(discord.ui.Modal, title='Create Club'):
    name = discord.ui.TextInput(
        label='Name',
        placeholder='Enter club name...',
        max_length=100
    )

    description = discord.ui.TextInput(
        label='Description',
        style=discord.TextStyle.long,
        placeholder='The club description...',
        required=False,
        max_length=300
    )

    icon_url = discord.ui.TextInput(
        label='Icon',
        placeholder='Enter the URL for the icon image... (e.g. https://i.imgur.com/0bXMnbm.jpeg)',
        required=False
    )
    banner_url = discord.ui.TextInput(
        label='Banner',
        placeholder='Enter the URL for the banner image... (e.g. https://i.imgur.com/2VzYLjT.png)',
        required=False
    )

    def __init__(self, connection):
        super().__init__()
        self.connection = connection

    async def on_submit(self, interaction: discord.Interaction):
        club = await create_club(interaction, self.connection, interaction.user, self.name.value, self.description.value, self.icon_url.value, self.banner_url.value)
        if club == ClubError.ALREADY_OWNED: return await interaction.response.send_message(content="You have already owned a club.")
        await interaction.response.send_message(embed=await create_club_embed(club))

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Something went wrong.', ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)

class club(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.club_ping_ctx_menu = app_commands.ContextMenu(
            name='Club Ping',
            callback=self.club_ping,
        )
        self.bot.tree.add_command(self.club_ping_ctx_menu)

    def check_connection(self):
        try:
            cur = self.bot.club_db.cursor()
            cur.execute("""SELECT 1""")
        except Exception as ex:
            print("Reconnecting to club_db...")
            self.bot.club_db = self.bot.connect_club_db()
            return self.check_connection()
        return self.bot.club_db
                
    async def get_connection(self):
        self.event_loop = asyncio.get_event_loop()
        return await self.event_loop.run_in_executor(None, self.check_connection)

    group = app_commands.Group(name="club", description="club stuff")

    @group.command(name="create", description="creates your club")
    async def createclub(self, interaction: discord.Interaction):
        club_modal = CreateClubModal(await self.get_connection())
        await interaction.response.send_modal(club_modal)

    @group.command(name="edit", description="edits your club")
    async def editclub(self, interaction: discord.Interaction):
        club_modal = EditClubModal(await self.get_connection())
        await interaction.response.send_modal(club_modal)

    @group.command(name="disband", description="disband/deletes your club")
    async def disbandclub(self, interaction: discord.Interaction):
        await interaction.response.defer()
        delete = await delete_club(interaction, await self.get_connection(), interaction.user)
        if delete: return await interaction.followup.send(f"Your club has been successfully disbanded, All of your club members are now kicked out.", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())
        return await interaction.followup.send(f"You are not a leader of a club.", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="join", description="joins a club")
    async def joinclub(self, interaction: discord.Interaction, leader: discord.User):
        await interaction.response.defer()
        club = await join_club(interaction, await self.get_connection(), interaction.user, leader)
        if club == ClubError.ALREADY_JOINED: return await interaction.followup.send(content="You have already joined a club.")
        elif club: return await interaction.followup.send(f"Joined club lead by {leader.mention}", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())
        return await interaction.followup.send(f"No club was owned by {leader.mention}", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="leave", description="leaves a club")
    async def leaveclub(self, interaction: discord.Interaction):
        await interaction.response.defer()
        club = await leave_club(interaction, await self.get_connection(), interaction.user)
        if club: return await interaction.followup.send(f"You have successfully left your club.", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())
        return await interaction.followup.send(f"You didn't join any club.", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="info", description="gets club info")
    async def info(self, interaction: discord.Interaction, leader: discord.User):
        await interaction.response.defer()
        club = await get_club(interaction, await self.get_connection(), leader)
        if club: return await interaction.followup.send(embed=await create_club_embed(club), ephemeral=False)
        return await interaction.followup.send(f"No club was owned by {leader.mention}", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())

    @group.command(name="ping", description="ping club members")
    async def ping(self, interaction: discord.Interaction):
        return await self.club_ping(interaction, message=None)

    async def club_ping(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        club = await get_club(interaction, await self.get_connection(), interaction.user)
        if club:
            ping_str = f"{club.name} Club Ping:\n"
            for user in club.users: ping_str += user.mention
            if not message: await interaction.channel.send(ping_str)
            else: await message.reply(ping_str)
            return await interaction.followup.send("Sent Club Ping.", ephemeral=False)
        return await interaction.followup.send(f"You are not a leader of a club.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):
    await bot.add_cog(club(bot))
