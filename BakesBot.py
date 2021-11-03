# BakesBot.py
from dotenv import load_dotenv

import os
import configparser
import discord
import discord.ext.commands
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
client = discord.ext.commands.Bot('!', intents=intents)

announce_channel_id = int(os.getenv('announce_channel_id'))
admin_channel_id = int(os.getenv('admin_channel_id'))
admin_id = int(os.getenv('admin_id'))
host_role_id = int(os.getenv('host_role_id'))
dev_id = int(os.getenv('dev_id'))

announceChannel: discord.TextChannel


@client.event
async def on_ready():
    print(f'{client.user} logged in')
    global announceChannel
    announceChannel = client.get_channel(announce_channel_id)
    guild: discord.Guild = announceChannel.guild
    messages.host_role = guild.get_role(host_role_id)
    messages.adminChannel = client.get_channel(admin_channel_id)
    messages.admin = await client.fetch_user(admin_id)
    messages.dev = await client.fetch_user(dev_id)
    print('')
    await pug_scheduler.schedule_announcement(announceChannel)


@client.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.Member):
    try:
        if user != client.user and reaction.message == pug_scheduler.pugMessage:
            await start_pug.on_reaction_add(reaction, user)
    except AttributeError:
        return   # Pug hasn't started yet, ignore


@client.command(name='select', aliases=['s'])
async def select_player(ctx: discord.ext.commands.Context, team, player_class, player: discord.Member):
    if start_pug.signupsMessage is None:
        await ctx.channel.send("Player selection only available after pug is announced")
        return
    await player_selection.select_player(ctx, team, player_class, player)


@select_player.error
async def select_player_error(ctx, error):
    if isinstance(error, discord.ext.commands.MissingRequiredArgument):
        await ctx.channel.send("Missing all parameters")
    elif isinstance(error, discord.ext.commands.MemberNotFound):
        await ctx.channel.send(f"Player not found. Try different capitalisation or mention them directly.")
    else:
        raise error


def main():
    client.run(os.getenv('TOKEN'))


if __name__ == '__main__':
    main()
