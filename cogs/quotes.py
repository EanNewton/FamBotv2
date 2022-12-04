from typing import Union

import disnake
from disnake.ext import commands
import pendulum
import pandas as pd
from sqlalchemy import and_, func, select, MetaData, Table, Column, Integer, String

# from DisnakeBot.utilities.database import fetch_value, is_admin
# from ..utilities.wrappers import debug
from utilities.database import fetch_value, is_admin
from config.constants import ENGINE, VERBOSE, EXT_SET, DEFAULT_DIR, BOT, RUNNING_ON


def setup() -> None:
    global meta, Quotes, Lore, Config
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
    )
    Quotes = Table(
        'famQuotes', meta,
        Column('id', Integer, primary_key=True),
        Column('name', String),
        Column('text', String),
        Column('date', String),
        Column('guild', String),
        Column('guild_name', String),
        Column('embed', String),
    )
    Lore = Table(
        'famLore', meta,
        Column('id', Integer, primary_key=True),
        Column('name', String),
        Column('text', String),
        Column('date', String),
        Column('guild', String),
        Column('embed', String),
        Column('guild_name', String),
    )
    meta.create_all(ENGINE)
    if VERBOSE >= 0:
        print('[+] End Quotes Setup')


class UserQuotes(commands.Cog, name="User Quotes"):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="Get a user quote.")
    async def quote(self, inter, username: disnake.Member = None, quote_id = None):
        if quote_id:
            await inter.response.send_message(get_quote(inter.guild_id, Quotes, quote_id=quote_id, raw=True))
        elif username:
            await inter.response.send_message(get_quote(inter.guild_id, Quotes, username=username.name, raw=True))
        else:
            await inter.response.send_message(get_quote(inter.guild_id, Quotes, raw=True))

    @commands.slash_command(description="Get a piece of your Discord's lore.")
    async def lore(self, inter, username: disnake.Member = None):
        if username:
            await inter.response.send_message(get_quote(inter.guild_id, Lore, username=username.name, raw=True))
        else:
            await inter.response.send_message(get_quote(inter.guild_id, Lore, raw=True))

    @commands.slash_command(description="Delete a user quote or lore.")
    async def delete_quote(self, inter, quote_id):
        if is_admin(inter.author, inter.guild):
            await inter.response.send_message(delete_quote(inter.guild_id, quote_id))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: disnake.RawReactionActionEvent):
        channel = await BOT.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        if str(payload.emoji) == '🗨️' and not message.author.bot:
            if not check_if_exists(message.guild.id, message.id):
                banner = insert_quote(message, None, message.id)
                await channel.send(embed=banner)


def get_quote(guild_id: int, _table: Table, username=None, quote_id=None, raw=False) -> Union[disnake.Embed, str]:
    """
    Retrieve a quote from the database.
    :param quote_id:
    :param guild_id: <int> message.guild.id
    :param _table: (Optional) <SQLAlchemy.Table> Quotes or Lore, defaults to Quotes
    :param username: (Optional) <str> Case sensitive Discord username, without discriminator
    :param raw:
    """
    _table = Quotes
    select_id, select_rand, select_user = None, None, None
    # Find out what we are getting
    if username:
        select_user = select([_table]).where(and_(
            _table.c.name == username,
            _table.c.guild == guild_id)).order_by(func.random())
    elif quote_id:
        select_id = select([_table]).where(and_(
            _table.c.id == quote_id,
            _table.c.guild == guild_id))
    else:
        select_rand = select([_table]).where(
            _table.c.guild == guild_id).order_by(func.random())
    # Actually get it
    with ENGINE.connect() as conn:
        if quote_id:
            result = conn.execute(select_id).fetchone()
        elif username:
            result = conn.execute(select_user).fetchone()
        else:
            result = conn.execute(select_rand).fetchone()
    # Pretty printing
        # Result fields translate as
        # [0]: message id, [1]: author, [2]: quote, [3]: date, [6]: embed url, [7]: jump_url
        if result:
            config = load_config(guild_id)
            stm = '---{} on {}'
            title = f'Quote {result[0]}'
            if config:
                if _table.name == 'famQuotes':
                    stm = config[4].replace('\\n', '\n')
                    title = f"Quote {result[0]}"
                elif _table.name == 'famLore':
                    stm = config[5].replace('\\n', '\n')
                    title = f"Lore {result[0]}"
            else:
                if _table.name == 'famQuotes':
                    stm = '---{} on {}'
                    title = f"Quote {result[0]}"
                elif _table.name == 'famLore':
                    stm = '---Scribed by the Lore Master {}, on the blessed day of {}'
                    title = f"Lore {result[0]}"
            if raw:
                # Check if there is an attached img or file to send as well
                if len(result) > 6 and result[6]:
                    stm = stm + '\n' + result[6]
                    result[2].replace(result[6], '')
                # Result fields translate as
                # [1]: author, [2]: quote, [3]: date, [6]: embed url, [7]: jump_url
                text = result[2]
                return stm.format(title, text, result[1], result[3])
        else:
            # TODO implement embed format
            pass


