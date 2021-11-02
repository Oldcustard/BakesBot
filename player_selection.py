from typing import Dict

import discord.ext.commands

import messages

blu_team = {
    'Scout': None,
    'Soldier': None,
    'Pyro': None,
    'Demoman': None,
    'Heavy': None,
    'Engineer': None,
    'Medic': None,
    'Sniper': None,
    'Spy': None
}

red_team = {
    'Scout': None,
    'Soldier': None,
    'Pyro': None,
    'Demoman': None,
    'Heavy': None,
    'Engineer': None,
    'Medic': None,
    'Sniper': None,
    'Spy': None
}

blu_name = ['blu', 'blue']

bluMessage: discord.Message = None
redMessage: discord.Message = None


async def select_player(ctx: discord.ext.commands.Context, team: str, player_class: str, player_obj: discord.Member):
    global bluMessage, redMessage
    if player_obj is None:
        await ctx.channel.send(f"Player {player_obj} not found. Try different capitalisation or mention them directly.")
        return
    if player_class.capitalize() not in blu_team:
        await ctx.channel.send(f"Class not recognised")
        return
    if team.lower() in blu_name:
        blu_team[player_class.capitalize()] = player_obj
        await ctx.channel.send(f"{player_obj} selected for BLU {player_class}")
        if bluMessage is None:
            bluMessage = await messages.send_to_admin("BLU Team:\n" + await list_players(blu_team))
            redMessage = await messages.send_to_admin("RED Team:\n" + await list_players(red_team))
            await redMessage.pin()
            await bluMessage.pin()
        else:
            await bluMessage.edit(content="BLU Team:\n" + await list_players(blu_team))

    elif team.lower() == 'red':
        red_team[player_class.capitalize()] = player_obj
        await ctx.channel.send(f"{player_obj} selected for RED {player_class}")
        if redMessage is None:
            bluMessage = await messages.send_to_admin("BLU Team:\n" + await list_players(blu_team))
            redMessage = await messages.send_to_admin("RED Team:\n" + await list_players(red_team))
            await redMessage.pin()
            await bluMessage.pin()
        else:
            await redMessage.edit(content="RED Team:\n" + await list_players(red_team))
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
