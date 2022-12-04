from os import listdir
from os.path import isdir, exists, abspath
from pathlib import Path
from random import choice

from aiohttp import ClientSession
from aiofiles import open as aioopen
import disnake
from disnake.ext import commands

from config.constants import DEFAULT_DIR, RUNNING_ON, VERBOSE
from utilities.wrappers import debug


class UserGifs(commands.Cog, name="User GIFs"):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="Get a random GIF")
    async def gif(self, inter, nsfw: bool = False):
        await inter.response.defer()
        file = disnake.File(get_react(inter.guild_id, nsfw))
        print(file.fp)
        if file:
            await inter.edit_original_message(file=file)

    @commands.slash_command(description="upload")
    async def upload(self, inter, attachment: disnake.Attachment, nsfw: bool = False):
        if attachment.size / (1024.0 * 1024.0) >= 8.0:
            await inter.response.send_message("File too large. Discord limits this to 8 MB or smaller.")
        else:
            result = await fetch_react(attachment.url, inter.guild_id, nsfw)
            await inter.response.send_message(result)


def get_react(guild_id: int, nsfw: bool) -> str:
    """
    Get a random gif file from ./gifs or the servers folder
    :param nsfw:
    :param guild_id:
    :return: <String> Describing file location
    """
    if exists('./gifs') and RUNNING_ON == 'Linux':
        # Generate a list of possible gif files to choose from
        reacts = [abspath("gifs/" + file) for file in listdir('./gifs')]
        # Include guild_id-specific results
        if isdir(f'{DEFAULT_DIR}/../gifs/{guild_id}'):
            reacts.extend(
                [abspath(f'{DEFAULT_DIR}/../gifs/{guild_id}/{each}') for each in listdir(f'{DEFAULT_DIR}/../gifs/{guild_id}')]
            )
        # Include guild_id-specific nsfw results
        if nsfw and isdir(f'{DEFAULT_DIR}/../gifs/{guild_id}/nsfw'):
            reacts.extend(
                [abspath(f'{DEFAULT_DIR}/../gifs/{guild_id}/nsfw/{each}') for each in listdir(f'{DEFAULT_DIR}/../gifs/{guild_id}/nsfw')]
            )
        return choice(reacts)

    elif RUNNING_ON == 'Windows':
        # Generate a list of possible gif files to choose from
        reacts = [abspath(f"{DEFAULT_DIR}\\..\\gifs\\{file}") for file in listdir(f"{DEFAULT_DIR}\\..\\gifs\\")]
        # Include guild_id-specific results
        if isdir(f'{DEFAULT_DIR}\\..\\gifs\\{guild_id}'):
            reacts.extend(
                [abspath(f"{DEFAULT_DIR}\\..\\gifs\\{guild_id}\\{each}") for each in
                 listdir(f"{DEFAULT_DIR}\\..\\gifs\\{guild_id}")]
            )
        # Include guild_id-specific nsfw results
        if nsfw and isdir(f'{DEFAULT_DIR}\\..\\gifs\\{guild_id}\\nsfw'):
            reacts.extend(
                [abspath(f'{DEFAULT_DIR}\\..\\gifs\\{guild_id}\\nsfw\\{each}') for each in
                 listdir(f"{DEFAULT_DIR}\\..\\gifs\\{guild_id}\\nsfw")]
            )
        return choice(reacts)


@debug
async def fetch_react(url: str, guild_id: int, nsfw: bool) -> str:
    """
    Save a gif a user added with !gif add
    :param url:
    :param guild_id:
    :param nsfw:
    :return: <String> Notify of gif being added or not
    """
    file_name = str(url.split('/')[-1])
    extension = str(url.split('.')[-1].lower())
    file_path = None
    if extension != 'gif':
        return 'File must be a gif'

    if RUNNING_ON == 'Linux':
        if nsfw:
            Path(f'{DEFAULT_DIR}/../gifs/{guild_id}/nsfw').mkdir(parents=True, exist_ok=True)
            file_path = f'{DEFAULT_DIR}/../gifs/{guild_id}/nsfw/{file_name}'
        else:
            Path(f'{DEFAULT_DIR}/../gifs/{guild_id}').mkdir(parents=True, exist_ok=True)
            file_path = f'{DEFAULT_DIR}/../gifs/{guild_id}/{file_name}'
    elif RUNNING_ON == 'Windows':
        if nsfw:
            Path(f'{DEFAULT_DIR}\\..\\gifs\\{guild_id}\\nsfw').mkdir(parents=True, exist_ok=True)
            file_path = f'{DEFAULT_DIR}\\..\\gifs\\{guild_id}\\nsfw\\{file_name}'
        else:
            Path(f'{DEFAULT_DIR}\\..\\gifs\\{guild_id}').mkdir(parents=True, exist_ok=True)
            file_path = f'{DEFAULT_DIR}\\..\\gifs\\{guild_id}\\{file_name}'

    if file_path:
        async with ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    f = await aioopen(file_path, mode='wb')
                    await f.write(await resp.read())
                    await f.close()
                    if VERBOSE >= 2:
                        print(f"[+] Saved: {file_path}")
                    return 'Added a new gif to /gif'
            