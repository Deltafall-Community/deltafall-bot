import discord
from discord.ext import commands
from discord import app_commands
from typing import Union, Optional, List, Any 

from libs.namuvaultmanager.vaultmanager import VaultManager, Vault
from libs.namusettingmanager.settingmanager import Settings, Entry, Option
from libs.namusettingmanager.discordsettingmanager import DiscordSettingManager

class ToggleButton(discord.ui.Button):
    def __init__(self, store_callback, active: bool, entry: Entry, *, disabled = False, custom_id = None, url = None, emoji = None, sku_id = None, id = None):
        super().__init__(style=None, label=None, disabled=disabled, custom_id=custom_id, url=url, emoji=emoji, sku_id=sku_id, id=id)
        self.active = active
        self.store_callback = store_callback
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
        if (mp := DiscordSettingManager.is_missing_permission(self.entry, interaction.user)):
            await interaction.response.send_message(f"You don't have the following permission(s):\n{', '.join(["`"+p+"`" for p in mp])}", ephemeral=self.ephemeral)
        else:
            self.active = not self.active
            self.update_style()
            await self.store_callback(self, interaction)

class MultiOptionSelectRespond():
    def __init__(self, select: discord.ui.Select, selected: Any, entry: Entry, mob: 'MultiOptionButton'):
        self.mob = mob
        self.entry = entry
        self.options: List[Option] = entry.options

        self.single = False
        if self.options[0].name in ("channelselect",):
            self.single = True

        self.view = discord.ui.LayoutView()
        self.select = select
        self.selected = selected

        self.update_view()

    def update_view(self):
        self.view.clear_items()
        if self.single:
            self.big_view()

    def big_view(self):
        container = discord.ui.Container()
        save_button = discord.ui.Button(style=discord.ButtonStyle.success, label="Save")
        save_button.callback = self.submit
        container.add_item(discord.ui.Section(accessory=save_button).add_item(discord.ui.TextDisplay(f"{self.options[0].title}\n-# {self.options[0].description}")))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(discord.ui.ActionRow(self.select))

        self.view.add_item(container)

    async def respond(self, interaction: discord.Interaction, ephemeral: bool):
        await interaction.response.send_message(view=self.view, ephemeral=ephemeral)

    async def submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.delete_original_response()
        await self.mob.store(interaction)

    async def select_option(self, select: discord.ui.Select, interaction: discord.Interaction):
        self.selected = select.values
        await interaction.response.defer()

class MultiOptionButton(discord.ui.Button):
    def __init__(self, edit_callback, store_callback, select: discord.ui.Select, selected: Any, entry: Entry, ephemeral=True, *, disabled = False, custom_id = None, url = None, sku_id = None, id = None):
        super().__init__(style=discord.ButtonStyle.primary, label="Config", disabled=disabled, custom_id=custom_id, url=url, emoji="⚙️", sku_id=sku_id, id=id)
        self.entry = entry
        self.mosr = MultiOptionSelectRespond(select, selected, entry, self)
        self.edit_callback = edit_callback
        self.store_callback = store_callback
        self.ephemeral = ephemeral

    async def callback(self, interaction: discord.Interaction):
        if (mp := DiscordSettingManager.is_missing_permission(self.entry, interaction.user)):
            await interaction.response.send_message(f"You don't have the following permission(s):\n{', '.join(["`"+p+"`" for p in mp])}", ephemeral=self.ephemeral)
        else:
            await self.mosr.respond(interaction, self.ephemeral)

    async def store(self, interaction: discord.Interaction):
        await self.store_callback(self, interaction, True)

