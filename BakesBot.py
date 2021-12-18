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
import main.pug_scheduler
import second.pug_scheduler
import player_selection
import player_tracking

load_dotenv()

logging.basicConfig(level=logging.WARNING)
config = configparser.ConfigParser()
config.read('config.ini')

intents = discord.Intents().default()
intents.members = True
client = commands.Bot('$', intents=intents, test_guilds=[902442233482063892], sync_permissions=True)

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
    if main.pug_scheduler.startup:
        main.pug_scheduler.announcement_future = asyncio.ensure_future(main.pug_scheduler.schedule_announcement(messages.announceChannel))
    if second.pug_scheduler.startup:
        print(f'{client.user} logged in, scheduling announcement')
        second.pug_scheduler.announcement_future = asyncio.ensure_future(second.pug_scheduler.schedule_announcement(messages.announceChannel))
    else:
        print(f'{client.user} reconnected.')
        await messages.send_to_admin(f"{messages.dev.mention}: Bot reconnected.")


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
    reaction = discord.utils.get(message.reactions, emoji=payload.emoji)
    if reaction is None:
        reaction = discord.utils.get(message.reactions, emoji=str(payload.emoji))
    user = payload.member
    if user != client.user and reaction.message in map_voting.active_votes:
        await map_voting.vote_for_map(reaction, user)
    try:
        if user != client.user and reaction.message == active_pug.early_pug_scheduler.earlyPugMessage:
            await active_pug.early_start_pug.on_reaction_add(reaction, user)  # Early signup
        elif user != client.user and reaction.message == active_pug.early_pug_scheduler.earlyMedicPugMessage:
            await active_pug.early_start_pug.on_reaction_add(reaction, user)  # Early medic signup
        elif user != client.user and reaction.message == active_pug.pug_scheduler.pugMessage:
            await active_pug.start_pug.on_reaction_add(reaction, user)  # Regular signup
    except AttributeError:  # Signups not declared yet, ignore
        pass


