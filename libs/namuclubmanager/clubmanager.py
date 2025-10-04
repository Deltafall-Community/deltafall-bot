import discord
import asyncio
from enum import Enum
from dataclasses import field
from dataclasses import dataclass
import logging
import sys
import sqlitecloud
import sqlite3
from typing import List, Optional

class ClubError(Enum):
    ALREADY_JOINED = 1
    ALREADY_OWNED = 2

@dataclass
class Club:
    name: str
    leader: discord.User
    description: str = None
    icon_url: str = "https://deltafall-community.github.io/resources/deltafall-logo-old.png"
    banner_url: str = "https://deltafall-community.github.io/resources/titieless_splash_screen.png"
    users: List[discord.User] = field(default_factory=list)

@dataclass
class ClubLight:
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

class ClubManager():
    def __init__(self, database: str, is_sqlitecloud: bool = False, logger: Optional[logging.Logger] = None):
        self.logger = logger
        if not logger:
            self.logger: logging.Logger = logging.getLogger('')
            self.logger.setLevel(logging.INFO)
            self.logger.addHandler(logging.StreamHandler(sys.stdout))

        self.is_sqlitecloud = is_sqlitecloud
        self.db_connect_str=database
        self.db=self.connect_db()

        self.event_loop = asyncio.get_running_loop()

    def connect_db(self):
        try:
            if self.is_sqlitecloud:
                return sqlitecloud.connect(self.db_connect_str)
            else:
                return sqlite3.connect(self.db_connect_str, check_same_thread=False)
        except Exception as e:
            self.logger.error(f"Failed to connect to Club Database.. (Reason: {e})") 

    def check_connection(self):
        try:
            cur = self.db.cursor()
            cur.execute("""SELECT 1""")
        except Exception as ex:
            self.logger.info(f"Reconnecting to Club Database... (Reason: {repr(ex)})")
            self.db = self.connect_db()
            return self.check_connection()
        return self.db
                
    async def get_connection(self):
        return await self.event_loop.run_in_executor(None, self.check_connection)

    async def get_member(self, interaction: discord.Interaction, id: int):
        # look in the cache first, if member doesn't exist try fetching it.
        member=interaction.guild.get_member(id)
        if not member:
            member = await interaction.client.fetch_user(id)
        if not member:
            return DummyUser(id, None, "0001")
        return member

    async def populate_club(self, interaction: discord.Interaction, club: tuple):
        leader = await self.get_member(interaction, club[1])
        return Club(club[0], leader, club[2], club[3], club[4], await self.get_club_users(interaction, leader))

    def db_get_table_clubs(self, connection, table):
        cur = connection.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}clubs'(name, leader, description, icon_url, banner_url)")
        return cur.execute(f"""
            SELECT * FROM '{table}clubs'
        """).fetchall()
    async def get_guild_clubs(self, interaction: discord.Interaction):
        connection = await self.get_connection()
        table = interaction.guild.id
        clubs = await self.event_loop.run_in_executor(None, self.db_get_table_clubs, connection, table)    
        return [await self.populate_club(interaction, club) for club in clubs]
    async def get_guild_clubs_light(self, id: int):
        clubs = await self.event_loop.run_in_executor(None, self.db_get_table_clubs, await self.get_connection(), id)    
        return [ClubLight(club[0], club[1], club[2], club[3], club[4]) for club in clubs]

    def db_get_club(self, connection, table, leader: discord.User):
        cur = connection.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}clubs'(name, leader, description, icon_url, banner_url)")
        return cur.execute(f"""
            SELECT * FROM '{table}clubs' WHERE leader = ?
        """, (leader.id,)).fetchone()
    async def get_club(self, interaction: discord.Interaction, leader: discord.User):
        connection = await self.get_connection()
        table = interaction.guild.id
        club = await self.event_loop.run_in_executor(None, self.db_get_club, connection, table, leader)    
        if club:
            return Club(club[0], interaction.guild.get_member(club[1]), club[2], club[3], club[4], await self.get_club_users(interaction, leader))

    def db_get_club_users(self, connection, table, leader: discord.User):
        cur = connection.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}users'(user, leader)")
        return cur.execute(f"""
            SELECT * FROM '{table}users' WHERE leader = ?
        """, (leader.id,)).fetchall()
    async def get_club_users(self, interaction: discord.Interaction, leader: discord.User):
        table = interaction.guild.id
        users = await self.event_loop.run_in_executor(None, self.db_get_club_users, await self.get_connection(), table, leader)    
        return [await self.get_member(interaction, user[0]) for user in users]

    def db_get_user_clubs(self, connection, table, user: discord.User):
        cur = connection.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}users'(user, leader)")
        return cur.execute(f"""
            SELECT * FROM '{table}users' WHERE user = ?
        """, (user.id,)).fetchall()
    async def get_user_clubs(self, interaction: discord.Interaction, user: discord.User):
        table = interaction.guild.id
        clubs = await self.event_loop.run_in_executor(None, self.db_get_user_clubs, await self.get_connection(), table, user)
        if clubs:
            return [await self.get_club(interaction, interaction.guild.get_member(club[1])) for club in clubs]

    def db_join_club(self, connection, table, user: discord.User, leader: discord.User):
        cur = connection.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}users'(user, leader)")
        cur.execute(f"""
            INSERT INTO '{table}users' VALUES
                (?, ?)
            """, (user.id, leader.id))
        connection.commit()
    async def join_club(self, interaction: discord.Interaction, user: discord.User, leader: discord.User):
        club = await self.get_club(interaction, leader)
        table = interaction.guild.id
        if club:
            if interaction.user in club.users:
                return ClubError.ALREADY_JOINED

            await self.event_loop.run_in_executor(None, self.db_join_club, await self.get_connection(), table, user, leader)
            return club

    def db_create_club(self, connection, table, club):
        cur = connection.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}clubs'(name, leader, description, icon_url, banner_url)")
        cur.execute(f"""
            INSERT INTO '{table}clubs' VALUES
                (?, ?, ?, ?, ?)
            """, (club.name, club.leader.id, club.description, club.icon_url, club.banner_url))
        connection.commit()
    async def create_club(self, interaction: discord.Interaction, leader: discord.User, name: str, desc: str = None, icon_url: str = None, banner_url: str = None):
        owned_club = await self.get_club(interaction, leader)
        if owned_club:
            return ClubError.ALREADY_OWNED

        table = interaction.guild.id
        club = Club(name, leader)
        if desc:
            club.description = desc
        if icon_url:
            club.icon_url = icon_url
        if banner_url:
            club.banner_url = banner_url
        await self.event_loop.run_in_executor(None, self.db_create_club, await self.get_connection(), table, club)

        return club

    def db_edit_club(self, connection, table, club):
        cur = connection.cursor()
        cur.execute(f"""
            UPDATE '{table}clubs' SET description = ?, icon_url = ?, banner_url = ? WHERE leader = ?
        """, (club.description, club.icon_url, club.banner_url, club.leader.id,))
        connection.commit()
    async def edit_club(self, interaction: discord.Interaction, leader: discord.User, desc: str = None, icon_url: str = None, banner_url: str = None):
        club = await self.get_club(interaction, leader)
        if club:
            table = interaction.guild.id
            if desc:
                club.description = desc
            if icon_url:
                club.icon_url = icon_url
            if banner_url:
                club.banner_url = banner_url
            await self.event_loop.run_in_executor(None, self.db_edit_club, await self.get_connection(), table, club)        

        return club

    def db_delete_club(self, connection, table, leader: discord.User):
        cur = connection.cursor()
        cur.execute(f"""
            DELETE FROM '{table}clubs'
            WHERE leader = ?""", (leader.id,))
        cur.execute(f"""
            DELETE FROM '{table}users'
            WHERE leader = ?""", (leader.id,))
        connection.commit()
    async def delete_club(self, interaction: discord.Interaction, leader: discord.User):
        owned_club = await self.get_club(interaction, leader)
        if not owned_club:
            return None

        table = interaction.guild.id
        await self.event_loop.run_in_executor(None, self.db_delete_club, await self.get_connection(), table, leader)        

        return True

    def db_leave_club(self, connection, table, user: discord.User, leader: discord.User):
        cur = connection.cursor()
        cur.execute(f"""
            DELETE FROM '{table}users'
            WHERE user = ? AND leader = ?""", (user.id,leader.id,))
        connection.commit()
    async def leave_club(self, interaction: discord.Interaction, user: discord.User, leader: discord.User):
        club = await self.get_club(interaction, leader)
        if club:
            if interaction.user not in club.users:
                return None

            table = interaction.guild.id
            await self.event_loop.run_in_executor(None, self.db_leave_club, await self.get_connection(), table, user, leader)

            return True

    def db_get_guilds(self, connection):
        cur = connection.cursor()
        return cur.execute("""SELECT name FROM sqlite_master WHERE type='table'""").fetchall()
    async def get_guilds_id(self):
        guilds = await self.event_loop.run_in_executor(None, self.db_get_guilds, await self.get_connection())
        return list(set([int(id) for guild in guilds if (id := ''.join(c for c in guild[0] if c.isdigit())) != '']))