class SettingsContainer(discord.ui.Container):
    def __init__(self, interaction: discord.Interaction, edit_callback, settings: Settings, vault: Vault, author: discord.User, ephemeral=True, children = ..., *, accent_colour = None, accent_color = None, spoiler = False, id = None):
        super().__init__(accent_colour=accent_colour, accent_color=accent_color, spoiler=spoiler, id=id)
        self.interaction = interaction
        self.edit_callback = edit_callback
        self.vault = vault
        self.settings = settings
        self.author = author
        self.ephemeral = ephemeral
        self.current_page = 0
        
        self.update()

    def update(self):
        self.clear_items()

        pages=[]
        for idx, page in zip(range(len(self.settings.pages)), self.settings.pages):
            option = discord.SelectOption(label=page.title, value=str(idx), description=page.description, default=True if idx == self.current_page else False)
            pages.append(option)
        
        self.add_item(discord.ui.TextDisplay(f"## {self.settings.title}"))
        page_select = discord.ui.Select(placeholder="Page", options=pages)
        page_select.callback = lambda interaciton: self.page_select_callback(page_select, interaciton)
        self.add_item(discord.ui.ActionRow(page_select))
        self.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        
        for entry in self.settings.pages[self.current_page].entries:
            if entry.options is bool:
                button = ToggleButton(store_callback=self.store_callback, active=self.vault.get(self.settings.pages[self.current_page].name+entry.name, entry.default), entry=entry)
            if type(entry.options) is list:
                for option in entry.options:
                    match option.name:
                        case "channelselect":
                            selected, max_value = self.get_selected(entry)
                            select = discord.ui.ChannelSelect(placeholder="Select Channel...", channel_types=[getattr(discord.ChannelType, e) for e in option.extras], min_values=0, max_values=max_value, default_values=selected[:max_value])
                            button = MultiOptionButton(edit_callback=self.edit_callback, store_callback=self.store_callback, select=select, selected=selected, entry=entry, ephemeral=self.ephemeral)
                            select.callback = lambda interaction: button.mosr.select_option(select, interaction)
                            break

            section = discord.ui.Section(accessory=button).add_item(discord.ui.TextDisplay(f"{entry.title}\n-# {entry.description}"))
            self.add_item(section)

    def get_selected(self, entry: Entry):
        selected = self.vault.get(self.settings.pages[self.current_page].name+entry.name, entry.default)
        if type(selected) is not list:
            selected = [e] if (e := selected) is not None else []
        selected = [sg for s in selected if (sg := self.interaction.guild.get_channel(s)) is not None]
        max_value = 25 if type(entry.default) is list else 1
        
        return (selected, max_value)

    async def store_callback(self, button: Union[ToggleButton], interaction, edit_og: bool = False):
        if not interaction.user == self.author:
            return
        button_type = type(button)
        if button_type is ToggleButton:
            await self.vault.store(self.settings.pages[self.current_page].name+button.entry.name, button.active)
        elif button_type is MultiOptionButton:
            match button.entry.options[0].name:
                case "channelselect":
                    selected = [s.id for s in button.mosr.selected]
                    if type(button.entry.default) is not list:
                        selected = selected[0]
                    await self.vault.store(self.settings.pages[self.current_page].name+button.entry.name, selected)

        if edit_og:
            interaction = None

        self.update()
        await self.edit_callback(interaction)

    async def page_select_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        if not interaction.user == self.author:
            return
        self.current_page = int(select.values[0])
        self.update()
        await self.edit_callback(interaction)

class SettingsView(discord.ui.LayoutView):
    def __init__(self, interaction: discord.Interaction, settings: Settings, vault: Vault, author: discord.User, ephemeral=True, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.author = author
        self.interaction = interaction
        self.add_item(SettingsContainer(interaction=interaction, edit_callback=self.edit_callback, settings=settings, vault=vault, author=self.author, ephemeral=ephemeral))

    async def edit_callback(self, interaction: Optional[discord.Interaction] = None):
        if interaction:
            await interaction.response.edit_message(view=self)
        else:
            await self.interaction.edit_original_response(view=self)

class SettingsCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vault_manager: VaultManager = self.bot.vault_manager
        self.setting_manager: DiscordSettingManager = self.bot.setting_manager
        self.group.allowed_installs = discord.app_commands.AppInstallationType(guild=True, user=False)

    group = app_commands.Group(name="settings", description="settings")

    @group.command(name="user", description="user settings")
    async def user(self, interaction: discord.Interaction):
        vault = await self.vault_manager.get(interaction.user.id)
        await interaction.response.send_message(view=SettingsView(interaction, self.setting_manager.get("user"), vault, interaction.user), ephemeral=True)

    @group.command(name="server", description="server settings")
    async def server(self, interaction: discord.Interaction):
        vault = await self.vault_manager.get(interaction.guild.id)
        await interaction.response.send_message(view=SettingsView(interaction, self.setting_manager.get("server"), vault, interaction.user), ephemeral=True)

async def setup(bot):
    await bot.add_cog(SettingsCommand(bot))
