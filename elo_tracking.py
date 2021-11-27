import urllib.request
import json

import discord.ext.commands


async def fetch_logs(ctx: discord.ext.commands.Context, log_url):
    log_id = log_url.split('.tf/')[1]
    log_json = urllib.request.urlopen("http://logs.tf/json/" + log_id)
    log_json = json.load(log_json)
    score = (log_json['teams']['Blue']['score'], log_json['teams']['Red']['score'])
