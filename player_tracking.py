import sqlite3
import discord

import messages
import active_pug
import player_selection


async def add_medic(player: discord.User):
    player_id = player.id
    db = sqlite3.connect('players.db')
    try:
        c = db.cursor()

        c.execute('''SELECT player, pugs_remaining FROM medics WHERE player = ?''', (player_id,))
        if c.fetchone() is None:  # Player is not on the medics table, add them with 3 weeks remaining
            c.execute('''INSERT INTO medics (player, pugs_remaining)
            VALUES (?, ?)''', (player_id, 6))
        else:  # Player is already on the medics table, reset their weeks remaining to 3
            c.execute('''UPDATE medics
            SET pugs_remaining = 6
            WHERE player = ?''', (player_id,))

        c.execute('''SELECT player, pugs_remaining FROM medics''')
        medics = c.fetchall()

        db.commit()
        return medics
    finally:
        db.close()


async def decrement_medic_counters():
    db = sqlite3.connect('players.db')
    try:
        c = db.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS medics
            (player TEXT PRIMARY KEY, pugs_remaining INTEGER)''')

        c.execute('''UPDATE medics
        SET pugs_remaining = pugs_remaining - 1''')  # Reduce weeks remaining by 1

        c.execute('''DELETE FROM medics
        WHERE pugs_remaining = 0''')  # Delete from table if weeks remaining is 0

        c.execute('''SELECT player, pugs_remaining FROM medics''')
        medics = c.fetchall()

        db.commit()
        return medics
    finally:
        db.close()


async def update_early_signups():
    db = sqlite3.connect('players.db')
    try:
        c = db.cursor()

        c.execute('''SELECT player, pugs_remaining FROM medics''')
        medics = c.fetchall()
        for medic in medics:
            player: discord.Member
            player = messages.guild.get_member(int(medic[0]))
            await player.add_roles(messages.medic_role)  # Give medics from table the medic role
        member: discord.Member
        medics = dict(medics)
        for member in messages.medic_role.members:
            if str(member.id) not in medics.keys():
                await member.remove_roles(messages.medic_role)  # Remove medic role from players not in the medic table
    finally:
        db.close()


async def warn_player(player: discord.User):
    player_name = player.display_name
    player_id = player.id
    db = sqlite3.connect('players.db')
    try:
        c = db.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS warnings
            (player TEXT PRIMARY KEY, warned_pugs_remaining INTEGER, total_warnings INTEGER, pug_banned BOOLEAN)''')

        c.execute('''SELECT player, warned_pugs_remaining, total_warnings FROM warnings WHERE player = ?''', (player_id,))
        row = c.fetchone()

        if row is None:  # Player is not on the warnings table, add them with 1 active warning
            c.execute('''INSERT INTO warnings (player, warned_pugs_remaining, total_warnings, pug_banned)
             VALUES (?, ?, ?, ?)''', (player_id, 2, 1, 0))
            await player.send(f"You have been warned for baiting. This may be due to a late withdrawal, or not showing up to a pug. This warning will last for 1 week.")
            await messages.send_to_admin(f"{player_name} has been warned. {player_name} has 1 total warning.")
            print(f"{player_name} has been warned.")
        elif row[1] == 1: # Player had a warning already, they will be reset to 2 weeks for baiting again.
            c.execute('''UPDATE warnings
                     SET warned_pugs_remaining = 2, total_warnings = total_warnings + 1
                     WHERE player = ?''', (player_id,))
            await player.send(f"You have been warned for baiting. This may be due to a late withdrawal, or not showing up to a pug. This warning will last for 1 week.")
            await messages.send_to_admin(f"{player_name} has been warned. They already had an active warning so their penalty has been reset to 2 pugs.  {player_name} has {row[2] + 1} total warning{'s' if row[2] + 1 != 1 else ''}.")
            print(f"{player_name} has been warned.")
        elif row[1] == 2:  # Player is on the warnings table, and has already been warned for this pug
            await messages.send_to_admin(f"{player_name} has already been warned for this pug, no warning added. {player_name} has {row[2]} total warning{'s' if row[2] != 1 else ''}.")
            print(f"{player_name} has already been warned for this pug, no warning added.")
        else:  # Player is already on the warnings table, give them a current warning and add 1 to their total
            c.execute('''UPDATE warnings
             SET warned_pugs_remaining = 2, total_warnings = total_warnings + 1
             WHERE player = ?''', (player_id,))
            await player.send(f"You have been warned for baiting. This may be due to a late withdrawal, or not showing up to a pug. This warning will last for 1 week.")
            await messages.send_to_admin(f"{player_name} has been warned. {player_name} has {row[2] + 1} total warning{'s' if row[2] + 1 != 1 else ''}.")
            print(f"{player_name} has been warned.")

        db.commit()
    finally:
        db.close()


async def unwarn_player(player: discord.User):
    player_name = player.display_name
    player_id = player.id
    db = sqlite3.connect('players.db')
    try:
        c = db.cursor()

        c.execute('''SELECT player, warned_pugs_remaining, total_warnings FROM warnings WHERE player = ?''', (player_id,))
        row = c.fetchone()

        if row is None:
            await messages.send_to_admin(f"{player_name} has had no recorded warnings. No action taken.")
        elif not row[1]:
            await messages.send_to_admin(f"{player_name} is not currently warned. No action taken.")
        else:
            c.execute('''UPDATE warnings
                     SET warned_pugs_remaining = 0, total_warnings = total_warnings - 1
                     WHERE player = ?''', (player_id,))
            await player.send(f"Your active warning for baiting has been removed by an admin.")
            await messages.send_to_admin(f"{player_name} has had their warning removed. They now have {row[2] - 1} total warning{'s' if row[2] - 1 != 1 else ''}.")
            print(f"{player_name} has been unwarned.")

        db.commit()
    finally:
        db.close()


