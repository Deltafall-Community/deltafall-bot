import discord
from discord.ext import commands
from discord import app_commands
from typing import Union

from libs.namuvaultmanager.vaultmanager import VaultManager, Vault
from libs.namusettingmanager.settingmanager import Settings, Entry
from libs.namusettingmanager.discordsettingmanager import DiscordSettingManager

class ToggleButton(discord.ui.Button):
    def __init__(self, button_callback, active: bool, entry: Entry, *, disabled = False, custom_id = None, url = None, emoji = None, sku_id = None, id = None):
        super().__init__(style=None, label=None, disabled=disabled, custom_id=custom_id, url=url, emoji=emoji, sku_id=sku_id, id=id)
        self.active = active
        self.button_callback = button_callback
        self.entry = entry
        self.update_style()

    def update_style(self):
        if self.active:
            self.style = discord.ButtonStyle.success
            self.label = "ON"
        else:
            self.style = discord.ButtonStyle.red
            self.label = "OFF"

    async def callback(self, interaction):
        self.active = not self.active
        self.update_style()
        await self.button_callback(self, interaction)

class SettingPageSelect(discord.ui.Select):
    def __init__(self, select_callback, *, custom_id = discord.utils.MISSING, placeholder = None, min_values = 1, max_values = 1, options = ..., disabled = False, required = True, row = None, id = None):
        super().__init__(custom_id=custom_id, placeholder=placeholder, min_values=min_values, max_values=max_values, options=options, disabled=disabled, required=required, row=row, id=id)
        self.select_callback = select_callback

    async def callback(self, interaction):
        await self.select_callback(self, interaction)

class SettingsContainer(discord.ui.Container):
    def __init__(self, edit_callback, settings: Settings, vault: Vault, author: discord.User, children = ..., *, accent_colour = None, accent_color = None, spoiler = False, id = None):
        super().__init__(accent_colour=accent_colour, accent_color=accent_color, spoiler=spoiler, id=id)
        self.edit_callback = edit_callback
        self.vault = vault
        self.settings = settings
        self.author = author
        self.current_page = 0
        
        self.update()

    def update(self):
        self.clear_items()

        pages=[]
        for idx, page in zip(range(len(self.settings.pages)), self.settings.pages):
            option = discord.SelectOption(label=page.title, value=str(idx), description=page.description, default=True if idx == self.current_page else False)
            pages.append(option)
        
        self.add_item(discord.ui.TextDisplay(f"## {self.settings.title}"))
        self.add_item(discord.ui.ActionRow(SettingPageSelect(placeholder="Page", options=pages, select_callback=self.page_select_callback)))
        self.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        
        for entry in self.settings.pages[self.current_page].entries:
            if entry.options is bool:
                button = ToggleButton(button_callback=self.button_callback, active=self.vault.get(self.settings.pages[self.current_page].name+entry.name, entry.default), entry=entry)
            section = discord.ui.Section(accessory=button).add_item(discord.ui.TextDisplay(f"{entry.title}\n-# {entry.description}"))
            self.add_item(section)

    async def button_callback(self, button: Union[ToggleButton], interaction: discord.Interaction):
        if not interaction.user == self.author:
            return
        button_type = type(button)
        if button_type is ToggleButton:
            await self.vault.store(self.settings.pages[self.current_page].name+button.entry.name, button.active)
        await self.edit_callback(interaction)

    async def page_select_callback(self, select: SettingPageSelect, interaction: discord.Interaction):
        if not interaction.user == self.author:
            return
        self.current_page = int(select.values[0])
        self.update()
        await self.edit_callback(interaction)

class SettingsView(discord.ui.LayoutView):
    def __init__(self, settings: Settings, vault: Vault, author: discord.User, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.author = author
        self.add_item(SettingsContainer(edit_callback=self.edit_callback, settings=settings, vault=vault, author=self.author))

    async def edit_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=self)

class SettingsCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vault_manager: VaultManager = self.bot.vault_manager
        self.setting_manager: DiscordSettingManager = self.bot.setting_manager

    group = app_commands.Group(name="settings", description="settings")

    @group.command(name="user", description="user settings")
    async def info(self, interaction: discord.Interaction):
        vault = await self.vault_manager.get(interaction.user.id)
        await interaction.response.send_message(view=SettingsView(self.setting_manager.get("user"), vault, interaction.user), ephemeral=True)

async def setup(bot):
    club = SettingsCommand(bot)
    await bot.add_cog(club)
