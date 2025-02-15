import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import json
import re

class ClubData(object):
    def __init__(self, json_string):
        if not json_string:
            self.data = {
                "name": None,
                "icon": "https://deltafall-community.github.io/resources/deltafall-logo-old.png",
                "point": 0
            }
        else: self.data = json.loads(json_string)
        
        self.name = self.data["name"] 
        self.icon_url = self.data["icon"]
        self.point = self.data["point"]
    
    def get_json_string(self):
        json.dumps(self.data, separators=(',', ':'))

class Club(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot

    async def get_quote_id(self, table, id):
        connection = self.bot.quote_db
        cur = connection.cursor()
        quote = cur.execute(f"""
            SELECT *, ROWID FROM '{table}' WHERE ROWID = {id}
        """) 
        return quote.fetchone()

    async def get_random_quote_db(self, table):
        connection = self.bot.quote_db
        cur = connection.cursor()
        quote = cur.execute(f"""
            SELECT *, ROWID FROM '{table}' ORDER BY RANDOM() LIMIT 1
        """)
        return quote.fetchone()

    async def create_club(self, table, author, name):
        connection = self.bot.quote_db
        cur = connection.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}'(author, club-data)")
        clubdata = ClubData(None)
        clubdata.name = name
        cur.execute(f"""
            INSERT INTO '{table}' VALUES
                (?, ?)
            """, (author, clubdata.get_json_string()))
        connection.commit()
        return cur.lastrowid

    async def delete_quote_db(self, table, id):
        connection = self.bot.quote_db
        cur = connection.cursor()
        cur.execute(f"""
            DELETE FROM '{table}'
            WHERE ROWID = ?
            """, (id,))
        connection.commit()

    @app_commands.command(name="create", description="creates a club")
    async def createclub(self, interaction: discord.Interaction, name: str, icon: Optional[str]):
        self.create_club(self, interaction.guild.id, interaction.message.author.id, name)
        if id:
            data = await self.get_quote_id(table=interaction.guild.id, id=id)
        else:
            data = await self.get_random_quote_db(table=interaction.guild.id)
        author = data[0]
        quote = data[1]
        await interaction.response.send_message(f'{quote}\n### `- {author} | id: {data[-1]}`', allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="join", description="joins a club")
    async def addquote(self, interaction: discord.Interaction, quote: str, by: str):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("u dont have manage message permission",ephemeral=True)
        else:
            await self.add_quote_db(table=interaction.guild.id, author=by, quote=quote)
            await interaction.response.send_message(f"added {quote} by {by}")

async def setup(bot):
    await bot.add_cog(randomquote(bot))
