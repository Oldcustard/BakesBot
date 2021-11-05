import sqlite3
import discord


def add_medic(player: discord.User):
    player_name = player.name
    db = sqlite3.connect('players.db')
    c = db.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS medics
    (player TEXT PRIMARY KEY, weeks_remaining INTEGER)''')

    c.execute('''SELECT player, weeks_remaining FROM medics WHERE player = ?''', (player_name,))
    if c.fetchone() is None:
        c.execute('''INSERT INTO medics (player, weeks_remaining)
        VALUES (?, ?)''', (player_name, 3))

    db.commit()
    db.close()
