import discord
from discord.ext import commands

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_routedef import RouteTableDef
from aiohttp_session import get_session
from jinja2 import Environment, FileSystemLoader

from libs.namuvaultmanager.vaultmanager import VaultManager, Vault

env = Environment(loader=FileSystemLoader('templates'))
account_template = env.get_template('account.html')
donate_template = env.get_template('donate.html')
manage_template = env.get_template('manage.html')
root_template = env.get_template('index.html')

class Web(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.vault_manager: VaultManager = self.bot.vault_manager
        self.app: Application = self.bot.app
        self.routes: RouteTableDef = self.bot.routes

        @self.routes.get("/account")
        async def account(request: web.Request):
            session = await get_session(request)
            id = session.get("id")
            if not id:
                return web.HTTPFound("/login/discord")
            user: discord.User = await self.bot.fetch_user(id)
            userDict = dict((name, getattr(user, name)) for name in dir(user) if not name.startswith('__'))

            properties = userDict

            vault: Vault = await self.vault_manager.get(user.id)
            
            githubUserID = vault.get("githubUser")
            if githubUserID:
                properties |= {"github": githubUserID}

            return web.Response(text=account_template.render(properties), content_type='text/html')

        @self.routes.get("/donate")
        async def donate(request: web.Request):
            return web.Response(text=donate_template.render({}), content_type='text/html')

        @self.routes.get("/manage")
        async def manage(request: web.Request):
            session = await get_session(request)
            id = session.get("id")
            if not id:
                return web.HTTPFound("/login/discord")
            user: discord.User = await self.bot.fetch_user(id)

            properties = {}
            properties["client_id"] = self.bot.user.id
            properties["servers"] = [{"icon": guild.icon.url if guild.icon else None, "id": guild.id, "name": guild.name} for guild in user.mutual_guilds]
            return web.Response(text=manage_template.render(properties), content_type='text/html')

        @self.routes.get("/")
        async def root(request: web.Request):
            session = await get_session(request)
            id = session.get("id")
            properties = {}
            
            if id:
                user: discord.User = await self.bot.fetch_user(id)
                properties = dict((name, getattr(user, name)) for name in dir(user) if not name.startswith('__'))

            return web.Response(text=root_template.render(properties), content_type='text/html')
        
        self.app.add_routes(self.routes)
        self.app.add_routes([web.static('/static', "static")])

async def setup(bot):
    await bot.add_cog(Web(bot))