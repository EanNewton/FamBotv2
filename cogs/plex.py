# TODO narrow imports

import configparser
import random
import re
import threading
import time
from typing import Union, Any
from math import ceil

import disnake
from disnake.ext import commands
import plexapi.video
import plexapi.audio
import plexapi.library
import plexapi.collection
from plexapi.myplex import MyPlexAccount

from config.constants import DEFAULT_DIR, VERBOSE, RUNNING_ON
from utilities.database import is_admin
from utilities.wrappers import debug
from utilities.general import ms_to_datestr, datestr_to_ms, wrap

config, account, plex, client_name, voice_channel_id = \
    configparser.ConfigParser, str, plexapi.myplex.PlexClient, str, int
regex_is_year = r"\d{4}"  # type: re # Confirm we received a valid 4-length digit for --year search
queue = []  # type: list[plexapi.video.Movie]
last = []  # type: list[Union[plexapi.video.Movie, plexapi.audio.Audio, str]]
music_queue = []  # type: list[plexapi.audio.Track]
# 'skip_votes' is a list of Discord Member ID's to ensure uniqueness
skip_votes = []  # type: list[disnake.Member.id]


class PlexInstance(commands.Cog, name="Plex Movie Night DJ"):
    def __init__(self, bot):
        self.bot = bot
        setup()

    ############
    # SEARCH   #
    ############
    # Why are you using camelCase and not following PEP8 guidelines?
    #
    # This API reads XML documents provided by MyPlex and the Plex Server.
    # We decided to conform to their style so that the API variable names directly match with
    # the provided XML documents.
    # noinspection PyPep8Naming
    @commands.slash_command(description="Search a Plex LIBRARY.")
    async def plex_search(
            self,
            inter,
            library: str = 'Movies',
            limit: int = 10,
            title: str = None,
            year: int = None,
            decade: int = None,
            actor: str = None,
            director: str = None,
            genre: str = None,
            audio_language: str = None,
            subtitle_language: str = None,
            content_rating: str = None,
            unwatched: bool = None
    ):
        advancedFilters = {
            'and': [
                {'year': year},
                {'title': title},
                {'decade': decade},
                {'actor': actor},
                {'director': director},
                {'genre': genre},
                {'audioLanguage': audio_language},
                {'subtitleLanguage': subtitle_language},
                {'contentRating': content_rating},
                {'unwatched': unwatched}
            ]
        }
        result = search_library(advancedFilters, library, limit)
        result = rendered_raw(result)
        await inter.response.send_message(result)

    @commands.slash_command(description="Show a list of available Libraries.")
    async def plex_libraries(self, inter):
        result = get_library_list()
        result = rendered_raw(result)
        await inter.response.send_message(result)

    @commands.slash_command(description="Get LIMIT [default: 10] number of random titles from LIBRARY.")
    async def plex_random(self, inter, library: str = 'Movies', limit: int = 10):
        result = get_random(library, limit)
        result = rendered_raw(result)
        await inter.response.send_message(result)

    @commands.slash_command(description="Get a list of collections available in the LIBRARY.")
    async def plex_collections(self, inter, library: str = 'Movies', limit: int = 10):
        result = get_collections_list(library, limit)
        result = rendered_raw(result)
        await inter.response.send_message(result)

    @commands.slash_command(description="Get list of media that has been partially played in the LIBRARY.")
    async def plex_inprogress(self, inter, library: str = 'Movies', limit: int = 10):
        result = get_in_progress(library, limit)
        result = rendered_raw(result)
        await inter.response.send_message(result)

    @commands.slash_command(description="Get list of LIMIT [Default: 10] most recently added media in the LIBRARY.")
    async def plex_recent(self, inter, library: str = 'Movies', limit: int = 10):
        result = get_in_progress(library, limit)
        result = rendered_raw(result)
        await inter.response.send_message(result)

    ############
    # PLAYBACK #
    ############


############
# GENERAL  #
############
def setup() -> None:
    """
    Establish global variables, then connect to the Plex instance.
    :return:
    """
    global config, account, plex, client_name, voice_channel_id
    # Read in config
    config = configparser.ConfigParser()
    if VERBOSE >= 2:
        print('[-] Reading Plex config')
    if RUNNING_ON == 'Windows':
        config.read(f"{DEFAULT_DIR}\\..\\config.ini")
    elif RUNNING_ON == 'Linux':
        config.read(f"{DEFAULT_DIR}/../config.ini")

    # Connect to Plex
    try:
        account = MyPlexAccount(config['plex']['Username'], config['plex']['Password'])
        if VERBOSE >= 2:
            print('[-] Connecting to Plex')
        plex = account.resource(config['plex']['Server']).connect()
        voice_channel_id = int(config['discord']['VC_ID'])  # type: int
        client_name = config['plex']['Name']  # type: str
    except Exception as e:
        print(f'[!] Oops! Something went wrong:\n'
              f'{e}\n'
              f'[!] Is the Plex instance online?')
    if VERBOSE >= 0:
        print('[+] End Plex Setup')


