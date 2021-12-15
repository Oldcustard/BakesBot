from typing import List

import disnake as discord
import disnake.ext.commands

import active_pug
import messages
import player_selection

active_votes: List[discord.MessageReference] = []

emoji_list = ('1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟')


async def start_map_vote(ctx: disnake.ext.commands.Context, *maps):
    map_list_string = ""
    for i, map_name in enumerate(maps):
        line = f"{emoji_list[i]} {map_name.capitalize()}"
        map_list_string = map_list_string + "\n" + line
    message = await messages.announceChannel.send("Map voting open. Please select from the maps below\n" + map_list_string)
    active_votes.append(discord.MessageReference.from_message(message))
    active_pug.start_pug.messages_to_delete.append(message)
    for i in range(len(maps)):
        await message.add_reaction(emoji_list[i])
    await ctx.channel.send("Vote has started")


async def vote_for_map(reaction: discord.Reaction, user: discord.Member):
    if user not in player_selection.blu_team.values() and user not in player_selection.red_team.values():
        await reaction.remove(user)
        await user.send("You may only vote once you have been assigned to a class.")
        return


async def clear_user_votes(user: discord.Member):
    for vote_ref in active_votes:
        vote = vote_ref.cached_message
        for reaction in vote.reactions:
            await reaction.remove(user)
