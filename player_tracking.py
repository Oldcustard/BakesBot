import sqlite3
import discord


async def add_medic(player: discord.User):
    player_name = player.name
    db = sqlite3.connect('players.db')
    c = db.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS medics
    (player TEXT PRIMARY KEY, weeks_remaining INTEGER)''')

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
