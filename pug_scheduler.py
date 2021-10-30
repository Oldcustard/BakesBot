import asyncio
import configparser
import datetime
import time
from distutils.util import strtobool

import discord

import messages
import start_pug

config = configparser.ConfigParser()
config.read('config.ini')
config = config['Pug Settings']

pug_enabled = bool(strtobool(config['pug enabled']))

announce_wday = config['announce weekday']
announce_hour = config['announce hour']
announce_minute = config['announce minute']

pugMessage: discord.Message


def seconds_until(desired_time: datetime.datetime):
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()  # Time and date now
    print(f"{(desired_time - now).total_seconds()} seconds until set time")
    return (desired_time - now).total_seconds()


async def schedule_announcement(announce_channel: discord.TextChannel):
    while pug_enabled:
        announce_day = time.strptime(announce_wday, "%A")
        current_date = datetime.datetime.now(datetime.timezone.utc).astimezone()
        current_day = current_date.weekday()
        time_to_announce = datetime.timedelta(days=announce_day.tm_wday - current_day, hours=int(announce_hour) - current_date.hour, minutes=int(announce_minute) - current_date.minute)
        if time_to_announce.total_seconds() < 0:
            time_to_announce = datetime.timedelta(
                days=time_to_announce.days + 8)  # Ensure announcement is in the future
        announce_date = current_date + time_to_announce
        announce_date = announce_date.replace(hour=int(announce_hour), minute=int(announce_minute), second=0, microsecond=0)
        print(f"Pug announcement scheduled for {announce_date}")
        await messages.send_to_admin(f"{messages.host_role.mention}: Pug announcement scheduled for {datetime.datetime.strftime(announce_date, '%A (%d %B) at %X')}")
        await asyncio.sleep(seconds_until(announce_date))
        global pugMessage
        pugMessage = await start_pug.announce_pug(announce_channel)
        await messages.send_to_admin(f"{messages.host_role.mention}: **Bakes Pug has been announced.** Signups will be listed below as they come in")
        await asyncio.sleep(60)
