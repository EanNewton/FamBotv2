import json

import disnake
from sqlalchemy import select, MetaData, Table, Column, Integer, String

from config.constants import JSON_FORMATTER_SET, ENGINE, DEFAULT_DIR, VERBOSE
from config.constants import BOT, RUNNING_ON
from utilities.general import fetch_file
from utilities.wrappers import debug

mod_roles = dict()


def setup() -> None:
    global meta, Config, Stats
    meta = MetaData()
    Config = Table(
        'config', meta,
        Column('id', Integer, primary_key=True),
        Column('guild_name', String),
        Column('locale', String),
        Column('schedule', String),
        Column('quote_format', String),
        Column('lore_format', String),
        Column('url', String),
        Column('qAdd_format', String),
        Column('filtered', String),
        Column('mod_roles', String),
        Column('anonymous', Integer),
    )
    Stats = Table(
        'usageCounts', meta,
        Column('id', Integer, primary_key=True),
        Column('guild_name', String),
        Column('raw_messages', Integer),
        Column('quote', Integer),
        Column('lore', Integer),
        Column('wolf', Integer),
        Column('wotd', Integer),
        Column('dict', Integer),
        Column('trans', Integer),
        Column('google', Integer),
        Column('config', Integer),
        Column('sched', Integer),
        Column('filter', Integer),
        Column('doip', Integer),
        Column('gif', Integer),
        Column('stats', Integer),
        Column('eight', Integer),
        Column('help', Integer),
        Column('custom', Integer),
    )
    meta.create_all(ENGINE)
    update_mod_roles()
    if VERBOSE >= 0:
        print('[+] End util.database Setup')


def config_load(guild: int) -> None:
    """
    Load the JSON file supplied by user into the database
    :param guild: <Int> Discord guild ID
    :return: <None>
    """
    # Undo the pretty printing
    if RUNNING_ON == 'Linux':
        with open(f'{DEFAULT_DIR}/../docs/config/{guild}.json', 'r') as f:
            dict_ = json.loads(f.read().split('```', maxsplit=1)[0])
    elif RUNNING_ON == 'Windows':
        with open(f'{DEFAULT_DIR}\\..\\docs\\config\\{guild}.json', 'r') as f:
            dict_ = json.loads(f.read().split('```', maxsplit=1)[0])
    for each in JSON_FORMATTER_SET[1]:
        dict_[each[0]] = dict_.pop(each[1])
    for each in JSON_FORMATTER_SET[0]:
        dict_['schedule'] = dict_['schedule'].replace(each[1], each[0])
    with ENGINE.connect() as conn:
        ins = Config.update().where(Config.c.id == guild).values(
            locale=dict_['locale'],
            schedule=dict_['schedule'],
            quote_format=dict_['quote_format'],
            lore_format=dict_['lore_format'],
            url=dict_['url'],
            qAdd_format=dict_['qAdd_format'],
            filtered=dict_['filtered'],
            mod_roles=dict_['mod_roles'],
            anonymous=dict_['anonymous'],
        )
        conn.execute(ins)
    # TODO ensure to lower
    mod_roles[guild] = fetch_value(guild, 9, ';')
    if VERBOSE >= 1:
        print(f'[+] Loaded new config for {BOT.fetch_guild(guild)}')


def fetch_value(guild: int, val: int, delim=None) -> list:
    """
    Get a specific cell from the guilds config table
    :param guild: <Int> Discord guild ID
    :param val: <String> Column name within Config Table
    :param delim: (Optional) <String> Delimeter for splitting values within the cell
    :return: <List> Values from within the specified cell
    """
    with ENGINE.connect() as conn:
        select_st = select([Config]).where(Config.c.id == guild)
        res = conn.execute(select_st)
        result = res.fetchone()
    if result and result[val]:
        if type(result[val]) is str:
            result = result[val].split(delim)
            result[:] = (val for val in result if val not in {'', ' ', '\n', None})
        else:
            result = result[val]
        return result


def update_mod_roles() -> None:
    """
    Sync in-memory mod roles with database values for all guilds
    :return: <None>
    """
    for guild in guild_list():
        roles = fetch_value(guild, 9, ';')
        if roles:
            mod_roles[guild] = [str(role).lower() for role in roles]
            if VERBOSE >= 1:
                print('[+] Updated mod roles')


async def is_admin(author: disnake.Member, guild: disnake.Guild) -> bool:
    """
    Check if a discord user has been given bot admin permissions
    :param message:
    :param author: <Discord.message.author object>
    :return: <bool>
    """
    if type(author) is disnake.Member and not author.bot:
        if author.id == 184474309891194880 or author.id == guild.owner_id:
            return True
        else:
            await author.send(content='Role based permissions are not currently supported by DiscordPy in private \
channels. Please try again in a different channel, or the guild owner can issue the command here.')
            return False
    else:
        if guild.owner_id == author.id or author.id == 184474309891194880:
            return True
        for role in author.roles:
            if str(role).lower() in mod_roles[guild.id]:
                return True
        return False


def guild_list() -> list:
    """
    Get a list of all guilds ids
    :return: <List> IDs for all guilds the bot is active in
    """
    with ENGINE.connect() as conn:
        select_st = select([Config])
        res = conn.execute(select_st)
        result = res.fetchall()
    return [each[0] for each in result]


