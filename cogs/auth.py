import discord
from discord.ext import commands

from aiohttp import web, ClientSession
from aiohttp.web_app import Application
from aiohttp.web_routedef import RouteTableDef
from aiohttp_session import get_session

import os
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
# you have to do this or oauthlib will be a bitch about scope comparing
# source: https://stackoverflow.com/a/51643134
from async_oauthlib import OAuth2Session

from libs.namuvaultmanager.vaultmanager import VaultManager, Vault

DISCORD_AUTH_BASE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_BASE_URL = "https://discord.com/api"

GITHUB_AUTH_BASE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE_URL = "https://api.github.com"

SCOPES = ["identify"]

class Auth(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Client = bot

        config: dict = self.bot.config

        self.discord_app_id = config["discord-app-id"]
        self.discord_app_secret = config["discord-app-secret"]
        self.discord_app_redirect = config["discord-app-redirect"]

        self.github_app_id = config["github-app-id"]
        self.github_app_secret = config["github-app-secret"]
        self.github_app_redirect = config["github-app-redirect"]

        self.vault_manager: VaultManager = self.bot.vault_manager

        self.app: Application = self.bot.app
        self.routes: RouteTableDef = self.bot.routes

        @self.routes.get('/login/discord')
        async def discord_login(request: web.Request):
            oauth = OAuth2Session(client_id=self.discord_app_id, redirect_uri=self.discord_app_redirect, scope=SCOPES)
            await oauth.close()
            authorization_url, state = oauth.authorization_url(DISCORD_AUTH_BASE_URL)
            request.app["oauth_state"] = state

            return web.HTTPFound(authorization_url)
        
        @self.routes.get('/login/github')
        async def github_login(request: web.Request):
            oauth = OAuth2Session(client_id=self.github_app_id, redirect_uri=self.github_app_redirect)
            await oauth.close()
            authorization_url, state = oauth.authorization_url(GITHUB_AUTH_BASE_URL)

            return web.HTTPFound(authorization_url)

        @self.routes.get("/oauth2/discord")
        async def discord_oauth2(request: web.Request):
            session = await get_session(request)

            code = request.query.get("code")
            state = request.app.get("oauth_state")

            oauth = OAuth2Session(client_id=self.discord_app_id, redirect_uri=self.discord_app_redirect, state=state, scope=SCOPES)
            token = await oauth.fetch_token(DISCORD_TOKEN_URL, client_secret=self.discord_app_secret, code=code)
            await oauth.close()

            async with ClientSession() as s:
                headers = {"Authorization": f"Bearer {token['access_token']}"}
                async with s.get(f"{DISCORD_API_BASE_URL}/users/@me", headers=headers) as resp:
                    user_info = await resp.json()
                
            id = user_info.get("id")
            session["id"] = id

            return web.HTTPFound("/account")
        
        @self.routes.get("/oauth2/github")
        async def github_oauth2(request: web.Request):
            session = await get_session(request)
            if "id" not in session:
                return web.Response(text="please link your discord account first")

            code = request.query.get("code")

            oauth = OAuth2Session(client_id=self.github_app_id, redirect_uri=self.github_app_redirect)
            token = await oauth.fetch_token(GITHUB_TOKEN_URL, client_secret=self.github_app_secret, code=code)
            await oauth.close()

            async with ClientSession() as s:
                headers = {"Authorization": f"Bearer {token['access_token']}"}
                async with s.get(f"{GITHUB_API_BASE_URL}/user", headers=headers) as resp:
                    user_info = await resp.json()

            vault: Vault = await self.vault_manager.get(session["id"])
            await vault.store("githubUser", user_info["id"])

            return web.HTTPFound("/account")

async def setup(bot):
    await bot.add_cog(Auth(bot))