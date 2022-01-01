from typing import Dict, List

import disnake as discord
import disnake.ext.commands

import messages
import active_pug

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

ping_messages: List[discord.Message] = []
current_select_msgs: List[discord.Message] = []
players_changed_late: List[discord.Member] = []


async def select_player(inter: discord.ApplicationCommandInteraction, team: str, player_class: str, player_obj: discord.Member):
    global bluMessage, redMessage
    if player_obj is None:
        await inter.send(f"Player {player_obj} not found. Try different capitalisation or mention them directly.")
        return
    if player_class.capitalize() not in blu_team:
        await inter.send(f"Class not recognised")
        return
    if team.lower() in blu_name:
        await inform_player_of_late_change(player_obj, player_class.capitalize())
        blu_team[player_class.capitalize()] = player_obj
        await inter.send(f"{player_obj.display_name} selected for BLU {player_class}")
        if bluMessage is None:
            bluMessage = await messages.announceChannel.send("BLU Team:\n" + await list_players(blu_team))
            redMessage = await messages.announceChannel.send("RED Team:\n" + await list_players(red_team))
            await redMessage.pin()
            await bluMessage.pin()
            active_pug.start_pug.messages_to_delete.append(bluMessage)
            active_pug.start_pug.messages_to_delete.append(redMessage)
        else:
            await bluMessage.edit(content="BLU Team:\n" + await list_players(blu_team))
            await announce_string()

    elif team.lower() == 'red':
        await inform_player_of_late_change(player_obj, player_class.capitalize())
        red_team[player_class.capitalize()] = player_obj
        await inter.send(f"{player_obj.display_name} selected for RED {player_class}")
        if redMessage is None:
            bluMessage = await messages.announceChannel.send("BLU Team:\n" + await list_players(blu_team))
            redMessage = await messages.announceChannel.send("RED Team:\n" + await list_players(red_team))
            await redMessage.pin()
            await bluMessage.pin()
            active_pug.start_pug.messages_to_delete.append(bluMessage)
            active_pug.start_pug.messages_to_delete.append(redMessage)
        else:
            await redMessage.edit(content="RED Team:\n" + await list_players(red_team))
            await announce_string()
    else:
        await inter.send("Team not recognised")
        return


async def select_player_callback(inter: discord.MessageInteraction):
    global bluMessage, redMessage, players_changed_late
    team, player_class = inter.component.placeholder.split()
    if team == 'BLU':
        if len(inter.values) == 0:
            players_changed_late.append(blu_team[player_class])
            blu_team[player_class] = None
        else:
            player_obj = messages.guild.get_member_named(inter.values[0])
            if player_obj is None:
                await inter.send("Player not found")
                return
            await inform_player_of_late_change(player_obj, player_class.capitalize())
            blu_team[player_class] = player_obj
        await inter.response.defer()
        await update_select_options()
        if bluMessage is None:
            bluMessage = await messages.announceChannel.send("BLU Team:\n" + await list_players(blu_team))
            redMessage = await messages.announceChannel.send("RED Team:\n" + await list_players(red_team))
            await redMessage.pin()
            await bluMessage.pin()
            active_pug.start_pug.messages_to_delete.append(bluMessage)
            active_pug.start_pug.messages_to_delete.append(redMessage)
        else:
            await bluMessage.edit(content="BLU Team:\n" + await list_players(blu_team))
            await announce_string()
    else:
        if len(inter.values) == 0:
            players_changed_late.append(red_team[player_class])
            red_team[player_class] = None
        else:
            player_obj = messages.guild.get_member_named(inter.values[0])
            if player_obj is None:
                await inter.send("Player not found")
                return
            await inform_player_of_late_change(player_obj, player_class.capitalize())
            red_team[player_class] = player_obj
        await inter.response.defer()
        await update_select_options()
        if redMessage is None:
            bluMessage = await messages.announceChannel.send("BLU Team:\n" + await list_players(blu_team))
            redMessage = await messages.announceChannel.send("RED Team:\n" + await list_players(red_team))
            await redMessage.pin()
            await bluMessage.pin()
            active_pug.start_pug.messages_to_delete.append(bluMessage)
            active_pug.start_pug.messages_to_delete.append(redMessage)
        else:
            await redMessage.edit(content="RED Team:\n" + await list_players(red_team))
            await announce_string()