def insert_quote(message: disnake.Message, _table: (None, Table), adder=None) -> disnake.Embed:
    """
    Insert a quote to the database
    :param message: <Discord.message object>
    :param _table: <SQLAlchemy.Table object>
    :param adder: <String> Username of the member who added the :speech_left:
    :return: <String> Notifying of message being added
    """
    if _table is None:
        _table = Quotes
    config = load_config(message.guild.id)
    if config:
        server_locale = config[2]
        stm = config[7].replace('\\n', '\n')
    else:
        server_locale = 'Asia/Tokyo'
        stm = '--{} on {}'
    # Suppress any user or role mentions
    text = message.content
    for each in message.mentions:
        text = text.replace('<@!{}>'.format(each.id), each.name)
    for each in message.role_mentions:
        text = text.replace('<@&{}>'.format(each.id), each.name)
    text = text.replace('@everyone', '@ everyone')
    text = text.replace('@here', '@ here')
    # jump_url = message.jump_url
    args = text.split()
    embed = str(message.attachments[0].url) if message.attachments else None
    if not embed:
        embed = ''
        for each in args:
            if each.find('http') != -1:
                if each.split('.')[-1] in EXT_SET['image']:
                    embed = '{}\n{}'.format(embed, each)
    date = pendulum.now(tz=server_locale).to_day_datetime_string()
    with ENGINE.connect() as conn:
        if _table.name == 'famQuotes':
            ins = _table.insert().values(
                id=message.id,
                name=message.author.name,
                text=text,
                date=date,
                guild=str(message.guild.id),
                guild_name=message.guild.name,
                embed=embed,
                #                context=jump_url,
            )
            conn.execute(ins)
            if not fetch_value(message.guild.id, 10):
                banner = disnake.Embed(title="{} Added Quote: {}".format(adder, message.id), description=text)
            else:
                banner = disnake.Embed(title="Added Quote: {}".format(message.id), description=text)
            if embed:
                banner.set_image(url=embed)
            banner.set_footer(text=stm.format(message.author.name, date))
        elif _table.name == 'famLore':
            ins = _table.insert().values(
                id=message.id,
                name=args[2],
                text=' '.join(args[3:]),
                date=date,
                guild=str(message.guild.id),
                embed=embed,
                guild_name=message.guild.name,
            )
            conn.execute(ins)
            banner = disnake.Embed(title="Added Lore: {}".format(message.id), description=' '.join(args[3:]))
            if embed:
                banner.set_image(url=embed)
            banner.set_footer(text=stm.format(args[2], date))
    return banner


def delete_quote(guild_id: int, msg_id: int) -> (str, None):
    """
    Remove a quote from the database
    :param guild_id: <Int> Discord guild ID
    :param msg_id: <Int> Discord message ID
    :return: <String> Notify if quote has been removed
    """
    with ENGINE.connect() as conn:
        for _table in {Quotes, Lore}:
            select_st = select([_table]).where(and_(
                _table.c.id == msg_id,
                _table.c.guild == guild_id
            ))
            try:
                result = conn.execute(select_st).fetchone()
                if result:
                    quote = f'{result[2]}\n ---{result[1]} on {result[3]}'
                    ins = _table.delete().where(and_(
                        _table.c.id == msg_id,
                        _table.c.guild == guild_id
                    ))
                    conn.execute(ins)
                return "Deleted quote: {}".format(quote)
            except Exception as e:
                if VERBOSE >= 1:
                    print(f'[!] Exception in tquote: {e}')
                return None


def load_config(guild_id: int) -> (None, list):
    """
    Retrieve any formatting options from database
    :param guild_id: <Int> Discord guild ID
    :return: <List> SQLAlchemy row entry from Config Table
    """
    result = None
    with ENGINE.connect() as conn:
        select_st = select([Config]).where(Config.c.id == guild_id)
        result = conn.execute(select_st).fetchone()
    return result


def check_if_exists(guild_id: int, msg_id: int) -> bool:
    """
    Internal function to ensure that we do not
    add the same message to the database multiple times.
    :param guild_id: <Int> Discord guild ID
    :param msg_id: <Int> Discord message ID
    :return: <Bool>
    """
    with ENGINE.connect() as conn:
        select_st = select([Quotes]).where(and_(
            Quotes.c.id == msg_id,
            Quotes.c.guild == guild_id))
        result = conn.execute(select_st).fetchall()
        if result:
            return True
    return False


def get_quote_log(guild_id: int) -> list:
    """
    Return an xlsx of all quotes in the guild to the user.
    :param guild_id:
    :return:
    """
    data_frame = [None, None]
    for idx, _table in enumerate({Quotes, Lore}):
        select_st = select([_table]).where(
            _table.c.guild == guild_id)
        with ENGINE.connect() as conn:
            result = conn.execute(select_st).fetchall()
            keys = conn.execute(select_st).keys()
            entries = [each.values() for each in result]
            for each in entries:
                each[0] = 'id_{}'.format(each[0])
                each[4] = 'g_{}'.format(each[4])
            data_frame[idx] = pd.DataFrame(entries, columns=keys)

    if RUNNING_ON == 'Linux':
        with pd.ExcelWriter(f'{DEFAULT_DIR}/../log/quoteLog_{guild_id}.xlsx', engine='xlsxwriter') as writer:
            data_frame[1].to_excel(writer, sheet_name='Sheet_1')
            data_frame[0].to_excel(writer, sheet_name='Sheet_2')
        return ['Log of all quotes and lore for this guild:', f'{DEFAULT_DIR}/../log/quoteLog_{guild_id}.xlsx']

    elif RUNNING_ON == 'Window':
        with pd.ExcelWriter(f'{DEFAULT_DIR}\\..\\log\\quoteLog_{guild_id}.xlsx', engine='xlsxwriter') as writer:
            data_frame[1].to_excel(writer, sheet_name='Sheet_1')
            data_frame[0].to_excel(writer, sheet_name='Sheet_2')
        return ['Log of all quotes and lore for this guild:', f'{DEFAULT_DIR}\\..\\log\\quoteLog_{guild_id}.xlsx']


setup()
