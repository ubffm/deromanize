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
from . import ReplacementKey
import unicodedata
from typing import Callable, Dict, Set, Tuple, Iterable, Sequence, Union
RepKeyValue = Iterable[Tuple[str, str]]


def strip_chars(rep_keyvalue: RepKeyValue,
                chars: Set[str]=set('ieaou')) -> RepKeyValue:
    for source, target in rep_keyvalue:
        new = ''
        for c in source:
            decomposed = unicodedata.normalize('NFD', c)
            if decomposed[0] in chars:
                new += decomposed[0]
            else:
                new += c
        yield new, target


def replacer_maker(
        simple_replacements: Dict[str, str],
        pair_replacements: Dict[str, Sequence[str]]
) -> Callable[[RepKeyValue], RepKeyValue]:
    pair_reps = {tuple(v): k for k, v in pair_replacements.items()}

    def replace(rep_keyvalue: RepKeyValue) -> RepKeyValue:
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


def get_combos(rep_key: ReplacementKey) -> Set[Tuple[str, str]]:
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

    def __setitem__(self, source: str, target: str):
        self.add(source, target)

    def add(self, source: str, target: str, count: int=1) -> None:
        current = self.data.setdefault(source, {}).setdefault(target, 0)
        self.data[source][target] = current + count

    def update(self, matches):
        for row in matches:
            self.add(*row)

    def __getitem__(
            self, value: Union[str, Tuple[str, str]]
    ) -> Union[Dict[str, int], int]:

        if isinstance(value, tuple):
            return self.data[value[0]][value[1]]
        return self.data[value]

    def get(self,
            value: Union[str, Tuple[str, str]],
            default=None) -> Union[Dict[str, int], int]:

        try:
            return self[value]
        except KeyError:
            return default

    def __iter__(self):
        for source, targets in self.data.items():
            for target, count in targets.items():
                yield source, target, count

    def inverted(self, new=None):
        if new is None:
            new = CacheObject()
        for source, target, count in self:
            new.add(target, source, count)
        return new

    def serializable(self):
        return self.data


class CacheDB(CacheObject):
    def __init__(self, connection, table_name='deromcache', seed=None):
        self.con = connection
        self.cur = connection.cursor()
        self.table = table_name
        with self:
            self.cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS {0} (
                    source VARCHAR,
                    target VARCHAR,
                    count INTEGER,
                    PRIMARY KEY (source, target)
                )
                '''.format(table_name))
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

    def add(self, source: str, target: str, count: int=1) -> None:
        self.cur.execute(
            '''
            INSERT OR REPLACE INTO {0} VALUES (
            ?,
            ?,
            COALESCE(
                (SELECT count FROM {0}
                    WHERE source = ? AND target = ?),
                    0) + ?
            )
            '''.format(self.table), (source, target, source, target, count))

    def __getitem__(
            self, value: Union[str, Tuple[str, str]]
    ) -> Union[Dict[str, int], int]:

        if isinstance(value, tuple):
            self.cur.execute(
                'SELECT count FROM {0} WHERE source = ? AND target = ?'.format(
                    self.table), (value[0], value[1])
            )
            try:
                return self.cur.fetchall()[0][0]
            except IndexError:
                raise KeyError('{!r} not found'.format(value))

        self.cur.execute(
            'SELECT target, count FROM {0} WHERE source = ?'.format(
                self.table), (value,)
        )
        results = self.cur.fetchall()
        if not results:
                raise KeyError('{!r} not found'.format(value))
        return dict(results)

    def __iter__(self):
        self.cur.execute('SELECT * FROM {0}'.format(self.table))
        return iter(self.cur.fetchall())

    def serializable(self) -> Dict[str, Dict[str, int]]:
        return CacheObject(self).data
