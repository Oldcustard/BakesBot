import configparser
from distutils.util import strtobool

import discord

config = configparser.ConfigParser()
config.read('config.ini')
config = config['Message Settings']

adminChannel: discord.TextChannel
admin: discord.User

useDM = bool(strtobool(config['use DMs']))


async def send_to_admin(message: str):
    if useDM:
        newMessage = await admin.send(message)
    else:
        newMessage = await adminChannel.send(message)
    return newMessage
