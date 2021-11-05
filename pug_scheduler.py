import asyncio
import configparser
import datetime
import time
from distutils.util import strtobool

import discord

import messages
import player_tracking
import start_pug
import player_selection

config = configparser.ConfigParser()
config.read('config.ini')
config = config['Pug Settings']

pug_enabled = bool(strtobool(config['pug enabled']))

ANNOUNCE_WDAY = config['announce weekday']
ANNOUNCE_HOUR = config['announce hour']
ANNOUNCE_MINUTE = config['announce minute']

pugMessage: discord.Message


def seconds_until(desired_time: datetime.datetime):
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()  # Time and date now
    print(f"{(desired_time - now).total_seconds()} seconds until set time")
    return (desired_time - now).total_seconds()


async def schedule_announcement(announce_channel: discord.TextChannel):
    while pug_enabled:
        announce_day = time.strptime(ANNOUNCE_WDAY, "%A")
        current_date = datetime.datetime.now(datetime.timezone.utc).astimezone()
        current_day = current_date.weekday()
        time_to_announce = datetime.timedelta(days=announce_day.tm_wday - current_day,
                                              hours=int(ANNOUNCE_HOUR) - current_date.hour,
                                              minutes=int(ANNOUNCE_MINUTE) - current_date.minute)
        if time_to_announce.total_seconds() < 0:
            time_to_announce = time_to_announce + datetime.timedelta(days=7)  # Ensure announcement is in the future
        announce_date = current_date + time_to_announce
        announce_date = announce_date.replace(hour=int(ANNOUNCE_HOUR), minute=int(ANNOUNCE_MINUTE), second=0,
                                              microsecond=0)
        print(f"Pug announcement scheduled for {announce_date}")
        await messages.send_to_admin(f"{messages.dev.mention}: Pug announcement scheduled for {datetime.datetime.strftime(announce_date, '%A (%d %B) at %X')}")
        await asyncio.sleep(seconds_until(announce_date))
        global pugMessage
        pugMessage = await start_pug.announce_pug(announce_channel)
        await messages.send_to_admin(f"{messages.host_role.mention}: **Bakes Pug has been announced.** Signups will be listed below as they come in")
        await asyncio.sleep(60)


async def schedule_pug_start(announce_channel: discord.TextChannel, pug_date: datetime.datetime):
    await messages.send_to_admin(f"{messages.dev.mention}: Pug scheduled for {datetime.datetime.strftime(pug_date, '%A (%d %B) at %X')}")
    print(f"Pug scheduled for {pug_date}")
    await asyncio.sleep(seconds_until(pug_date))
    print("Pug starts now; saving medics")
    medics = [player_selection.blu_team['Medic'], player_selection.red_team['Medic']]
    for medic in medics:
        await player_tracking.add_medic(medic)
