import datetime
import math

from config.constants import DEFAULT_DIR


def fetch_file(directory: str, filename: str):
    """
    Safely read in a dynamically designated local file
    :param directory:
    :param filename:
    :return:
    """
    with open('{}/docs/{}/{}.txt'.format(DEFAULT_DIR, directory, filename), 'r') as f:
        return f.read()


def wrap(s: str, w: int) -> list:
    """
    Break a long string s into a list of strings of length w
    :param s:
    :param w:
    :return:
    """
    return [s[i:i + w] for i in range(0, len(s), w)]


def datestr_to_ms(time_str: str) -> int:
    """Get seconds from time."""
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


def ms_to_datestr(time_str: int) -> str:
    """
    Convert ms to hh:mm:ss format.
    :param time_str:
    :return:
    """
    return datetime.datetime.fromtimestamp(time_str / 1000).strftime('%M:%S')


def bytes_to_str(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def flatten_sublist(list_of_lists: list) -> list:
    """
    Convert a list of lists into a flat list.
    :param list_of_lists:
    :return:
    """
    return [item for sublist in list_of_lists for item in sublist]

