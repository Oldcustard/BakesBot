# BakesBot.py
from dotenv import load_dotenv

import os
import configparser
import discord
import logging

import messages
import pug_scheduler
import start_pug


load_dotenv()

logging.basicConfig(level=logging.WARNING)
config = configparser.ConfigParser()
config.read('config.ini')

intents = discord.Intents().default()
intents.members = True
client = discord.Client(intents=intents)

announce_channel_id = int(os.getenv('announce_channel_id'))
admin_channel_id = int(os.getenv('admin_channel_id'))
admin_id = int(os.getenv('admin_id'))
host_role_id = int(os.getenv('host_role_id'))

announceChannel: discord.TextChannel
pugMessage: discord.Message


@client.event
async def on_ready():
    print(f'{client.user} logged in')
    global announceChannel
    announceChannel = client.get_channel(announce_channel_id)
    guild: discord.Guild = announceChannel.guild
    messages.host_role = guild.get_role(host_role_id)
    messages.adminChannel = client.get_channel(admin_channel_id)
    messages.admin = await client.fetch_user(admin_id)
    print('')
    await pug_scheduler.schedule_announcement(announceChannel)


@client.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.Member):
    try:
        pug_scheduler.pugMessage  # Pug not announced yet, ignore
    except AttributeError:
        return
    if user != client.user and reaction.message == pug_scheduler.pugMessage:
        if reaction.emoji == "\U0000274C":  # Withdraw player
            await withdraw_player(user)
            for user_reaction in reaction.message.reactions:
                await user_reaction.remove(user)
            return
        players = start_pug.signups.get(str(reaction.emoji))
        if players is None:  # User added their own reaction
            await reaction.remove(user)
            return
        if user.display_name not in start_pug.player_classes:  # Add player to the player list
            start_pug.player_classes[user.display_name] = []
        if reaction.emoji in start_pug.player_classes[user.display_name]:  # Player already signed up for this class
            return
        start_pug.player_classes[user.display_name].append(reaction.emoji)  # Add class to that player's list
        preference = len(start_pug.player_classes[user.display_name])  # Preference for this class
        players.append(user.display_name + f' ({preference})')
        print(f'{user.display_name} has signed up for {reaction.emoji}')
        if start_pug.signupsMessage is None:
            start_pug.signupsMessage = await messages.send_to_admin(await start_pug.list_players())
        else:
            await start_pug.signupsMessage.edit(content=await start_pug.list_players())
        await user.send(f"Successfully signed up for {reaction.emoji} (preference {preference})")


async def withdraw_player(user: discord.Member):
    if user.display_name not in start_pug.player_classes:  # user pressed withdraw without being signed up
        return
    start_pug.player_classes.pop(user.display_name)
    for signup_class in start_pug.signups.values():
        user_signup = [s for s in signup_class if user.display_name in s]
        if len(user_signup) == 1:
            signup_class.remove(user_signup[0])
    print(f'{user.display_name} has withdrawn')
    await start_pug.signupsMessage.edit(content=await start_pug.list_players())
    await messages.send_to_admin(f"{messages.host_role.mention}: {user.display_name} has withdrawn from the pug")
    await user.send("You have withdrawn from the pug")


client.run(os.getenv('TOKEN'))
