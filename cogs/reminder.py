import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from dataclasses import dataclass

from discord.ext.paginators.button_paginator import ButtonPaginator, PaginatorButton

import dateparser
from libs.namuscheduler.scheduler import Scheduler
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
class TimestampedReminder:
    timestamp: datetime
    reminder: Reminder

class ReminderCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduler: Scheduler = self.bot.scheduler
        self.scheduler.subscribe("Reminder", self.on_remind_end)

    async def on_remind_end(self, reminder: Reminder):
        bot: discord.Client = self.bot
        allowed_mentions = discord.AllowedMentions()
        allowed_mentions.everyone=False
        await bot.get_channel(reminder.channel_id).send(f"{bot.get_user(reminder.author_id).mention} Reminder{": `"+reminder.message+"`" if reminder.message is not None else ""}", allowed_mentions=allowed_mentions)

    group = app_commands.Group(name="remind", description="remind you")

    @group.command(name="create", description="make reminder")
    async def create_reminder(self, interaction: discord.Interaction, on: str, message: Optional[str]):
        await interaction.response.defer()
        on: datetime = dateparser.parse(on)
        if on.timestamp() < time.time():
            on = datetime.fromtimestamp(time.time()+(time.time()-on.timestamp()))
        reminder = Reminder(interaction.channel.id, interaction.user.id, message)
        await self.scheduler.add_payload(interaction.guild.id, on, reminder)
        await interaction.followup.send(f"Reminder{": `"+message+"` " if message is not None else " "}going off <t:{str(int(on.timestamp()))}:R>.")

    @group.command(name="list", description="lists reminders")
    async def list_reminder(self, interaction: discord.Interaction):
        await interaction.response.defer()
        reminder_embeds = [discord.Embed(description="## Reminder(s)", color=discord.Color.from_rgb(255,255,255))]
        current_page=0
        for payload in await self.scheduler.get_all_payloads_from_table(interaction.guild.id, Reminder):
            if (reminder := self.scheduler.decode_payload(payload)).author_id == interaction.user.id:
                reminder = TimestampedReminder(payload.trigger_on, reminder)
                if reminder_embeds[current_page].description.count('\n') > 9:
                    current_page+=1
                if len(reminder_embeds) < current_page+1:
                    reminder_embeds.append(discord.Embed(description="", color=discord.Color.from_rgb(255,255,255)))
                reminder_embeds[current_page].description += f'\n- **`{reminder.reminder.message}`** <t:{str(int(reminder.timestamp.timestamp()))}:R>\n'
        paginator = ButtonPaginator(reminder_embeds, author_id=interaction.user.id, buttons=paginator_buttons)
        return await paginator.send(interaction, override_page_kwargs=True, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ReminderCommand(bot))