import discord
from discord.ext import commands
from discord import app_commands

class labubu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="labubu", description="labubu,,, labulabulabubu")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def labubu(self, interaction: discord.Interaction):
        await interaction.response.send_message(content="```ansi\n[2;31m         ::.      --.:           \n       :***+*.   ++*#**+         \n      **##-%#*. *#*#+##*-        \n     :###--=%#* ##%===%#*.       \n     ##%--==#%+*#%--==%%#:       \n     #%%-=#=%%%=%#-=%-+##*.      \n    :##%-##=*%%%%%=+#=+%#*       \n    .##%**#+++**##%****#%*       \n    .##****+*#*%%%%#%#%#**       \n    -**%%%*##%#@**##*%#**#+:     \n   =#*######***#%#*#**%***#*-    \n  =#*#####***##%#%##%*+*##**+:   \n :#*##%%--:-----------=+@###**   \n *##%#=-:-----:----===--=%#*##+  \n:+###+-:-.%#--:----%%%---+%*%*+: \n.+*#%=-:*=*##-:----%%%---=%##*+  \n **#%+=:-:%%:-=#%-=+%+=-=-%*#*+  \n  **#%+:-::::-----------=%##**   \n  .**%%%+-:*-------+:-=%%#*#*    \n    -*#####%%#%%%%%%%%#*###:     \n      *#%#%###*##%#%%#%@%#.      \n    #%@%%%#%%%%@%@%#=%%%%%#*     \n   %%%%@%%%%%%%%###=--#%%%###*   \n -#%%%%@#%#%##%%%%##+-#%#%%%%#*  \n.#%%@@%####%%##%%%%#####%%%%###+ \n:-+%%%%##%##%%%%%#%###%##%%#%*== \n-+***###*####%#%%#%##%%#%%#+:   =\n      **####%###%%@%%######-     \n     .####%%#%#%#%%####%%%%:     \n     *##%##########%#@##%##+     \n     **###%#%#@#%%##%##%###*+    \n     *#@%#####@%%%%%#%###%**+    \n     =####%%%%    %##%%%##*      \n      -=-+-*        +=+-=-       \n```", ephemeral=interaction.channel.is_guild_installation())

async def setup(bot):
    await bot.add_cog(labubu(bot))