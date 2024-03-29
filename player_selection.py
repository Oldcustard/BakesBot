import asyncio
import re
from typing import Dict, List, Tuple

import disnake as discord

import messages
import active_pug
import start_pug

blu_team = {
    'Scout': None,
    'Soldier': None,
    'Pyro': None,
    'Demo': None,
    'Heavy': None,
    'Engi': None,
    'Medic': None,
    'Sniper': None,
    'Spy': None
}

red_team = {
    'Scout': None,
    'Soldier': None,
    'Pyro': None,
    'Demo': None,
    'Heavy': None,
    'Engi': None,
    'Medic': None,
    'Sniper': None,
    'Spy': None
}

blu_name = ['blu', 'blue']

bluMessage: discord.Message | None = None
redMessage: discord.Message | None = None
stringMessage: discord.Message | None = None
reminderMessage: discord.Message | None = None
timeMessage: discord.Message | None = None

messages_to_delete: List[discord.Message] = []
current_select_msgs: List[discord.MessageReference] = []
players_changed_late: List[discord.Member] = []
pending_players: Dict[discord.Member, Tuple[str, str]] = {}


async def select_player(inter: discord.ApplicationCommandInteraction, team: str, player_class: str, player_obj: discord.Member, force=False):
    global bluMessage, redMessage
    pug_starts_soon, _timestamp = await active_pug.active_pug_scheduler.after_penalty_trigger_check()
    if player_obj is None:
        await inter.send(f"Player {player_obj} not found. Try different capitalisation or mention them directly.")
        return
    if player_class.capitalize() not in blu_team:
        await inter.send(f"Class not recognised")
        return
    if team.lower() in blu_name:
        if pug_starts_soon and not force:
            if blu_team[player_class] is not None:
                players_changed_late.append(blu_team[player_class])
            await inform_player_of_late_change(player_obj, 'BLU', player_class.capitalize())
        else:
            blu_team[player_class] = player_obj
        await inter.send(f"{player_obj.display_name} selected for BLU {player_class}")
        if bluMessage is None:
            bluMessage = await messages.announceChannel.send("BLU Team:\n" + await list_players(blu_team))
            redMessage = await messages.announceChannel.send("RED Team:\n" + await list_players(red_team))
            active_pug.active_start_pug.messages_to_delete.append(bluMessage)
            active_pug.active_start_pug.messages_to_delete.append(redMessage)
        else:
            bluMessage = await bluMessage.edit(content="BLU Team:\n" + await list_players(blu_team))
            await announce_string()

    elif team.lower() == 'red':
        if pug_starts_soon and not force:
            if red_team[player_class] is not None:
                players_changed_late.append(red_team[player_class])
            await inform_player_of_late_change(player_obj, 'RED', player_class.capitalize())
        else:
            red_team[player_class] = player_obj
        await inter.send(f"{player_obj.display_name} selected for RED {player_class}")
        if redMessage is None:
            bluMessage = await messages.announceChannel.send("BLU Team:\n" + await list_players(blu_team))
            redMessage = await messages.announceChannel.send("RED Team:\n" + await list_players(red_team))
            active_pug.active_start_pug.messages_to_delete.append(bluMessage)
            active_pug.active_start_pug.messages_to_delete.append(redMessage)
        else:
            redMessage = await redMessage.edit(content="RED Team:\n" + await list_players(red_team))
            await announce_string()
    else:
        await inter.send("Team not recognised")
        return


