import sqlite3
import re

import pandas as pd
import disnake
from disnake.ext import commands
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from sklearn.feature_extraction.text import CountVectorizer
import seaborn as sns

from config.constants import VERBOSE, PATH_DB, DEFAULT_DIR, STOPWORDS, RUNNING_ON


class UserStats(commands.Cog, name="User Stats"):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="Generate a wordcloud of the most common words.")
    async def wordcloud(
            self,
            inter,
            username: disnake.Member = None,
            channel: disnake.TextChannel = None
    ):
        if username:
            setup(inter.guild.id, user=username.name)
            _file, _embed = word_cloud(username.name, inter.guild.name)
            await inter.response.send_message(embed=_embed, file=_file)
        elif channel:
            setup(inter.guild.id, channel=channel.name)
            _file, _embed = word_cloud(channel.name, inter.guild.name)
            await inter.response.send_message(embed=_embed, file=_file)
        else:
            setup(inter.guild.id)
            _file, _embed = word_cloud('the server', inter.guild.name)
            await inter.response.send_message(embed=_embed, file=_file)

    @commands.slash_command(description="Get a list of the most common words.")
    async def wordcount(
            self,
            inter,
            low: int = commands.Param(ge=1),
            high: int = commands.Param(ge=2),
            username: disnake.Member = None,
            channel: disnake.TextChannel = None
    ):
        if high <= low:
            high = low + 1
        if username:
            setup(inter.guild.id, user=username.name)
        elif channel:
            setup(inter.guild.id, channel=channel.name)
        else:
            setup(inter.guild.id)
        _file, _embed = word_count(low, high, inter.guild.name)
        await inter.response.send_message(embed=_embed, file=_file)

    @commands.slash_command(description="Get a list of the most common phrases.")
    async def wordphrases(
            self,
            inter,
            low: int = commands.Param(ge=1),
            high: int = commands.param(ge=2),
            limit: int = commands.Param(ge=1),
            username: disnake.Member = None,
            channel: disnake.TextChannel = None
    ):
        if high <= low:
            high = low + 1
        if not limit:
            limit = 10
        if username:
            setup(inter.guild.id, user=username.name)
        elif channel:
            setup(inter.guild.id, channel=channel.name)
        else:
            setup(inter.guild.id)
        _file, _embed = get_ngrams(low, high, limit, inter.guild.name)
        await inter.response.send_message(embed=_embed, file=_file)

    @commands.slash_command(description="Generate a wordcloud of the most common words.")
    async def wordfrequency(
            self,
            inter,
            limit: int = commands.Param(ge=1),
            username: disnake.Member = None,
            channel: disnake.TextChannel = None
    ):
        if not limit:
            limit = 10
        if username:
            setup(inter.guild.id, user=username.name)
        elif channel:
            setup(inter.guild.id, channel=channel.name)
        else:
            setup(inter.guild.id)
        _embed = word_frequency(limit)
        await inter.response.send_message(embed=_embed)


def setup(guild: int, user=None, channel=None) -> None:
    """
    TODO
    :param guild:
    :param user:
    :param channel:
    :return:
    """
    global log_df, clean_description, stem_description
    log_df = []
    clean_description = []
    stem_description = []
    with sqlite3.connect(PATH_DB) as conn:
        if user:
            sql_st = 'Select content from corpus where user_name like {} and guild={}'.format(
                '\'' + user + '%\'', guild)
            log_df = pd.read_sql(sql_st, conn)
        elif channel:
            sql_st = 'Select content from corpus where channel like {} and guild={}'.format(
                '\'' + channel + '%\'', guild)
            log_df = pd.read_sql(sql_st, conn)
        else:
            sql_st = 'Select content from corpus where guild={}'.format(guild)
            log_df = pd.read_sql(sql_st, conn)

        log_df['word_count'] = log_df['content'].apply(lambda x: len(str(x).split(" ")))
        normalize_pd_dataframe(log_df.content)
    if VERBOSE >= 0:
        print(f"[-] Stats setup complete with user={user} channel={channel}")


def normalize_pd_dataframe(dataframe: pd.DataFrame) -> None:
    """
    Remove special characters and normalize words
    :param dataframe: <Pandas dataframe>
    :return: <Pandas dataframe>
    """
    for w in range(len(dataframe)):
        desc = log_df['content'][w].lower()
        desc = re.sub('[^a-zA-Z]', ' ', desc)
        desc = re.sub("&lt;/?.*?&gt;", " &lt;&gt ", desc)
        # TODO check this
        desc = re.sub("`|'", " ", desc)
        desc = re.sub("'", " ", desc)
        clean_description.append(desc)
    log_df['clean_description'] = clean_description


def word_frequency(limit: int) ->  disnake.Embed:
    """
    Generate a pandas Series of word frequency pairs
    :param limit: <Int> user supplied input describing upper limit
    :return: <List> Contains Pandas series of word frequency pairs
    """
    # TODO reduce to single line
    frequency = pd.Series(' '.join(clean_description).split()).value_counts()[:limit]
    frequency = str(frequency).split('dtype')[0]
    split_frequency = [each.split('\n') for each in frequency.split(' ') if each]
    split_frequency = [item for sublist in split_frequency for item in sublist]
    # Find the longest combination of WORD and FREQ to create appropriate padding for pretty printing
    longest = 0
    for index in range(0, len(split_frequency) - 1):
        if len(split_frequency[index]) + len(split_frequency[index + 1]) > longest:
            longest = len(split_frequency[index]) + len(split_frequency[index + 1]) + 1
    count = 1
    values = ''
    for index, _ in enumerate(split_frequency):
        if index + 1 == len(split_frequency):
            break
        padding = ' '
        prefix = count if count >= 10 else '0{}'.format(count)
        if index % 2 == 0:
            while len(padding) + len(split_frequency[index]) + len(split_frequency[index + 1]) <= longest:
                padding += ' '
            values += '`{}: {}{}{}`\n'.format(prefix, split_frequency[index], padding, split_frequency[index + 1])
            count += 1
    banner = disnake.Embed(title='Word Frequencies')
    banner.add_field(name=f'The {limit} most common words for this server are:', value=values)
    return banner


