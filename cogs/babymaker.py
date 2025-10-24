import discord
from discord.ext import commands
from discord import app_commands

class baby(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def matchtextint(self, text, selectedtext):
        tfilter = []
        for i in selectedtext:
            tfilter.append(i)
        currenttextpos = 0
        charcount = 0
        matchedcount = 0
        for char in text:
            charcount += 1
            if char in tfilter:
                currenttextpos += 1
                for i in tfilter:
                    if char == i:
                        matchedcount += 1
                        break
        return matchedcount

    @app_commands.command(name="make_baby", description="baby")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def baby(self, interaction: discord.Interaction, first_person: str, second_person: str):
        babyname = (first_person[:int(len(first_person) / 2)] + second_person[int(len(second_person) / 2):])

        allchances = 0
        chances = 0

        for i in open("data/names.txt", "r").readlines():
            name = i.replace("\n", "").lower()
            try:
                if name[0].lower() == babyname[0].lower():
                    chance = await self.matchtextint(babyname, name)
                    if chance > 0:
                        allchances += len(name)
                        chances += chance
            except:  # noqa: E722
                pass

        embed=discord.Embed(title="Baby", description=f"{first_person} x {second_person} = {babyname}\nchances of {first_person} and {second_person} having a baby named {babyname} is {round(chances / allchances * 100)}%", color=0x57e389)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(baby(bot))