@client.slash_command(name='select', aliases=['s'], description='Select a player for a class', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def select_player(inter: discord.ApplicationCommandInteraction, team, player_class, *, player: discord.Member):
    if active_pug.start_pug.signupsMessage is None:
        await inter.send("Player selection only available after pug is announced")
        return
    await player_selection.select_player(inter, team, player_class, player)


@client.event
async def on_slash_command_error(inter: discord.ApplicationCommandInteraction, error):
    if inter.application_command.has_error_handler():  # Command has a specific handler, ignore
        return
    if isinstance(error, commands.CommandInvokeError):
        await inter.response.send_message(f"An error occurred: {error.original} {type(error.original)} ({messages.dev.mention})")
        raise error
    else:
        await inter.response.send_message(f"An error occurred: {error} {type(error)} ({messages.dev.mention})")
        raise error


@client.slash_command(name='forcestart', description='Force start pug', default_permission=False)
@commands.guild_permissions(GUILD_ID, {DEV_ID: True})
async def force_start_pug(inter: discord.ApplicationCommandInteraction):
    await active_pug.pug_scheduler.schedule_pug_start(datetime.datetime.now(datetime.timezone.utc).astimezone(), True)


@client.slash_command(name='forcereset', description='Force reset pug', default_permission=False)
@commands.guild_permissions(GUILD_ID, {DEV_ID: True})
async def force_reset(inter: discord.ApplicationCommandInteraction):
    await active_pug.start_pug.reset_pug()


@client.slash_command(name='withdraw', description='Withdraw a player from a pug', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def force_withdraw_player(inter: discord.ApplicationCommandInteraction, *, player: discord.Member):
    await active_pug.start_pug.withdraw_player(player, inter)


@client.slash_command(name='warn', description="Warn a player for baiting", default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def warn_player(inter: discord.ApplicationCommandInteraction, *, player: discord.Member):
    await player_tracking.warn_player(player, inter)


@client.slash_command(name='unwarn', description="Manually remove a warning", default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def unwarn_player(inter: discord.ApplicationCommandInteraction, *, player: discord.Member):
    await player_tracking.unwarn_player(player, inter)


@client.slash_command(name='ban', description='Ban a player from playing in pugs', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def ban_player(inter: discord.ApplicationCommandInteraction, player: discord.Member, *, reason):
    await player_tracking.pug_ban(inter, player, reason)


@client.slash_command(name='unban', description='Unban a player', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def unban_player(inter: discord.ApplicationCommandInteraction, *, player: discord.Member):
    await player_tracking.pug_unban(inter, player)


@client.slash_command(name='status', description='Get the current status of a player', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def get_player_status(inter: discord.ApplicationCommandInteraction, *, player: discord.Member):
    await player_tracking.player_status(inter, player)


@client.slash_command(name='string', description='Announce the pug connect string', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def announce_string(inter: discord.ApplicationCommandInteraction, *, connect_string):
    await player_selection.announce_string(connect_string)


@client.slash_command(name='switch', description='Switch two players on a class', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def switch_players(inter: discord.ApplicationCommandInteraction, player_class: str):
    await player_selection.swap_class_across_teams(inter, player_class)


@client.slash_command(name='unassigned', aliases=['ua'], description='List players who are signed up but not assigned a class', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def list_unassigned_players(inter: discord.ApplicationCommandInteraction):
    await player_selection.list_unassigned_players(inter)


@client.slash_command(name='vote', description='Start a map vote', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def start_map_vote(inter: discord.ApplicationCommandInteraction, *maps):
    await map_voting.start_map_vote(inter, *maps)


@client.slash_command(name='teamvc', description='Move players into their team voice channel', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def drag_into_team_vc(inter: discord.ApplicationCommandInteraction):
    await player_selection.drag_into_team_vc(inter)


@client.slash_command(name='summon', aliases=['here'], description='Move players into your current voice channel', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def drag_into_same_vc(inter: discord.ApplicationCommandInteraction):
    await player_selection.drag_into_same_vc(inter)


@client.slash_command(name='log', description='Submit the logs.tf log for elo tracking', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def fetch_logs(inter: discord.ApplicationCommandInteraction, log_url: str):
    await elo_tracking.fetch_logs(inter, log_url)


@fetch_logs.error
async def fetch_logs_error(ctx, error):
    if isinstance(error, IndexError):
        await ctx.channel.send("Log not found")
    elif isinstance(error, json.JSONDecodeError):
        await ctx.channel.send("Log not found")
    elif isinstance(error, commands.CheckFailure):
        return
    else:
        ctx.channel.send(f"An unhandled error occurred ({messages.dev.mention})")
        raise error


@client.slash_command(name='ping', description='Ping signed up players who are currently not in a voice channel', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def ping_players(inter: discord.ApplicationCommandInteraction):
    await player_selection.ping_not_present(inter)


@client.slash_command(name='shutdown', default_permission=False)
@commands.guild_permissions(GUILD_ID, user_ids={DEV_ID: True})
async def cancel_scheduled_announcements(inter: discord.ApplicationCommandInteraction):
    await inter.send("Cancelling future announcements...")
    main.pug_scheduler.announcement_future.cancel()
    main.pug_scheduler.early_announcement_future.cancel()
    second.pug_scheduler.announcement_future.cancel()
    second.pug_scheduler.early_announcement_future.cancel()


@client.slash_command(name='clearpins', default_permission=False)
@commands.guild_permissions(GUILD_ID, user_ids={DEV_ID: True})
async def clear_bot_pins(inter: discord.ApplicationCommandInteraction):
    pinned_message: discord.Message
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


@client.slash_command(description='button', default_permission=False)
@commands.guild_permissions(GUILD_ID, {HOST_ROLE_ID: True})
async def button(inter: discord.ApplicationCommandInteraction):
    view = discord.ui.View()
    #button_obj = discord.ui.Button(style=discord.ButtonStyle.danger, label='test')
    #button_obj2 = discord.ui.Button(style=discord.ButtonStyle.success, label='test')
    options = [discord.SelectOption(label='dibbydoda', description='a bad player'), discord.SelectOption(label='oldcustard', description='a good player')]
    selection = discord.ui.Select(placeholder="Select a Player", options=options)
    selection2 = discord.ui.Select(placeholder="Select a Player", options=options)
    selection3 = discord.ui.Select(placeholder="Select a Player", options=options)
    selection4 = discord.ui.Select(placeholder="Select a Player", options=options)
    selection5 = discord.ui.Select(placeholder="Select a Player", options=options)
    selection6 = discord.ui.Select(placeholder="Select a Player", options=options)
    view.add_item(selection)
    view.add_item(selection2)
    view.add_item(selection3)
    view.add_item(selection4)
    view.add_item(selection5)
    await inter.response.send_message('test', view=view)


def start():
    client.run(os.getenv('TOKEN'))


if __name__ == '__main__':
    start()
