import discord
import time
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
config = config['Pug Settings']

announce_string = config['intro string']
pug_wday = config['pug weekday']
pug_hour = config['pug hour']

emojis_ids = [
    '<:scout:902551045891309579>',
    '<:soldier:902551045861957642>',
    '<:pyro:902551046189092875>',
    '<:demoman:902551045815816202>',
    '<:heavy:902551045677416489>',
    '<:engineer:902551046004572211>',
    '<:medic:902551045761269782>',
    '<:sniper:902551045891313754>',
    '<:spy:902551045853560842>'
]

signups = {
    emojis_ids[0]: [],
    emojis_ids[1]: [],
    emojis_ids[2]: [],
    emojis_ids[3]: [],
    emojis_ids[4]: [],
    emojis_ids[5]: [],
    emojis_ids[6]: [],
    emojis_ids[7]: [],
    emojis_ids[8]: []
}
signupsMessage: discord.Message = None


async def start_pug(channel: discord.TextChannel):
    pug_time = time.strptime(pug_wday + ' ' + pug_hour, "%A %H")
    pug_time_string = time.strftime("%A at %I%p", pug_time)
    announce_message = announce_string+"\nPug will be **" + pug_time_string + "**"
    pugMessage: discord.Message = await channel.send(announce_message)
    for reactionEmoji in emojis_ids:
        await pugMessage.add_reaction(reactionEmoji)
    return pugMessage


async def list_players():
    signupClass: str
    players: list
    msg: str = ""
    for signupClass, players in signups.items():
        line = signupClass + ": " + ", ".join(players)
        msg = msg + "\n" + line
    return msg
