import discord
from typing import Tuple

from libs.namusettingmanager.settingmanager import SettingManager, Entry
from libs.namuvaultmanager.vaultmanager import VaultManager

class DiscordSettingManager(SettingManager):
    def __init__(self, path, vault_manager: VaultManager):
        super().__init__(path)
        self.vault_manager = vault_manager
        
    @staticmethod
    def is_missing_permission(entry: Entry, member: discord.Member):
        missing_perms = []
        for perm in entry.permissions:
            if not getattr(member.guild_permissions, perm):
                missing_perms.append(perm)
        return missing_perms

    async def get_user_setting(self, user: discord.User, entry: Tuple[str]):
        vault = await self.vault_manager.get(user.id)
        settings = self.get("user")
        for page in settings.pages:
            if page.name == entry[0]:
                for e in page.entries:
                    if e.name == entry[1]:
                        return vault.get(entry[0]+entry[1], e.default)
                    
    async def get_guild_setting(self, guild: discord.Guild, entry: Tuple[str]):
        vault = await self.vault_manager.get(guild.id)
        settings = self.get("server")
        for page in settings.pages:
            if page.name == entry[0]:
                for e in page.entries:
                    if e.name == entry[1]:
                        return vault.get(entry[0]+entry[1], e.default)
