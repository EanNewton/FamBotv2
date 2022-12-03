

from dotenv import load_dotenv
from os import path, getenv
from platform import system
if system() == 'Linux':
    RUNNING_ON = 'Linux'
elif system() == 'Windows':
    RUNNING_ON = 'Windows'
else:
    RUNNING_ON = 'Unknown'

import disnake
from disnake.ext import commands
from sqlalchemy import create_engine
from nltk import download as nltk_download
from nltk.data import find as nltk_find
try:
    nltk_find('stopwords')
except LookupError:
    nltk_download('stopwords')
finally:
    from nltk.corpus import stopwords


##################
# File Locations #
##################
DEFAULT_DIR = path.dirname(path.abspath(__file__))
if RUNNING_ON == 'Linux':
    PATH_DB = path.join(path.dirname(__file__), '../log/quotes.db')
elif RUNNING_ON == 'Windows':
    PATH_DB = path.join(path.abspath(__file__), '..\..\log\quotes.db')
# PATH_WOTD = path.join(path.dirname(__file__), './docs/wordoftheday.txt')
ENGINE = create_engine('sqlite:///./log/quotes.db', echo=False)


##################
# Bot & API Info #
##################
load_dotenv()
TOKEN = getenv('DISCORD_TOKEN')
POC_TOKEN = getenv('POC_TOKEN')
GUILD = getenv('DISCORD_GUILD')
WOLFRAM = getenv('WOLFRAM_TOKEN')
VERSION = '11.28.2022'
VERBOSE = 3

command_sync_flags = commands.CommandSyncFlags.default()
command_sync_flags.sync_commands_debug = True
intents = disnake.Intents.default()
intents.typing = False
intents.message_content = True
intents.messages = True
intents.presences = False

BOT = commands.Bot(
    command_prefix=commands.when_mentioned,
    test_guilds=[579812270167687178], # Optional
    command_sync_flags=command_sync_flags,
    intents=intents,
)



#################################
# Internal Function Static Data #
#################################
# combine all 2 letter codes and fully qualified names into flat list from a dict()
# LANGCODES = [each for tuple_ in LANGCODES.items() for each in tuple_]
DIVIDER = '<<>><<>><<>><<>><<>><<>><<>><<>><<>>\n'
URL_WOTD = 'https://www.wordsmith.org/words/today.html'
URL_WOLF_IMG = 'http://api.wolframalpha.com/v1/simple?appid={}&i={}'
URL_WOLF_TXT = 'http://api.wolframalpha.com/v1/result?appid={}&i={}'

JSON_FORMATTER_SET = [[
    ['0=', 'Monday = '],
    ['1=', 'Tuesday = '],
    ['2=', 'Wednesday = '],
    ['3=', 'Thursday = '],
    ['4=', 'Friday = '],
    ['5=', 'Saturday = '],
    ['6=', 'Sunday = '],
    [',', ', '],
    [';', '; '],
], [
    ['id', 'Server ID'],
    ['guild_name', 'Server Name'],
    ['locale', 'Server Locale'],
    ['schedule', 'Schedule'],
    ['url', 'URL Footer'],
    ['quote_format', 'Quote Format'],
    ['qAdd_format', 'Quote Added Format'],
    ['lore_format', 'Lore Format'],
    ['filtered', 'Blacklisted Words'],
    ['mod_roles', 'Moderator Roles'],
    ['anonymous', 'Anonymous Mode'],
    # ['timer_channel', 'Timer Channel ID'],
]]

EXT_SET = {
    'image': [
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'
    ],
    'audio': [
        '3gp', 'aa', 'aac', 'aax', 'act', 'aiff', 'alac', 'amr',
        'ape', 'au', 'awb', 'dct', 'dss', 'dvf', 'flac', 'gsm',
        'iklax', 'ivs', 'm4a', 'm4b', 'm4p', 'mmf', 'mp3', 'mpc',
        'msv', 'nmf', 'nsf', 'ogg', 'oga', 'mogg', 'opus', 'ra',
        'rm', 'raw', 'rf64', 'sln', 'tta', 'voc', 'vox', 'wav',
        'wma', 'wv', 'webm', '8svx', 'cda'
    ],
    'video': [
        'webm', 'mkv', 'flv', 'vob', 'ogv', 'ogg', 'drc',
        'gifv', 'mng', 'avi', 'mts', 'm2ts', 'ts', 'mov', 'qt',
        'wmv', 'yuv', 'rm', 'rmvb', 'asf', 'amv', 'mp4', 'm4p',
        'm4v', 'mpg', 'mp2', 'mpeg', 'mpe', 'mpv', 'm4v', 'svi',
        '3gp', '3g2', 'mxf', 'roq', 'nsv', 'f4v', 'f4p', 'f4a', 'f4b'
    ],
    'document': [
        '0', '1st', '600', '602', 'abw', 'acl', 'afp', 'ami',
        'ans', 'ascaww', 'ccf', 'csv', 'cwk', 'dbk', 'dita', 'doc',
        'docm', 'docx', 'dotdotx', 'dwd', 'egt', 'epub', 'ezw',
        'fdx', 'ftm', 'ftx', 'gdoc', 'html', 'hwp', 'hwpml', 'log',
        'lwp', 'mbp', 'md', 'me', 'mcw', 'mobinb', 'nbp', 'neis',
        'odm', 'odoc', 'odt', 'osheet', 'ott', 'ommpages', 'pap',
        'pdax', 'pdf', 'quox', 'rtf', 'rpt', 'sdw', 'sestw',
        'sxw', 'tex', 'info', 'troff', 'txt', 'uof', 'uoml', 'viawpd',
        'wps', 'wpt', 'wrd', 'wrf', 'wri', 'xhtml', 'xht', 'xml', 'xps'
    ]
}

STOPWORDS = set(stopwords.words("english")).union([
    "wa",
    "thi",
    "https",
    "tenor",
    "com",
    "lol'",
    "lol '",
    "gif",
    "gif'",
    "gif '",
    "it'",
    "it '",
    "quote'",
    "quote '",
    "youtu",
    "cdn",
    "discordapp",
    "youtu be",
    "twitch",
    "twitter",
    " https",
    "https ",
    "https:",
    "https:/",
    "https://",
    "twitch tv",
    "twitch.tv",
    "com attachments",
    "com/attachments",
    ".com/attachments",
    ".com/attachments/",
    "channel cannot",
    "channel cannot used music",
    "cannot used music command",
    "cannot used",
    "used music",
    "music command",
    "channel cannot used",
    "cannot used music",
    "used music command",
    "channel cannot used music command",
    "quote",
    "gif",
    "www",
    "http",
    "https",
    "com",
    "youtube",
    "'",
    "\"",
    "`",
    "im",
    "I",
    "like",
    "watch",
    "get",
    "got",
    "override",
    "schedule",
    "sched",
    "cc",
    "discordapp",
    "discord",
])

URL_KEYWORDS = {
    'USAGE:': '**USAGE:**',
    'MEANING:': '**MEANING:**',
    'PRONUNCIATION:': '**PRONUNCIATION:**',
    'ETYMOLOGY:': '**ETYMOLOGY:**',
    'NOTES:': '**NOTES:**'
}
