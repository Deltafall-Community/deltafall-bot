[![discord.py](https://img.shields.io/badge/discord.py-white?logo=discord&style=flat-square)](https://github.com/Rapptz/discord.py)
[![deltafall](https://img.shields.io/badge/deltafall-white?logo=discord&style=flat-square)](https://discord.gg/hT3HtPSwth)
![GitHub top language](https://img.shields.io/github/languages/top/45-razrblds/YAMB-fixed?style=flat-square&labelColor=white&color=white)

# deltafall-bot
> also known as Deltaballin
> 
A general purpose *silly* bot used by the Deltafall discord server.

## How do I run this bot?
### Requirements
- Python 3.13+
- FFmpeg
- Discord Bot Token
#### How do I obtain the discord bot token?
- if you don't have a discord bot account, you can follow this [documentation](https://discordpy.readthedocs.io/en/stable/discord.html).
- you can also use the existing token from your existing discord bot if you already got one.
### Setup
#### clone the github repository
```shell
git clone https://github.com/Deltafall-Community/deltafall-bot/
```
#### installing all the required dependencies
```shell
cd deltafall-bot
python -m venv env
source env/bin/activate
pip install -r requirement.txt
```
#### configuring the config file
> [!IMPORTANT]
> to run the bot you MUST do this step or it will not work.
>
starting by copying the `config.json.example` and renaming it to `config.json`

<sub>if you have a gui file manager this step can also be done by using the file manager</sub>
```shell
cp config.json.example config.json
```
edit the `config.json` file

<sup>you can use whatever text editor you like in this case we will be using `nano`</sup>
```shell
nano config.json
```
```json
{
    "token": "",
    "sqlitecloud-quote": "",
    "sqlitecloud-club": ""
}
```
for the minimum requirement for the bot to run, you need to put your bot token in the `"token": "<INSERT TOKEN HERE>"`
it will look something like:
```json
{
    "token": "MTIDJ8jn239jA299jda9DKaasdv.DJKLa48jDDJ3LJE2",
    "sqlitecloud-quote": "",
    "sqlitecloud-club": ""
}
```
#### running the bot
```shell
python main.py
```

## Features

| Command        | Description                                                                                         | Usage                                                                                                                     |
|----------------|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| **addquote**   | Adds a quote for random-quote to use.                                                                | `quote:` The main body of the text you want to add<br>`by:` Who it should be displayed as by                              |
| **goat**       | Gets a random image from r/Ralsei.                                                                   | -                                                                                                                         |
| **make_baby**  | Uses algorithms to decide what name is most likely to come from two names.                           | `first_person:` The first name you want to compare<br>`second_person:` The second name you want to compare                |
| **random_quote** | Gets a random quote.                                                                               | -                                                                                                                         |
| **speechbubble** | Adds a reaction transparent speech bubble to an image.                                             | `image:` The image you want to add the speech bubble to                                                                    |
| **stat**       | Lists stats about the server.                                                                        | -                                                                                                                         |
| **textbox**    | Creates a highly customizable Undertale/Deltarune style textbox.                                     | `text:` The body text of the textbox<br>`name:` The displayed name on the textbox<br>`asterisk:` Adds an asterisk to the start of the textbox, makes it more authentic to some UT characters<br>`portrait:` Allows you to pick between a collection of UT/DR characters for the textbox<br>`animated:` Animates the textbox into a GIF to replicate a UT/DR textbox<br>`custom_portrait:` Allows you to add a custom image to the textbox |