async def load_select_options(team: str, player_class: str) -> List[discord.SelectOption]:
    options: List[discord.SelectOption] = []
    for player, _pref in active_pug.start_pug.signups[active_pug.start_pug.emojis_ids[player_class]]:
        option = discord.SelectOption(label=player.display_name)
        if team == 'BLU' and blu_team[player_class] == player:
            option.default = True
        elif team == 'RED' and red_team[player_class] == player:
            option.default = True
        elif player in blu_team.values() or player in red_team.values():
            continue
        options.append(option)
    return options


async def update_select_options():
    for message in current_select_msgs:
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
    for view in views:
        if not inter.response.is_done():
            await inter.response.send_message(f"BLU Team ({views.index(view)+1}/{len(views)})", view=view)
            message = await inter.original_message()
        else:
            message = await inter.followup.send(f"BLU Team ({views.index(view)+1}/{len(views)})", view=view)
        current_select_msgs.append(message)

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
        if not inter.response.is_done():
            message = await inter.response.send(f"RED Team ({views.index(view) + 1}/{len(views)})", view=view)
        else:
            message = await inter.followup.send(f"RED Team ({views.index(view) + 1}/{len(views)})", view=view)
        current_select_msgs.append(message)


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


async def announce_string(connect_string=None, timestamp=None):
    global stringMessage, reminderMessage, timeMessage
    msg = f"{bluMessage.content}\n\n{redMessage.content}"
    if connect_string is None:  # Function was called to update players/post early reminder
        if reminderMessage is not None:  # Check if reminder message already exists
            await reminderMessage.edit(content=msg)
        else:
            if timestamp is None:  # Function was called to update players, but no reminder exists, so exit
                return
            timeMessage = await bluMessage.channel.send(f"**Reminder:** pug is <t:{timestamp}:R>. Please withdraw if you are not able to make it")
            reminderMessage = await bluMessage.channel.send(msg)
            active_pug.start_pug.messages_to_delete.append(timeMessage)
        return
    if stringMessage is None:  # First string
        stringMessage = await bluMessage.channel.send(connect_string)
        await reminderMessage.delete()
        reminderMessage = await bluMessage.channel.send(msg)
        active_pug.start_pug.messages_to_delete.append(stringMessage)
        active_pug.start_pug.messages_to_delete.append(reminderMessage)
    else:  # Updated string
        await stringMessage.edit(content=connect_string)


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
        await bluMessage.edit(content="BLU Team:\n" + await list_players(blu_team))
        await redMessage.edit(content="RED Team:\n" + await list_players(red_team))
        await announce_string()
        await inter.send(f"{blu_team[player_class].display_name} is now BLU {player_class} & {red_team[player_class].display_name} is now RED {player_class}.")


async def list_unassigned_players(inter: discord.ApplicationCommandInteraction):
    unassigned = []
    for player in active_pug.start_pug.player_classes.keys():
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


async def ping_not_present(inter: discord.ApplicationCommandInteraction):
    player: discord.Member
    signed_up_players = set(blu_team.values()) | set(red_team.values())
    present_players = set(messages.bluChannel.members) | set(messages.redChannel.members) | set(messages.waitingChannel.members)
    absent_players = [player.mention for player in (signed_up_players - present_players)]
    message = await messages.announceChannel.send(f"Join up! {', '.join(absent_players)}")
    ping_messages.append(message)
    active_pug.start_pug.messages_to_delete.append(message)
    await inter.send("Absent players have been pinged!")


async def inform_player_of_late_change(player: discord.Member, player_class: str):
    global players_changed_late
    pug_starts_soon, _timestamp = await active_pug.pug_scheduler.after_penalty_trigger_check()
    signed_up_players = list(blu_team.values()) + list(red_team.values())
    if pug_starts_soon and (player in signed_up_players or player in players_changed_late):
        await player.send(f"**Please Note:** Your class in the upcoming Bakes Pug has been switched to **{player_class}**.")
    elif pug_starts_soon:
        await player.send(f"**IMPORTANT:** You have just been assigned to play **{player_class}** in the upcoming Bakes Pug.\nIf you are unable to make it, please withdraw by pressing ❌ on the pug announcement.")





