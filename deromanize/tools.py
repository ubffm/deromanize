import json
import os
import pathlib
from collections import abc
from .keygenerator import KeyGenerator, ReplacementList


def cached_keys(loader, profile_file, cache_path,
                base_key='base', tree_cache=False):
    stats = os.stat(profile_file.name)
    cache_path = pathlib.Path(cache_path)
    if not cache_path.exists():
        with cache_path.open('w', encoding='utf8') as cache:
            cache.write('0')
    cache_file = cache_path.open(encoding='utf8')
    cached_mtime = float(cache_file.readline())
    if stats.st_mtime == cached_mtime:
        try:
            return KeyGenerator(json.loads(cache_file.readline()),
                                base_key=base_key,
                                mtime=stats.st_mtime,
                                from_cache=True,
                                tree_cache=tree_cache)
            cache_file.close()
        except json.JSONDecodeError:
            cache_file.close()
            os.remove(cache_path)
            raise
    else:
        cache_file.close()
        key = KeyGenerator(loader(profile_file),
                           base_key=base_key,
                           mtime=stats.st_mtime,
                           tree_cache=tree_cache)
        pid = os.fork()
        if pid == 0:
            cache_writer(cache_path, key)
            os._exit(0)
        else:
            return key


def cache_writer(path, key):
    with path.open('w', encoding='utf8') as cache:
        key.serialize(cache, ensure_ascii=False, separators=(',', ':'))


def front_mid_end_decode(keys, word):
    # get ending clusters, then beginning clusters, then whatever's left in the
    # middle.
    end, remainder = keys['end'].getpart(word)
    if remainder:
        try:
            front, remainder = keys['front'].getpart(remainder)
        except KeyError:
            return _no_end(keys, word)
    else:
        return _no_end(keys, word)

    if remainder:
        middle = keys['mid'].getallparts(remainder).add()
        return (front + middle + end)
    else:
        return (front + end)


def _no_end(keys, word):
    # this is where words go when getting the ending first produces strange
    # results.
    front, remainder = keys['front'].getpart(word)
    if remainder:
        end, remainder = keys['end'].getpart(remainder)
        if remainder:
            middle = keys['mid'].getallparts(remainder).add()
            return (front + middle + end)
        else:
            return (front + end)
    else:
        return (front)


def get_self_rep(string):
    return ReplacementList(string, [string])


def _flatten(iterable):
    """return a flat iterator containing all the strings an non-iterables from
    a nested data structure.
    """
    for item in iterable:
        if isinstance(item, str) or not isinstance(item, abc.Iterable):
            yield item
        else:
            yield from _flatten(item)


def stripper_factory(*wordgroups):
    """create a strip function based on groups of characters *not* to be
    stripped
    """
    chars = {c for string in _flatten(wordgroups)
             if isinstance(string, str)
             for c in string}

    def strip(word):
        """remove non-character symbols from the front of a word. return a tuple
        containing the junk from the front, and the remainder of the word.
        """
        junk = []
        remainder = ''
        for i, char in enumerate(word):
            if char in chars:
                remainder = word[i:]
                break
            junk.append(char)

        return (''.join(junk), remainder) if remainder else ('', ''.join(junk))

    def double_strip(word):
        """strip non-character symbols off the front and back of a word. return
        a tuple with (extra stuff from the front, word, extra stuff from the
        back)
        """
        front_junk, remainder = strip(word)
        back_junk, stripped_word = [
            i[::-1] for i in strip(remainder[::-1])]
        return front_junk, stripped_word, back_junk

    return double_strip
