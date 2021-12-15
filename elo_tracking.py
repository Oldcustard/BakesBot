import sqlite3
import urllib.request
import json
from elosports.elo import Elo

import disnake.ext.commands

import player_selection


async def fetch_logs(ctx: disnake.ext.commands.Context, log_url):
    log_id = log_url.split('.tf/')[1]
    log_json = urllib.request.urlopen("http://logs.tf/json/" + log_id)
    log_json = json.load(log_json)
    round_wins = []
    for game_round in log_json['rounds']:
        round_wins.append(game_round['winner'])
    score = (log_json['teams']['Blue']['score'], log_json['teams']['Red']['score'])
    winning_team = 'BLU' if score[0] > score[1] else 'RED'
    game_type = 'AD' if log_json['info']['AD_scoring'] is True else 'KOTH'
    await ctx.channel.send(f"Game type: {game_type}. Round wins: {round_wins}")
    await ctx.channel.send(f"Winning team: {winning_team}. Score {score[0]}-{score[1]}")
    await update_elo(winning_team, round_wins, game_type)
    await ctx.channel.send("elo scores updated")


async def update_elo(winning_team, round_wins, game_type):
    db = sqlite3.connect('players.db')
    try:
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
            c.execute(f'''SELECT player_id, {player_class} FROM elo WHERE player_id = ?''',
                      (player.id,))  # String substitution not an issue here
            row = c.fetchone()
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
            red_elo.append(row[1])

        blu_avg = round(sum(blu_elo) / len(blu_elo))
        red_avg = round(sum(red_elo) / len(red_elo))
        print(f"Average elo: {blu_avg}, {red_avg}")
        elo.add_player("BluAVG", blu_avg)
        elo.add_player("RedAVG", red_avg)

        if game_type == 'KOTH':
            for winner in round_wins:
                if winner == 'Blue':
                    exp_result = elo.expected_result("BluAVG", "RedAVG", names=True)
                    elo_change = round(elo.k * (1 - exp_result))
                    blu_elo = [player_elo + elo_change for player_elo in blu_elo]
                    red_elo = [player_elo - elo_change for player_elo in red_elo]
                    blu_avg = round(sum(blu_elo) / len(blu_elo))
                    red_avg = round(sum(red_elo) / len(red_elo))
                    print(f"Average elo: {blu_avg}, {red_avg}")
                    elo.add_player("BluAVG", blu_avg)
                    elo.add_player("RedAVG", red_avg)
                    for player_class, player in player_selection.blu_team.items():
                        if player is None:
                            continue
                        c.execute(f'''UPDATE elo 
                        SET {player_class} = {player_class} + ? WHERE player_id = ?''', (elo_change, player.id))
                    for player_class, player in player_selection.red_team.items():
                        if player is None:
                            continue
                        c.execute(f'''UPDATE elo 
                        SET {player_class} = {player_class} - ? WHERE player_id = ?''', (elo_change, player.id))
                elif winner == 'Red':
                    exp_result = elo.expected_result("RedAVG", "BluAVG", names=True)
                    elo_change = round(elo.k * (1 - exp_result))
                    blu_elo = [player_elo - elo_change for player_elo in blu_elo]
                    red_elo = [player_elo + elo_change for player_elo in red_elo]
                    blu_avg = round(sum(blu_elo) / len(blu_elo))
                    red_avg = round(sum(red_elo) / len(red_elo))
                    print(f"Average elo: {blu_avg}, {red_avg}")
                    elo.add_player("BluAVG", blu_avg)
                    elo.add_player("RedAVG", red_avg)
                    for player_class, player in player_selection.blu_team.items():
                        if player is None:
                            continue
                        c.execute(f'''UPDATE elo 
                        SET {player_class} = {player_class} - ? WHERE player_id = ?''', (elo_change, player.id))
                    for player_class, player in player_selection.red_team.items():
                        if player is None:
                            continue
                        c.execute(f'''UPDATE elo 
                        SET {player_class} = {player_class} + ? WHERE player_id = ?''', (elo_change, player.id))
        elif game_type == 'AD':
            if winning_team == 'BLU':
                exp_result = elo.expected_result("BluAVG", "RedAVG", names=True)
                elo_change = round(elo.k * (1 - exp_result))
                for player_class, player in player_selection.blu_team.items():
                    if player is None:
                        continue
                    c.execute(f'''UPDATE elo 
                    SET {player_class} = {player_class} + ? WHERE player_id = ?''', (elo_change, player.id))
                for player_class, player in player_selection.red_team.items():
                    if player is None:
                        continue
                    c.execute(f'''UPDATE elo 
                    SET {player_class} = {player_class} - ? WHERE player_id = ?''', (elo_change, player.id))
            elif winning_team == 'RED':
                exp_result = elo.expected_result("RedAVG", "BluAVG", names=True)
                elo_change = round(elo.k * (1 - exp_result))
                for player_class, player in player_selection.blu_team.items():
                    if player is None:
                        continue
                    c.execute(f'''UPDATE elo 
                                SET {player_class} = {player_class} - ? WHERE player_id = ?''', (elo_change, player.id))
                for player_class, player in player_selection.red_team.items():
                    if player is None:
                        continue
                    c.execute(f'''UPDATE elo 
                                SET {player_class} = {player_class} + ? WHERE player_id = ?''', (elo_change, player.id))

        db.commit()
    finally:
        db.close()
