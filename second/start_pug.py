from typing import Dict, List, Tuple

import disnake as discord
import time
import datetime
import configparser

import map_voting
import messages
import player_selection
from second import pug_scheduler
import player_tracking

config = configparser.ConfigParser()
config.read('config.ini')
global_config = config['Global Pug Settings']

ANNOUNCE_STRING = global_config['intro string']
EARLY_ANNOUNCE_STRING = global_config['early signups intro string']

config = config['Second Pug Settings']
PUG_WDAY = config['pug weekday']
PUG_HOUR = config['pug hour']
LIST_PLAYER_NAME_LENGTH = 7

emojis_ids = {
    'Scout': '<:scout:902551045891309579>',
    'Soldier': '<:soldier:902551045861957642>',
    'Pyro': '<:pyro:902551046189092875>',
    'Demo': '<:demoman:902551045815816202>',
    'Heavy': '<:heavy:902551045677416489>',
    'Engi': '<:engineer:902551046004572211>',
    'Medic': '<:medic:902551045761269782>',
    'Sniper': '<:sniper:902551045891313754>',
    'Spy': '<:spy:902551045853560842>'
}

signups: Dict[str, List[Tuple[discord.Member, int]]] = {
    emojis_ids['Scout']: [],
    emojis_ids['Soldier']: [],
    emojis_ids['Pyro']: [],
    emojis_ids['Demo']: [],
    emojis_ids['Heavy']: [],
    emojis_ids['Engi']: [],
    emojis_ids['Medic']: [],
    emojis_ids['Sniper']: [],
    emojis_ids['Spy']: []
}

player_classes: Dict[discord.Member, List[discord.Emoji]] = {}

signupsMessage: discord.Message | None = None
signupsListMessage: discord.Message | None = None

players_to_warn = []
messages_to_delete: List[discord.Message] = []


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
    view = discord.ui.View(timeout=None)
    for class_name, class_emoji in emojis_ids.items():
        button = discord.ui.Button(label=class_name, emoji=class_emoji)
        button.callback = signup_player_callback
        view.add_item(button)
    withdraw_button = discord.ui.Button(label='Withdraw', emoji='❌', style=discord.ButtonStyle.danger)
    withdraw_button.callback = withdraw_player
    view.add_item(withdraw_button)
    pugMessage: discord.Message = await channel.send(announce_message, view=view)
    messages_to_delete.append(pugMessage)
    return pugMessage, pug_date


async def announce_early(early_signups_channel: discord.TextChannel, signups_channel: discord.TextChannel):
    announce_message = f"{messages.medic_role.mention}\n{EARLY_ANNOUNCE_STRING} \nPress ❌ to withdraw from the pug."
    medic_announce_message = f"Early signups open!\nIf you want to play **Medic**, press the button below. Medics will gain 3 weeks of early signup!"
    early_view = discord.ui.View(timeout=None)
    for class_name, class_emoji in emojis_ids.items():
        button = discord.ui.Button(label=class_name, emoji=class_emoji)
        button.callback = signup_player_callback
        early_view.add_item(button)
    withdraw_button = discord.ui.Button(label='Withdraw', emoji='❌', style=discord.ButtonStyle.danger)
    withdraw_button.callback = withdraw_player
    early_view.add_item(withdraw_button)
    earlyPugMessage: discord.Message = await early_signups_channel.send(announce_message, view=early_view)
    early_medic_view = discord.ui.View(timeout=None)
    medic_button = discord.ui.Button(label='Medic', emoji=emojis_ids['Medic'])
    medic_button.callback = signup_player_callback
    early_medic_view.add_item(medic_button)
    earlyPugMedicMessage: discord.Message = await signups_channel.send(medic_announce_message, view=early_medic_view)
    messages_to_delete.append(earlyPugMessage)
    messages_to_delete.append(earlyPugMedicMessage)
    return earlyPugMessage, earlyPugMedicMessage


async def signup_player_callback(inter: discord.MessageInteraction):
    global signupsMessage, signupsListMessage

    await inter.response.defer()
    if await player_tracking.check_active_baiter(inter.author):
        before_late_signup_time, late_signup_time = await pug_scheduler.penalty_signups_check()
        if before_late_signup_time:
            await inter.send(
                f"You have a current active warning, and are subject to a late signup penalty. You will be able to signup from {late_signup_time}", ephemeral=True)
            print(
                f"{inter.author.display_name} attempted to sign up, but was denied due to warning")
            return
    players = signups[str(inter.component.emoji)]
    if inter.author not in player_classes:  # Add player to the player list
        player_classes[inter.author] = []
    if inter.component.emoji in player_classes[inter.author]:  # Player already signed up for this class
        await inter.send(f"You are already signed up for {inter.component.emoji}{inter.component.label}", ephemeral=True)
        return
    player_classes[inter.author].append(inter.component.emoji)  # Add class to that player's list
    preference = len(player_classes[inter.author])  # Preference for this class
    players.append((inter.author, preference))
    print(f'{inter.author.display_name} has signed up for {inter.component.label}')
    if signupsMessage is None:
        signupsMessage = await messages.send_to_admin(await list_players_by_class())
        signupsListMessage = await messages.send_to_admin(await list_players())
        await signupsMessage.pin()
        await signupsListMessage.pin()
    else:
        await signupsMessage.edit(content=await list_players_by_class())
        await signupsListMessage.edit(content=await list_players())
    await inter.send(f"Successfully signed up for {inter.component.emoji}{inter.component.label} (preference {preference})", ephemeral=True)


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


