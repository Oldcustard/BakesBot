import asyncio
from typing import Dict, List, Tuple

import disnake as discord
import time
import datetime
import configparser

import map_voting
import messages
import player_selection
import player_tracking

LIST_PLAYER_NAME_LENGTH = 7
emojis_ids = {
    'Scout': '<:scout:902551045891309579>',
    'Soldier': '<:soldier:902551045861957642>',
    'Pyro': '<:pyro:902551046189092875>',
    'Demo': '<:demoman:902551045815816202>',
    'Heavy': '<:heavy:902551045677416489>',
    'Engi': '<:engineer:902551046004572211>',
    'Medic': '<:medic:902551045761269782>',
    'Sniper': '<:sniper:902551045891313754>',
    'Spy': '<:spy:902551045853560842>'
}

allclass_emoji_id = '<:allclass:934032081670008842>'


class StartPug:
    def __init__(self, pug_id, scheduler):
        self.pug_scheduler = scheduler
        config = configparser.ConfigParser()
        config.read('config.ini')
        global_config = config['Global Pug Settings']

        self.ANNOUNCE_STRING = global_config['intro string']
        self.EARLY_ANNOUNCE_STRING = global_config['early signups intro string']

        if pug_id == 'main':
            config = config['Main Pug Settings']
        elif pug_id == 'second':
            config = config['Second Pug Settings']
        self.PUG_WDAY = config['pug weekday']
        self.PUG_HOUR = config['pug hour']

        self.signups: Dict[str, List[Tuple[discord.Member, int]]] = {
            emojis_ids['Scout']: [],
            emojis_ids['Soldier']: [],
            emojis_ids['Pyro']: [],
            emojis_ids['Demo']: [],
            emojis_ids['Heavy']: [],
            emojis_ids['Engi']: [],
            emojis_ids['Medic']: [],
            emojis_ids['Sniper']: [],
            emojis_ids['Spy']: []
        }

        self.player_classes: Dict[discord.Member, List[discord.Emoji]] = {}
        self.fill_players: List[discord.Member] = []

        self.signupsMessage: discord.Message | None = None
        self.signupsListMessage: discord.Message | None = None

        self.players_to_warn = []
        self.messages_to_delete: List[discord.Message] = []

    async def get_pug_time(self):
        pug_day = time.strptime(self.PUG_WDAY, "%A")
        current_date = datetime.datetime.now(datetime.timezone.utc).astimezone()
        current_day = current_date.weekday()
        time_to_pug = datetime.timedelta(days=pug_day.tm_wday - current_day)
        if time_to_pug.days < 0:
            time_to_pug = time_to_pug + datetime.timedelta(days=7)  # Ensure pug is in the future
        pug_date = current_date + time_to_pug
        pug_date = pug_date.replace(hour=int(self.PUG_HOUR), minute=0, second=0, microsecond=0)
        print(f"Pug is on {pug_date}")
        pug_timestamp = round(datetime.datetime.timestamp(pug_date))
        pug_time_string = f"<t:{pug_timestamp}:F>"
        return pug_date, pug_time_string

    async def announce_pug(self, channel: discord.TextChannel):
        pug_date, time_string = await self.get_pug_time()
        announce_message = f"\n{self.ANNOUNCE_STRING} \nPug will be **{time_string}** (this is displayed in your **local time**)\nPress withdraw if you can no longer play."
        view = discord.ui.View(timeout=None)
        for class_name, class_emoji in emojis_ids.items():
            button = discord.ui.Button(label=class_name, emoji=class_emoji)
            button.callback = self.signup_player_callback
            view.add_item(button)
        fill_button = discord.ui.Button(label='Fill', emoji=allclass_emoji_id, style=discord.ButtonStyle.success)
        withdraw_button = discord.ui.Button(label='Withdraw', emoji='❌', style=discord.ButtonStyle.danger)
        fill_button.callback = self.fill_callback
        withdraw_button.callback = self.withdraw_player
        view.add_item(fill_button)
        view.add_item(withdraw_button)
        pugMessage: discord.Message = await channel.send(announce_message, view=view)
        self.messages_to_delete.append(pugMessage)
        return pugMessage, pug_date

    async def announce_early(self, early_signups_channel: discord.TextChannel, signups_channel: discord.TextChannel):
        pug_date, time_string = await self.get_pug_time()
        self.pug_scheduler.penalty_trigger_time = pug_date - datetime.timedelta(hours=self.pug_scheduler.PENALTY_TRIGGER_OFFSET)
        announce_message = f"{messages.medic_role.mention}\n{self.EARLY_ANNOUNCE_STRING} \nPug will be on {time_string}\nPress withdraw if you can no longer play."
        medic_announce_message = f"\nEarly signups open!\nIf you want to play **Medic** for the pug on {time_string}, press the button below. Medics will gain 3 weeks of early signup!"
        early_view = discord.ui.View(timeout=None)
        for class_name, class_emoji in emojis_ids.items():
            button = discord.ui.Button(label=class_name, emoji=class_emoji)
            button.callback = self.signup_player_callback
            early_view.add_item(button)
        withdraw_button = discord.ui.Button(label='Withdraw', emoji='❌', style=discord.ButtonStyle.danger)
        withdraw_button.callback = self.withdraw_player
        early_view.add_item(withdraw_button)
        earlyPugMessage: discord.Message = await early_signups_channel.send(announce_message, view=early_view)
        early_medic_view = discord.ui.View(timeout=None)
        medic_button = discord.ui.Button(label='Medic', emoji=emojis_ids['Medic'])
        medic_button.callback = self.signup_player_callback
        early_medic_view.add_item(medic_button)
        earlyPugMedicMessage: discord.Message = await signups_channel.send(medic_announce_message, view=early_medic_view)
        self.messages_to_delete.append(earlyPugMessage)
        self.messages_to_delete.append(earlyPugMedicMessage)
        return earlyPugMessage, earlyPugMedicMessage

    async def signup_player_callback(self, inter: discord.MessageInteraction):
        await asyncio.sleep(0.5)
        await inter.response.defer()
        if await player_tracking.check_active_baiter(inter.author):
            before_late_signup_time, late_signup_time = await self.pug_scheduler.penalty_signups_check()
            if before_late_signup_time:
                await inter.send(
                    f"You have a current active warning, and are subject to a late signup penalty. You will be able to signup from {late_signup_time}", ephemeral=True)
                print(
                    f"{inter.author.display_name} attempted to sign up, but was denied due to warning")
                return
        players = self.signups[str(inter.component.emoji)]
        if inter.author not in self.player_classes:  # Add player to the player list
            self.player_classes[inter.author] = []
        if inter.component.emoji in self.player_classes[inter.author]:  # Player already signed up for this class
            await inter.send(f"You are already signed up for {inter.component.emoji}{inter.component.label}", ephemeral=True)
            return
        self.player_classes[inter.author].append(inter.component.emoji)  # Add class to that player's list
        preference = len(self.player_classes[inter.author])  # Preference for this class
        players.append((inter.author, preference))
        print(f'{inter.author.display_name} has signed up for {inter.component.label}')
        if self.signupsMessage is None:
            self.signupsMessage = await messages.send_to_admin(await self.list_players_by_class())
            self.signupsListMessage = await messages.send_to_admin(await self.list_players())
            await self.signupsMessage.pin()
            await self.signupsListMessage.pin()
        else:
            self.signupsMessage = await self.signupsMessage.edit(content=await self.list_players_by_class())
            self.signupsListMessage = await self.signupsListMessage.edit(content=await self.list_players())
        await inter.send(f"Successfully signed up for {inter.component.emoji}{inter.component.label} (preference {preference})", ephemeral=True)

    async def fill_callback(self, inter: discord.MessageInteraction):
        await asyncio.sleep(0.5)
        await inter.response.defer()
        if await player_tracking.check_active_baiter(inter.author):
            before_late_signup_time, late_signup_time = await self.pug_scheduler.penalty_signups_check()
            if before_late_signup_time:
                await inter.send(
                    f"You have a current active warning, and are subject to a late signup penalty. You will be able to signup from {late_signup_time}",
                    ephemeral=True)
                print(
                    f"{inter.author.display_name} attempted to sign up, but was denied due to warning")
                return
        if inter.author in self.fill_players:
            await inter.send(f"You are already signed up as a {allclass_emoji_id} fill player.",
                             ephemeral=True)
            return
        self.fill_players.append(inter.author)
        print(f'{inter.author.display_name} has signed up as a fill player.')
        if self.signupsMessage is None:
            self.signupsMessage = await messages.send_to_admin(await self.list_players_by_class())
            self.signupsListMessage = await messages.send_to_admin(await self.list_players())
            await self.signupsMessage.pin()
            await self.signupsListMessage.pin()
        else:
            self.signupsMessage = await self.signupsMessage.edit(content=await self.list_players_by_class())
            self.signupsListMessage = await self.signupsListMessage.edit(content=await self.list_players())
        await inter.send(f"Successfully signed up as a {allclass_emoji_id} fill player.", ephemeral=True)

    async def list_players_by_class(self):
        signupClass: str
        players: Tuple[discord.Member, int]
        msg: str = ""
        for signupClass, players in self.signups.items():
            formatted_players: List[str] = []
            for member, pref in players:
                name = member.display_name.replace('`', '')
                if len(name) <= LIST_PLAYER_NAME_LENGTH:
                    formatted_name = f"{name:>{LIST_PLAYER_NAME_LENGTH}.{LIST_PLAYER_NAME_LENGTH}} ({pref})"
                else:
                    formatted_name = f"{name[:LIST_PLAYER_NAME_LENGTH - 1]}- ({pref})"
                formatted_players.append(formatted_name)
            line = signupClass + ":`" + "| ".join(formatted_players) + " `"
            msg = msg + "\n" + line
        return msg

    async def list_players(self):
        msg = "Signups in order: " + ', '.join(player.display_Name for player in self.player_classes.keys())
        msg += "\nFill players: " + ", ".join(player.display_name for player in self.fill_players)
        return msg

    async def withdraw_player(self, inter: discord.ApplicationCommandInteraction | discord.MessageInteraction, user: discord.Member = None):
        if user is None:  # Player invoked withdraw
            user = inter.author

        async def respond_admin(message):
            if isinstance(inter, discord.ApplicationCommandInteraction):  # Admin invoked withdraw
                await inter.send(message)
            elif isinstance(inter, discord.MessageInteraction):  # User invoked withdraw
                await messages.send_to_admin(message)

        async def respond_user(message):
            if isinstance(inter, discord.ApplicationCommandInteraction): # Admin invoked withdraw
                await user.send(message)
            elif isinstance(inter, discord.MessageInteraction): # User invoked withdraw
                await inter.send(message, ephemeral=True)

        if user not in self.player_classes and user not in self.fill_players:  # user is already withdrawn
            if isinstance(inter, discord.ApplicationCommandInteraction):
                await respond_admin(f"{user.display_name} is already withdrawn.")
            elif isinstance(inter, discord.MessageInteraction):
                await respond_user(f"You are already withdrawn.")
            return
        if user in self.player_classes:
            self.player_classes.pop(user)
        else:
            self.fill_players.remove(user)
        for signup_class in self.signups.values():
            for signup in signup_class:
                if user in signup:
                    signup_class.remove(signup)
        print(f'{user.display_name} has withdrawn')
        await map_voting.remove_player_votes(user)
        await self.signupsMessage.edit(content=await self.list_players_by_class())
        await self.signupsListMessage.edit(content=await self.list_players())
        if user in player_selection.blu_team.values() or user in player_selection.red_team.values():
            is_past_penalty_time, penalty_trigger_time = await self.pug_scheduler.after_penalty_trigger_check()
            if is_past_penalty_time:
                await respond_admin(f"{messages.host_role.mention}: {user.display_name} has withdrawn from the pug. As it is after {penalty_trigger_time}, they will receive a bait warning.")
                self.players_to_warn.append(user)
                await respond_user(f"You have withdrawn from the pug. As you have been assigned a class and it is after {penalty_trigger_time}, you will receive a bait warning.")
            else:
                await respond_admin(f"{messages.host_role.mention}: {user.display_name} has withdrawn from the pug.")
                await respond_user(f"You have withdrawn from the pug.")
        else:
            if isinstance(inter, discord.ApplicationCommandInteraction):
                await respond_admin(f"{user.display_name} has withdrawn from the pug.")
                await respond_user(f"You have withdrawn from the pug.")
            elif isinstance(inter, discord.MessageInteraction):
                await respond_user(f"You have withdrawn from the pug.")
        for player_class, player in player_selection.blu_team.items():
            if player == user:
                player_selection.blu_team[player_class] = None
                player_selection.bluMessage = await player_selection.bluMessage.edit(content="BLU Team:\n" + await player_selection.list_players(player_selection.blu_team))
                await player_selection.announce_string()
        for player_class, player in player_selection.red_team.items():
            if player == user:
                player_selection.red_team[player_class] = None
                player_selection.redMessage = await player_selection.redMessage.edit(content="RED Team:\n" + await player_selection.list_players(player_selection.red_team))
                await player_selection.announce_string()

    async def auto_warn_bating_players(self):
        for user in self.players_to_warn:
            await player_tracking.warn_player(user)
        self.players_to_warn.clear()

    async def reset_pug(self):
        for message in self.messages_to_delete:
            try:
                await message.delete()
            except discord.NotFound:
                continue
        self.messages_to_delete.clear()
        for message in player_selection.messages_to_delete:
            try:
                await message.delete()
            except discord.NotFound:
                continue
        player_selection.messages_to_delete.clear()
        await self.signupsMessage.unpin()
        await self.signupsListMessage.unpin()
        self.signupsMessage = None
        self.signupsListMessage = None
        player_selection.bluMessage = None
        player_selection.redMessage = None
        player_selection.stringMessage = None
        player_selection.reminderMessage = None
        player_selection.timeMessage = None
        self.pug_scheduler.pugMessage = None
        self.pug_scheduler.earlyMedicPugMessage = None
        self.pug_scheduler.earlyPugMessage = None
        map_voting.active_votes.clear()
        player_selection.blu_team = dict.fromkeys(player_selection.blu_team.keys(), None)
        player_selection.red_team = dict.fromkeys(player_selection.red_team.keys(), None)
        player_selection.players_changed_late.clear()
        self.signups = dict.fromkeys(self.signups.keys(), [])
        self.player_classes = {}
        print("Pug status reset; messages deleted")
