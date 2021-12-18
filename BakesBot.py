# BakesBot.py
import datetime
import json
import asyncio

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
client = commands.Bot('$', intents=intents, test_guilds=[902442233482063892])

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
    messages.guild = messages.announceChannel.guild
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


def is_host():
    def predicate(inter: discord.ApplicationCommandInteraction):
        return messages.host_role in inter.author.roles

    return commands.check(predicate)


def is_dev():
    def predicate(ctx: commands.Context):
        return ctx.author == messages.dev

    return commands.check(predicate)


@client.command(name='select', aliases=['s'])
@is_host()
async def select_player(ctx: commands.Context, team, player_class, *, player: discord.Member):
    if active_pug.start_pug.signupsMessage is None:
        await ctx.channel.send("Player selection only available after pug is announced")
        return
    await player_selection.select_player(ctx, team, player_class, player)


@client.event
async def on_command_error(ctx: commands.Context, error):
    if ctx.command is None:  # Command not recognised
        await ctx.channel.send(f"Command not recognised.")
        return
    if ctx.command.has_error_handler():  # Command has a specific handler, ignore
        return
    if isinstance(error, commands.CheckFailure):
        await ctx.channel.send(f"Insufficient permissions.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.channel.send(f"Player not found. Try different capitalisation or mention them directly.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.channel.send("Missing all required parameters")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.channel.send(f"An error occurred: {error.original} {type(error.original)} ({messages.dev.mention})")
        raise error
    else:
        await ctx.channel.send(f"An error occurred: {error} {type(error)} ({messages.dev.mention})")
        raise error


@client.command(name='forcestart')
@is_dev()
async def force_start_pug(ctx: commands.Context):
    await active_pug.pug_scheduler.schedule_pug_start(datetime.datetime.now(datetime.timezone.utc).astimezone(), True)


@client.command(name='forcereset')
@is_dev()
async def force_reset(ctx: commands.Context):
    await active_pug.start_pug.reset_pug()


@client.command(name='withdraw')
@is_host()
async def force_withdraw_player(ctx: commands.Context, *, player: discord.Member):
    await active_pug.start_pug.withdraw_player(player)


@client.slash_command(name='warn', description="Warn a player for baiting")
@is_host()
async def warn_player(inter: discord.ApplicationCommandInteraction, *, player: discord.Member):
    await player_tracking.warn_player(player, inter)


@client.slash_command(name='unwarn', description="Manually remove a warning")
@is_host()
async def unwarn_player(inter: discord.ApplicationCommandInteraction, *, player: discord.Member):
    await player_tracking.unwarn_player(player, inter)


@client.command(name='ban')
@is_host()
async def ban_player(ctx: commands.Context, player: discord.Member, *, reason):
    await player_tracking.pug_ban(player, reason)


@ban_player.error
async def ban_player_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.channel.send("Insufficient permissions.")
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.channel.send("Required Parameters: <player> <reason>")
    else:
        await ctx.channel.send(f"An error occurred: {error} {type(error)} ({messages.dev.mention})")
        raise error


@client.command(name='unban')
@is_host()
async def unban_player(ctx: commands.Context, *, player: discord.Member):
    await player_tracking.pug_unban(player)


@client.command(name='status')
@is_host()
async def get_player_status(ctx: commands.Context, *, player: discord.Member):
    await player_tracking.player_status(ctx, player)


@client.command(name='string')
@is_host()
async def announce_string(ctx: commands.Context, *, connect_string):
    await player_selection.announce_string(connect_string)


@client.command(name='switch')
@is_host()
async def switch_players(ctx: commands.Context, player_class: str):
    await player_selection.swap_class_across_teams(ctx, player_class)


@client.command(name='unassigned', aliases=['ua'])
@is_host()
async def list_unassigned_players(ctx: commands.Context):
    await player_selection.list_unassigned_players(ctx)


@client.command(name='vote')
@is_host()
async def start_map_vote(ctx: commands.Context, *maps):
    await map_voting.start_map_vote(ctx, *maps)


@client.command(name='teamvc')
@is_host()
async def drag_into_team_vc(ctx: commands.Context):
    await player_selection.drag_into_team_vc(ctx)


@client.command(name='summon', aliases=['here'])
@is_host()
async def drag_into_same_vc(ctx: commands.Context):
    await player_selection.drag_into_same_vc(ctx)


@client.command(name='log')
@is_host()
async def fetch_logs(ctx: commands.Context, log_url: str):
    await elo_tracking.fetch_logs(ctx, log_url)


@fetch_logs.error
async def fetch_logs_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.channel.send("Missing all parameters")
    elif isinstance(error, IndexError):
        await ctx.channel.send("Log not found")
    elif isinstance(error, json.JSONDecodeError):
        await ctx.channel.send("Log not found")
    elif isinstance(error, commands.CheckFailure):
        return
    else:
        ctx.channel.send(f"An unhandled error occurred ({messages.dev.mention})")
        raise error


@client.command(name='ping')
@is_host()
async def ping_players(ctx: commands.Context):
    await player_selection.ping_not_present()


@client.command(name='shutdown')
@is_dev()
async def cancel_scheduled_announcements(ctx: commands.Context):
    await ctx.channel.send("Cancelling future announcements...")
    main.pug_scheduler.announcement_future.cancel()
    main.pug_scheduler.early_announcement_future.cancel()
    second.pug_scheduler.announcement_future.cancel()
    second.pug_scheduler.early_announcement_future.cancel()


@client.command(name='clearpins')
@is_dev()
async def clear_bot_pins(ctx: commands.Context):
    pinned_message: discord.Message
    await ctx.channel.send("Clearing admin channel pins...")
    for pinned_message in await messages.adminChannel.pins():
        if pinned_message.author == client.user:
            await pinned_message.unpin()
    print("Cleared admin channel pins")
    await ctx.channel.send("Cleared admin channel pins")
    await ctx.channel.send("Clearing announce channel pins...")
    for pinned_message in await messages.announceChannel.pins():
        if pinned_message.author == client.user:
            await pinned_message.unpin()
    print("Cleared announce channel pins")
    await ctx.channel.send("Cleared announce channel pins")


def start():
    client.run(os.getenv('TOKEN'))


if __name__ == '__main__':
    start()
