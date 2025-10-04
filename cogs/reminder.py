import discord
from discord.ext import commands
from discord import app_commands
import dateparser
from dataclasses import dataclass
from typing import Optional

from libs.namuschedule.schedule import Schedule
from datetime import datetime
import time

@dataclass
class Reminder:
    channel_id: int
    author_id: int
    message: Optional[str]

class reminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduler: Schedule = self.bot.scheduler
        self.scheduler.subscribe("Reminder", self.on_remind_end)

    async def on_remind_end(self, reminder: Reminder):
        bot: discord.Client = self.bot
        allowed_mentions = discord.AllowedMentions()
        allowed_mentions.everyone=False
        await bot.get_channel(reminder.channel_id).send(f"{bot.get_user(reminder.author_id).mention} Reminder{": `"+reminder.message+"`" if reminder.message is not None else ""}", allowed_mentions=allowed_mentions)

    group = app_commands.Group(name="remind", description="remind you")

    @group.command(name="create", description="make reminder")
    async def createreminder(self, interaction: discord.Interaction, on: str, message: Optional[str]):
        await interaction.response.defer()
        on: datetime = dateparser.parse(on)
        if on.timestamp() < time.time():
            on = datetime.fromtimestamp(time.time()+(time.time()-on.timestamp()))
        reminder = Reminder(interaction.channel.id, interaction.user.id, message)
        await self.scheduler.add_payload(interaction.guild.id, on, reminder)
        await interaction.followup.send(f"Reminder{": `"+message+"` " if message is not None else " "}going off <t:{str(int(on.timestamp()))}:R>.")

async def setup(bot):
    await bot.add_cog(reminder(bot))