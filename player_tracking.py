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

    c.execute('''SELECT player FROM medics''')
    medics = c.fetchall()
    for medic in medics:
        print(medic[0])
        player: discord.Member
        player = messages.guild.get_member_named(medic[0])
        print(player)
        await player.add_roles(messages.medic_role)  # Give medics from table the medic role
    member: discord.Member
    for member in messages.medic_role.members:
        if member not in medics:
            await member.remove_roles(messages.medic_role)  # Remove medic role from players not in the medic table
