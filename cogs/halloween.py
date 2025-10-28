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
        "mmrp",
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
        "are these candies even safe to eat?",
        "I put razor blades in your candies",
        "Don't run into the road",
        "Big Namu Corp will soon silence me, please hel"
    ]
    textbox = Textbox("data/textbox/deltarune.toml", Image.open("data/pfp/deltaballinhalloweenfit.png"), "data/fonts/determination-mono.ttf", random.choice(random_dialogue), True, False)
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
            "estrogen",
            "progesterone",
            "spiro",
            "testosterone",
            "tylenol",
            "prozac"
        ]
        self.jumpscare_gifs = [
            "https://tenor.com/view/uni-kuroneko-black-cat-cat-jumping-cat-jumpscare-chey-gif-5697602643041941027",
            "https://tenor.com/view/but-heres-the-kicker-heres-the-kicker-but-heres-cat-jumpscare-gif-26573900",
            "https://tenor.com/view/cat-cat-meme-jumpscare-jump-turn-around-gif-2261440711797458974",
            "https://tenor.com/view/cat-jumpscare-box-gif-12399387153107465639",
            "https://tenor.com/view/cat-flying-flying-cat-jumpscare-jump-gif-20372835"
        ]
        self.special_eat_outcomes = [
            "candy was spiked D:",
            "candy had razor blades in it D:",
            "candy had laxatives in it D: (shits loudly)",
            "```ansi\n[2;32mthe candy was radioactive????????\n```"
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
                await message.reply(content=random.choice(self.jumpscare_gifs))

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
        if interaction.user == user:
            return await interaction.response.send_message(content="you cant give yourself candies")
        
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

    @app_commands.command(name="request_candy", description="halloween")
    @app_commands.allowed_installs(guilds=True, users=False)
    async def request(self, interaction: discord.Interaction, candy_name: str, user: discord.User, amount: int):
        if interaction.user == user:
            return await interaction.response.send_message(content="you cant request yourself candies")
        
        candy_name = candy_name.lower()
        if candy_name not in self.vaild_candies:
            return await interaction.response.send_message(content=f"{candy_name} is not a vaild candy name")
        if amount < 1:
            return await interaction.response.send_message(content="you cant just ask for 0 candies")

        giver_vault = await self.vault_manager.get(user.id)
        giver_candies: Dict = giver_vault.get("halloween2025Candies", {})

        reciever_vault = await self.vault_manager.get(interaction.user.id)
        reciever_candies: Dict = reciever_vault.get("halloween2025Candies", {})

        if (candy_amount := giver_candies.get(candy_name)):            
            if candy_amount < amount:
                return await interaction.response.send_message(content=f"{user.display_name} only has {candy_amount} of {candy_name}")
            else:
                accepted = None
                view = discord.ui.View()

                accept_button = discord.ui.Button(label="Accept", style=discord.ButtonStyle.success)
                decline_button = discord.ui.Button(label="Decline", style=discord.ButtonStyle.danger)

                async def accept(interaction: discord.Interaction):
                    nonlocal accepted
                    if interaction.user.id != user.id:
                        return await interaction.response.send_message("wasn't asking you dummy", ephemeral=True)
                    accepted = True
                    await interaction.response.defer()
                    view.stop()

                async def decline(interaction: discord.Interaction):
                    nonlocal accepted
                    if interaction.user.id != user.id:
                        return await interaction.response.send_message("wasn't asking you dummy", ephemeral=True)
                    accepted = False
                    await interaction.response.defer()
                    view.stop()

                accept_button.callback = accept
                decline_button.callback = decline

                view.add_item(accept_button)
                view.add_item(decline_button)

                await interaction.response.send_message(content=f"{user.mention}, {interaction.user.display_name} wants {amount} {candy_name} candies from you", view=view)
                await view.wait()

                if accepted is None:
                    return await interaction.edit_original_response(content=f"{user.mention}, {interaction.user.display_name} wants {amount} {candy_name} candies from you (expired)", view=None)
                elif not accepted:
                    return await interaction.edit_original_response(content=f"{user.display_name} declined the candy transfer", view=None)
                
                if candy_name not in reciever_candies:
                    reciever_candies[candy_name] = 0

                giver_candies[candy_name] -= amount
                reciever_candies[candy_name] += amount

                if giver_candies[candy_name] < 1:
                    del giver_candies[candy_name]
        else:
            return await interaction.response.send_message(content=f"{user.display_name} doesn't have {candy_name}")

        await giver_vault.store("halloween2025Candies", giver_candies)
        await reciever_vault.store("halloween2025Candies", reciever_candies)

        await interaction.edit_original_response(content=f"{interaction.user.mention} congrats on your new {amount} {candy_name} candy from {user.mention}", view=None)

    @app_commands.command(name="eat", description="halloween")
    @app_commands.allowed_installs(guilds=True, users=False)
    async def eat(self, interaction: discord.Interaction, candy_name: str):
        candy_name = candy_name.lower()
        if candy_name not in self.vaild_candies:
            return await interaction.response.send_message(content=f"{candy_name} is not a vaild candy name")

        eater_vault = await self.vault_manager.get(interaction.user.id)
        eater_candies: Dict = eater_vault.get("halloween2025Candies", {})

        if (candy_amount := eater_candies.get(candy_name)):
            if candy_amount > 0:
                eater_candies[candy_name] -= 1

                if eater_candies[candy_name] < 1:
                    del eater_candies[candy_name]

                if candy_name in ("estrogen", "progesterone", "spiro"):
                    await interaction.response.send_message(content="man you alr a girl that didn't do anything")
                elif candy_name == "testosterone":
                    await interaction.response.send_message(content="man you alr a boy that didn't do anything")
                else:
                    await interaction.response.send_message(content=random.choice(self.special_eat_outcomes) if random.getrandbits(1) else "yum")

                return await eater_vault.store("halloween2025Candies", eater_candies)
            
        await interaction.response.send_message(content=f"https://tenor.com/view/byuntear-meme-reaction-hungry-ready-to-eat-gif-13927671183202449503 (you have no {candy_name})")

async def setup(bot):
    await bot.add_cog(HalloweenCommand(bot))
