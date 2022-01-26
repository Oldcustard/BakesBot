import asyncio
import configparser
import datetime
import time
from distutils.util import strtobool

import disnake as discord

import active_pug
import messages
import player_tracking
import player_selection
import start_pug


def seconds_until(desired_time: datetime.datetime):
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()  # Time and date now
    print(f"{(desired_time - now).total_seconds()} seconds until set time")
    return (desired_time - now).total_seconds()


class PugScheduler:
    def __init__(self, pug_id):
        self.pug_id = pug_id
        self.start_pug = start_pug.StartPug(pug_id, self)
        config = configparser.ConfigParser()
        config.read('config.ini')
        timing_config = config['Timing Settings']
        if pug_id == 'main':
            config = config['Main Pug Settings']
        elif pug_id == 'second':
            config = config['Second Pug Settings']

        self.pug_enabled = bool(strtobool(config['pug enabled']))

        self.ANNOUNCE_WDAY = config['announce weekday']
        self.ANNOUNCE_HOUR = config['announce hour']
        self.ANNOUNCE_MINUTE = config['announce minute']

        self.EARLY_OFFSET = float(timing_config['medic offset'])
        self.LATE_SIGNUP_PENALTY = float(timing_config['signup penalty time'])
        self.PENALTY_TRIGGER_OFFSET = float(timing_config['late penalty offset'])

        self.pugMessage: discord.Message | None = None
        self.earlyPugMessage: discord.Message | None = None
        self.earlyMedicPugMessage: discord.Message | None = None
        self.penalty_signup_time: datetime.datetime | None = None
        self.penalty_trigger_time: datetime.datetime | None = None
        self.pug_date: datetime.datetime | None = None

        self.announcement_future: asyncio.Task | None = None
        self.early_announcement_future: asyncio.Task | None = None

    async def schedule_announcement(self, announce_channel: discord.TextChannel):
        try:
            if self.pug_enabled:
                announce_day = time.strptime(self.ANNOUNCE_WDAY, "%A")
                current_date = datetime.datetime.now(datetime.timezone.utc).astimezone()
                current_day = current_date.weekday()
                time_to_announce = datetime.timedelta(days=announce_day.tm_wday - current_day,
                                                      hours=int(self.ANNOUNCE_HOUR) - current_date.hour,
                                                      minutes=int(self.ANNOUNCE_MINUTE) - current_date.minute)
                if time_to_announce.total_seconds() < 0:
                    time_to_announce = time_to_announce + datetime.timedelta(days=7)  # Ensure announcement is in the future
                announce_date = current_date + time_to_announce
                announce_date = announce_date.replace(hour=int(self.ANNOUNCE_HOUR), minute=int(self.ANNOUNCE_MINUTE), second=0,
                                                      microsecond=0)
                early_announce_date = announce_date - datetime.timedelta(hours=self.EARLY_OFFSET)
                self.penalty_signup_time = announce_date + datetime.timedelta(hours=self.LATE_SIGNUP_PENALTY)
                self.early_announcement_future = asyncio.ensure_future(self.schedule_early_announcement(messages.earlyAnnounceChannel, announce_channel, early_announce_date))
                print(f"Pug announcement scheduled for {announce_date}")
                announce_timestamp = round(datetime.datetime.timestamp(announce_date))
                await messages.send_to_admin(f"Pug announcement scheduled for <t:{announce_timestamp}:F>")
                await asyncio.sleep(seconds_until(announce_date))
                self.pugMessage, self.pug_date = await self.start_pug.announce_pug(announce_channel)
                await messages.send_to_admin(f"{messages.host_role.mention}: **Bakes Pug has been announced.**")
                asyncio.ensure_future(self.schedule_pug_start(self.pug_date))
        except asyncio.CancelledError:
            print(f"Announcement for {announce_date} has been cancelled.")
            await messages.send_to_admin(f"Announcement for <t:{announce_timestamp}:F> has been cancelled.")

    async def schedule_early_announcement(self, early_announce_channel: discord.TextChannel, regular_announce_channel: discord.TextChannel, early_announce_date: datetime.datetime):
        try:
            print(f"Early announcement scheduled for {early_announce_date}")
            early_announce_timestamp = round(datetime.datetime.timestamp(early_announce_date))
            await messages.send_to_admin(f"Early announcement scheduled for <t:{early_announce_timestamp}:F>")
            await asyncio.sleep(seconds_until(early_announce_date))
            self.earlyPugMessage, self.earlyMedicPugMessage = await self.start_pug.announce_early(early_announce_channel, regular_announce_channel)
            await messages.send_to_admin(f"{messages.host_role.mention}: **Early signups are open**")
            active_pug.early_pug_scheduler = self
            active_pug.early_start_pug = self.start_pug
        except asyncio.CancelledError:
            print(f"Early Announcement for {early_announce_date} has been cancelled.")
            await messages.send_to_admin(f"Early Announcement for <t:{early_announce_timestamp}:F> has been cancelled.")

    async def schedule_pug_start(self, date: datetime.datetime, immediate=False):
        print(f"Pug scheduled for {date}")
        if not immediate:
            await asyncio.sleep(seconds_until(self.penalty_trigger_time))
        print("Penalty withdrawals begin now, posting reminder")
        pug_timestamp = round(datetime.datetime.timestamp(date))
        await player_selection.announce_string(timestamp=pug_timestamp)
        await asyncio.sleep(seconds_until(date))
        print("Pug starts now: clearing active warnings, warning baiters")
        await player_tracking.decrement_active_warnings()
        await self.start_pug.auto_warn_bating_players()
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
        await self.start_pug.reset_pug()
        self.announcement_future = asyncio.ensure_future(self.schedule_announcement(messages.announceChannel))

    async def penalty_signups_check(self):
        current_date = datetime.datetime.now(datetime.timezone.utc).astimezone()
        penalty_signup_timestamp = round(datetime.datetime.timestamp(self.penalty_signup_time))
        return current_date < self.penalty_signup_time, f"<t:{penalty_signup_timestamp}:F> (<t:{penalty_signup_timestamp}:R>)"

    async def after_penalty_trigger_check(self):
        current_date = datetime.datetime.now(datetime.timezone.utc).astimezone()
        penalty_trigger_timestamp = round(datetime.datetime.timestamp(self.penalty_trigger_time))
        return self.penalty_trigger_time < current_date, f"<t:{penalty_trigger_timestamp}:F> (<t:{penalty_trigger_timestamp}:R>)"