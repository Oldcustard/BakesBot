import asyncio
import configparser
import datetime
import time
from distutils.util import strtobool

import discord

import active_pug
import messages
import player_tracking
from main import start_pug
import player_selection

config = configparser.ConfigParser()
config.read('config.ini')
timing_config = config['Timing Settings']
config = config['Main Pug Settings']

pug_enabled = bool(strtobool(config['pug enabled']))

ANNOUNCE_WDAY = config['announce weekday']
ANNOUNCE_HOUR = config['announce hour']
ANNOUNCE_MINUTE = config['announce minute']

EARLY_OFFSET = float(timing_config['medic offset'])
LATE_SIGNUP_PENALTY = float(timing_config['signup penalty time'])
PENALTY_TRIGGER_OFFSET = float(timing_config['late penalty offset'])

pugMessage: discord.Message
earlyPugMessage: discord.Message
earlyMedicPugMessage: discord.Message
penalty_signup_time: datetime.datetime
penalty_trigger_time: datetime.datetime
pug_date: datetime.datetime

announcement_future: asyncio.Task
early_announcement_future: asyncio.Task

startup = True


def seconds_until(desired_time: datetime.datetime):
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()  # Time and date now
    print(f"{(desired_time - now).total_seconds()} seconds until set time")
    return (desired_time - now).total_seconds()


async def schedule_announcement(announce_channel: discord.TextChannel):
    try:
        if pug_enabled:
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
            global penalty_signup_time
            penalty_signup_time = announce_date + datetime.timedelta(hours=LATE_SIGNUP_PENALTY)

            global early_announcement_future
            early_announcement_future = asyncio.ensure_future(schedule_early_announcement(messages.earlyAnnounceChannel, announce_channel, early_announce_date))
            print(f"Pug announcement scheduled for {announce_date}")
            announce_timestamp = round(datetime.datetime.timestamp(announce_date))
            await messages.send_to_admin(f"{messages.dev.mention}: Pug announcement scheduled for <t:{announce_timestamp}:F>")
            global startup
            startup = False
            await asyncio.sleep(seconds_until(announce_date))
            global pugMessage, pug_date
            pugMessage, pug_date = await start_pug.announce_pug(announce_channel)
            global penalty_trigger_time
            penalty_trigger_time = pug_date - datetime.timedelta(hours=PENALTY_TRIGGER_OFFSET)
            await messages.send_to_admin(f"{messages.host_role.mention}: **Bakes Pug has been announced.**")
            asyncio.ensure_future(schedule_pug_start(pug_date))
            await active_pug.change_active_pug('main')
    except asyncio.CancelledError:
        print(f"Announcement for {announce_date} has been cancelled.")
        await messages.send_to_admin(f"Announcement for <t:{announce_timestamp}:F> has been cancelled.")


async def schedule_early_announcement(early_announce_channel: discord.TextChannel, regular_announce_channel: discord.TextChannel, early_announce_date: datetime.datetime):
    try:
        print(f"Early announcement scheduled for {early_announce_date}")
        early_announce_timestamp = round(datetime.datetime.timestamp(early_announce_date))
        await messages.send_to_admin(f"{messages.dev.mention}: Early announcement scheduled for <t:{early_announce_timestamp}:F>")
        await asyncio.sleep(seconds_until(early_announce_date))
        global earlyPugMessage, earlyMedicPugMessage
        earlyPugMessage, earlyMedicPugMessage = await start_pug.announce_early(early_announce_channel, regular_announce_channel)
        await messages.send_to_admin(f"{messages.host_role.mention}: **Early signups are open**")
        await active_pug.change_early_active_pug('main')
    except asyncio.CancelledError:
        print(f"Early Announcement for {early_announce_date} has been cancelled.")
        await messages.send_to_admin(f"Early Announcement for <t:{early_announce_timestamp}:F> has been cancelled.")


async def schedule_pug_start(date: datetime.datetime, immediate=False):
    print(f"Pug scheduled for {date}")
    if not immediate:
        await asyncio.sleep(seconds_until(penalty_trigger_time))
    print("Penalty withdrawals begin now, posting reminder")
    pug_timestamp = round(datetime.datetime.timestamp(date))
    await player_selection.announce_string(timestamp=pug_timestamp)
    await asyncio.sleep(seconds_until(date))
    print("Pug starts now: clearing active warnings, warning baiters")
    await player_tracking.decrement_active_warnings()
    await start_pug.auto_warn_bating_players()
    if not immediate:
        print("Medic processing will occur in 75 minutes")
        await asyncio.sleep(75*60)
    print("Saving medics")
    print(await player_tracking.decrement_medic_counters())
    medics = [player_selection.blu_team['Medic'], player_selection.red_team['Medic']]
    for medic in medics:
        if medic is not None:
            print(await player_tracking.add_medic(medic))
    await player_tracking.update_early_signups()
    if immediate:
        return
    await start_pug.reset_pug()
    global announcement_future
    announcement_future = asyncio.ensure_future(schedule_announcement(messages.announceChannel))


async def penalty_signups_check():
    global penalty_signup_time
    current_date = datetime.datetime.now(datetime.timezone.utc).astimezone()
    penalty_signup_timestamp = round(datetime.datetime.timestamp(penalty_signup_time))
    return current_date < penalty_signup_time, f"<t:{penalty_signup_timestamp}:F> (<t:{penalty_signup_timestamp}:R>)"


async def after_penalty_trigger_check():
    global penalty_trigger_time
    current_date = datetime.datetime.now(datetime.timezone.utc).astimezone()
    penalty_trigger_timestamp = round(datetime.datetime.timestamp(penalty_trigger_time))
    return penalty_trigger_time < current_date, f"<t:{penalty_trigger_timestamp}:F> (<t:{penalty_trigger_timestamp}:R>)"