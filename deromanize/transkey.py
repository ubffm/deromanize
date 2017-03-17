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
"""
Classes, mostly for implementing the TransKey type.
"""
import copy
from collections import abc
import itertools
import functools
import operator
import json
import os
from .trees import Trie, SuffixTree


class Replacement:
    """a type for holding a replacement and it's weight. A Replacment on its
    own doesn't know what it's replacing. It should be an item in a
    ReplacmentList.
    """
    def __init__(self, weight: int, value: str):
        self.weight, self.value = weight, value

    def __add__(self, other):
        """adding one Replacement to another results in them combining their
        weight and string values.
        """
        return Replacement(self.weight + other.weight,
                           self.value + other.value)

    def __repr__(self):
        return "Replacement({!r}, {!r})".format(self.weight, self.value)

    def __str__(self):
        return self.value


class StatRep(Replacement):
    def __add__(self, other):
        return StatRep(self.weight * other.weight,
                       self.value + other.value)


class ReplacementList(abc.MutableSequence):
    """a list of Replacements with a .key attribute containing the key to which
    they belong
    """
    reptype = Replacement

    def __init__(self, key, values: list=None, weight=None):
        self.key = key
        self.data = []
        if values is not None:
            self.extend(values, weight)

    @staticmethod
    def _prep_value(i, value):
        if isinstance(value, Replacement):
            return value
        elif isinstance(value, (tuple, list)) and len(value) == 2:
            return Replacement(*value)
        elif isinstance(value, str):
            return Replacement(i, value)
        else:
            raise TypeError(
                '%s is not supported for insertion in ReplacementList'
                % type(value))

    def __setitem__(self, i, value):
        self.data[i] = self._prep_value(i, value)

    def __getitem__(self, i):
        return self.data[i]

    def __delitem__(self, i):
        del self.data[i]

    def __len__(self):
        return len(self.data)

    def insert(self, i, value):
        self.data.insert(i, self._prep_value(i, value))

    def extend(self, iterable, weight=None):
        if weight is None:
            super().extend(iterable)
        else:
            for i, value in enumerate(iterable):
                rep = self._prep_value(i, value)
                rep.weight += weight
                self.data.append(rep)

    def add_weight(self, weight):
        for i in self:
            i.weight += weight

    def __add__(self, other):
        """When two ReplacementList instances are added together, the keys are
        concatinated, and all combinations of the replacements are also added
        together. It's a bit multiplicative, really.
        """
        key = self.key + other.key
        composite_values = [x + y for x, y in itertools.product(self, other)]

        return ReplacementList(key, composite_values)

    def __repr__(self):
        string = "ReplacementList({!r}, [".format(self.key)
        if not self.data:
            return string + '])'
        for i in self:
            string += '%r, ' % ((i.weight, i.value),)
        return string[:-2] + '])'

    def __str__(self):
        string = self.key + ':'
        for r in self:
            string += '\n{:2} {}'.format(r.weight, r.value)
        return string

    def sort(self, reverse=False, key=lambda rep: rep.weight, *args, **kwargs):
        self.data.sort(key=key, reverse=reverse, *args, **kwargs)

    def prune(self, reverse=False):
        self.sort(reverse)
        repeats = []
        seen = set()
        for i, rep in enumerate(self):
            if rep.value in seen:
                repeats.append(i)
            seen.add(rep.value)
        for i in repeats[::-1]:
            self.data.remove(i)


class ReplacementTrie(Trie):
    template = 'ReplacementTrie(%r)'

    def __repr__(self):
        return self.template % self.simplify()

    def __setitem__(self, key, value, weight=None):
        super().__setitem__(key, self._ensurereplist(key, value, weight))

    def update(self, dictionary, weight=None, parent=None):
        if parent:
            for k, v in dictionary.items():
                if any(i in k for i in parent.char_sets):
                    generated = parent.patterngen(
                        k, v, broken_clusters=parent.broken_clusters)
                    self.update(generated, weight)
                else:
                    self.__setitem__(k, v, weight)
        else:
            for k, v in dictionary.items():
                self.__setitem__(k, v, weight)

    def extend(self, dictionary, weight=None, parent=None):
        """For each item in in the input dictionary, the coresponding
        replacement list in the trie is extended with the given replacemnts.
        """
        if parent:
            for k, v in dictionary.items():
                if any(i in k for i in parent.char_sets):
                    generated = parent.patterngen(
                        k, v, broken_clusters=parent.broken_clusters)
                    self.extend(generated, weight)
                else:
                    self.setdefault(k, ReplacementList(k)).extend(v, weight)
        else:
            for k, v in dictionary.items():
                self.setdefault(k, ReplacementList(k)).extend(v, weight)

    def simplify(self):
        return {k: [(i.weight, i.value) for i in v.data]
                for k, v in self.items()}

    def child(self, *dicts, weight=None, suffix=False):
        child = ReplacementSuffixTree() if suffix else ReplacementTrie()
        if type(self) is type(child):
            child = self.copy()
        else:
            child.update(copy.deepcopy(self.dict()))
        for d in dicts:
            child.update(d, weight)
        return child

    @staticmethod
    def _ensurereplist(key, value, weight=None):
        if isinstance(value, ReplacementList):
            if weight is not None:
                value.add_weight(weight)
            return value
        elif not isinstance(value, list) or isinstance(value[0], int):
            value = [value]
        return ReplacementList(key, value, weight)


