import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta

import builtins

class mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def purge(self, channel, number, user=None):
        await channel.purge(limit=number)

    async def delete(self, message):
        await message.delete()

    async def timeout(self, user, rawlength, reason=None):
        unit_map = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days', 'w': 'weeks'}
        number = ""
        length_type = ""
        for st in rawlength:
            if st.isalpha():
                length_type += st
            else:
                number += st
        number = int(number)    
        unit = unit_map.get(length_type)
        if unit == None: unit = length_type
        await user.timeout(timedelta(**{unit: number}), reason=reason)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        message_content = message.content.lower()
        if not message_content.startswith(".m"):
            return
        if not message.author.guild_permissions.manage_messages: # i thought this would improve performance but idk
            return
        actions = await self.bot.parse_args(args=message_content,prefix=".m")
        errors = actions[1]
        actions = actions[0]
        # execute
        for d in actions:
            for var in d.items():
                try:
                    match var[0]:

                        # requires no parameters
                        case "d" | "delete":
                            messager = await message.channel.fetch_message(message.reference.message_id)
                            await self.delete(message=messager)

                        # requires parameters
                        case "p" | "purge":
                            allowedtype = [int]
                            match type(var[1]):
                                case builtins.int:
                                    await self.purge(channel=message.channel, number=var[1])
                                case _:
                                    errors.append(f"invaild action at `{var[0]}`: {type(var[1])} not in {allowedtype}")

                        case "t" | "timeout":
                            messager = await message.channel.fetch_message(message.reference.message_id)
                            allowedtype = [list, str]
                            match type(var[1]):
                                case builtins.list:
                                    await self.timeout(user=messager.author, rawlength=var[1][0], reason=var[1][1])
                                case builtins.str:
                                    await self.timeout(user=messager.author, rawlength=var[1])
                                case _:
                                    errors.append(f"invaild action at `{var[0]}`: {type(var[1])} not in {allowedtype}")

                        # what the fuck
                        case _:
                            errors.append(f"invaild action: `{var[0]}`")
                            break

                except Exception as e:
                    errors.append((f"invaild action at `{var[0]}`:\n```{e}```"))
                    break
        if errors:
            errors = '\n'.join(errors)
            await message.channel.send(errors, reference=message)
        await message.delete()
        

async def setup(bot):
    await bot.add_cog(mod(bot))