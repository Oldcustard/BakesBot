import sqlite3

import openskill
import openskill.models
import disnake as discord

import player_selection
import start_pug


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


async def get_rank(inter: discord.ApplicationCommandInteraction, user: discord.Member):
    db = sqlite3.connect('players.db')
    try:
        ranks = []
        c = db.cursor()
        c.execute('''SELECT * FROM openskill WHERE player_id = ?''', (user.id,))
        row = c.fetchone()
        if row is None:
            await inter.send(f"{user.display_name} does not currently have any rank.")
            return
        for i, mean in enumerate(row):
            if i < 2 or i % 2 != 0:
                continue
            rank = openskill.ordinal(float(mean), float(row[i+1]))
            ranks.append(round(rank))
        msg = f"{user.display_name} has the following ranks:"
        for i, player_class in enumerate(start_pug.emojis_ids.values()):
            line = f"\n{player_class}: {ranks[i]}"
            msg = msg + line
        await inter.send(msg)
    finally:
        db.close()


async def compare_rank(inter: discord.ApplicationCommandInteraction, player_class: str):
    blu_player = player_selection.blu_team[player_class]
    red_player = player_selection.red_team[player_class]
    db = sqlite3.connect('players.db')
    try:
        c = db.cursor()
        c.execute(f'''SELECT player_name, {player_class}_mean, {player_class}_std FROM openskill WHERE player_id = ? OR player_id = ?''', (blu_player.id, red_player.id))
        players = c.fetchall()
        msg = ""
        for row in players:
            rank = openskill.ordinal(float(row[1]), float(row[2]))
            msg = msg + f"\n{row[0]} **{player_class}** rank: **{round(rank)}**"
        await inter.send(msg)
    finally:
        db.close()


async def get_team_balance(inter: discord.ApplicationCommandInteraction):
    db = sqlite3.connect('players.db')
    try:
        ranks = {}
        blu_ranks = []
        red_ranks = []
        c = db.cursor()
        for player_class in player_selection.blu_team.keys():
            blu_player = player_selection.blu_team[player_class]
            red_player = player_selection.red_team[player_class]
            class_ranks = []
            if blu_player is None or red_player is None:
                continue
            c.execute(f'''SELECT {player_class}_mean, {player_class}_std FROM openskill WHERE player_id = ?''', (blu_player.id,))
            row = c.fetchone()
            if row is None:
                class_ranks.append(0)
                blu_ranks.append(0)
            else:
                rank = openskill.ordinal(float(row[0]), float(row[1]))
                class_ranks.append(round(rank))
                blu_ranks.append(round(rank))
            c.execute(f'''SELECT {player_class}_mean, {player_class}_std FROM openskill WHERE player_id = ?''', (red_player.id,))
            row = c.fetchone()
            if row is None:
                class_ranks.append(0)
                red_ranks.append(0)
            else:
                rank = openskill.ordinal(float(row[0]), float(row[1]))
                class_ranks.append(round(rank))
                red_ranks.append(round(rank))
            ranks[player_class] = class_ranks
        msg = "**Class vs Class Balance**"
        for player_class, player_ranks in ranks.items():
            if player_ranks[0] > player_ranks[1]:
                better = 'BLU'
            elif player_ranks[1] > player_ranks[0]:
                better = 'RED'
            else:
                better = 'EVEN'
            line = f"\n{'**' if better == 'BLU' else ''}{player_selection.blu_team[player_class].display_name} ({player_ranks[0]}){'**' if better == 'BLU' else ''}" \
                   f" {start_pug.emojis_ids[player_class]}" \
                   f" {'**' if better == 'RED' else ''}{player_selection.red_team[player_class].display_name} ({player_ranks[1]}){'**' if better == 'RED' else ''}"
            msg += line
        blu_avg = round(sum(blu_ranks)/len(blu_ranks), 2)
        red_avg = round(sum(red_ranks)/len(red_ranks), 2)
        team_better = 'BLU' if blu_avg > red_avg else 'RED'
        msg += f"\n{'**' if team_better == 'BLU' else ''}BLU Average: {blu_avg}{'**' if team_better == 'BLU' else ''} 🟦🟥 " \
                    f"{'**' if team_better == 'RED' else ''}RED Average: {red_avg}{'**' if team_better == 'RED' else ''}"

        msg += f"\n\n**{start_pug.emojis_ids['Pyro']}{start_pug.emojis_ids['Demo']}Combo Balance{start_pug.emojis_ids['Heavy']}{start_pug.emojis_ids['Medic']}**"
        blu_combo = round((blu_ranks[2] + blu_ranks[3] + blu_ranks[4] + blu_ranks[6])/4, 2)
        red_combo = round((red_ranks[2] + red_ranks[3] + red_ranks[4] + red_ranks[6])/4, 2)
        combo_better = 'BLU' if blu_combo > red_combo else 'RED'
        msg += f"\n{'**' if combo_better == 'BLU' else ''}BLU Average: {blu_combo}{'**' if combo_better == 'BLU' else ''} 🟦🟥 " \
                    f"{'**' if combo_better == 'RED' else ''}RED Average: {red_combo}{'**' if combo_better == 'RED' else ''}"

        msg += f"\n\n**{start_pug.emojis_ids['Scout']}Flank Balance{start_pug.emojis_ids['Soldier']}**"
        blu_flank = round((blu_ranks[0] + blu_ranks[1]) / 2, 2)
        red_flank = round((red_ranks[0] + red_ranks[1]) / 2, 2)
        flank_better = 'BLU' if blu_flank > red_flank else 'RED'
        msg += f"\n{'**' if flank_better == 'BLU' else ''}BLU Average: {blu_flank}{'**' if flank_better == 'BLU' else ''} 🟦🟥 " \
                    f"{'**' if flank_better == 'RED' else ''}RED Average: {red_flank}{'**' if flank_better == 'RED' else ''}"

        msg += f"\n\n**{start_pug.emojis_ids['Sniper']}Picks Balance{start_pug.emojis_ids['Spy']}**"
        blu_picks = round((blu_ranks[7] + blu_ranks[8]) / 2, 2)
        red_picks = round((red_ranks[7] + red_ranks[8]) / 2, 2)
        picks_better = 'BLU' if blu_picks > red_picks else 'RED'
        msg += f"\n{'**' if picks_better == 'BLU' else ''}BLU Average: {blu_picks}{'**' if picks_better == 'BLU' else ''} 🟦🟥 " \
                    f"{'**' if picks_better == 'RED' else ''}RED Average: {red_picks}{'**' if picks_better == 'RED' else ''}"
        await inter.send(msg)
    finally:
        db.close()
