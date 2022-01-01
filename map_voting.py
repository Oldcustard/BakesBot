from typing import List, Dict

import disnake as discord
import disnake.ext.commands

import active_pug
import messages
import player_selection


class MapVote:
    def __init__(self, message: discord.Message, options: Dict[str, List[discord.Member]]):
        self.message = message
        self.options = options

    def add_vote(self, member: discord.Member, option: str):
        if member not in self.options[option]:
            self.options[option].append(member)
            return True
        else:
            return False

    def delete_votes(self, member: discord.Member):
        for option in self.options.values():
            if member in option:
                option.remove(member)



active_votes: List[MapVote] = []

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
        async def _vote_for_map(inter: discord.MessageInteraction):
            if inter.author in player_selection.blu_team.values() or inter.author in player_selection.red_team.values():
                for vote in active_votes:
                    if vote.message == inter.message:
                        if vote.add_vote(inter.author, inter.component.label):
                            await inter.send(f"Successfully voted for {inter.component.emoji}{inter.component.label}", ephemeral=True)
                        else:
                            await inter.send(f"You have already voted for {inter.component.emoji}{inter.component.label}", ephemeral=True)
            else:
                await inter.send(f"You may only vote once you have been assigned a class", ephemeral=True)
        return _vote_for_map

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
        active_votes.append(MapVote(message, dict([(key, []) for key in selected_maps])))
        active_pug.start_pug.messages_to_delete.append(message)


async def view_results(inter: discord.ApplicationCommandInteraction):
    msg = ""
    for vote in active_votes:
        msg += "\n"
        for option, voters in vote.options.items():
            msg += f"\n{option}: {len(voters)}"
    await inter.send(msg)


async def remove_player_votes(user: discord.Member):
    for vote in active_votes:
        vote.delete_votes(user)
