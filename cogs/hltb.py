from typing import Union

import disnake
from disnake.ext import commands
from howlongtobeatpy import HowLongToBeat, HowLongToBeatEntry


regex_is_year = r"\d{4}"


class HLTB(commands.Cog, name="How Long To Beat"):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="Search How Long to Beat by title.")
    async def hltb(self, inter, title: str):
        result = search_hltb(title)
        if result:
            await inter.response.send_message(embed=rendered_embed(result))
        else:
            await inter.response.send_message("Nothing found.")

    @commands.slash_command(description="Search How Long to Beat by id.")
    async def hltb_by_id(self, inter, _id: int):
        result = search_hltb_by_id(_id)
        if result:
            await inter.response.send_message(embed=rendered_embed(result))
        else:
            await inter.response.send_message("Nothing found.")


def rendered_embed(message: list) -> disnake.Embed:
    """

    :param message:
    :return:
    """
    banner = disnake.Embed(title="Multiple Results Found", description="Use /htlb_by_id to narrow results.")
    for index, each in enumerate(message):
        if type(each) is HowLongToBeatEntry:
            print('game entry')
            print(each)
            attrs = vars(each)
            print(attrs)
            banner = disnake.Embed(title=f"{attrs['game_name']}")
            banner.add_field(name="Web Link", value=f"{attrs['game_web_link']}", inline=False)
            banner.add_field(name="Review Score", value=f"{attrs['review_score']}")
            banner.add_field(name="Developer", value=f"{attrs['profile_dev']}")
            banner.add_field(name="Platforms", value=f"{' '.join(attrs['profile_platforms'])}")
            banner.add_field(name="Release Date", value=f"{attrs['release_world']}")
            banner.add_field(name="Main Story", value=f"{attrs['main_story']}")
            banner.add_field(name="Main Extra", value=f"{attrs['main_extra']}")
            banner.add_field(name="Completionist", value=f"{attrs['completionist']}")
            banner.set_image(url=f"{attrs['game_image_url']}")
        else:
            banner.add_field(name=f"Result {index}", value=each)
    return banner


def search_hltb(title: str) -> Union[None, list[HowLongToBeatEntry], list[str]]:
    """
    :param title:
    :return:
    """
    best_element = None
    results_list = HowLongToBeat().search(title)  # type: Union[None, list[HowLongToBeatEntry]]
    if results_list is not None and len(results_list) > 1:
        # TODO do we need double loop? if so, use product()
        for _ in results_list:
            best_element = [f'{each.game_name} {each.similarity * 100:.2f}% -- {each.game_id}' for each in results_list]
        # Saving in case I decide to do 'pick best automatically'
        # best_element = max(results_list, key=lambda element: element.similarity)
    else:
        best_element = results_list
    return best_element


def search_hltb_by_id(id: int) -> Union[None, list[HowLongToBeatEntry]]:
    """
    :param id:
    :return:
    """
    return [HowLongToBeat().search_from_id(id)]


# LEGACY CODE
# Saved for testing purposes. For production, should use embed version
# @debug
# def rendered_raw(message: list) -> str:
#     """
#     Convert raw results to something Discord safe.
#     :param message:
#     :return:
#     """
#     # similar = message[1]
#     # message = message[0]
#     result = []
#     for each in message:
#         print(each)
#         if type(each) is HowLongToBeatEntry:
#             attrs = vars(each)
#             result.append(f"**{attrs['game_name']}**")
#             result.append(f"Game Image: {attrs['game_image_url']}")
#             result.append(f"Web Link: {attrs['game_web_link']}")
#             result.append(f"Review Score: {attrs['review_score']}")
#             result.append(f"Developer: {attrs['profile_dev']}")
#             result.append(f"Platforms: {attrs['profile_platforms']}")
#             result.append(f"Release Date: {attrs['release_world']}")
#             result.append(f"Similarity to your search: {attrs['similarity'] * 100:.2f}%")
#             result.append(f"{DIVIDER.strip()}")
#             result.append(f"Main Story: {attrs['main_story']}")
#             result.append(f"Main Extra: {attrs['main_extra']}")
#             result.append(f"Completionist: {attrs['completionist']}")
#         else:
#             result.append(each)
#     # else:
#     #     result = message
#     return '\r'.join(result)