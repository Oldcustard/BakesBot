import sqlite3
import urllib.request
import json
from elosports.elo import Elo

import discord.ext.commands

import player_selection


async def fetch_logs(ctx: discord.ext.commands.Context, log_url):
    log_id = log_url.split('.tf/')[1]
    log_json = urllib.request.urlopen("http://logs.tf/json/" + log_id)
    log_json = json.load(log_json)
    score = (log_json['teams']['Blue']['score'], log_json['teams']['Red']['score'])
    winning_team = 'BLU' if score[0] > score[1] else 'RED'
    await ctx.channel.send(f"Winning team: {winning_team}. Score {score[0]}-{score[1]}")
    await update_elo(score[0], score[1])


async def update_elo(blu_score, red_score):
    db = sqlite3.connect('players.db')
    c = db.cursor()

    elo = Elo(k=32)
    blu_elo = []
    red_elo = []

    c.execute('''CREATE TABLE IF NOT EXISTS elo
    (player_id TEXT PRIMARY KEY, player_name TEXT, Scout INTEGER DEFAULT 1500, Soldier INTEGER DEFAULT 1500, 
    Pyro INTEGER DEFAULT 1500, Demo INTEGER DEFAULT 1500, Heavy INTEGER DEFAULT 1500, Engi INTEGER DEFAULT 1500, 
    Medic INTEGER DEFAULT 1500, Sniper INTEGER DEFAULT 1500, Spy INTEGER DEFAULT 1500)''')

    for player_class, player in player_selection.blu_team.items():
        if player is None:
            continue
        c.execute('''SELECT player_id FROM elo WHERE player_id = ?''', (player.id,))
        row = c.fetchone()
        if row is None:  # Player does not have an elo assigned.
            c.execute('''INSERT INTO elo (player_id, player_name)
                     VALUES (?, ?)''', (player.id, player.name))
        c.execute(f'''SELECT player_id, {player_class} FROM elo WHERE player_id = ?''', (player.id,))  # String substitution not an issue here
        row = c.fetchone()
        elo.add_player(row[0], row[1])
        blu_elo.append(row[1])

    for player_class, player in player_selection.red_team.items():
        if player is None:
            continue
        c.execute('''SELECT player_id FROM elo WHERE player_id = ?''', (player.id,))
        row = c.fetchone()
        if row is None:  # Player does not have an elo assigned.
            c.execute('''INSERT INTO elo (player_id, player_name)
                             VALUES (?, ?)''', (player.id, player.name))
        c.execute(f'''SELECT player_id, {player_class} FROM elo WHERE player_id = ?''', (player.id,))
        row = c.fetchone()
        elo.add_player(row[0], row[1])
        red_elo.append(row[1])

    blu_avg = sum(blu_elo)/len(blu_elo)
    red_avg = sum(red_elo)/len(red_elo)
    elo.add_player("BluAVG", blu_avg)
    elo.add_player("RedAVG", red_avg)

    for player_class, player in player_selection.blu_team.items():
        if player is None:
            continue
        for i in range(blu_score):
            elo.game_over(str(player.id), "RedAVG", 'N')
        c.execute(f'''UPDATE elo 
        SET {player_class} = ? WHERE player_id = ?''', (elo.ratingDict[str(player.id)], player.id))

    for player_class, player in player_selection.red_team.items():
        if player is None:
            continue
        for i in range(red_score):
            elo.game_over(str(player.id), "BluAVG", 'N')
        c.execute(f'''UPDATE elo 
        SET {player_class} = ? WHERE player_id = ?''', (elo.ratingDict[str(player.id)], player.id))

    db.commit()
    db.close()
