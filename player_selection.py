import discord.ext.commands
from enum import Enum


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


async def select_player(ctx: discord.ext.commands.Context, team: str, player_class: str, player: str):
    if len(ctx.message.mentions) > 0:
        player_obj = ctx.message.mentions[0]
    else:
        player_obj = ctx.guild.get_member_named(player)
        if player_obj is None:
            await ctx.channel.send(f"Player {player} not found. Try different capitalisation or mention them directly.")
            return
    if player_class.capitalize() not in blu_team:
        await ctx.channel.send(f"Class not found")
        return
    if team.lower() in blu_name:
        blu_team[player_class.capitalize()] = player_obj
        await ctx.channel.send(f"{player_obj} selected for BLU {player_class}")
    elif team.lower() == 'red':
        red_team[player_class.capitalize()] = player_obj
        await ctx.channel.send(f"{player_obj} selected for RED {player_class}")
    else:
        await ctx.channel.send("Team not recognised")
        return