async def select_player_callback(inter: discord.MessageInteraction):
    global bluMessage, redMessage, players_changed_late
    team, player_class = inter.component.placeholder.split()
    pug_starts_soon, _timestamp = await active_pug.active_pug_scheduler.after_penalty_trigger_check()
    if team == 'BLU':
        if len(inter.values) == 0:
            if pug_starts_soon:
                players_changed_late.append(blu_team[player_class])
            blu_team[player_class] = None
        else:
            player_obj = messages.guild.get_member_named(inter.values[0])
            if player_obj is None:
                await inter.send("Player not found")
                return
            if pug_starts_soon:
                if blu_team[player_class] is not None:
                    players_changed_late.append(blu_team[player_class])
                await inform_player_of_late_change(player_obj, 'BLU', player_class.capitalize())
            else:
                blu_team[player_class] = player_obj
        await inter.response.defer()
        await update_select_options()
        if bluMessage is None:
            bluMessage = await messages.announceChannel.send("BLU Team:\n" + await list_players(blu_team))
            redMessage = await messages.announceChannel.send("RED Team:\n" + await list_players(red_team))
            active_pug.active_start_pug.messages_to_delete.append(bluMessage)
            active_pug.active_start_pug.messages_to_delete.append(redMessage)
        else:
            bluMessage = await bluMessage.edit(content="BLU Team:\n" + await list_players(blu_team))
            await announce_string()
    else:
        if len(inter.values) == 0:
            if pug_starts_soon:
                players_changed_late.append(red_team[player_class])
            red_team[player_class] = None
        else:
            player_obj = messages.guild.get_member_named(inter.values[0])
            if player_obj is None:
                await inter.send("Player not found")
                return
            if pug_starts_soon:
                if red_team[player_class] is not None:
                    players_changed_late.append(red_team[player_class])
                await inform_player_of_late_change(player_obj, 'RED', player_class.capitalize())
            else:
                red_team[player_class] = player_obj
        await inter.response.defer()
        await update_select_options()
        if redMessage is None:
            bluMessage = await messages.announceChannel.send("BLU Team:\n" + await list_players(blu_team))
            redMessage = await messages.announceChannel.send("RED Team:\n" + await list_players(red_team))
            active_pug.active_start_pug.messages_to_delete.append(bluMessage)
            active_pug.active_start_pug.messages_to_delete.append(redMessage)
        else:
            redMessage = await redMessage.edit(content="RED Team:\n" + await list_players(red_team))
            await announce_string()


async def load_select_options(team: str, player_class: str) -> List[discord.SelectOption]:
    options: List[discord.SelectOption] = []
    for player, _pref in active_pug.active_start_pug.signups[start_pug.emojis_ids[player_class]]:
        option = discord.SelectOption(label=player.display_name, emoji=start_pug.emojis_ids[player_class], value=player.display_name)
        if player in blu_team.values() or player in red_team.values() or player in pending_players.keys():
            continue
        options.append(option)
    for player, signups in start_pug.active_pug.active_start_pug.player_classes.items():
        if discord.PartialEmoji.from_str(start_pug.allclass_emoji_id) in signups:
            option = discord.SelectOption(label=player.display_name, emoji=start_pug.emojis_ids[player_class], value=player.display_name)
            if player in blu_team.values() or player in red_team.values():
                continue
            options.append(option)
    for player, assignment in pending_players.items():
        if assignment[0] == team and assignment[1] == player_class:
            option = discord.SelectOption(label=player.display_name + ' (pending)', emoji=start_pug.emojis_ids[player_class])
            option.default = True
            options.append(option)
            return options
    if team == 'BLU' and blu_team[player_class] is not None:
        option = discord.SelectOption(label=blu_team[player_class].display_name, emoji=start_pug.emojis_ids[player_class])
        option.default = True
        options.append(option)
    elif team == 'RED' and red_team[player_class] is not None:
        option = discord.SelectOption(label=red_team[player_class].display_name, emoji=start_pug.emojis_ids[player_class])
        option.default = True
        options.append(option)
    return options


async def update_select_options():
    for message_reference in current_select_msgs:
        message = message_reference.cached_message
        view = discord.ui.View.from_message(message)
        select: discord.ui.Select
        for select in view.children:
            team, player_class = select.placeholder.split()
            select.options = await load_select_options(team, player_class)
            if len(select.options) == 0:
                select.options = [discord.SelectOption(label='No players available')]
                select.disabled = True
            else:
                select.disabled = False
            select.callback = select_player_callback
        await message.edit(content=message.content, view=view)