async def withdraw_player(inter: discord.ApplicationCommandInteraction | discord.MessageInteraction, user: discord.Member = None):
    if user is None:  # Player invoked withdraw
        user = inter.author

    async def respond_admin(message):
        if isinstance(inter, discord.ApplicationCommandInteraction):  # Admin invoked withdraw
            await inter.send(message)
        elif isinstance(inter, discord.MessageInteraction):  # User invoked withdraw
            await messages.send_to_admin(message)

    async def respond_user(message):
        if isinstance(inter, discord.ApplicationCommandInteraction): # Admin invoked withdraw
            await user.send(message)
        elif isinstance(inter, discord.MessageInteraction): # User invoked withdraw
            await inter.send(message, ephemeral=True)

    if user not in player_classes:  # user is already withdrawn
        if isinstance(inter, discord.ApplicationCommandInteraction):
            await respond_admin(f"{user.display_name} is already withdrawn.")
        elif isinstance(inter, discord.MessageInteraction):
            await respond_user(f"You are already withdrawn.")
        return
    player_classes.pop(user)
    for signup_class in signups.values():
        for signup in signup_class:
            if user in signup:
                signup_class.remove(signup)
    print(f'{user.display_name} has withdrawn')
    await map_voting.remove_player_votes(user)
    await signupsMessage.edit(content=await list_players_by_class())
    await signupsListMessage.edit(content=await list_players())
    await map_voting.clear_user_votes(user)
    if user in player_selection.blu_team.values() or user in player_selection.red_team.values():
        is_past_penalty_time, penalty_trigger_time = await pug_scheduler.after_penalty_trigger_check()
        if is_past_penalty_time:
            await respond_admin(f"{messages.host_role.mention}: {user.display_name} has withdrawn from the pug. As it is after {penalty_trigger_time}, they will receive a bait warning.")
            players_to_warn.append(user)
            await respond_user(f"You have withdrawn from the pug. As you have been assigned a class and it is after {penalty_trigger_time}, you will receive a bait warning.")
        else:
            await respond_admin(f"{messages.host_role.mention}: {user.display_name} has withdrawn from the pug.")
            await respond_user(f"You have withdrawn from the pug.")
    else:
        if isinstance(inter, discord.ApplicationCommandInteraction):
            await respond_admin(f"{user.display_name} has withdrawn from the pug.")
        elif isinstance(inter, discord.MessageInteraction):
            await respond_user(f"You have withdrawn from the pug.")
    for player_class, player in player_selection.blu_team.items():
        if player == user:
            player_selection.blu_team[player_class] = None
            await player_selection.bluMessage.edit(content="BLU Team:\n" + await player_selection.list_players(player_selection.blu_team))
            await player_selection.announce_string()
    for player_class, player in player_selection.red_team.items():
        if player == user:
            player_selection.red_team[player_class] = None
            await player_selection.redMessage.edit(content="RED Team:\n" + await player_selection.list_players(player_selection.red_team))
            await player_selection.announce_string()


async def auto_warn_bating_players():
    for user in players_to_warn:
        await player_tracking.warn_player(user)
    players_to_warn.clear()


async def reset_pug():
    global messages_to_delete, signupsMessage, signupsListMessage, signups, player_classes
    for message in messages_to_delete:
        try:
            await message.delete()
        except discord.NotFound:
            continue
    messages_to_delete.clear()
    await signupsMessage.unpin()
    await signupsListMessage.unpin()
    signupsMessage = None
    signupsListMessage = None
    player_selection.bluMessage = None
    player_selection.redMessage = None
    player_selection.stringMessage = None
    player_selection.reminderMessage = None
    pug_scheduler.pugMessage = None
    pug_scheduler.earlyMedicPugMessage = None
    pug_scheduler.earlyPugMessage = None
    map_voting.active_votes.clear()
    player_selection.ping_messages.clear()
    player_selection.blu_team = dict.fromkeys(player_selection.blu_team.keys(), None)
    player_selection.red_team = dict.fromkeys(player_selection.red_team.keys(), None)
    signups = dict.fromkeys(signups.keys(), [])
    player_classes = {}
    print("Pug status reset; messages deleted")
