import sqlite3
import discord

import messages
import player_selection
import start_pug


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


async def warn_player(player: discord.User):
    player_name = player.name
    db = sqlite3.connect('players.db')
    c = db.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS warnings
        (player TEXT PRIMARY KEY, currently_warned BOOLEAN, total_warnings INTEGER, pug_banned BOOLEAN)''')


    c.execute('''SELECT player, currently_warned, total_warnings FROM warnings WHERE player = ?''', (player_name,))
    row = c.fetchone()

    if row is None:  # Player is not on the warnings table, add them with 1 active warning
        c.execute('''INSERT INTO warnings (player, currently_warned, total_warnings)
         VALUES (?, ?, ?)''', (player_name, 1, 1))
        await messages.send_to_admin(f"{player_name} has been warned. {player_name} has 1 total warning.")
        print(f"{player_name} has been warned.")
    elif row[1]:  # Player is on the warnings table, and has already been warned for this pug
        await messages.send_to_admin(f"{player_name} has already been warned for this pug, no warning added. {player_name} has {row[2]} total warning{'s' if row[2] != 1 else ''}.")
        print(f"{player_name} has already been warned for this pug, no warning added.")
    else:  # Player is already on the warnings table, give them a current warning and add 1 to their total
        c.execute('''UPDATE warnings
         SET currently_warned = 1, total_warnings = total_warnings + 1
         WHERE player = ?''', (player_name,))
        await messages.send_to_admin(f"{player_name} has been warned. {player_name} has {row[2] + 1} total warning{'s' if row[2] + 1 != 1 else ''}.")
        print(f"{player_name} has been warned.")

    db.commit()
    db.close()


async def unwarn_player(player: discord.User):
    player_name = player.name
    db = sqlite3.connect('players.db')
    c = db.cursor()

    c.execute('''SELECT player, currently_warned, total_warnings FROM warnings WHERE player = ?''', (player_name,))
    row = c.fetchone()

    if row is None:
        await messages.send_to_admin(f"{player_name} has had no recorded warnings. No action taken.")
    elif not row[1]:
        await messages.send_to_admin(f"{player_name} is not currently warned. No action taken.")
    else:
        c.execute('''UPDATE warnings
                 SET currently_warned = 0, total_warnings = total_warnings - 1
                 WHERE player = ?''', (player_name,))
        await messages.send_to_admin(f"{player_name} has had their warning removed. They now have {row[2] - 1} total warning{'s' if row[2] - 1 != 1 else ''}.")
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


async def check_active_baiter(player: discord.Member):
    player_name = player.name
    db = sqlite3.connect('players.db')
    c = db.cursor()

    c.execute('''SELECT player, currently_warned, total_warnings FROM warnings WHERE player = ?''', (player_name,))
    row = c.fetchone()
    if row is None:  # Player not in database
        return False
    else:
        return bool(row[1])  # Return True or False depending on active warning status


async def pug_ban(player: discord.Member, reason : str):
    player_name = player.name
    db = sqlite3.connect('players.db')
    c = db.cursor()

    c.execute('''SELECT player, pug_banned FROM warnings WHERE player = ?''', (player_name,))
    row = c.fetchone()

    if row is None:  # Player is not on the warnings table, add them and give them a pug ban
        c.execute('''INSERT INTO warnings (player, currently_warned, total_warnings, pug_banned)
         VALUES (?, ?, ?, ?)''', (player_name, 0, 0, 1))
        await player.add_roles()
        await user.send()
        await messages.send_to_admin(f"{player_name} has been pug_banned.")
        print(f"{player_name} has been pug banned.")
    elif not row[1]:
        await player.add_roles()
        await user.send()
        await messages.send_to_admin(f"{player_name} has been pug_banned.")
        print(f"{player_name} has been pug banned.")
    elif row[1]:
        await messages.send_to_admin(f"{player_name} is already pug banned. No action taken.")



async def player_status(ctx, player: discord.Member):
    player_name = player.name
    db = sqlite3.connect('players.db')
    c = db.cursor()

    c.execute('''SELECT player, currently_warned, total_warnings FROM warnings WHERE player = ?''', (player_name,))
    warnings_row = c.fetchone()
    c.execute('''SELECT player, weeks_remaining FROM medics WHERE player = ?''', (player_name,))
    medics_row = c.fetchone()

    if warnings_row is None:
        active_warning = "**not currently warned**"
        total_warnings = 0
    elif warnings_row[1] == 0:
        active_warning = "**not currently warned**"
        total_warnings = warnings_row[2]
    else:
        active_warning = "**currently warned**"
        total_warnings = warnings_row[2]

    if medics_row is None:
        medic_status = "**does not have Medic priority**."
    else:
        medic_status = f"**has Medic priority** for **{medics_row[1]}** more week{'s' if medics_row[1] != 1 else ''}."

    if player_name in start_pug.player_classes.keys():
        signed_up_classes = ', '.join([str(emoji) for emoji in start_pug.player_classes[player_name]])
    else:
        signed_up_classes = "**no classes**"

    if player in player_selection.blu_team.values():
        assigned_classes = []
        for tf2class, player_obj in player_selection.blu_team.items():
            if player_obj == player:
                assigned_classes.append(tf2class)
        assigned_message = f"are assigned to **{' and '.join(assigned_classes)}** on **BLU** team."

    elif player in player_selection.red_team.values():
        assigned_classes = []
        for tf2class, player_obj in player_selection.red_team.items():
            if player_obj == player:
                assigned_classes.append(tf2class)
        assigned_message = f"are assigned to **{' and '.join(assigned_classes)}** on **RED** team."
    else:
        assigned_message = 'are **not assigned to any class.**'

    await ctx.channel.send(f"{player_name} {medic_status}\nThey are {active_warning} and have **{total_warnings}** total warning{'s' if total_warnings != 1 else ''}.\nThey are signed up for {signed_up_classes} and {assigned_message}")