def rendered_raw(result: list, limit: int = 10) -> str:
    """
    Convert raw results to something Discord safe
    :param limit:
    :param result:
    :return:
    """
    # result = result[0]   # Search results
    banner = []
    for each in result:
        # print(type(each))
        if type(each) == plexapi.video.Movie:
            duration = int(each.duration / 1000)
            m, s = divmod(duration, 60)
            h, m = divmod(m, 60)
            banner.append(f'`{each.title} - ({each.year}) -- {h:02d}:{m:02d}:{s:02d}`')
        elif type(each) == plexapi.audio.Album:
            banner.append(f'`{each.parentTitle} - {each.title} ({each.year})`')
            for index, track in enumerate(each.tracks()):
                banner.append(f'`  {str(index + 1).zfill(2)}. - {track.title} ({ms_to_datestr(track.duration)})`')
        elif type(each) == plexapi.audio.Artist:
            for album in each.albums():
                banner.append(f'`{album.parentTitle} - {album.title} ({album.year})`')
        elif type(each) == plexapi.collection.Collection:
            # https://python-plexapi.readthedocs.io/en/latest/modules/collection.html
            banner.append(f"`{each.title}: {each.childCount} items from ({each.minYear} - {each.maxYear})`")
        else:
            banner.append(f'{each}')
    banner = [*set(random.choices(banner, k=limit))]
    banner = '\r'.join(banner)
    if len(banner) > 1999:
        banner = wrap(banner, 1999)
    return banner


############
# SEARCH   #
############
# Why are you using camelCase and not following PEP8 guidelines?
#
# This API reads XML documents provided by MyPlex and the Plex Server.
# We decided to conform to their style so that the API variable names directly match with
# the provided XML documents.
# noinspection PyPep8Naming
def search_library(advancedFilters: dict, library: str, limit: int) -> list:
    """
    The main search function of the Plex instance
    :param limit:
    :param library:
    :param advancedFilters:
    :return:
    """
    # noinspection PyUnresolvedReferences
    selection = plex.library.section(library)  # type: plexapi.library.Library
    try:
        # TODO implement 'or' and 'not'
        filtered = {}
        for each in advancedFilters["and"]:
            # drop 'None' values
            # noinspection PyUnresolvedReferences
            for key, value in each.items():
                if value:
                    filtered[key] = value
        advancedFilters["and"] = [filtered]
        selection = selection.search(filters=advancedFilters)
    except Exception as e:
        print(f'[!] Oops! Something went wrong during Advanced Filter selection.\n'
              f'[!] Trying to fall back to default title search.\n'
              f'[!] {e}')
        try:
            selection = selection.search(advancedFilters["and"]["title"])
        except Exception as e:
            print(f'[!] Oops! Something went wrong. Please check your search and try again.\n{e}')
    return list(set(random.choices(selection, k=limit)))  # type: list[Any]


def get_library_list() -> str:
    """
    Get list of libraries available on the Plex instance
    :return:
    """
    return '\r'.join([section.title for section in plex.library.sections()])


def get_random(library: str, limit: int) -> list:
    """
    Get LIMIT [default: 10] number of random titles from LIBRARY
    :param limit:
    :param library:
    :return:
    """
    selection = plex.library.section(library)
    selection = selection.search()
    return [*set(random.choices(selection, k=limit))]


def get_collections_list(library: str, limit: int) -> list:
    """
    Get a list of collections available in the LIBRARY.
    :param limit:
    :param library:
    :return:
    """
    selection = plex.library.section(library)
    selection = selection.collections()
    return [*set(random.choices(selection, k=limit))]


# TODO convert to parameter -ip --inprogress
def get_in_progress(library: str, limit: int) -> list:
    """
    Get list of media that has been partially played in the LIBRARY.
    :param limit:
    :param library:
    :return:
    """
    selection = plex.library.section(library)
    selection = selection.search(filters={"inProgress": True})
    if not len(selection):
        return ['No media in progress.']
    return [*set(random.choices(selection, k=limit))]


def get_recently_added(library: str, limit: int) -> list:
    """
    Get list of LIMIT [Default: 10] most recently added media in the LIBRARY.
    :param limit:
    :param library:
    :return:
    """
    selection = plex.library.section(library)
    selection = selection.recentlyAdded()
    return [*set(random.choices(selection, k=limit))]


############
# PLAYBACK #
############
def play(args) -> str:
    if 'music' in args:
        return play_music()
    elif 'movie' in args:
        return play_media()
    else:
        return "Please specify either `play music` or `play movie`. "


def play_media() -> str:
    """
    Start the first item in queue.
    :return:
    """
    try:
        player = plex.client(client_name)
    except Exception as e:
        return f"Oops something went wrong! {e}\nIs the Plex instance online?"
    if len(queue) > 0:
        movie = plex.library.section('Movies').get(queue[0].title)
        player.playMedia(media=movie)
        return f'Now playing: {movie.title}'
    else:
        return "No media in queue."


