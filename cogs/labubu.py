import discord
from discord.ext import commands
from discord import app_commands

class labubu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="labubu", description="labubu,,, labulabulabubu")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def baby(self, interaction: discord.Interaction):
        await interaction.response.send_message(content="https://cdn.discordapp.com/attachments/1311950927527149568/1431994666244378634/LABUBU_NATION_RESPECK_labubu_funny_jugg_fyp_targetaudience_7560848512133434679.mp4")

async def setup(bot):
    await bot.add_cog(labubu(bot))