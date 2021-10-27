# main.py

import os
import configparser
import discord
import logging

import start_pug

logging.basicConfig(level=logging.WARNING)
config = configparser.ConfigParser()
config.read('config.ini')

intents = discord.Intents().default()
intents.members = True
client = discord.Client(intents=intents)

announce_channel_id = int(os.getenv('announce_channel_id'))
admin_channel_id = int(os.getenv('admin_channel_id'))
admin_id = int(os.getenv('admin_id'))

if config['Message Settings']['use DMs'] == 'true':
    useDM = True
else:
    useDM = False

announceChannel: discord.TextChannel
adminChannel: discord.TextChannel
admin: discord.User
pugMessage: discord.Message


async def send_to_admin(message: str):
    if useDM:
        newMessage = await admin.send(message)
    else:
        newMessage = await adminChannel.send(message)
    return newMessage


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    global announceChannel, adminChannel, admin
    announceChannel = client.get_channel(announce_channel_id)
    adminChannel = client.get_channel(admin_channel_id)
    admin = await client.fetch_user(admin_id)
    print('')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$start'):
        global pugMessage
        pugMessage = await start_pug.start_pug(announceChannel)
        await send_to_admin("**Bakes Pug has been announced.** Signups will be listed below as they come in")
        print("Pug has been announced")


@client.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.Member):
    if user != client.user and reaction.message == pugMessage:
        players = start_pug.signups.get(str(reaction.emoji))
        if players is None:
            await reaction.remove(user)
            return
        players.append(user.display_name)
        print(f'{user.display_name} has signed up for {reaction.emoji}')
        print(reaction.emoji, players)
        if start_pug.signupsMessage is None:
            start_pug.signupsMessage = await send_to_admin(await start_pug.list_players())
        else:
            await start_pug.signupsMessage.edit(content=await start_pug.list_players())


@client.event
async def on_reaction_remove(reaction: discord.Reaction, user: discord.Member):
    if reaction.message == pugMessage:
        players = start_pug.signups.get(str(reaction.emoji))
        if players is None:
            return
        players.remove(user.display_name)
        print(f'{user.display_name} has withdrawn from {reaction.emoji}')
        print(reaction.emoji, players)
        await start_pug.signupsMessage.edit(content=(await start_pug.list_players()))


client.run(os.getenv('TOKEN'))
