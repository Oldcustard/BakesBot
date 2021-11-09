# BakesBot.py
import datetime

from dotenv import load_dotenv

import os
import configparser
import discord
from discord.ext import commands
import logging

import messages
import player_selection
import pug_scheduler
import start_pug

load_dotenv()

logging.basicConfig(level=logging.WARNING)
config = configparser.ConfigParser()
config.read('config.ini')

intents = discord.Intents().default()
intents.members = True
client = commands.Bot('!', intents=intents)

ANNOUNCE_CHANNEL_ID = int(os.getenv('announce_channel_id'))
EARLY_ANNOUNCE_CHANNEL_ID = int(os.getenv('early_announce_channel_id'))
ADMIN_CHANNEL_ID = int(os.getenv('admin_channel_id'))
ADMIN_ID = int(os.getenv('admin_id'))
MEDIC_ROLE_ID = int(os.getenv('medic_role_id'))
HOST_ROLE_ID = int(os.getenv('host_role_id'))
DEV_ID = int(os.getenv('dev_id'))

announceChannel: discord.TextChannel


@client.event
async def on_ready():
    print(f'{client.user} logged in')
    global announceChannel
    announceChannel = client.get_channel(ANNOUNCE_CHANNEL_ID)
    messages.earlyAnnounceChannel = client.get_channel(EARLY_ANNOUNCE_CHANNEL_ID)
    messages.guild = announceChannel.guild
    messages.medic_role = messages.guild.get_role(MEDIC_ROLE_ID)
    messages.host_role = messages.guild.get_role(HOST_ROLE_ID)
    messages.adminChannel = client.get_channel(ADMIN_CHANNEL_ID)
    messages.admin = await client.fetch_user(ADMIN_ID)
    messages.dev = await client.fetch_user(DEV_ID)
    print('')
    await pug_scheduler.schedule_announcement(announceChannel)


@client.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.Member):
    try:
        if user != client.user and reaction.message == pug_scheduler.earlyPugMessage:
            await start_pug.on_reaction_add(reaction, user)  # Early signup
        elif user != client.user and reaction.message == pug_scheduler.earlyMedicPugMessage:
            await start_pug.on_reaction_add(reaction, user)  # Early medic signup
        elif user != client.user and reaction.message == pug_scheduler.pugMessage:
            await start_pug.on_reaction_add(reaction, user)  # Regular signup
    except AttributeError:  # Signups not declared yet, ignore
        pass


def is_host():
    def predicate(ctx):
        return messages.host_role in ctx.message.author.roles

    return commands.check(predicate)


@client.command(name='select', aliases=['s'])
@is_host()
async def select_player(ctx: commands.Context, team, player_class, player: discord.Member):
    if start_pug.signupsMessage is None:
        await ctx.channel.send("Player selection only available after pug is announced")
        return
    await player_selection.select_player(ctx, team, player_class, player)


@select_player.error
async def select_player_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.channel.send("Missing all parameters")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.channel.send(f"Player not found. Try different capitalisation or mention them directly.")
    elif isinstance(error, commands.CheckFailure):
        await ctx.channel.send(f"Insufficient permissions.")
    else:
        raise error


@client.command(name='forcestart')
@is_host()
async def force_start_pug(ctx: discord.ext.commands.Context):
    await pug_scheduler.schedule_pug_start(datetime.datetime.now(datetime.timezone.utc).astimezone())


def main():
    client.run(os.getenv('TOKEN'))


if __name__ == '__main__':
    main()
