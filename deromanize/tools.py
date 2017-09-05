import json
import os
import pathlib
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
        # cache_writer(cache_path, key)
        # return key


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
