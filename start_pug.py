from typing import Dict, List

import discord
import time
import datetime
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
config = config['Pug Settings']

announce_string = config['intro string']

pug_wday = config['pug weekday']
pug_hour = config['pug hour']

emojis_ids = [
    '<:scout:902551045891309579>',
    '<:soldier:902551045861957642>',
    '<:pyro:902551046189092875>',
    '<:demoman:902551045815816202>',
    '<:heavy:902551045677416489>',
    '<:engineer:902551046004572211>',
    '<:medic:902551045761269782>',
    '<:sniper:902551045891313754>',
    '<:spy:902551045853560842>'
]

signups: Dict[str, List] = {
    emojis_ids[0]: [],
    emojis_ids[1]: [],
    emojis_ids[2]: [],
    emojis_ids[3]: [],
    emojis_ids[4]: [],
    emojis_ids[5]: [],
    emojis_ids[6]: [],
    emojis_ids[7]: [],
    emojis_ids[8]: []
}

player_classes: Dict[str, List[discord.Emoji]] = {}

signupsMessage: discord.Message = None


async def announce_pug(channel: discord.TextChannel):
    pug_day = time.strptime(pug_wday, "%A")
    current_date = datetime.datetime.now(datetime.timezone.utc).astimezone()
    if current_date.utcoffset().seconds == datetime.timedelta(hours=11).seconds:  # Daylight savings currently active
        timezone_string = "AEDT"
    else:
        timezone_string = "AEST"
    current_day = current_date.weekday()
    time_to_pug = datetime.timedelta(days=pug_day.tm_wday - current_day)
    if time_to_pug.days < 0:
        time_to_pug = datetime.timedelta(days=time_to_pug.days + 7)  # Ensure pug is in the future
    pug_date = current_date + time_to_pug
    pug_date = pug_date.replace(hour=int(pug_hour), minute=0, second=0, microsecond=0)
    print(f"Pug is on {pug_date}")
    pug_time_string = pug_date.strftime(f"%A (%d %B) at %I %p {timezone_string}")
    announce_message = announce_string + "\nPug will be **" + pug_time_string + "**"
    pugMessage: discord.Message = await channel.send(announce_message)
    for reactionEmoji in emojis_ids:
        await pugMessage.add_reaction(reactionEmoji)
    await pugMessage.add_reaction('\U0000274C')
    return pugMessage


async def list_players():
    signupClass: str
    players: list
    msg: str = ""
    for signupClass, players in signups.items():
        line = signupClass + ": " + ", ".join(players)
        msg = msg + "\n" + line
    return msg