async def select_player_new(inter: discord.ApplicationCommandInteraction):
    # Delete any previous select messages
    for selectmessage in current_select_msgs:
        message = selectmessage.cached_message
        await message.delete()
    current_select_msgs.clear()

    views: List[discord.ui.View] = []
    select_view = discord.ui.View(timeout=300)
    views.append(select_view)

    for player_class in blu_team.keys():
        dropdown = discord.ui.Select(placeholder='BLU ' + player_class, min_values=0, options=await load_select_options('BLU', player_class))
        if len(dropdown.options) == 0:
            dropdown.options = [discord.SelectOption(label='No players available')]
            dropdown.disabled = True
        dropdown.callback = select_player_callback
        if len(select_view.children) == 5:
            select_view = discord.ui.View(timeout=300)
            views.append(select_view)
        select_view.add_item(dropdown)
    await inter.send("**Player Selection**")
    for view in views:
        message = await inter.followup.send(f"BLU Team ({views.index(view)+1}/{len(views)})\n🟦🟦🟦🟦🟦🟦", view=view)
        current_select_msgs.append(discord.MessageReference.from_message(message))
    views.clear()
    select_view = discord.ui.View(timeout=300)
    views.append(select_view)

    for player_class in red_team.keys():
        dropdown = discord.ui.Select(placeholder='RED ' + player_class, min_values=0, options=await load_select_options('RED', player_class))
        if len(dropdown.options) == 0:
            dropdown.options = [discord.SelectOption(label='No players available')]
            dropdown.disabled = True
        dropdown.callback = select_player_callback
        if len(select_view.children) == 5:
            select_view = discord.ui.View(timeout=300)
            views.append(select_view)
        select_view.add_item(dropdown)
    for view in views:
        message = await inter.followup.send(f"RED Team ({views.index(view) + 1}/{len(views)})\n🟥🟥🟥🟥🟥🟥", view=view)
        current_select_msgs.append(discord.MessageReference.from_message(message))


async def list_players(team: Dict):
    Class: str
    player: discord.Member
    msg: str = ""
    for Class, player in team.items():
        if player is None:
            line = Class + ": "
        else:
            line = Class + ": " + player.mention
        msg = msg + "\n" + line
    return msg


async def announce_string(connect_string: str | None = None, timestamp=None):
    global stringMessage, reminderMessage, timeMessage
    msg = f"{bluMessage.content}\n\n{redMessage.content}"
    if connect_string is None:  # Function was called to update players/post early reminder
        if reminderMessage is not None:  # Check if reminder message already exists
            reminderMessage = await reminderMessage.edit(content=msg)
        else:
            if timestamp is None:  # Function was called to update players, but no reminder exists, so exit
                return
            timeMessage = await messages.announceChannel.send(f"**Reminder:** pug is <t:{timestamp}:R>. Please withdraw if you are not able to make it")
            reminderMessage = await messages.announceChannel.send(msg)
            messages_to_delete.append(timeMessage)
        return
    string_parts = re.split('connect |[;"]', connect_string)
    print(string_parts)
    steam_string = f"steam://connect/{string_parts[1]}/{string_parts[3]}"
    print(steam_string)
    if stringMessage is None:  # First string
        stringMessage = await messages.announceChannel.send(f"{connect_string}\n**Click this link to join immediately** -> {steam_string}")
        try:
            await reminderMessage.delete()
        except discord.NotFound:
            pass
        reminderMessage = await messages.announceChannel.send(msg)
        messages_to_delete.append(stringMessage)
        messages_to_delete.append(reminderMessage)
    else:  # Updated string
        stringMessage = await stringMessage.edit(content=f"{connect_string}\n**Click this link to join immediately** -> {steam_string}")


async def swap_class_across_teams(inter: discord.ApplicationCommandInteraction, player_class: str):
    global bluMessage, redMessage
    player_class = player_class.capitalize()
    if player_class not in blu_team:
        await inter.send(f"Class not recognised.")
        return
    if bluMessage is None or redMessage is None:
        await inter.send(f"No players are assigned to classes yet.")
        return
    else:
        blu_team[player_class], red_team[player_class] = red_team[player_class], blu_team[player_class]
        bluMessage = await bluMessage.edit(content="BLU Team:\n" + await list_players(blu_team))
        redMessage = await redMessage.edit(content="RED Team:\n" + await list_players(red_team))
        await announce_string()
        await inter.send(f"{blu_team[player_class].display_name} is now BLU {player_class} & {red_team[player_class].display_name} is now RED {player_class}.")


async def list_unassigned_players(inter: discord.ApplicationCommandInteraction):
    unassigned = []
    for player in active_pug.active_start_pug.player_classes.keys():
        if player not in blu_team.values() and player not in red_team.values():
            unassigned.append(player.display_name)
    await inter.send("Players yet to be assigned a class: " + ", ".join(unassigned))


async def drag_into_team_vc(inter: discord.ApplicationCommandInteraction):
    member: discord.Member
    for member in inter.author.voice.channel.members:
        if member in blu_team.values():
            try:
                await member.move_to(messages.bluChannel)
            except discord.HTTPException:
                continue
        elif member in red_team.values():
            try:
                await member.move_to(messages.redChannel)
            except discord.HTTPException:
                continue
    await inter.send("All players moved to team VCs")


