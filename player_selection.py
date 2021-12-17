from typing import Dict, List

import discord.ext.commands

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

bluMessage: discord.Message = None
redMessage: discord.Message = None
stringMessage: discord.Message = None
reminderMessage: discord.Message = None
timeMessage: discord.Message = None

ping_messages: List[discord.Message] = []


async def select_player(ctx: discord.ext.commands.Context, team: str, player_class: str, player_obj: discord.Member):
    global bluMessage, redMessage
    if player_obj is None:
        await ctx.channel.send(f"Player {player_obj} not found. Try different capitalisation or mention them directly.")
        return
    if player_class.capitalize() not in blu_team:
        await ctx.channel.send(f"Class not recognised")
        return
    if team.lower() in blu_name:
        await inform_player_of_late_change(player_obj, player_class.capitalize())
        blu_team[player_class.capitalize()] = player_obj
        await ctx.channel.send(f"{player_obj.display_name} selected for BLU {player_class}")
        if bluMessage is None:
            bluMessage = await messages.announceChannel.send("BLU Team:\n" + await list_players(blu_team))
            redMessage = await messages.announceChannel.send("RED Team:\n" + await list_players(red_team))
            await redMessage.pin()
            await bluMessage.pin()
        else:
            await bluMessage.edit(content="BLU Team:\n" + await list_players(blu_team))
            await announce_string()

    elif team.lower() == 'red':
        await inform_player_of_late_change(player_obj, player_class.capitalize())
        red_team[player_class.capitalize()] = player_obj
        await ctx.channel.send(f"{player_obj.display_name} selected for RED {player_class}")
        if redMessage is None:
            bluMessage = await messages.announceChannel.send("BLU Team:\n" + await list_players(blu_team))
            redMessage = await messages.announceChannel.send("RED Team:\n" + await list_players(red_team))
            await redMessage.pin()
            await bluMessage.pin()
        else:
            await redMessage.edit(content="RED Team:\n" + await list_players(red_team))
            await announce_string()
    else:
        await ctx.channel.send("Team not recognised")
        return


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
        return
    if stringMessage is None:  # First string
        stringMessage = await bluMessage.channel.send(connect_string)
        await reminderMessage.delete()
        reminderMessage = await bluMessage.channel.send(msg)
    else:  # Updated string
        await stringMessage.edit(content=connect_string)


async def swap_class_across_teams(ctx: discord.ext.commands.Context, player_class: str):
    global bluMessage, redMessage
    player_class = player_class.capitalize()
    if player_class not in blu_team:
        await ctx.channel.send(f"Class not recognised.")
        return
    if bluMessage is None or redMessage is None:
        await ctx.channel.send(f"No players are assigned to classes yet.")
        return
    else:
        blu_team[player_class], red_team[player_class] = red_team[player_class], blu_team[player_class]
        await bluMessage.edit(content="BLU Team:\n" + await list_players(blu_team))
        await redMessage.edit(content="RED Team:\n" + await list_players(red_team))
        await announce_string()
        await ctx.channel.send(f"{blu_team[player_class].display_name} is now BLU {player_class} & {red_team[player_class].display_name} is now RED {player_class}.")


async def list_unassigned_players(ctx: discord.ext.commands.Context):
    unassigned = []
    for player in active_pug.start_pug.player_classes.keys():
        if player not in blu_team.values() and player not in red_team.values():
            unassigned.append(player.display_name)
    await ctx.channel.send("Players yet to be assigned a class: " + ", ".join(unassigned))


async def drag_into_team_vc(ctx: discord.ext.commands.Context):
    member: discord.Member
    for member in ctx.author.voice.channel.members:
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


async def drag_into_same_vc(ctx: discord.ext.commands.Context):
    member: discord.Member
    for member in messages.bluChannel.members:
        try:
            await member.move_to(ctx.author.voice.channel)
        except discord.HTTPException:
            continue
    for member in messages.redChannel.members:
        try:
            await member.move_to(ctx.author.voice.channel)
        except discord.HTTPException:
            continue


async def ping_not_present():
    player: discord.Member
    signed_up_players = set(blu_team.values()) | set(red_team.values())
    present_players = set(messages.bluChannel.members) | set(messages.redChannel.members) | set(messages.waitingChannel.members)
    absent_players = [player.mention for player in (signed_up_players - present_players)]
    message = await messages.announceChannel.send(f"Join up! {', '.join(absent_players)}")
    ping_messages.append(message)
    await messages.send_to_admin("Absent players have been pinged!")


async def inform_player_of_late_change(player: discord.Member, player_class: str):
    pug_starts_soon, _timestamp = await active_pug.pug_scheduler.after_penalty_trigger_check()
    signed_up_players = list(blu_team.values()) + list(red_team.values())
    if pug_starts_soon and player in signed_up_players:
        await player.send(f"Your class in the upcoming Bakes Pug has been switched to {player_class}. As the pug is less than 3 hours away we are letting you know.")
    elif pug_starts_soon:
        await player.send(f"You have been assigned to play {player_class} in the upcoming Bakes Pug. As the pug is less than 3 hours away we are letting you know.\n If you are unable to make it, please withdraw by pressing the ❌ on the pug announcement.")





