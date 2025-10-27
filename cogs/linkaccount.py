import discord
from discord.ext import commands
from discord import app_commands

from aiohttp import ClientSession

from libs.namuvaultmanager.vaultmanager import VaultManager, Vault

class LinkCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = self.bot.config["redirect"]
        self.vault_manager: VaultManager = self.bot.vault_manager

        self.repo = "Deltafall-Community/deltafall-bot"
        self.guild = 1198291214672347308
        self.role = 1432259128742510602

    async def check_contribute(self, github_user_id: int):
        async with ClientSession() as session:
            async with session.get(f"https://api.github.com/repos/{self.repo}/contributors") as resp:
                users = await resp.json()
        
        if github_user_id in [user["id"] for user in users]:
            return True
        return False

    @app_commands.command(name="link", description="link github account")
    @app_commands.allowed_installs(guilds=True, users=False)
    async def link(self, interaction: discord.Interaction):
        if interaction.guild.id != self.guild:
            return await interaction.response.send_message(content="This command is intented to be used in a specific discord server.", ephemeral=True)

        vault: Vault = await self.vault_manager.get(interaction.user.id)
        githubUserID = vault.get("githubUser")
        if githubUserID:
            contributed = await self.check_contribute(githubUserID)

            if contributed:
                has_role = False
                for role in interaction.user.roles:
                    if role.id == self.role:
                        has_role = True
                        break
                if not has_role:
                    await interaction.user.add_roles(interaction.guild.get_role(self.role))
                    
                embed=discord.Embed(title="", description="## Role Successfully Given\nYou now have special access to some channels in the server.", color=discord.Color.green())
                return await interaction.response.send_message(embed=embed)
            
            embed=discord.Embed(title="", description=f"## Erm\nYou stil have not contributed anything to {self.repo}, send patches :3", color=discord.Color.green())
        else:
            embed=discord.Embed(title="", description=f"## Link\nYou can link your discord account & github account at {self.base_url}/account\nand re-run this command to gain special access.", color=discord.Color.green())
        
        await interaction.response.send_message(embed=embed)

            

async def setup(bot):
    await bot.add_cog(LinkCommand(bot))