async def decrement_active_warnings():
    db = sqlite3.connect('players.db')
    try:
        c = db.cursor()

        c.execute('''UPDATE warnings
           SET warned_pugs_remaining = warned_pugs_remaining - 1 WHERE warned_pugs_remaining > 0''')  # Decrement active warnings.

        db.commit()
    finally:
        db.close()


async def check_active_baiter(player: discord.Member):
    player_name = player.display_name
    player_id = player.id
    db = sqlite3.connect('players.db')
    try:
        c = db.cursor()

        c.execute('''SELECT player, warned_pugs_remaining, total_warnings FROM warnings WHERE player = ?''', (player_id,))
        row = c.fetchone()
        if row is None:  # Player not in database
            return False
        else:
            return bool(row[1])  # Return True or False depending on active warning status
    finally:
        db.close()


async def pug_ban(player: discord.Member, reason: str):
    player_name = player.name
    player_id = player.id
    db = sqlite3.connect('players.db')
    try:
        c = db.cursor()

        c.execute('''SELECT player, pug_banned FROM warnings WHERE player = ?''', (player_id,))
        row = c.fetchone()

        if row is None:  # Player is not on the warnings table, add them and give them a pug ban
            c.execute('''INSERT INTO warnings (player, warned_pugs_remaining, total_warnings, pug_banned)
             VALUES (?, ?, ?, ?)''', (player_id, 0, 0, 1))
            await player.add_roles(messages.banned_role)
            await player.remove_roles(messages.gamer_role)
            await player.send(f"You have been banned from playing in Bakes Pugs.\nReason: {reason}")
            await messages.send_to_admin(f"{player_name} has been Pug Banned.")
            print(f"{player_name} has been pug banned.")
        elif not row[1]:
            c.execute('''UPDATE warnings
                     SET pug_banned = 1 
                     WHERE player = ?''', (player_id,))
            c.execute('''DELETE FROM medics
            WHERE player = ?''', (player_id,))  # Remove player from medic table
            db.commit()
            await update_early_signups()
            await player.add_roles(messages.banned_role)
            await player.remove_roles(messages.gamer_role)
            await player.send(f"You have been banned from playing in Bakes Pugs.\nReason: {reason}")
            await messages.send_to_admin(f"{player_name} has been Pug Banned.")
            print(f"{player_name} has been pug banned.")
        elif row[1]:
            await messages.send_to_admin(f"{player_name} is already Pug Banned. No action taken.")

        db.commit()
    finally:
        db.close()


async def pug_unban(player: discord.Member):
    player_name = player.name
    player_id = player.id
    db = sqlite3.connect('players.db')
    try:
        c = db.cursor()

        c.execute('''SELECT player, pug_banned FROM warnings WHERE player = ?''', (player_id,))
        row = c.fetchone()

        if row is None or not row[1]:  # No player ban recorded, but if they have the banned role, remove it anyway
            await player.remove_roles(messages.banned_role)
            await player.add_roles(messages.gamer_role)
            await messages.send_to_admin(f"{player_name} had no ban recorded. If they had the Pug Banned role it has been removed.")
            print(f"{player_name} has been unbanned.")
        elif row[1]:
            c.execute('''UPDATE warnings
                     SET pug_banned = 0 
                     WHERE player = ?''', (player_id,))
            await player.remove_roles(messages.banned_role)
            await player.add_roles(messages.gamer_role)
            await messages.send_to_admin(f"{player_name} has been unbanned.")
            await player.send(f"You have been unbanned from playing in Bakes Pugs.")
            print(f"{player_name} has been unbanned.")

        db.commit()
    finally:
        db.close()


async def player_status(ctx, player: discord.Member):
    player_name = player.display_name
    player_id = player.id
    db = sqlite3.connect('players.db')
    try:
        c = db.cursor()

        c.execute('''SELECT player, warned_pugs_remaining, total_warnings, pug_banned FROM warnings WHERE player = ?''', (player_id,))
        warnings_row = c.fetchone()
        c.execute('''SELECT player, pugs_remaining FROM medics WHERE player = ?''', (player_id,))
        medics_row = c.fetchone()

        if warnings_row is None:
            active_warning = "**not currently warned**"
            total_warnings = 0
        elif warnings_row[1] == 0:
            active_warning = "**not currently warned**"
            total_warnings = warnings_row[2]
        else:
            active_warning = f"**currently warned for {warnings_row[1]} more pugs**"
            total_warnings = warnings_row[2]

        if warnings_row is None:
            banned_status = "**not currently banned**"
        elif warnings_row[3]:
            banned_status = "**currently banned**"
        else:
            banned_status = "**not currently banned**"

        if medics_row is None:
            medic_status = "**does not have Medic priority**."
        else:
            medic_status = f"**has Medic priority** for **{medics_row[1]}** more pug{'s' if medics_row[1] != 1 else ''}."

        if player in active_pug.start_pug.player_classes.keys():
            signed_up_classes = ', '.join([str(emoji) for emoji in active_pug.start_pug.player_classes[player]])
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

        await ctx.channel.send(f"{player_name} {medic_status}\nThey are {active_warning} and have **{total_warnings}** total warning{'s' if total_warnings != 1 else ''}. They are {banned_status} from playing in pugs.\nThey are signed up for {signed_up_classes} and {assigned_message}")
    finally:
        db.close()
