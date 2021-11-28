from typing import List

import discord.ext.commands

import messages

active_votes: List[discord.Message] = []

emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']


async def start_map_vote(ctx: discord.ext.commands.Context, *maps):
    map_list_string = ""
    for i, map_name in enumerate(maps):
        line = f"{emoji_list[i]} {map_name.capitalize()}"
        map_list_string = map_list_string + "\n" + line
    message = await messages.announceChannel.send("Map voting open. Please select from the maps below\n" + map_list_string)
    active_votes.append(message)
    for i in range(len(maps)):
        await message.add_reaction(emoji_list[i])
    await ctx.channel.send("Vote has started")