async def drag_into_same_vc(inter: discord.ApplicationCommandInteraction):
    member: discord.Member
    for member in messages.bluChannel.members:
        try:
            await member.move_to(inter.author.voice.channel)
        except discord.HTTPException:
            continue
    for member in messages.redChannel.members:
        try:
            await member.move_to(inter.author.voice.channel)
        except discord.HTTPException:
            continue
    await inter.send("All players moved to your VC")


async def ping_not_present(inter: discord.ApplicationCommandInteraction):
    player: discord.Member
    signed_up_players = set(blu_team.values()) | set(red_team.values())
    present_players = set(messages.bluChannel.members) | set(messages.redChannel.members) | set(messages.waitingChannel.members)
    absent_players = [player for player in (signed_up_players - present_players)]
    absent_classes = []
    for player_class, player in blu_team.items():
        if player in absent_players:
            absent_classes.append(player_class)
    for player_class, player in red_team.items():
        if player in absent_players:
            absent_classes.append(player_class)
    message = await messages.announceChannel.send(f"Join up! {', '.join(player.mention for player in absent_players)}")
    messages_to_delete.append(message)
    absent_classes_string = f"Absent classes: {', '.join(absent_classes)}"
    await inter.send(f"Absent players have been pinged!\n{absent_classes_string}")


async def inform_player_of_late_change(player: discord.Member, team: str, player_class: str):
    global players_changed_late
    pug_starts_soon, _timestamp = await active_pug.active_pug_scheduler.after_penalty_trigger_check()
    signed_up_players = list(blu_team.values()) + list(red_team.values())
    if pug_starts_soon and (player in signed_up_players or player in players_changed_late):
        if team == 'BLU':
            blu_team[player_class] = player
        elif team == 'RED':
            red_team[player_class] = player
        await player.send(f"**Please Note:** Your class in the upcoming Bakes Pug has been switched to **{player_class}**.")
        await messages.send_to_admin(f"{player.display_name} has been informed of the late change")
        print(f"{player.display_name} informed of late class change")
    elif pug_starts_soon:
        pending_players[player] = (team, player_class)
        view = discord.ui.View(timeout=10800)
        yes_button = discord.ui.Button(style=discord.ButtonStyle.success, label="I can play", emoji="✔")
        no_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="I can't play", emoji="❌")
        yes_button.callback = yes_button_callback
        no_button.callback = no_button_callback
        view.add_item(yes_button)
        view.add_item(no_button)
        await player.send(f"**IMPORTANT:** You have just been assigned to play **{player_class}** in the upcoming Bakes Pug.\nPlease confirm whether you can play by using the buttons below (there will be no penalty for indicating you cannot play)", view=view)
        await messages.send_to_admin(f"{player.display_name} has been informed of the late assignment, they will be added pending confirmation.")
        print(f"{player.display_name} informed of late assignment")


async def yes_button_callback(inter: discord.MessageInteraction):
    global bluMessage, redMessage
    await asyncio.sleep(0.5)
    await inter.response.defer()
    if inter.author not in pending_players.keys():
        await inter.send("You have already responded.")
        return
    team, player_class = pending_players[inter.author]
    if team == 'BLU':
        blu_team[player_class] = inter.author
    elif team == 'RED':
        red_team[player_class] = inter.author
    pending_players.pop(inter.author)
    bluMessage = await bluMessage.edit(content="BLU Team:\n" + await list_players(blu_team))
    redMessage = await redMessage.edit(content="RED Team:\n" + await list_players(red_team))
    await announce_string()
    await inter.send("You have confirmed you will play. **Please note** you will now be expected to play and will face a warning for being a no-show.")
    await messages.send_to_admin(f"{messages.host_role.mention}: {inter.author.display_name} has confirmed they will play {team} {player_class}")


async def no_button_callback(inter: discord.MessageInteraction):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    if inter.author not in pending_players.keys():
        await inter.send("You have already responded.")
        return
    pending_players.pop(inter.author)
    await inter.send("You have confirmed you will not play.")
    if inter.author in active_pug.active_start_pug.player_classes.keys():
        await active_pug.active_start_pug.withdraw_player(inter, inter.author)
    await messages.send_to_admin(f"{messages.host_role.mention}: {inter.author.display_name} has indicated they **cannot** play.")
