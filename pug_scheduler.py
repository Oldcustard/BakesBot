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

EARLY_OFFSET = float(config['medic offset'])

pugMessage: discord.Message
earlyPugMessage: discord.Message
earlyMedicPugMessage: discord.Message


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
        early_announce_date = announce_date - datetime.timedelta(hours=EARLY_OFFSET)
        asyncio.ensure_future(schedule_early_announcement(messages.earlyAnnounceChannel, announce_channel, early_announce_date))
        print(f"Pug announcement scheduled for {announce_date}")
        await messages.send_to_admin(f"{messages.dev.mention}: Pug announcement scheduled for {datetime.datetime.strftime(announce_date, '%A (%d %B) at %X')}")
        await asyncio.sleep(seconds_until(announce_date))
        global pugMessage
        pugMessage, pug_date = await start_pug.announce_pug(announce_channel)
        await messages.send_to_admin(f"{messages.host_role.mention}: **Bakes Pug has been announced.**")
        asyncio.ensure_future(schedule_pug_start(pug_date))
        await asyncio.sleep(60)


async def schedule_early_announcement(early_announce_channel: discord.TextChannel, regular_announce_channel: discord.TextChannel, early_announce_date: datetime.datetime):
    print(f"Early announcement scheduled for {early_announce_date}")
    await messages.send_to_admin(f"{messages.dev.mention}: Early announcement scheduled for {datetime.datetime.strftime(early_announce_date, '%A (%d %B) at %X')}")
    await asyncio.sleep(seconds_until(early_announce_date))
    global earlyPugMessage, earlyMedicPugMessage
    earlyPugMessage, earlyMedicPugMessage = await start_pug.announce_early(early_announce_channel, regular_announce_channel)
    await messages.send_to_admin(f"{messages.host_role.mention}: **Early signups are open**")


async def schedule_pug_start(pug_date: datetime.datetime):
    print(f"Pug scheduled for {pug_date}")
    await asyncio.sleep(seconds_until(pug_date))
    print("Pug starts now; saving medics")
    print(await player_tracking.decrement_medic_counters())
    medics = [player_selection.blu_team['Medic'], player_selection.red_team['Medic']]
    for medic in medics:
        if medic is None:
            continue
        print(await player_tracking.add_medic(medic))
    await player_tracking.update_early_signups()
    await start_pug.reset_pug()
