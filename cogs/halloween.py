import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, Optional
import random
import asyncio

from PIL import Image
from io import BytesIO
from libs.pilutils.repeatscaling import scale
from libs.pilutils.label import LabelContainer
from libs.namutextbox.textbox import Textbox

from libs.namuvaultmanager.vaultmanager import VaultManager

def makepic(candies: Dict) -> Image.Image:
    random_dialogue = [
        "happy halloween or something",
        "meow",
        "im not server cat",
        "spook",
        "boo",
        "shoutout to hipxel for inventing halloween",
        "you look scary",
        "do i look scary?",
        "candy are made out of sugar",
        "happy halloween",
        "Loading TVO Client...",
        "C A N D Y candy candy candy land, candy candy land",
        "shoutout to namu for inventing deltaballin",
        "are these candies even safe to eat?"
    ]
    textbox = Textbox("data/textbox/deltarune.toml", Image.open("data/pfp/deltaballinhalloweenfit.png"), "data/fonts/determination-mono.ttf", random.sample(random_dialogue, 1)[0], True, False)
    textbox = textbox.render()[0]

    label = LabelContainer("data/fonts/determination-mono.ttf", 64, (0, 400), wrap=False)
    title: Image.Image = label.render("You've Obtained")[0]
    label.font_size = 32
    label.size = (300, 300)
    label.spcaing = 1
    content = label.render("\n".join([f"- {value} {key} candy" for key, value in candies.items()]))[0]

    candy = Image.open("data/candy.png")
    candy = candy.convert("RGBA")
    candy = candy.resize((300, 200))

    house = Image.open("data/background/house.jpg")
    house = house.convert("RGBA")
    house = house.resize((300, 200))


    grid = Image.open("data/background/grid.png")
    grid = grid.convert("RGBA")
    scaled_grid = scale(grid, (800, 500))

    base = Image.new("RGBA", (800, 500))
    base.paste(scaled_grid)
    base.paste(candy, (100, 50), candy)
    base.paste(house, (450, 100), house)
    base.paste(title, (300 + 150 - int(title.size[0] / 2), 50), title)
    base.paste(content, (450, 150), content)
    base.paste(textbox, (int((800 - textbox.size[0]) / 2), 500 - textbox.size[1] - 50), textbox)

    return base

def merge_dicts_no_override(dict1, dict2):
    merged_dict = dict1.copy()
    for key, value in dict2.items():
        if key not in merged_dict:
            merged_dict[key] = value
    return merged_dict

class HalloweenCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vaild_candies = [
            "hipxel",
            "n&n",
            "sneaker",
            "womentos",
            "tungsten",
            "toby fox",
            "flavorless",
            "purple",
            "estrogen"
        ]
        self.jumpscare_gifs = [
            "https://tenor.com/view/uni-kuroneko-black-cat-cat-jumping-cat-jumpscare-chey-gif-5697602643041941027",
            "https://tenor.com/view/but-heres-the-kicker-heres-the-kicker-but-heres-cat-jumpscare-gif-26573900",
            "https://tenor.com/view/cat-cat-meme-jumpscare-jump-turn-around-gif-2261440711797458974",
            "https://tenor.com/view/cat-jumpscare-box-gif-12399387153107465639"
        ]
        self.current_vaild_message = None
        self.channel = None
        self.vault_manager: VaultManager = self.bot.vault_manager
        self.msg_count = 0
        self.channel_id = 1311950927527149568

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id == self.channel_id and message.author != self.bot:
            if self.msg_count >= 0:
                self.msg_count += 1
            else:
                return

            if self.msg_count > 20:
                self.msg_count = -1
                await asyncio.sleep(random.randint(1, 60))
                msg = await message.channel.send("trick or treat")
                self.current_vaild_message = msg
                self.msg_count = 0
                return

        if self.current_vaild_message:
            if message.content.lower() == "treat":
                self.current_vaild_message = None
                give_out = {}
                random_candies = random.sample(self.vaild_candies, random.randint(1, 4))
                for candy in random_candies:
                    give_out[candy] = random.randint(1,4)
                
                vault = await self.vault_manager.get(message.author.id)
                candies: Dict = vault.get("halloween2025Candies", {})

                give_out_keys = list(give_out.keys())
                for key, value in candies.items():
                    if key in give_out_keys:
                        candies[key] += give_out[key]

                candies = merge_dicts_no_override(candies, give_out)
                
                image = await asyncio.get_running_loop().run_in_executor(None, makepic, give_out)
                
                image_binary = BytesIO()
                image.save(image_binary, "png")
                image_binary.seek(0)

                await vault.store("halloween2025Candies", candies)
                await message.reply(file=discord.File(image_binary, "image.png"))

            elif message.content.lower() == "trick":
                self.current_vaild_message = None
                await message.reply(content=random.sample(self.jumpscare_gifs, 1)[0])

    @app_commands.command(name="candy", description="halloween")
    @app_commands.allowed_installs(guilds=True, users=False)
    async def candy(self, interaction: discord.Interaction, user: Optional[discord.User]):
        target = user or interaction.user
        vault = await self.vault_manager.get(target.id)
        candies: Dict = vault.get("halloween2025Candies", {})
        
        if candies:
            candies_list = "\n".join([f"- {value} {key} candy" for key, value in candies.items()])
        else:
            candies_list = "Nothing yet."
        
        embed=discord.Embed(title="", description=f"## {target.mention}'s candies 🍫\n"+candies_list, color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="give", description="halloween")
    @app_commands.allowed_installs(guilds=True, users=False)
    async def give(self, interaction: discord.Interaction, candy_name: str, user: discord.User, amount: int):
        candy_name = candy_name.lower()
        if candy_name not in self.vaild_candies:
            return await interaction.response.send_message(content=f"{candy_name} is not a vaild candy name")
        if amount < 1:
            return await interaction.response.send_message(content="you cant just give someone 0 candies")

        giver_vault = await self.vault_manager.get(interaction.user.id)
        giver_candies: Dict = giver_vault.get("halloween2025Candies", {})

        reciever_vault = await self.vault_manager.get(user.id)
        reciever_candies: Dict = reciever_vault.get("halloween2025Candies", {})

        if (candy_amount := giver_candies.get(candy_name)):
            if candy_amount < amount:
                return await interaction.response.send_message(content=f"you only have {candy_amount} of {candy_name}")
            else:
                if candy_name not in reciever_candies:
                    reciever_candies[candy_name] = 0

                giver_candies[candy_name] -= amount
                reciever_candies[candy_name] += amount

                if giver_candies[candy_name] < 1:
                    del giver_candies[candy_name]
        else:
            return await interaction.response.send_message(content=f"you dont have {candy_name}")

        await giver_vault.store("halloween2025Candies", giver_candies)
        await reciever_vault.store("halloween2025Candies", reciever_candies)

        await interaction.response.send_message(content=f"{user.mention} congrats on your new {amount} {candy_name} candy from {interaction.user.mention}")

async def setup(bot):
    await bot.add_cog(HalloweenCommand(bot))
