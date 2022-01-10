import sqlite3

import openskill
import openskill.models

import player_selection


async def update_openskill(winning_team, round_wins, game_type):
    db = sqlite3.connect('players.db')
    try:
        c = db.cursor()

        blu_players = {}
        red_players = {}

        c.execute('''CREATE TABLE IF NOT EXISTS openskill
                (player_id TEXT PRIMARY KEY, player_name TEXT, Scout_mean REAL DEFAULT 25, Scout_std REAL DEFAULT 8.3333, Soldier_mean REAL DEFAULT 25, Soldier_std REAL DEFAULT 8.3333, 
                Pyro_mean REAL DEFAULT 25, Pyro_std REAL DEFAULT 8.3333, Demo_mean REAL DEFAULT 25, Demo_std REAL DEFAULT 8.3333,
                Heavy_mean REAL DEFAULT 25, Heavy_std REAL DEFAULT 8.3333, Engi_mean REAL DEFAULT 25, Engi_std REAL DEFAULT 8.3333, 
                Medic_mean REAL DEFAULT 25, Medic_std REAL DEFAULT 8.3333, Sniper_mean REAL DEFAULT 25, Sniper_std REAL DEFAULT 8.3333,
                Spy_mean REAL DEFAULT 25, Spy_std REAL DEFAULT 8.3333)''')

        for player_class, player in player_selection.blu_team.items():
            if player is None:
                continue
            c.execute('''SELECT player_id FROM openskill WHERE player_id = ?''', (player.id,))
            row = c.fetchone()
            if row is None:  # Player does not have an openskill rank assigned.
                c.execute('''INSERT INTO openskill (player_id, player_name)
                         VALUES (?, ?)''', (player.id, player.name))
            c.execute(f'''SELECT player_id, {player_class}_mean, {player_class}_std FROM openskill WHERE player_id = ?''',
                      (player.id,))  # String substitution not an issue here
            row = c.fetchone()
            blu_players[row[0]] = [row[1], row[2]]

        for player_class, player in player_selection.red_team.items():
            if player is None:
                continue
            c.execute('''SELECT player_id FROM openskill WHERE player_id = ?''', (player.id,))
            row = c.fetchone()
            if row is None:  # Player does not have an openskill rank assigned.
                c.execute('''INSERT INTO openskill (player_id, player_name)
                         VALUES (?, ?)''', (player.id, player.name))
            c.execute(f'''SELECT player_id, {player_class}_mean, {player_class}_std FROM openskill WHERE player_id = ?''',
                      (player.id,))  # String substitution not an issue here
            row = c.fetchone()
            red_players[row[0]] = [row[1], row[2]]

        if game_type == 'KOTH':
            for winner in round_wins:
                blu_ratings = [openskill.create_rating(player) for player in blu_players.values()]
                red_ratings = [openskill.create_rating(player) for player in red_players.values()]
                if winner == 'Blue':
                    [blu_ratings, red_ratings] = openskill.rate([blu_ratings, red_ratings], model=openskill.models.BradleyTerryFull)
                elif winner == 'Red':
                    [red_ratings, blu_ratings] = openskill.rate([red_ratings, blu_ratings], model=openskill.models.BradleyTerryFull)
                for i, player in enumerate(blu_players):
                    blu_players[player] = blu_ratings[i]
                for i, player in enumerate(red_players):
                    red_players[player] = red_ratings[i]

                for player_class, player in player_selection.blu_team.items():
                    if player is None:
                        continue
                    c.execute(f'''UPDATE openskill 
                    SET {player_class}_mean = ?, {player_class}_std = ? WHERE player_id = ?''', (blu_players[str(player.id)][0], blu_players[str(player.id)][1], player.id))
                for player_class, player in player_selection.red_team.items():
                    if player is None:
                        continue
                    c.execute(f'''UPDATE openskill 
                    SET {player_class}_mean = ?, {player_class}_std = ? WHERE player_id = ?''', (red_players[str(player.id)][0], red_players[str(player.id)][1], player.id))
        elif game_type == 'AD':
            blu_ratings = [openskill.create_rating(player) for player in blu_players.values()]
            red_ratings = [openskill.create_rating(player) for player in red_players.values()]
            if winning_team == 'BLU':
                [blu_ratings, red_ratings] = openskill.rate([blu_ratings, red_ratings], model=openskill.models.BradleyTerryFull)
            elif winning_team == 'RED':
                [red_ratings, blu_ratings] = openskill.rate([red_ratings, blu_ratings], model=openskill.models.BradleyTerryFull)
            for i, player in enumerate(blu_players):
                blu_players[player] = blu_ratings[i]
            for i, player in enumerate(red_players):
                red_players[player] = red_ratings[i]

            for player_class, player in player_selection.blu_team.items():
                if player is None:
                    continue
                c.execute(f'''UPDATE openskill 
                SET {player_class}_mean = ?, {player_class}_std = ? WHERE player_id = ?''', (blu_players[str(player.id)][0], blu_players[str(player.id)][1], player.id))
            for player_class, player in player_selection.red_team.items():
                if player is None:
                    continue
                c.execute(f'''UPDATE openskill 
                SET {player_class}_mean = ?, {player_class}_std = ? WHERE player_id = ?''', (red_players[str(player.id)][0], red_players[str(player.id)][1], player.id))
        db.commit()
    finally:
        db.close()
