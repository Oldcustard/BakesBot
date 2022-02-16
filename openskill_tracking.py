import sqlite3
import regex

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
                blu_ranks.append(openskill.create_rating([25, 8.3333]))
            else:
                rank = openskill.ordinal(float(row[0]), float(row[1]))
                class_ranks.append(round(rank))
                blu_ranks.append(openskill.create_rating([row[0], row[1]]))
            c.execute(f'''SELECT {player_class}_mean, {player_class}_std FROM openskill WHERE player_id = ?''', (red_player.id,))
            row = c.fetchone()
            if row is None:
                class_ranks.append(0)
                red_ranks.append(openskill.create_rating([25, 8.3333]))
            else:
                rank = openskill.ordinal(float(row[0]), float(row[1]))
                class_ranks.append(round(rank))
                red_ranks.append(openskill.create_rating([row[0], row[1]]))
            ranks[player_class] = class_ranks
        msg = "**Class vs Class Balance**"
        blu_name_max_length = max(map(get_display_name_width, player_selection.blu_team.values()))
        red_name_max_length = max(map(get_display_name_width, player_selection.red_team.values()))

        for player_class, player_ranks in ranks.items():
            blu_emoji_match = regex.findall("\p{Emoji=yes}", player_selection.blu_team[player_class].display_name)
            red_emoji_match = regex.findall("\p{Emoji=yes}", player_selection.red_team[player_class].display_name)
            blu_name = f"`{player_selection.blu_team[player_class].display_name.replace('`',''):>{blu_name_max_length - len(blu_emoji_match)}} ({player_ranks[0]:+03d})`"
            red_name = f"`({player_ranks[1]:+03d}) {player_selection.red_team[player_class].display_name.replace('`',''):<{red_name_max_length - len(red_emoji_match)}}`"
            class_emoji = str(start_pug.emojis_ids[player_class])
            left_space = "      "
            right_space = "      "
            if player_ranks[0] > player_ranks[1]:
                # blue player is better
                blu_name = f"***{blu_name}***"
                left_space = "⬅️"
            elif player_ranks[1] > player_ranks[0]:
                # red player is better
                red_name = f"***{red_name}***"
                right_space = "➡️"

            line = f"\n{blu_name} {left_space}{class_emoji}{right_space} {red_name}"
            msg += line

        win_percent = openskill.predict_win([blu_ranks, red_ranks])
        blu_msg = f"BLU Win Prediction: {round(win_percent[0]*100, 1)}%"
        red_msg = f"RED Win Prediction: {round(win_percent[1]*100, 1)}%"
        if win_percent[0] > win_percent[1]:
            blu_msg = f"**{blu_msg}**"
        elif win_percent[1] > win_percent[0]:
            red_msg = f"**{red_msg}**"
        msg += f"\n{blu_msg} 🟦🟥 {red_msg}"

        msg += f"\n\n**{start_pug.emojis_ids['Pyro']}{start_pug.emojis_ids['Demo']}Combo Balance{start_pug.emojis_ids['Heavy']}{start_pug.emojis_ids['Medic']}**"
        combo_percent = openskill.predict_win([[blu_ranks[2], blu_ranks[3], blu_ranks[4], blu_ranks[6]], [red_ranks[2], red_ranks[3], red_ranks[4], red_ranks[6]]])
        blu_msg = f"BLU Win Prediction: {round(combo_percent[0]*100, 1)}%"
        red_msg = f"RED Win Prediction: {round(combo_percent[1]*100, 1)}%"
        if combo_percent[0] > combo_percent[1]:
            blu_msg = f"**{blu_msg}**"
        elif combo_percent[1] > combo_percent[0]:
            red_msg = f"**{red_msg}**"
        msg += f"\n{blu_msg} 🟦🟥 {red_msg}"

        msg += f"\n\n**{start_pug.emojis_ids['Scout']}Flank Balance{start_pug.emojis_ids['Soldier']}**"
        flank_percent = openskill.predict_win([[blu_ranks[0], blu_ranks[1]], [red_ranks[0], red_ranks[1]]])
        blu_msg = f"BLU Win Prediction: {round(flank_percent[0]*100, 1)}%"
        red_msg = f"RED Win Prediction: {round(flank_percent[1]*100, 1)}%"
        if flank_percent[0] > flank_percent[1]:
            blu_msg = f"**{blu_msg}**"
        elif flank_percent[1] > flank_percent[0]:
            red_msg = f"**{red_msg}**"
        msg += f"\n{blu_msg} 🟦🟥 {red_msg}"

        msg += f"\n\n**{start_pug.emojis_ids['Sniper']}Picks Balance{start_pug.emojis_ids['Spy']}**"
        picks_percent = openskill.predict_win([[blu_ranks[7], blu_ranks[8]], [red_ranks[7], red_ranks[8]]]) #78
        blu_msg = f"BLU Win Prediction: {round(picks_percent[0]*100, 1)}%"
        red_msg = f"RED Win Prediction: {round(picks_percent[1]*100, 1)}%"
        if picks_percent[0] > picks_percent[1]:
            blu_msg = f"**{blu_msg}**"
        elif picks_percent[1] > picks_percent[0]:
            red_msg = f"**{red_msg}**"
        msg += f"\n{blu_msg} 🟦🟥 {red_msg}"

        await inter.send(msg)
    finally:
        db.close()

def get_display_name_width(user: discord.User):
    base_length = len(user.display_name)
    emoji_match = regex.findall("\p{Emoji=yes}", user.display_name)
    return base_length + len(emoji_match)