class ReplacementSuffixTree(ReplacementTrie, SuffixTree):
    template = 'ReplacementSuffixTree(%r)'


class CharSets:
    def __init__(self, char_sets, key):
        self.unparsed = Trie(char_sets)
        self.parsed = Trie()
        self.key = key

    def __getitem__(self, key):
        try:
            return self.parsed[key]
        except KeyError:
            self.parse(key)
        return self.parsed[key]

    def __setitem__(self, key, value):
        self.parsed[key] = value

    def __contains__(self, key):
        return key in self.unparsed

    def __iter__(self):
        return iter(self.unparsed)

    def getpart(self, key):
        try:
            return self.parsed.getpart(key)
        except KeyError:
            _, remainder = self.unparsed.getpart(key)
            matched = key[:len(key)-len(remainder)]
            self.parse(matched)
        return self.parsed.getpart(key)

    def parse_pattern(self, key):
        results = []
        remainder = key
        counter = 0
        index = {}
        while remainder:
            try:
                value, remainder = self.getpart(remainder)
                counter += 1
                index[counter] = len(results)
            except KeyError:
                value = remainder[0]
                remainder = remainder[1:]
            results.append(value)
        return results, index

    def parse(self, key):
        def_ = self.unparsed[key]
        try:
            chars = self.key.profile[def_]
            parent = self.key[self.key.base_key]
        except (TypeError, KeyError):
            chars = self.key.profile[def_['chars']]
            parent = self.key.get_base(def_['base'])
        self.parsed[key] = [parent[c] for c in chars]


