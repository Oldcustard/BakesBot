import sqlite3
import discord

import messages


async def add_medic(player: discord.User):
    player_name = player.name
    db = sqlite3.connect('players.db')
    c = db.cursor()

    c.execute('''SELECT player, weeks_remaining FROM medics WHERE player = ?''', (player_name,))
    if c.fetchone() is None:  # Player is not on the medics table, add them with 3 weeks remaining
        c.execute('''INSERT INTO medics (player, weeks_remaining)
        VALUES (?, ?)''', (player_name, 3))
    else:  # Player is already on the medics table, reset their weeks remaining to 3
        c.execute('''UPDATE medics
        SET weeks_remaining = 3
        WHERE player = ?''', (player_name,))

    c.execute('''SELECT player, weeks_remaining FROM medics''')
    medics = c.fetchall()

    db.commit()
    db.close()
    return medics


async def decrement_medic_counters():
    db = sqlite3.connect('players.db')
    c = db.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS medics
        (player TEXT PRIMARY KEY, weeks_remaining INTEGER)''')

    c.execute('''UPDATE medics
    SET weeks_remaining = weeks_remaining - 1''')  # Reduce weeks remaining by 1

    c.execute('''DELETE FROM medics
    WHERE weeks_remaining = 0''')  # Delete from table if weeks remaining is 0

    c.execute('''SELECT player, weeks_remaining FROM medics''')
    medics = c.fetchall()

    db.commit()
    db.close()
    return medics


async def update_early_signups():
    db = sqlite3.connect('players.db')
    c = db.cursor()

    c.execute('''SELECT player, weeks_remaining FROM medics''')
    medics = c.fetchall()
    for medic in medics:
        player: discord.Member
        player = messages.guild.get_member_named(medic[0])
        await player.add_roles(messages.medic_role)  # Give medics from table the medic role
    member: discord.Member
    medics = dict(medics)
    for member in messages.medic_role.members:
        if member.name not in medics.keys():
            await member.remove_roles(messages.medic_role)  # Remove medic role from players not in the medic table


async def warn_player(ctx: discord.ext.commands.Context, player: discord.User):
    player_name = player.name
    db = sqlite3.connect('players.db')
    c = db.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS warnings
        (player TEXT PRIMARY KEY, currently_warned BOOLEAN, total_warnings INTEGER)''')

    c.execute('''SELECT player, currently_warned, total_warnings FROM warnings WHERE player = ?''', (player_name,))
    row = c.fetchone()

    if row is None:  # Player is not on the warnings table, add them with 1 active warning
        c.execute('''INSERT INTO warnings (player, currently_warned, total_warnings)
         VALUES (?, ?, ?)''', (player_name, 1, 1))
        await ctx.channel.send(f"{player_name} has been warned. {player_name} has 1 total warning.")
        print(f"{player_name} has been warned.")
    elif row[1]: # Player is on the warnings table, and has already been warned for this pug
        await ctx.channel.send(f"{player_name} has already been warned for this pug, no warning added. {player_name} has {row[2]} total warning{'s' if row[2] != 1 else ''}.")
        print(f"{player_name} has already been warned for this pug, no warning added.")
    else:  # Player is already on the warnings table, give them a current warning and add 1 to their total
        c.execute('''UPDATE warnings
         SET currently_warned = 1, total_warnings = total_warnings + 1
         WHERE player = ?''', (player_name,))
        await ctx.channel.send(f"{player_name} has been warned. {player_name} has {row[2] + 1} total warning{'s' if row[2] + 1 != 1 else ''}.")
        print(f"{player_name} has been warned.")

    db.commit()
    db.close()

async def unwarn_player(ctx: discord.ext.commands.Context, player: discord.User):
    player_name = player.name
    db = sqlite3.connect('players.db')
    c = db.cursor()

    c.execute('''SELECT player, currently_warned, total_warnings FROM warnings WHERE player = ?''', (player_name,))
    row = c.fetchone()

    if row is None:
        await ctx.channel.send(f"{player_name} has had no recorded warnings. No action taken.")
    elif not row[1]:
        await ctx.channel.send(f"{player_name} is not currently warned. No action taken.")
    else:
        c.execute('''UPDATE warnings
                 SET currently_warned = 0, total_warnings = total_warnings - 1
                 WHERE player = ?''', (player_name,))
        await ctx.channel.send(f"{player_name} has had their warning removed. They now have {row[2] - 1} total warning{'s' if row[2] - 1 != 1 else ''}.")
        print(f"{player_name} has been unwarned.")

    db.commit()
    db.close()

async def clear_active_warnings():
    db = sqlite3.connect('players.db')
    c = db.cursor()

    c.execute('''UPDATE warnings
       SET currently_warned = 0''')  # Clear all active warnings for the week.

    db.commit()
    db.close()