def play_music() -> str:
    """
    Start the first item in queue.
    :return:
    """
    try:
        player = plex.client(client_name)
    except Exception as e:
        return f"Oops something went wrong! {e}\nIs the Plex instance online?"
    if len(music_queue) > 0:
        try:
            player.playMedia(media=music_queue[0])
            threading.Timer(float(music_queue[0].duration / 1000), play_next_song).start()
        except Exception as e:
            print(f'[!] {e}')
        return f'Now playing: {music_queue[0].title}'
    else:
        return "No media in queue."


# TODO add stopper to pause_media()
def play_next_song() -> None:
    """

    :return:
    """
    music_queue.pop(0)
    if len(music_queue) > 0:
        player = plex.client(client_name)
        player.playMedia(media=music_queue[0])
        threading.Timer(float(music_queue[0].duration / 1000), play_next_song).start()


def pause_media() -> str:
    """
    Pause anything currently playing.
    :return:
    """
    try:
        player = plex.client(client_name)
        player.pause()
        return "Paused. Use `$plex resume hh:mm:ss` to start again."
    except Exception as e:
        return f"Oops something went wrong! {e}"


def resume_media(args: list) -> str:
    """
    Skip to given hh:mm:ss of current media.
    :param args:
    :return:
    """
    ms = datestr_to_ms(args[2]) * 1000
    try:
        if {'movie', 'movies'}.intersection(args):
            result = play_media()
        else:
            result = play_music()
        # We need to sleep() because if we call player.seekTo() too soon it will be ignored if movie is still loading.
        # A value between 2-4 seconds seems to work best.
        time.sleep(3)
        plex.client(client_name).seekTo(ms)
        return f'{result} at {args[2]}'
    except Exception as e:
        return f"Oops something went wrong! {e}"


def show_queue() -> str:
    """
    Show what is currently contained in 'queue'
    :return:
    """
    return '\r'.join([f'{_.title} - ({_.year})' for _ in queue])


def shuffle_queue() -> str:
    """
    Randomize the order of the play queue.
    :return:
    """
    result = None
    # Must be done on two lines as f-strings cannot contain backslash fragments.
    if len(queue):
        random.shuffle(queue)
        result = '\r'.join([f'{_.title} - ({_.year})' for _ in queue])
    if len(music_queue):
        random.shuffle(music_queue)
        result = 'music.'
    if result:
        return f"Play queue has been shuffled:\n{result}"
    else:
        return 'Nothing in queue to shuffle.'


def clear_queue(args: list) -> str:
    """
    Remove everything in queue.
    :return:
    """
    if {'q', 'queue'}.intersection(args):
        if len(queue) or len(music_queue):
            skip_votes.clear()
            queue.clear()
            music_queue.clear()
            return "Cleared queue."
        else:
            return "There is already nothing in queue."
    elif {'vote', 'votes', 'skip'}.intersection(args):
        skip_votes.clear()
        return "Cleared all votes to skip."
    else:
        return "Please specify either `votes` or `queue`."


async def next_queue(message: disnake.Message) -> str:
    """
    Remove first item in queue and start the second item.
    Based on a simple majority vote of users in the config['discord']['VC_ID'] channel.
    Users with admin / mod roles can always skip.
    :param message: <Discord.message object>
    :return:
    """
    if len(queue):
        voice_channel = BOT.get_channel(voice_channel_id)  # type: discord.VoiceChannel
        if await is_admin(message.author, message) or len(skip_votes) > ceil(len(voice_channel.members) / 2):
            queue.pop(0)
            skip_votes.clear()
            return play_media()
        else:
            if message.author.id not in skip_votes:
                skip_votes.append(message.author.id)
                return f"Added vote to skip. {len(skip_votes)}/{ceil(len(voice_channel.members) / 2)}"
            else:
                return f"You have already voted {message.author.name}.\n" \
                       f"All votes can be cleared with `$plex clear votes`."
    else:
        return "There is already nothing in queue."


def add_to_queue() -> str:
    """
    Add the results of the most recent search to the play queue.
    :return:
    """
    if not last:
        return "Nothing to add. Use `$plex search` first."
    else:
        banner = ["Added the following to play queue: "]
        for each in last:
            if type(each) == plexapi.audio.Album:
                for track in each.tracks():
                    music_queue.append(track)
            elif type(each) == plexapi.audio.Artist:
                for album in each.albums():
                    for track in album.tracks():
                        music_queue.append(track)
            elif type(each) == plexapi.audio.Track:
                # noinspection PyTypeChecker
                music_queue.append(each)
            elif type(each) == plexapi.video.Movie:
                queue.append(each)
            banner.append(each.title)
        return '\r'.join(banner)
