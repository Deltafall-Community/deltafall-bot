[![discord.py](https://img.shields.io/badge/discord.py-white?logo=discord&style=flat-square)](https://github.com/Rapptz/discord.py)
[![deltafall](https://img.shields.io/badge/deltafall-white?logo=discord&style=flat-square)](https://discord.gg/hT3HtPSwth)
![GitHub top language](https://img.shields.io/github/languages/top/Deltafall-Community/deltafall-bot?style=flat-square&labelColor=white&color=white)

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
> a bot token is required to run this.
>
start by running the `main.py` for the first time
```shell
python main.py
```
a config file will be created in the working directory.

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

<table><thead>
  <tr>
    <th colspan="2">Command</th>
    <th>Description</th>
    <th>Usage</th>
  </tr></thead>
<tbody>
  <tr>
    <td colspan="2">add_quote</td>
    <td>Adds a quote for random-quote to use.</td>
    <td>quote: The main body of the text you want to add<br>by: Who it should be displayed as by</td>
  </tr>
  <tr>
    <td rowspan="10">club</td>
    <td>announce</td>
    <td>Sends an announcement pinging all members of your club.</td>
    <td>-</td>
  </tr>
  <tr>
    <td>create</td>
    <td>Creates a club, if you have none.</td>
    <td>-</td>
  </tr>
  <tr>
    <td>disband</td>
    <td>Disbands a club, if you have none.</td>
    <td>-</td>
  </tr>
  <tr>
    <td>edit</td>
    <td>Allows you to edit your club.</td>
    <td>Description: Description to be displayed<br>Icon: URL of icon image you wish to use, should be square<br>Banner: URL of banner image you wish to use, should be wide</td>
  </tr>
  <tr>
    <td>info</td>
    <td>Allows you to see information about a given club.</td>
    <td>search: Name of club to search for<br>leader: The user who owns the club</td>
  </tr>
  <tr>
    <td>join</td>
    <td>Allows you to join someone else's club.</td>
    <td>search: Name of club to search for<br>leader: The user who owns the club</td>
  </tr>
  <tr>
    <td>joined_list</td>
    <td>Lists clubs you've joined.</td>
    <td>search: Name of club to search for<br>leader: The user who owns the club</td>
  </tr>
  <tr>
    <td>leave</td>
    <td>Allows you to leave someone else's club.</td>
    <td>search: Name of club to search for<br>leader: The user who owns the club</td>
  </tr>
  <tr>
    <td>list</td>
    <td>Lists clubs in the server.</td>
    <td>-</td>
  </tr>
  <tr>
    <td>ping</td>
    <td>Pings all members of your club.</td>
    <td>-</td>
  </tr>
  <tr>
    <td colspan="2">make_baby</td>
    <td>Uses algorithms to decide what name is most likely to come from two names.</td>
    <td>first_person: The first name you want to compare<br>second_person: The second name you want to compare</td>
  </tr>
  <tr>
    <td rowspan="2">manga</td>
    <td>random</td>
    <td>Gets a random manga from MangaDex.</td>
    <td>-</td>
  </tr>
  <tr>
    <td>random_page</td>
    <td>Gets a random page of a random manga from MangaDex.</td>
    <td>-</td>
  </tr>
  <tr>
    <td rowspan="9">music</td>
    <td>current_playing</td>
    <td>Displays the currently playing music.</td>
    <td>-</td>
  </tr>
  <tr>
    <td>pause</td>
    <td>Pauses music.</td>
    <td>-</td>
  </tr>
  <tr>
    <td>play</td>
    <td>Adds a song from YouTube or from an audio file to the queue.</td>
    <td>search: The name of the video on YouTube, or a URL to the video<br>file: An audio file</td>
  </tr>
  <tr>
    <td>queue</td>
    <td>Lists all songs on the music queue.</td>
    <td>-</td>
  </tr>
  <tr>
    <td>resume</td>
    <td>Unpauses music.</td>
    <td>-</td>
  </tr>
  <tr>
    <td>skip</td>
    <td>Skips the current song.</td>
    <td>-</td>
  </tr>
  <tr>
    <td>stop</td>
    <td>Stops all music and clears the queue.</td>
    <td>-</td>
  </tr>
  <tr>
    <td>transition</td>
    <td>Allows you to modify the crossfade transitions between songs.</td>
    <td>enabled: Whether or not to have transitions between songs<br>duration: The duration of each transition<br>strength: The strength of the crossfade</td>
  </tr>
  <tr>
    <td>volume</td>
    <td>Sets the volume of the song.</td>
    <td>volume: Volume of the song from 0-100%</td>
  </tr>
  <tr>
    <td colspan="2">petpet</td>
    <td>Petpet.</td>
    <td>user: User to have the petpet applied to<br>custom_image: Image to have the petpet applied to</td>
  </tr>
  <tr>
    <td colspan="2">random_quote</td>
    <td>Gets a random quote.</td>
    <td>-</td>
  </tr>
  <tr>
    <td rowspan="3">remind</td>
    <td>create</td>
    <td>Creates a reminder.</td>
    <td>on: Datetime to set reminder to<br>message: Message to be displayed with the reminder</td>
  </tr>
  <tr>
    <td>delete</td>
    <td>Deletes a reminder.</td>
    <td>search: Name of the reminder to delete<br>id: ID of the reminder</td>
  </tr>
  <tr>
    <td>list</td>
    <td>Lists your set reminders.</td>
    <td>-</td>
  </tr>
  <tr>
    <td rowspan="2">settings</td>
    <td>server</td>
    <td>Allows you to modify server settings, if you have the permissions.</td>
    <td>-</td>
  </tr>
  <tr>
    <td>user</td>
    <td>Allows you to modify your settings.</td>
    <td>-</td>
  </tr>
  <tr>
    <td colspan="2">speechbubble</td>
    <td>Adds a reaction transparent speech bubble to an image.</td>
    <td>image: The image you want to add the speech bubble to</td>
  </tr>
  <tr>
    <td colspan="2">textbox</td>
    <td>Creates a highly customizable Undertale/Deltarune style textbox.</td>
    <td>text: The body text of the textbox<br>name: The displayed name on the textbox<br>asterisk: Adds an asterisk to the start of the textbox, makes it more authentic to some UT characters<br>portrait: Allows you to pick between a collection of UT/DR characters for the textbox<br>animated: Animates the textbox into a GIF to replicate a UT/DR textbox<br>custom_portrait: Allows you to add a custom image to the textbox</td>
  </tr>
  <tr>
    <td colspan="2">wiki</td>
    <td>(deprecated) Pulls a given article from the Deltafall Wiki</td>
    <td>search: Article to display</td>
  </tr>
</tbody></table>