def increment_usage(guild: disnake.Guild, command: str) -> int:
    """
    Keeps track of how many times various commands have been used.
    :param guild: 
    :param command: 
    :return: 
    """
    with ENGINE.connect() as conn:
        select_st = select([Stats]).where(Stats.c.id == guild.id)
        result = conn.execute(select_st).fetchone()
        if result:
            columns = []
            for each in Stats.c:
                columns.append(each.name)
            dict_ = dict(zip(columns, result))
            dict_[command] = int(dict_[command]) + 1
            ins = Stats.update().where(Stats.c.id == guild.id).values(
                raw_messages=dict_['raw_messages'],
                quote=dict_['quote'],
                lore=dict_['lore'],
                wolf=dict_['wolf'],
                wotd=dict_['wotd'],
                dict=dict_['dict'],
                trans=dict_['trans'],
                google=dict_['google'],
                config=dict_['config'],
                sched=dict_['sched'],
                filter=dict_['filter'],
                doip=dict_['doip'],
                gif=dict_['gif'],
                stats=dict_['stats'],
                eight=dict_['eight'],
                help=dict_['help'],
                custom=dict_['custom'],
            )
            conn.execute(ins)
        else:
            if VERBOSE >= 2:
                print(f'[-] Creating usage counter for {guild.name}')
            ins = Stats.insert().values(
                id=guild.id,
                guild_name=guild.name,
                raw_messages=0,
                quote=0,
                lore=0,
                wolf=0,
                wotd=0,
                dict=0,
                trans=0,
                google=0,
                config=0,
                sched=0,
                filter=0,
                doip=0,
                gif=0,
                stats=0,
                eight=0,
                help=0,
                custom=0,
            )
            conn.execute(ins)
            return increment_usage(guild, command)


async def config_helper(message: disnake.Message):
    """
    Create or reset the server config entry
    :param message:
    :return: <String> Describing file location
    """
    increment_usage(message.guild, 'config')
    if await is_admin(message.author, message):
        args = message.content.split()
        if len(args) > 1 and args[1] == 'reset':
            return config_reset(message.guild)
        else:
            return config_create(message.guild)


def config_create(guild: disnake.Guild) -> str:
    """
    Get the config file for the server and give to the user
    :param guild:
    :return: <String> Describing file location
    """
    with ENGINE.connect() as conn:
        select_st = select([Config]).where(Config.c.id == guild.id)
        result = conn.execute(select_st).fetchone()
        if result:
            if VERBOSE >= 2:
                print(f'[-] Found guild config for {guild.name}')
            # Create an in-memory version of the config
            columns = []
            for each in Config.c:
                columns.append(each.name)
            dict_ = dict(zip(columns, result))
            # For pretty printing, make the user's life easier
            for each in JSON_FORMATTER_SET[0]:
                dict_['schedule'] = dict_['schedule'].replace(each[0], each[1])
            for each in JSON_FORMATTER_SET[1]:
                dict_[each[1]] = dict_.pop(each[0])
            if RUNNING_ON == 'Linux':
                with open(f'{DEFAULT_DIR}/../docs/config/{guild.id}.json', 'w') as f:
                    json.dump(dict_, f, indent=4)
                    f.write(f"\n\n{fetch_file('help', 'config')}")
                return f'{DEFAULT_DIR}/../docs/config/{guild.id}.json'
            elif RUNNING_ON == 'Windows':
                with open(f'{DEFAULT_DIR}\\..\\docs\\config\\{guild.id}.json', 'w') as f:
                    json.dump(dict_, f, indent=4)
                    f.write(f"\n\n{fetch_file('help', 'config')}")
                return f'{DEFAULT_DIR}\\..\\docs\\config\\{guild.id}.json'
        else:
            # Guild has no config entry, create one and try again
            config_create_default(guild)
            return config_create(guild)


def config_create_default(guild: disnake.Guild) -> None:
    """
    Create a new default entry for the given guild.
    :param guild:
    :return:
    """
    if VERBOSE >= 1:
        print(f'[+] Creating new guild config for {guild.name}')
    with ENGINE.connect() as conn:
        ins = Config.insert().values(
            id=guild.id,
            guild_name=guild.name,
            locale='Asia/Tokyo',
            schedule='0=10,17:15;1=10,12;2=16,10:15;3=2:44;4=10;5=16:30;',
            quote_format='**{}**\n{}\n ---{} on {}',
            lore_format='**{}**\n{}\n---Scribed by the Lore Master {}, on the blessed day of {}',
            url='Come hang with us at: <https://www.twitch.tv/>',
            qAdd_format='Added:\n \"{0}\"\n by {1} on {2}',
            filtered='none',
            mod_roles='mod;admin;discord mod;',
            anonymous=1,
        )
        conn.execute(ins)


def config_reset(guild: disnake.Guild) -> str:
    """
    Return the config to default values
    :param guild:
    :return:
    """
    with ENGINE.connect() as conn:
        ins = Config.delete().where(Config.c.id == guild.id)
        conn.execute(ins)
    if VERBOSE >= 1:
        print(f'[+] Reset config for: {guild.name}')
    return config_create(guild)


setup()