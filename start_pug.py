from typing import Dict, List, Tuple

import discord
import time
import datetime
import configparser

import map_voting
import messages
import player_selection
import pug_scheduler
import player_tracking

config = configparser.ConfigParser()
config.read('config.ini')
config = config['Pug Settings']

ANNOUNCE_STRING = config['intro string']
EARLY_ANNOUNCE_STRING = config['early signups intro string']

PUG_WDAY = config['pug weekday']
PUG_HOUR = config['pug hour']
LIST_PLAYER_NAME_LENGTH = 7

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

signups: Dict[str, List[Tuple[discord.Member, int]]] = {
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

player_classes: Dict[discord.Member, List[discord.Emoji]] = {}

signupsMessage: discord.Message = None
signupsListMessage: discord.Message = None

players_to_warn = []


async def announce_pug(channel: discord.TextChannel):
    pug_day = time.strptime(PUG_WDAY, "%A")
    current_date = datetime.datetime.now(datetime.timezone.utc).astimezone()
    current_day = current_date.weekday()
    time_to_pug = datetime.timedelta(days=pug_day.tm_wday - current_day)
    if time_to_pug.days < 0:
        time_to_pug = time_to_pug + datetime.timedelta(days=7)  # Ensure pug is in the future
    pug_date = current_date + time_to_pug
    pug_date = pug_date.replace(hour=int(PUG_HOUR), minute=0, second=0, microsecond=0)
    print(f"Pug announced. Pug is on {pug_date}")
    pug_timestamp = round(datetime.datetime.timestamp(pug_date))
    pug_time_string = f"<t:{pug_timestamp}:F>"
    announce_message = f"\n{ANNOUNCE_STRING} \nPug will be **{pug_time_string}** (this is displayed in your **local time**)\nPress ❌ to withdraw from the pug."
    pugMessage: discord.Message = await channel.send(announce_message)
    for reactionEmoji in emojis_ids:
        await pugMessage.add_reaction(reactionEmoji)
    await pugMessage.add_reaction('❌')
    return pugMessage, pug_date


async def announce_early(early_signups_channel: discord.TextChannel, signups_channel: discord.TextChannel):
    announce_message = f"{messages.medic_role.mention}\n{EARLY_ANNOUNCE_STRING} \nPress ❌ to withdraw from the pug."
    medic_announce_message = f"@everyone\nEarly signups open!\nIf you want to play **Medic**, press the button below. Medics will gain 3 weeks of early signup!"
    earlyPugMessage: discord.Message = await early_signups_channel.send(announce_message)
    for reactionEmoji in emojis_ids:
        await earlyPugMessage.add_reaction(reactionEmoji)
    await earlyPugMessage.add_reaction('❌')
    earlyPugMedicMessage: discord.Message = await signups_channel.send(medic_announce_message)
    await earlyPugMedicMessage.add_reaction(emojis_ids[6])
    return earlyPugMessage, earlyPugMedicMessage


async def list_players_by_class():
    signupClass: str
    players: Tuple[discord.Member, int]
    msg: str = ""
    for signupClass, players in signups.items():
        formatted_players: List[str] = []
        for member, pref in players:
            name = member.display_name.replace('`', '')
            if len(name) <= LIST_PLAYER_NAME_LENGTH:
                formatted_name = f"{name:>{LIST_PLAYER_NAME_LENGTH}.{LIST_PLAYER_NAME_LENGTH}} ({pref})"
            else:
                formatted_name = f"{name[:LIST_PLAYER_NAME_LENGTH - 1]}- ({pref})"
            formatted_players.append(formatted_name)
        line = signupClass + ":`" + "| ".join(formatted_players) +" `"
        msg = msg + "\n" + line
    return msg


async def list_players():
    msg = ''
    players = player_classes.keys()
    player_names = []
    for player in players:
        player_names.append(player.display_name)
    msg = "Signups in order: " + ', '.join(player_names)
    return msg


async def on_reaction_add(reaction: discord.Reaction, user: discord.Member):
    global signupsMessage, signupsListMessage

    if await player_tracking.check_active_baiter(user):
        before_late_signup_time, late_signup_time = await pug_scheduler.penalty_signups_check()
        if before_late_signup_time:
            await user.send(f"You have a current active warning, and are subject to a late signup penalty. You will be able to signup from {late_signup_time}")
            print(f"{user.display_name} attempted to sign up, but was denied due to warning. Signup available at {late_signup_time}")
            await reaction.remove(user)
            return
    if reaction.emoji == "❌":  # Withdraw player
        await withdraw_player(user)
        for user_reaction in reaction.message.reactions:
            await user_reaction.remove(user)
        return
    try:
        players = signups[str(reaction.emoji)]
    except KeyError:  # User added their own reaction
        await reaction.remove(user)
        return
    if user not in player_classes:  # Add player to the player list
        player_classes[user] = []
    if reaction.emoji in player_classes[user]:  # Player already signed up for this class
        return
    player_classes[user].append(reaction.emoji)  # Add class to that player's list
    preference = len(player_classes[user])  # Preference for this class
    players.append((user, preference))
    print(f'{user.display_name} has signed up for {reaction.emoji}')
    if signupsMessage is None:
        signupsMessage = await messages.send_to_admin(await list_players_by_class())
        signupsListMessage = await messages.send_to_admin(await list_players())
        await signupsMessage.pin()
        await signupsListMessage.pin()
    else:
        await signupsMessage.edit(content=await list_players_by_class())
        await signupsListMessage.edit(content=await list_players())
    await user.send(f"Successfully signed up for {reaction.emoji} (preference {preference})")


async def withdraw_player(user: discord.Member):
    if user not in player_classes:  # user pressed withdraw without being signed up
        return
    player_classes.pop(user)
    for signup_class in signups.values():
        for signup in signup_class:
            if user in signup:
                signup_class.remove(signup)
    print(f'{user.display_name} has withdrawn')
    await signupsMessage.edit(content=await list_players_by_class())
    await signupsListMessage.edit(content=await list_players())
    if user in player_selection.blu_team.values() or user in player_selection.red_team.values():
        is_past_penalty_time, penalty_trigger_time = await pug_scheduler.after_penalty_trigger_check()
        if is_past_penalty_time:
            await messages.send_to_admin(f"{messages.host_role.mention}: {user.display_name} has withdrawn from the pug. As it is after {penalty_trigger_time}, they will receive a bait warning.")
            players_to_warn.append(user)
            await user.send(f"You have withdrawn from the pug. As you have been assigned a class and it is after {penalty_trigger_time}, you will receive a bait warning.")
            return
        else:
            await messages.send_to_admin(f"{messages.host_role.mention}: {user.display_name} has withdrawn from the pug.")
    await user.send(f"You have withdrawn from the pug.")


async def auto_warn_bating_players():
    for user in players_to_warn:
        await player_tracking.warn_player(user)
    players_to_warn.clear()


async def reset_pug():
    global signupsMessage, signupsListMessage
    await signupsMessage.unpin()
    await signupsListMessage.unpin()
    await player_selection.bluMessage.delete()
    await player_selection.redMessage.delete()
    await player_selection.stringMessage.delete()
    await player_selection.reminderMessage.delete()
    await player_selection.timeMessage.delete()
    await pug_scheduler.pugMessage.delete()
    await pug_scheduler.earlyMedicPugMessage.delete()
    await pug_scheduler.earlyPugMessage.delete()
    for vote in map_voting.active_votes:
        try:
            await vote.delete()
        except discord.NotFound:
            pass
        map_voting.active_votes.remove(vote)
    for ping in player_selection.ping_messages:
        try:
            await ping.delete()
        except discord.NotFound:
            pass
        player_selection.ping_messages.remove(ping)
    signupsMessage = None
    signupsListMessage = None
    player_selection.bluMessage = None
    player_selection.redMessage = None
    player_selection.stringMessage = None
    player_selection.reminderMessage = None
    pug_scheduler.pugMessage = None
    pug_scheduler.earlyMedicPugMessage = None
    pug_scheduler.earlyPugMessage = None
    print("Pug status reset; messages deleted")