class TransKey:
    """an object to build up a transliteration key from a config file. (or
    rather, a python dictionary unmarshalled from a config file.)
    """
    def __init__(self, profile, base_key='base', mtime=None, from_cache=False):
        self.mtime = mtime
        self.base_key = base_key
        self.keys = {}
        if from_cache:
            self.profile = profile['profile']
            self.normalize_profile()
            self.broken_clusters = profile.get('broken_clusters')
            for k, v in profile['keys'].items():
                if self.profile['keys'][k].get('suffix'):
                    trie = ReplacementSuffixTree
                else:
                    trie = ReplacementTrie
                self[k] = trie(v)
        else:
            self.profile = profile
            self.normalize_profile()
            self.broken_clusters = profile.get('broken_clusters')
            try:
                self.char_sets = CharSets(profile['char_sets'], self)
            except KeyError:
                self.char_sets = {}
            if 'keys' in profile:
                try:
                    self.keygen(base_key)
                except KeyError:
                    self[base_key] = ReplacementTrie()
                for k in profile['keys']:
                    if k == base_key or k in self.keys:
                        continue
                    self.keygen(k)

    def __setitem__(self, key, value):
        self.keys[key] = value

    def __getitem__(self, key):
        return self.keys[key]

    def normalize_profile(self):
        keys = self.profile['keys']
        for k, v in keys.items():
            if isinstance(v, (list, str)):
                keys[k] = {'groups': v}
            if isinstance(keys[k]['groups'], str):
                keys[k]['groups'] = [keys[k]['groups']]

    def keygen(self, keyname):
        info = self.profile['keys'][keyname]
        suffix = info.get('suffix')
        parent = info.get(
            'parent', None if keyname == self.base_key else self.base_key)
        groups = info.get('groups', [])
        if parent not in self.keys and parent is not None:
            self.keygen(parent)
        key = self.new(keyname, parent=parent, suffix=suffix)
        for g in groups:
            if isinstance(g, str):
                key.update(self.profile[g], parent=self)
            else:
                if isinstance(g, dict):
                    g = g.items()
                else:
                    g = g[::-1]
                for k, v in g:
                    key.extend(self.profile[k], weight=v, parent=self)
        self[keyname] = key

    def new(self, key_name, *profile_groups,
            parent=None, weight=None, suffix=False):
        parent = self.get_base(parent)
        dicts = (self.profile[g] for g in profile_groups)
        self[key_name] = parent.child(*dicts, weight=weight, suffix=suffix)
        return self[key_name]

    def extend(self, key_name, *profile_groups, weight=None):
        for g in profile_groups:
            self[key_name].extend(self.profile[g], weight)

    def update(self, key_name, *profile_groups, weight=None):
        for g in profile_groups:
            self[key_name].update(self.profile[g], weight)

    def definecharset(self, char, character_set, parent=None):
        parent = self.get_base(parent)
        self.char_sets[char] = [parent[c] for c in character_set]

    def patterngen(self, key_pattern, rep_patterns,
                   weight=0, broken_clusters=None):
        """implement some kind of pattern matching for character classes that
        generates all possible matches ahead of time.
        """
        # parse pattern strings
        blocks, pattern_idx = self.char_sets.parse_pattern(key_pattern)
        if isinstance(rep_patterns, str) or isinstance(rep_patterns[0], int):
            rep_patterns = [rep_patterns]
        rep_patterns = [self._parse_rep(i) for i in rep_patterns]
        generated = {}
        for keyparts in itertools.product(*blocks):
            key = self._get_sane_key(keyparts, broken_clusters)
            for i, rep_group in enumerate(rep_patterns):
                reps = []
                for block in rep_group:
                    try:
                        reps.append(keyparts[pattern_idx[block]])
                    except KeyError:
                        reps.append(ReplacementList('', [(i, block)]))
                replacement = add_reps(reps)
                generated.setdefault(
                    key, ReplacementList(key)).extend(replacement.data, weight)

        return generated

    @staticmethod
    def _parse_rep(rep):
        results = []
        remainder = rep
        while remainder:
            try:
                value, remainder = esc_numbs.getpart(remainder)
            except KeyError:
                value = remainder[0]
                remainder = remainder[1:]
            results.append(value)
        return results

    @staticmethod
    def _get_sane_key(keyparts, broken_clusters=None):
        """Helper function for TransKey.patterngen(), so the keys actually
        make sense (i.e. don't create any unintentional digraphs).
        """
        if not broken_clusters:
            letters = []
            for p in keyparts:
                try:
                    letters.append(p.key)
                except AttributeError:
                    letters.append(p)
            return ''.join(letters)

        oldparts = []
        for p in keyparts:
            try:
                oldparts.append(p.key)
            except AttributeError:
                oldparts.append(p)
        newparts = []
        for i, part in enumerate(oldparts[:-1]):
            nextpart = oldparts[i+1]
            try:
                newparts.append(broken_clusters[part + nextpart])
                oldparts[i+1] = ''
            except KeyError:
                newparts.append(part)
        newparts.append(oldparts[-1])
        return ''.join(newparts)

    def patterns2key(self, target, pattern_dict, weight=None,
                     broken_clusters=None):
        target = self.get_base(target)
        for pattern_key, pattern_rep in pattern_dict.items():
            generated = self.patterngen(pattern_key, pattern_rep,
                                        weight=weight, broken_clusters=None)
            target.update(generated)

    def processor(self, func):
        """decorator to define the process for decoding words. Basicaly just
        sugar for separating concerns.
        """
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            return func(self, *args, **kwargs)
        return wrapped

    def get_stat_part(self, key, string):
        reps, remainder = self[key].getpart(string)
        max_i = max(i.weight for i in reps) + 1
        intermediate = [(max_i - i.weight, i.value) for i in reps]
        total = sum(i[0] for i in intermediate)
        return (ReplacementList(
            reps.key, [StatRep(i[0]/total, i[1]) for i in intermediate]),
                remainder)

    def get_all_stat_parts(self, key, string):
        results = []
        remainder = string
        while remainder:
            value, remainder = self.get_stat_part(key, remainder)
            results.append(value)
        return results

    def get_base(self, base=None):
        if isinstance(base, str):
            return self[base]
        elif base is None:
            try:
                return self[self.base_key]
            except KeyError:
                return ReplacementTrie()
        elif isinstance(base, ReplacementTrie):
            return base
        else:
            raise TypeError('%s is not supported as "base" argument.'
                            % type(base))

    def serialize(self, file, *args, **kwargs):
        file.write(str(self.mtime) + '\n')
        data = {'keys': {}, 'profile': self.profile}

        for k, v in self.keys.items():
            data['keys'][k] = v.simplify()

        file.write(json.dumps(data, *args, **kwargs))


def get_empty_replist():
    return ReplacementList('', [Replacement(0, '')])


def add_reps(reps):
    """Add together a bunch of ReplacementLists"""
    try:
        return functools.reduce(operator.add, reps)
    except TypeError:
        return get_empty_replist()


def cached_keys(loader, profile_file, cache_file, base_key='base'):
    mtime = os.stat(profile_file.name).st_mtime
    cached_mtime = float(cache_file.readline())
    if mtime == cached_mtime:
        return TransKey(json.loads(cache_file.readline()),
                        base_key=base_key,
                        mtime=mtime,
                        from_cache=True)
    else:
        cache_file.close()
        key = TransKey(loader(profile_file),
                       base_key=base_key,
                       mtime=mtime)
        with open(cache_file.name, 'w') as cache:
            key.serialize(cache)
        return key


esc_numbs = Trie()
for i in range(1, 10):
    s = str(i)
    esc_numbs['\\'+s] = i
    esc_numbs['\\\\'+s] = '\\' + s

del s, i


if __name__ == '__main__':
    import yaml
    prof = yaml.safe_load(open('data/new.yml'))
    key = TransKey(prof, 'base')
