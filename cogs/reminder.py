import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
from rapidfuzz import fuzz, process
from dataclasses import dataclass

import textwrap
import humanize

from discord.ext.paginators.button_paginator import ButtonPaginator, PaginatorButton

import dateparser
from libs.namuscheduler.scheduler import Scheduler, Payload
from datetime import datetime
import time

paginator_buttons = {
    "FIRST": PaginatorButton(label="", position=0),
    "LEFT": PaginatorButton(label="Back", position=1),
    "PAGE_INDICATOR": PaginatorButton(label="Page N/A / N/A", position=2, disabled=False),
    "RIGHT": PaginatorButton(label="Next", position=3),
    "LAST": PaginatorButton(label="", position=4),
    "STOP": None
}

@dataclass
class Reminder:
    channel_id: int
    author_id: int
    message: Optional[str] = None

@dataclass
class PayloadReminder:
    id: int
    timestamp: datetime
    reminder: Reminder

class ReminderCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduler: Scheduler = self.bot.scheduler
        self.scheduler.subscribe("Reminder", self.on_remind_end)

    async def reminder_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        payloads: List[Payload] = await self.scheduler.get_all_payloads_from_table(interaction.guild.id, Reminder)
        matches = process.extract(
            current,
            [app_commands.Choice(name=f"{rm if (rm := textwrap.shorten(reminder.message, 50)) else "No Message."} - {humanize.naturaltime(datetime.now() - payload.trigger_on)}", value=str(payload.reference.id)) for payload in payloads if (reminder := self.scheduler.decode_payload(payload)).author_id == interaction.user.id],
            scorer=fuzz.ratio,
            processor=lambda c: getattr(c, "name", str(c)),
        )
        return [reminder for reminder, score, _ in matches][:5]

    async def get_user(self, client: discord.Client, id: int):
        # look in the cache first, if user doesn't exist try fetching it.
        user = client.get_user(id)
        if not user:
            try:
                user = await client.fetch_user(id)
            except discord.errors.NotFound:
                pass
        return user
    
    async def get_channel(self, client: discord.Client, id: int):
        # look in the cache first, if channel doesn't exist try fetching it.
        channel = client.get_channel(id)
        if not channel:
            try:
                channel = await client.fetch_channel(id)
            except discord.errors.NotFound:
                pass
        return channel

    async def on_remind_end(self, reminder: Reminder):
        user: discord.User = await self.get_user(self.bot, reminder.author_id)
        source = channel if (channel := await self.get_channel(self.bot, reminder.channel_id)) else user
        if source:
            await source.send(f"{user.mention} Reminder{f": {reminder.message}" if reminder.message else ""}", allowed_mentions=discord.AllowedMentions(users=[user], everyone=False, roles=False))

    group = app_commands.Group(name="remind", description="remind you")

    @group.command(name="create", description="make reminder")
    @app_commands.allowed_installs(guilds=True, users=False)
    async def create_reminder(self, interaction: discord.Interaction, on: str, message: Optional[str]):
        await interaction.response.defer()
        on: datetime = dateparser.parse(on)
        if on.timestamp() < time.time():
            on = datetime.fromtimestamp(time.time()+(time.time()-on.timestamp()))
        reminder = Reminder(interaction.channel.id, interaction.user.id, message)
        await self.scheduler.add_payload(interaction.guild.id, on, reminder)
        await interaction.followup.send(f"Reminder{f": {message} " if message else " "}going off <t:{str(int(on.timestamp()))}:R>.", allowed_mentions=discord.AllowedMentions(users=[interaction.user], everyone=False, roles=False))

    @group.command(name="list", description="lists reminders")
    @app_commands.allowed_installs(guilds=True, users=False)
    async def list_reminder(self, interaction: discord.Interaction):
        await interaction.response.defer()
        reminder_embeds = [discord.Embed(description="## Reminder(s)", color=discord.Color.from_rgb(255,255,255))]
        current_page=0
        for payload in await self.scheduler.get_all_payloads_from_table(interaction.guild.id, Reminder):
            if (reminder := self.scheduler.decode_payload(payload)).author_id == interaction.user.id:
                reminder = PayloadReminder(payload.reference.id, payload.trigger_on, reminder)
                if reminder_embeds[current_page].description.count('\n') > 9:
                    current_page+=1
                if len(reminder_embeds) < current_page+1:
                    reminder_embeds.append(discord.Embed(description="", color=discord.Color.from_rgb(255,255,255)))
                reminder_embeds[current_page].description += f'\n- {f"**`{rm}`**" if (rm := reminder.reminder.message) else "*No Message.*"}\n-# ↳ **<t:{str(int(reminder.timestamp.timestamp()))}:R>** • <#{reminder.reminder.channel_id}> • **ID: `{reminder.id}`**'
        paginator = ButtonPaginator(reminder_embeds, author_id=interaction.user.id, buttons=paginator_buttons)
        return await paginator.send(interaction, override_page_kwargs=True, ephemeral=True)

    @group.command(name="delete", description="deletes reminder")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.autocomplete(search=reminder_autocomplete)
    async def delete_reminder(self, interaction: discord.Interaction, search: Optional[str], id: Optional[int]):
        await interaction.response.defer()
        if search:
            id = int(search)
        elif not id:
            return await interaction.followup.send("Please specify an input.", ephemeral=True)
        for payload in await self.scheduler.get_all_payloads_from_table(interaction.guild.id, Reminder):
            if payload.reference.id == id and self.scheduler.decode_payload(payload).author_id == interaction.user.id:
                await self.scheduler.delete_payload(payload)
                return await interaction.followup.send(f"Deleted Reminder ID {id}.", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())
        return await interaction.followup.send("Invaild Reminder.", ephemeral=False, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):
    await bot.add_cog(ReminderCommand(bot))