# BakesBot.py
import datetime
import json
import asyncio
from typing import List

from dotenv import load_dotenv

import os
import configparser
import disnake as discord
from disnake.ext import commands
import logging

import active_pug
import elo_tracking
import map_voting
import messages
import openskill_tracking
import pug_scheduler
import player_selection
import player_tracking

load_dotenv()

logging.basicConfig(level=logging.WARNING)
config = configparser.ConfigParser()
config.read('config.ini')

intents = discord.Intents().default()
intents.members = True
client = commands.Bot('!', intents=intents, test_guilds=[int(os.getenv('guild_id'))], sync_permissions=True)

permissions: List[discord.PartialGuildApplicationCommandPermissions] = []

GUILD_ID = int(os.getenv('guild_id'))
ANNOUNCE_CHANNEL_ID = int(os.getenv('announce_channel_id'))
EARLY_ANNOUNCE_CHANNEL_ID = int(os.getenv('early_announce_channel_id'))
ADMIN_CHANNEL_ID = int(os.getenv('admin_channel_id'))
ADMIN_ID = int(os.getenv('admin_id'))
MEDIC_ROLE_ID = int(os.getenv('medic_role_id'))
HOST_ROLE_ID = int(os.getenv('host_role_id'))
PUG_BANNED_ROLE_ID = int(os.getenv('pug_banned_role_id'))
GAMER_ROLE_ID = int(os.getenv('gamer_role_id'))
DEV_ID = int(os.getenv('dev_id'))
BLU_CHANNEL_ID = int(os.getenv('blu_channel_id'))
RED_CHANNEL_ID = int(os.getenv('red_channel_id'))
WAITING_CHANNEL_ID = int(os.getenv('waiting_channel_id'))

main_scheduler: pug_scheduler.PugScheduler | None = None
second_scheduler: pug_scheduler.PugScheduler | None = None


@client.event
async def on_ready():
    messages.announceChannel = client.get_channel(ANNOUNCE_CHANNEL_ID)
    messages.earlyAnnounceChannel = client.get_channel(EARLY_ANNOUNCE_CHANNEL_ID)
    messages.guild = client.get_guild(GUILD_ID)
    messages.medic_role = messages.guild.get_role(MEDIC_ROLE_ID)
    messages.host_role = messages.guild.get_role(HOST_ROLE_ID)
    messages.banned_role = messages.guild.get_role(PUG_BANNED_ROLE_ID)
    messages.gamer_role = messages.guild.get_role(GAMER_ROLE_ID)
    messages.adminChannel = client.get_channel(ADMIN_CHANNEL_ID)
    messages.admin = await client.fetch_user(ADMIN_ID)
    messages.dev = await client.fetch_user(DEV_ID)
    messages.bluChannel = client.get_channel(BLU_CHANNEL_ID)
    messages.redChannel = client.get_channel(RED_CHANNEL_ID)
    messages.waitingChannel = client.get_channel(WAITING_CHANNEL_ID)
    if active_pug.startup:
        global main_scheduler, second_scheduler
        main_scheduler = pug_scheduler.PugScheduler('main')
        second_scheduler = pug_scheduler.PugScheduler('second')
        main_scheduler.announcement_future = asyncio.ensure_future(
            main_scheduler.schedule_announcement(messages.announceChannel))
        second_scheduler.announcement_future = asyncio.ensure_future(
            second_scheduler.schedule_announcement(messages.announceChannel))
        active_pug.startup = False
        print(f'{client.user} logged in, scheduling announcement')
    else:
        print(f'{client.user} reconnected.')
        await messages.send_to_admin(f"{messages.dev.mention}: Bot reconnected.")

Team = commands.option_enum(['BLU', 'RED'])
PlayerClass = commands.option_enum(['Scout', 'Soldier', 'Pyro', 'Demo', 'Heavy', 'Engi', 'Medic', 'Sniper', 'Spy'])


