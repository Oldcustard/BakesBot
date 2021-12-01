import configparser
from distutils.util import strtobool

import discord

config = configparser.ConfigParser()
config.read('config.ini')
config = config['Message Settings']

guild: discord.Guild

announceChannel: discord.TextChannel
earlyAnnounceChannel: discord.TextChannel
adminChannel: discord.TextChannel

bluChannel: discord.VoiceChannel
redChannel: discord.VoiceChannel

host_role: discord.Role
medic_role: discord.Role
banned_role: discord.Role
gamer_role: discord.Role

admin: discord.User
dev: discord.User

useDM = bool(strtobool(config['use DMs']))


async def send_to_admin(message: str):
    if useDM:
        newMessage = await admin.send(message)
    else:
        newMessage = await adminChannel.send(message)
    return newMessage
