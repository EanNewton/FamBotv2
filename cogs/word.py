from urllib.parse import quote_plus
from typing import Union
import aiohttp
import aiofiles

from bs4 import BeautifulSoup
import disnake
from disnake.ext import commands
from wiktionaryparser import WiktionaryParser

from config.constants import VERBOSE, WOLFRAM, URL_WOLF_IMG, URL_WOLF_TXT, \
    URL_WOTD, DEFAULT_DIR, URL_KEYWORDS, RUNNING_ON
from utilities.wrappers import debug


parser = WiktionaryParser()


class WebInterface(commands.Cog, name="Web Queries"):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="Reverse image search.")
    async def reverse_image_search(self, inter, image_url: str):
        await inter.response.send_message(yandex(image_url))

    @commands.slash_command(description="Search on wolfram alpha")
    async def wolfram(self, inter, query: str, return_image: bool):
        await inter.response.defer()
        if return_image:
            result = await wolfram_image(query)
            if type(result) is str:
                await inter.edit_original_message(result)
            elif type(result) is disnake.File:
                await inter.edit_original_message(file=result)
        else:
            result = await wolfram_txt(query)
            await inter.edit_original_message(embed=result)

    @commands.slash_command(description="Get the word of the day with Anu Garg.")
    async def wotd(self, inter):
        result = await get_todays_word()
        await inter.response.send_message(embed=result)

    @commands.slash_command(description="Query Wiktionary.com for a word.")
    async def wiktionary(self, inter, query: str):
        result = wiktionary(query)
        await inter.response.send_message(embed=result)


def yandex(image_url: str) -> str:
    """
    Search Yandex reverse image search
    :param image_url:
    :return:
    """
    yandex = f'<https://yandex.com/images/search?url={quote_plus(image_url)}&rpt=imageview>'
    tineye = 'https://tineye.com'
    return f'{yandex}\n{tineye}'


def wiktionary(word: str) -> disnake.Embed:
    """
    Get the www.wiktionary.org entry for a word or phrase
    :param message: <Discord.message object>
    :return: <str> Banner or None
    """

    try:
        result = parser.fetch(word.strip())[0]
        etymology = result['etymology']
        definitions = result['definitions'][0]
        pronunciations = result['pronunciations']
        banner = disnake.Embed(title="Wiktionary", description=word)
        if definitions['partOfSpeech']:
            banner.add_field(name="Parts of Speech", value=definitions['partOfSpeech'], inline=False)
        if etymology:
            banner.add_field(name="Etymology", value=etymology, inline=False)
        if definitions['text']:
            defs = ''
            for each in definitions['text']:
                defs += '{} \n'.format(each)
            banner.add_field(name="Definitions", value=defs, inline=False)
        if definitions['relatedWords']:
            defs = ''
            for each in definitions['relatedWords']:
                for sub in each['words']:
                    defs += '{}, '.format(sub)
                defs += '\n'
            banner.add_field(name="Related Words", value=defs, inline=False)
        if definitions['examples']:
            defs = ''
            for each in definitions['examples']:
                defs += '{} \n'.format(each)
            banner.add_field(name="Examples", value=defs, inline=False)
        if pronunciations['text']:
            defs_text = ''
            for each in pronunciations['text']:
                defs_text += '{} \n'.format(each)
            banner.add_field(name="Pronunciation, IPA", value=defs_text, inline=False)
            return banner
    except Exception as e:
        if VERBOSE >= 0:
            print('[!] Exception in wiki: {}'.format(e))


async def wolfram_txt(query: str) -> Union[list, str, disnake.Embed]:
    """
    Return an image based response from the Wolfram Alpha API
    :param query:
    :return: <str> Banner or None
    """
    banner = disnake.Embed(title="Wolfram Alpha")
    try:
        query = URL_WOLF_TXT.format(WOLFRAM, query)
        async with aiohttp.ClientSession() as session:
            async with session.get(query) as resp:
                if resp.status == 200:
                    text = await resp.read()
                elif resp.status == 501:
                    return 'Wolfram cannot interpret your request.'
                else:
                    return [f'[!] Wolfram Server Status {resp.status}', None]
        text = text.decode('UTF-8')
        banner.add_field(name='Wolfram Alpha Search', value=text)
        return banner
    except Exception as e:
        if VERBOSE >= 0:
            print(f'[!] Wolfram failed to process command on: {query}')
            print(f'[!] {e}')


async def wolfram_image(query: str) -> Union[disnake.File, str]:
    """
    Query Wolfram Alpha for an image based response.
    :param query:
    :return:
    """
    try:
        query = URL_WOLF_IMG.format(WOLFRAM, query)
        if RUNNING_ON == 'Linux':
            file_path = f'{DEFAULT_DIR}/../log/wolf/image.gif'
        elif RUNNING_ON == 'Windows':
            file_path = f'{DEFAULT_DIR}\\..\\log\\wolf\\image.gif'
        async with aiohttp.ClientSession() as session:
            async with session.get(query) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(file_path, mode='wb')
                    await f.write(await resp.read())
                    await f.close()
                    result = disnake.File(file_path)
                    return result
                elif resp.status == 501:
                    return 'Wolfram cannot interpret your request.'
                else:
                    return f'[!] Wolfram Server Status {resp.status}'
    except Exception as e:
        if VERBOSE >= 0:
            print(f'[!] Wolfram failed to process command on: {query}')
            print(f'[!] {e}')


async def get_todays_word() -> disnake.Embed:
    """
    Pull the word of the day from www.wordsmith.org
    :return: <str> Banner
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(URL_WOTD) as resp:
            if resp.status == 200:
                text = await resp.read()
            else:
                if VERBOSE >= 2:
                    print(f"[!] Status {resp.status}")
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()
    text = text.split('with Anu Garg')
    text = text[1].split('A THOUGHT FOR TODAY')
    text = text[0].strip()
    text = text.split('\n')
    fields = {'header': '', }
    for index, line in enumerate(text):
        if line:
            if line in URL_KEYWORDS.keys():
                fields[line] = ''
                key = line
            elif index == 0:
                # f-strings cannot self-reference, '.format()' can
                fields['header'] = '{}\n{}'.format(fields['header'], line)
            else:
                # f-strings cannot self-reference, '.format()' can
                fields[key] = '{}\n{}'.format(fields[key], line)
    banner = disnake.Embed(
        title="Word of the Day",
        description=fields['header']
    )
    fields.pop('header')
    for key, val in fields.items():
        banner.add_field(name=key, value=val)
    banner.set_footer(text=URL_WOTD)
    return banner