@client.slash_command(name='override', description='Manually select a player for a class', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def select_player(inter: discord.ApplicationCommandInteraction, team: Team, player_class: PlayerClass, *, player: discord.Member):
    if active_pug.active_start_pug.signupsMessage is None:
        await inter.send("Player selection only available after pug is announced")
    else:
        await asyncio.sleep(0.5)
        await inter.response.defer()
        await player_selection.select_player(inter, team, player_class, player)


@client.slash_command(name='forceselect', description='Force select a player for a class (they will not receive confirmation)', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def select_player(inter: discord.ApplicationCommandInteraction, team: Team, player_class: PlayerClass, *, player: discord.Member):
    if active_pug.active_start_pug.signupsMessage is None:
        await inter.send("Player selection only available after pug is announced")
    else:
        await asyncio.sleep(0.5)
        await inter.response.defer()
        await player_selection.select_player(inter, team, player_class, player, True)


@client.slash_command(name='select', description='Select players for classes.', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def select_player_new(inter: discord.ApplicationCommandInteraction):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await player_selection.select_player_new(inter)


@client.event
async def on_slash_command_error(inter: discord.ApplicationCommandInteraction, error):
    if inter.application_command.has_error_handler():  # Command has a specific handler, ignore
        return
    if isinstance(error, commands.CommandInvokeError):
        await inter.send(f"An error occurred: {error.original} {type(error.original)} ({messages.dev.mention})")
        raise error
    else:
        await inter.send(f"An error occurred: {error} {type(error)} ({messages.dev.mention})")
        raise error


@client.slash_command(name='forcestart', description='Force start pug', default_permission=False)
@commands.guild_permissions(GUILD_ID, {DEV_ID: True})
async def force_start_pug(inter: discord.ApplicationCommandInteraction):
    await inter.send("Forcing Start...")
    await active_pug.active_pug_scheduler.schedule_pug_start(datetime.datetime.now(datetime.timezone.utc).astimezone(), True)


@client.slash_command(name='forcereset', description='Force reset pug', default_permission=False)
@commands.guild_permissions(GUILD_ID, {DEV_ID: True})
async def force_reset(inter: discord.ApplicationCommandInteraction):
    await inter.send("Forcing Reset...")
    await active_pug.active_start_pug.reset_pug()


@client.slash_command(name='withdraw', description='Withdraw a player from a pug', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def force_withdraw_player(inter: discord.ApplicationCommandInteraction, *, player: discord.Member):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await active_pug.active_start_pug.withdraw_player(inter, player)


@client.slash_command(name='warn', description="Warn a player for baiting", default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def warn_player(inter: discord.ApplicationCommandInteraction, *, player: discord.Member):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await player_tracking.warn_player(player, inter)


@client.slash_command(name='unwarn', description="Manually remove a warning", default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def unwarn_player(inter: discord.ApplicationCommandInteraction, *, player: discord.Member):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await player_tracking.unwarn_player(player, inter)


@client.slash_command(name='ban', description='Ban a player from playing in pugs', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def ban_player(inter: discord.ApplicationCommandInteraction, player: discord.Member, *, reason):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await player_tracking.pug_ban(inter, player, reason)


@client.slash_command(name='unban', description='Unban a player', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def unban_player(inter: discord.ApplicationCommandInteraction, *, player: discord.Member):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await player_tracking.pug_unban(inter, player)


@client.slash_command(name='status', description='Get the current status of a player', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def get_player_status(inter: discord.ApplicationCommandInteraction, *, player: discord.Member):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await player_tracking.player_status(inter, player)


@client.slash_command(name='string', description='Announce the pug connect string', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def announce_string(inter: discord.ApplicationCommandInteraction, *, connect_string):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await player_selection.announce_string(connect_string)
    await inter.send("Posting string")


@client.slash_command(name='switch', description='Switch two players on a class', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def switch_players(inter: discord.ApplicationCommandInteraction, player_class: PlayerClass):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await player_selection.swap_class_across_teams(inter, player_class)


@client.slash_command(name='unassigned', aliases=['ua'], description='List players who are signed up but not assigned a class', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def list_unassigned_players(inter: discord.ApplicationCommandInteraction):
    await player_selection.list_unassigned_players(inter)


@client.slash_command(name='vote', description='Start a map vote', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def start_map_vote(inter: discord.ApplicationCommandInteraction, map_type=commands.param(choices=["Attack/Defend", "KOTH"])):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await map_voting.start_map_vote(inter, map_type)


@client.slash_command(name='results', description='View map vote results', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def view_vote_results(inter: discord.ApplicationCommandInteraction):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await map_voting.view_results(inter)


@client.slash_command(name='teamvc', description='Move players into their team voice channel', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def drag_into_team_vc(inter: discord.ApplicationCommandInteraction):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await player_selection.drag_into_team_vc(inter)


@client.slash_command(name='summon', aliases=['here'], description='Move players into your current voice channel', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def drag_into_same_vc(inter: discord.ApplicationCommandInteraction):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await player_selection.drag_into_same_vc(inter)


@client.slash_command(name='log', description='Submit the logs.tf log for openskill tracking', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def fetch_logs(inter: discord.ApplicationCommandInteraction, log_url: str):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await elo_tracking.fetch_logs(inter, log_url)


@fetch_logs.error
async def fetch_logs_error(inter: discord.ApplicationCommandInteraction, error):
    if isinstance(error.original, IndexError):
        await inter.send("Log not found")
    elif isinstance(error.original, json.JSONDecodeError):
        await inter.send("Log not found")
    else:
        await inter.send(f"An error occurred: {error.original} {type(error.original)} ({messages.dev.mention})")
        raise error


@client.slash_command(name='ping', description='Ping signed up players who are currently not in a voice channel', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def ping_players(inter: discord.ApplicationCommandInteraction):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await player_selection.ping_not_present(inter)


@client.slash_command(name='shutdown', default_permission=False)
@commands.guild_permissions(GUILD_ID, user_ids={DEV_ID: True})
async def cancel_scheduled_announcements(inter: discord.ApplicationCommandInteraction):
    await inter.send("Cancelling future announcements...")
    main_scheduler.announcement_future.cancel()
    main_scheduler.early_announcement_future.cancel()
    second_scheduler.announcement_future.cancel()
    second_scheduler.early_announcement_future.cancel()


@client.slash_command(name='clearpins', default_permission=False)
@commands.guild_permissions(GUILD_ID, user_ids={DEV_ID: True})
async def clear_bot_pins(inter: discord.ApplicationCommandInteraction):
    pinned_message: discord.Message
    await asyncio.sleep(0.5)
    await inter.response.defer()
    for pinned_message in await messages.adminChannel.pins():
        if pinned_message.author == client.user:
            await pinned_message.unpin()
    print("Cleared admin channel pins")
    for pinned_message in await messages.announceChannel.pins():
        if pinned_message.author == client.user:
            await pinned_message.unpin()
    print("Cleared announce channel pins")
    await inter.send("Cleared pins")


@client.slash_command(name='rank', description="Display a player's confident openskill rank", default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def get_player_rank(inter: discord.ApplicationCommandInteraction, player: discord.Member):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await openskill_tracking.get_rank(inter, player)


@client.user_command(name='Get Rank', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def get_player_rank_context(inter: discord.ApplicationCommandInteraction):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await openskill_tracking.get_rank(inter, inter.target)


@client.slash_command(name='compare', description="Compare a class for balance", default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def compare_class_rank(inter: discord.ApplicationCommandInteraction, player_class: PlayerClass):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await openskill_tracking.compare_rank(inter, player_class)


@client.slash_command(name='balance', description="Get team balance", default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def get_team_balance(inter: discord.ApplicationCommandInteraction):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    await openskill_tracking.get_team_balance(inter)


@client.slash_command(name='selectall', description="Assign player to all classes on a team", default_permission=False)
@commands.guild_permissions(GUILD_ID, user_ids={DEV_ID: True})
async def assign_player_to_all_classes(inter: discord.ApplicationCommandInteraction, team: Team, user: discord.Member):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    for player_class in player_selection.blu_team.keys():
        await player_selection.select_player(inter, team, player_class, user)


@client.slash_command(name='forceactive', description="Force the current early pug to become active", default_permission=False)
@commands.guild_permissions(GUILD_ID, user_ids={DEV_ID: True})
async def force_active_pug(inter: discord.ApplicationCommandInteraction):
    await asyncio.sleep(0.5)
    await inter.response.defer()
    active_pug.change_active_pug()
    await inter.send("Active pug set.")


def start():
    client.run(os.getenv('TOKEN'))


if __name__ == '__main__':
    start()
