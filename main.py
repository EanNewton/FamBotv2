#!/bin/env/python3
from cogs.quotes import UserQuotes
from cogs.stats import UserStats
from cogs.word import WebInterface
from cogs.gifs import UserGifs
from cogs.games import MagicEightball
from cogs.hltb import HLTB
from cogs.plex import PlexInstance
from config.constants import POC_TOKEN, BOT


BOT.i18n.load("locale/")
BOT.add_cog(UserQuotes(BOT))
BOT.add_cog(UserStats(BOT))
BOT.add_cog(WebInterface(BOT))
BOT.add_cog(UserGifs(BOT))
BOT.add_cog(MagicEightball(BOT))
BOT.add_cog(HLTB(BOT))
BOT.add_cog(PlexInstance(BOT))
BOT.run(POC_TOKEN)
