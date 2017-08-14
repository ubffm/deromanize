# Copyright 2017, Goethe University
#
# This library is free software; you can redistribute it and/or
# modify it either under the terms of:
#
#   the EUPL, Version 1.1 or – as soon they will be approved by the
#   European Commission - subsequent versions of the EUPL (the
#   "Licence"). You may obtain a copy of the Licence at:
#   https://joinup.ec.europa.eu/software/page/eupl
#
# or
#
#   the terms of the Mozilla Public License, v. 2.0. If a copy of the
#   MPL was not distributed with this file, You can obtain one at
#   http://mozilla.org/MPL/2.0/.
#
# If you do not alter this notice, a recipient may use your version of
# this file under either the MPL or the EUPL.
import unicodedata


def strip_chars(rep_keyvalue, chars=set('ieaou')):
    for source, target in rep_keyvalue:
        new = ''
        for c in source:
            decomposed = unicodedata.normalize('NFD', c)
            if decomposed[0] in chars:
                new += decomposed[0]
            else:
                new += c
        yield new, target


def replacer_maker(simple_replacements, pair_replacements):
    pair_reps = {tuple(v): k for k, v in pair_replacements.items()}

    def replace(rep_keyvalue):
        for pair in rep_keyvalue:
            target = pair[1]
            if pair in pair_reps:
                yield pair_reps[pair], target
            else:
                new = pair[0]
                for k, v in simple_replacements.items():
                    new = new.replace(k, v)
                yield new, target

    return replace


def get_combos(rep_key):
    return set(
        pair
        for replist in rep_key.values()
        for rep in replist
        for pair in rep.keyvalue)


CACHE_DOC = '''\
object to track numbers of occurances of certain word pairs
'''


class CacheObject:
    """
    """
    def __init__(self, seed=None):
        if isinstance(seed, dict):
            self.data = seed
        else:
            self.data = {}
            if seed:
                self.update(seed)

    def __setitem__(self, source, target):
        self.add(source, target)

    def add(self, source, target, count=1):
        current = self.data.setdefault(source, {}).setdefault(target, 0)
        self.data[source][target] = current + count

    def update(self, matches):
        for row in matches:
            self.add(*row)

    def __getitem__(self, value):
        if isinstance(value, tuple):
            return self.data[value[0]][value[1]]
        return self.data[value]

    def get(self, value, default=None):
        try:
            return self[value]
        except KeyError:
            return default

    def __iter__(self):
        for source, targets in self.data.items():
            for target, count in targets.items():
                yield source, target, count

    def inverted(self):
        new = CacheObject()
        for source, target, count in self:
            new.add(target, source, count)
        return new

    def serializable(self):
        return self.data


class CacheDB(CacheObject):
    def __init__(self, connection, seed=None):
        self.con = connection
        self.cur = connection.cursor()
        with self:
            self.cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS deromcache (
                    source VARCHAR,
                    target VARCHAR,
                    count INTEGER,
                    PRIMARY KEY (source, target)
                )
                ''')
        if isinstance(seed, dict):
            seed = CacheObject(seed)

        if seed:
            with self:
                for row in seed:
                    self.add(*row)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self.con.__exit__(type, value, traceback)

    def add(self, source, target, count=1):
        self.cur.execute(
            '''
            INSERT OR REPLACE INTO deromcache VALUES (
            ?,
            ?,
            COALESCE(
                (SELECT count FROM deromcache
                    WHERE source = ? AND target = ?),
                    0) + ?
            )
            ''', (source, target, source, target, count))

    def __getitem__(self, value):
        if isinstance(value, tuple):
            self.cur.execute(
                'SELECT count FROM deromcache WHERE source = ? AND target = ?',
                (value[0], value[1]))
            try:
                return self.cur.fetchall()[0][0]
            except IndexError:
                raise KeyError('{!r} not found'.format(value))

        self.cur.execute(
            'SELECT target, count FROM deromcache WHERE source = ?',
            (value,))
        results = self.cur.fetchall()
        if not results:
                raise KeyError('{!r} not found'.format(value))
        return dict(results)

    def __iter__(self):
        self.cur.execute('SELECT * FROM deromcache')
        return iter(self.cur.fetchall())

    def serializable(self):
        return CacheObject(self).data
