import configparser
from distutils.util import strtobool

import discord

config = configparser.ConfigParser()
config.read('config.ini')
config = config['Message Settings']

earlyAnnounceChannel: discord.TextChannel
guild: discord.Guild
adminChannel: discord.TextChannel
admin: discord.User
host_role: discord.Role
medic_role: discord.Role
banned_role: discord.Role
gamer_role: discord.Role
dev: discord.User

useDM = bool(strtobool(config['use DMs']))


async def send_to_admin(message: str):
    if useDM:
        newMessage = await admin.send(message)
    else:
        newMessage = await adminChannel.send(message)
    return newMessage
