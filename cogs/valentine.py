import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import plyvel
import json
import asyncio

class valentine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="chocolates", description="valentine")
    async def chocolate(
        self,
        interaction: discord.Interaction):

        choco_count = 0
        choco_list = self.bot.valentine_lvl_db.get(str(interaction.user.id).encode())

        if choco_list != None:
            choco_list = json.loads(choco_list.decode())
            choco_count = len(choco_list)
            choco_added = " ".join([f"<@{id}>" for id in choco_list])
        else: choco_added = "No one."
        
        embed=discord.Embed(title="Chocolates", description=f"You have received {choco_count} 🍫 so far!\nfrom {choco_added}", color=0xFF0000)
        await interaction.response.send_message(embed=embed)


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.emoji == "🍫":
            if reaction.message.author.id == user.id: return

            choco_added = self.bot.valentine_lvl_db.get(str(reaction.message.author.id).encode())
            if choco_added == None: return self.bot.valentine_lvl_db.put(str(reaction.message.author.id).encode(), str([user.id]).encode())
            choco_added = json.loads(choco_added.decode())
            
            if user.id in choco_added: return
            choco_added.append(user.id)

            #print(f"{reaction.message.author.id} {choco_added}")
            return self.bot.valentine_lvl_db.put(str(reaction.message.author.id).encode(), str(choco_added).encode())
        
        
            

async def setup(bot):
    await bot.add_cog(valentine(bot))