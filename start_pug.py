from typing import Dict, List

import discord
import time
import datetime
import configparser

import messages

config = configparser.ConfigParser()
config.read('config.ini')
config = config['Pug Settings']

ANNOUNCE_STRING = config['intro string']

PUG_WDAY = config['pug weekday']
PUG_HOUR = config['pug hour']

emojis_ids = (
    '<:scout:902551045891309579>',
    '<:soldier:902551045861957642>',
    '<:pyro:902551046189092875>',
    '<:demoman:902551045815816202>',
    '<:heavy:902551045677416489>',
    '<:engineer:902551046004572211>',
    '<:medic:902551045761269782>',
    '<:sniper:902551045891313754>',
    '<:spy:902551045853560842>'
)

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
    pug_day = time.strptime(PUG_WDAY, "%A")
    current_date = datetime.datetime.now(datetime.timezone.utc).astimezone()
    if current_date.utcoffset().seconds == datetime.timedelta(hours=11).seconds:  # Daylight savings currently active
        timezone_string = "AEDT"
    else:
        timezone_string = "AEST"
    current_day = current_date.weekday()
    time_to_pug = datetime.timedelta(days=pug_day.tm_wday - current_day)
    if time_to_pug.days < 0:
        time_to_pug = time_to_pug + datetime.timedelta(days=7)  # Ensure pug is in the future
    pug_date = current_date + time_to_pug
    pug_date = pug_date.replace(hour=int(PUG_HOUR), minute=0, second=0, microsecond=0)
    print(f"Pug announced. Pug is on {pug_date}")
    pug_time_string = pug_date.strftime(f"%A (%d %B) at %I %p {timezone_string}")
    announce_message = f"""{ANNOUNCE_STRING}
                       Pug will be **{pug_time_string}**
                       Press ❌ to withdraw from the pug."""
    pugMessage: discord.Message = await channel.send(announce_message)
    for reactionEmoji in emojis_ids:
        await pugMessage.add_reaction(reactionEmoji)
    await pugMessage.add_reaction('❌')
    return pugMessage


async def list_players():
    signupClass: str
    players: list
    msg: str = ""
    for signupClass, players in signups.items():
        line = signupClass + ": " + ", ".join(players)
        msg = msg + "\n" + line
    return msg


async def on_reaction_add(reaction: discord.Reaction, user: discord.Member):
    global signupsMessage
    if reaction.emoji == "\U0000274C":  # Withdraw player
        await withdraw_player(user)
        for user_reaction in reaction.message.reactions:
            await user_reaction.remove(user)
        return
    players = signups.get(str(reaction.emoji))
    if players is None:  # User added their own reaction
        await reaction.remove(user)
        return
    if user.display_name not in player_classes:  # Add player to the player list
        player_classes[user.display_name] = []
    if reaction.emoji in player_classes[user.display_name]:  # Player already signed up for this class
        return
    player_classes[user.display_name].append(reaction.emoji)  # Add class to that player's list
    preference = len(player_classes[user.display_name])  # Preference for this class
    players.append(user.display_name + f' ({preference})')
    print(f'{user.display_name} has signed up for {reaction.emoji}')
    if signupsMessage is None:
        signupsMessage = await messages.send_to_admin(await list_players())
        await signupsMessage.pin()
    else:
        await signupsMessage.edit(content=await list_players())
    await user.send(f"Successfully signed up for {reaction.emoji} (preference {preference})")


async def withdraw_player(user: discord.Member):
    if user.display_name not in player_classes:  # user pressed withdraw without being signed up
        return
    player_classes.pop(user.display_name)
    for signup_class in signups.values():
        user_signup = [s for s in signup_class if user.display_name in s]
        if len(user_signup) == 1:
            signup_class.remove(user_signup[0])
    print(f'{user.display_name} has withdrawn')
    await signupsMessage.edit(content=await list_players())
    await messages.send_to_admin(f"{messages.host_role.mention}: {user.display_name} has withdrawn from the pug")
    await user.send("You have withdrawn from the pug")