def word_count(low: int, high: int, guild: str) -> tuple[disnake.File, disnake.Embed]:
    """
    Create a bar plot of message lengths
    :param high:
    :param low:
    :param guild: <String> Discord guild name
    :return: <List> Strings describing args and filename of graph
    """
    image = None
    plt.xlabel("Message word length")
    plt.ylabel("# of Messages")
    plt.hist(
        log_df['word_count'],
        bins='auto',
        range=(low, high)
    )
    filename = f'{guild}_wordcount.png'
    if RUNNING_ON == 'Linux':
        plt.savefig(f"{DEFAULT_DIR}/../log/stats/{filename}")
        plt.clf()
        image = disnake.File(
            f'{DEFAULT_DIR}/../log/stats/{filename}',
            filename=filename
    )
    elif RUNNING_ON == 'Windows':
        plt.savefig(f"{DEFAULT_DIR}\\..\\log\\stats\\{filename}")
        plt.clf()
        image = disnake.File(
            f'{DEFAULT_DIR}\\..\\log\\stats\\{filename}',
            filename=filename
    )
    banner = disnake.Embed(
        title='Wordcount',
        description=f"Number of messages between length {low} and {high}."
    )
    banner.set_image(url=f'attachment://{filename}')
    return image, banner


def word_cloud(type_: str, guild: str) -> tuple[disnake.File, disnake.Embed]:
    """
    Create a word cloud of common phrases in the server.
    :param type_: <String> Either the user, channel, or guild name
    :param guild: <String> Discord guild name
    :return: <List> Strings describing the type_ and filename
    """
    image = None
    word_cloud_obj = WordCloud(
        width=800,
        height=800,
        background_color='black',
        stopwords=STOPWORDS,
        max_words=1000,
        min_font_size=20
    ).generate(str(clean_description))
    fig = plt.figure(figsize=(8, 8), facecolor=None)
    plt.imshow(word_cloud_obj)
    plt.axis('off')
    filename = f'{guild}_wordcloud.png'
    if RUNNING_ON == 'Linux':
        fig.savefig(f"{DEFAULT_DIR}/../log/stats/{filename}")
        plt.clf()
        image = disnake.File(f'{DEFAULT_DIR}/../log/stats/{filename}', filename=filename)
    elif RUNNING_ON == 'Windows':
        fig.savefig(f'{DEFAULT_DIR}\\..\\log\\stats\\{filename}')
        plt.clf()
        image = disnake.File(f'{DEFAULT_DIR}\\..\\log\\stats\\{filename}', filename=filename)
    banner = disnake.Embed(title='Wordcloud', description=f"The most common single words for {type_}.")
    banner.set_image(url=f'attachment://{filename}')
    return image, banner


def get_ngrams(low: int, high: int, limit: int, guild: str) -> tuple[disnake.File, disnake.Embed]:
    """
    Create a bar plot of common short phrases within messages
    :param limit:
    :param high:
    :param low:
    :param guild: <String> Discord guild name
    :return:
    """
    def make_ngrams(low: int, high: int, n=None) -> list:
        """
        Internal function to convert corpus into a set of ngrams
        :param low: <Int> Lower ngram length
        :param high: <Int> Upper ngram length
        :return: <List> Sorted ngram frequency list
        """
        vec = CountVectorizer(
            strip_accents='unicode',
            ngram_range=(low, high),
            max_features=20000
        ).fit(clean_description)
        bag_of_words = vec.transform(clean_description)
        sum_words = bag_of_words.sum(axis=0)
        # TODO test for membership should be 'not in'
        words_freq = [(word, sum_words[0, i]) for word, i in vec.vocabulary_.items() if not word in STOPWORDS]
        words_freq = sorted(words_freq, key=lambda x: x[1], reverse=True)
        return words_freq[:n]

    image = None
    ngrams = make_ngrams(int(low), int(high), n=int(limit))
    # Plotting
    trigram_df = pd.DataFrame(ngrams)
    trigram_df.columns = ["n-gram", "Freq"]
    sns.set(rc={'figure.figsize': (12, 8)}, font_scale=1)
    bp = sns.barplot(x="n-gram", y="Freq", data=trigram_df)
    bp.set_xticklabels(bp.get_xticklabels(), rotation=75)
    plt.tight_layout()
    plt.axis('on')
    # Cleanup
    filename = f"{guild}_ngram.png"
    figure = bp.get_figure()
    if RUNNING_ON == 'Linux':
        figure.savefig(f'{DEFAULT_DIR}/../log/stats/{filename}')
        plt.clf()
        image = disnake.File(
            f'{DEFAULT_DIR}/../log/stats/{filename}',
            filename=filename
        )
    elif RUNNING_ON == 'Windows':
        figure.savefig(f'{DEFAULT_DIR}\\..\\log\\stats\\{filename}')
        plt.clf()
        image = disnake.File(
            f'{DEFAULT_DIR}\\..\\log\\stats\\{filename}',
            filename=filename
        )
    banner = disnake.Embed(
        title='N-Grams',
        description=f"The {limit} most common phrases of length {low} to {high}."
    )
    banner.set_image(url='attachment://{filename}')
    return image, banner
