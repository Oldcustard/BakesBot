from typing import List, Dict

import disnake as discord
import disnake.ext.commands

import active_pug
import messages
import player_selection

active_votes: List[discord.Message] = []

payload_map_list = {
            'Swiftwater': '🚇',
            'Badwater': '🏜',
            'Upward': '⛰',
            'Borneo': '🌲',
            'Vigil': '🔭',
            'Steel': '🕳'}

koth_map_list = {
            'Ashville': '🏭',
            'Product': '🌉',
            'Warmtic': '☀'}


async def start_map_vote(inter: discord.ApplicationCommandInteraction, map_type):
    if map_type == "Attack/Defend":
        map_list = payload_map_list
    elif map_type == "KOTH":
        map_list = koth_map_list
    maps = []
    selected_maps = []
    for map_name, map_emoji in map_list.items():
        maps.append(discord.SelectOption(label=map_name, emoji=map_emoji))

    class MapSelectView(discord.ui.View):
        @discord.ui.select(options=maps, max_values=len(maps), placeholder="Select maps")
        async def submit_maps(self: discord.ui.View, select: discord.ui.Select, confirm_inter: discord.MessageInteraction):
            for selection in select.values:
                selected_maps.append(selection)
            await start_vote()
            await confirm_inter.send("Vote Started")
            select.disabled = True
            await inter.edit_original_message(view=self)

    await inter.response.send_message("Select maps", view=MapSelectView())

    def create_callback():
        async def _callback(inter: discord.MessageInteraction):
            await inter.send(f"Successfully voted for {inter.component.emoji} {inter.component.label}", ephemeral=True)
        return _callback

    async def start_vote():
        view = discord.ui.View(timeout=None)

        for map_name, map_emoji in map_list.items():
            if map_name not in selected_maps:
                continue
            callback = create_callback()
            button = discord.ui.Button(label=map_name, emoji=map_emoji)
            button.callback = callback
            view.add_item(button)

        message = await messages.announceChannel.send("Map voting open. Please select from the maps below (as many as you like)", view=view)
        active_votes.append(message)
        #active_pug.start_pug.messages_to_delete.append(message)


async def vote_for_map(reaction: discord.Reaction, user: discord.Member):
    if user not in player_selection.blu_team.values() and user not in player_selection.red_team.values():
        await reaction.remove(user)
        await user.send("You may only vote once you have been assigned to a class.")
        return

