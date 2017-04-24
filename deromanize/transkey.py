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
Classes for implementing the TransKey type.
"""
import copy
from collections import abc
import itertools
import functools
import operator
import json
import os
import pathlib
from .trees import Trie, BackTrie, empty


class TransKeyError(Exception):
    pass


class CharSetsError(TransKeyError):
    pass


class PatternError(TransKeyError):
    pass


class reify:
    """ Use as a class method decorator.  It operates almost exactly like the
    Python ``@property`` decorator, but it puts the result of the method it
    decorates into the instance dict after the first call, effectively
    replacing the function it decorates with an instance variable.  It is, in
    Python parlance, a non-data descriptor.

    Stolen from pyramid.
    http://docs.pylonsproject.org/projects/pyramid/en/latest/api/decorator.html#pyramid.decorator.reify
    """
    def __init__(self, wrapped):
        self.wrapped = wrapped
        functools.update_wrapper(self, wrapped)

    def __get__(self, inst, objtype=None):
        if inst is None:
            return self
        val = self.wrapped(inst)
        setattr(inst, self.wrapped.__name__, val)
        return val


class Replacement:
    """a type for holding a replacement and it's weight. A Replacment on its
    own doesn't know what it's replacing. It should be an item in a
    ReplacmentList.
    """
    def __init__(self, weight: int, value):
        if isinstance(value, (tuple, list)):
            self.valuetree = value
        elif isinstance(value, str):
            self.valuetree = (value,)
        else:
            raise TransKeyError("The value of a replacement must be a string, "
                                "not %r" % value)
        self.weight = weight

    def __add__(self, other):
        """adding one Replacement to another results in them combining their
        weight and string values.
        """
        return Replacement(self.weight + other.weight,
                           (self, other))

    def __repr__(self):
        return "Replacement({!r}, {!r})".format(self.weight, self.str)

    def __str__(self):
        return self.str

    def _value(self):
        for val in self.valuetree:
            if isinstance(val, str):
                yield val
            else:
                yield from val.value

    @reify
    def value(self):
        return tuple(self._value())

    @reify
    def str(self):
        return ''.join(self.value)

    def __deepcopy__(self, memo=None):
        # new = Replacement(self.weight, self.value)
        # if 'str' in self.__dict__:
        #     new.str = self.str
        # if 'value' in self.__dict__['value']:
        #     new.value = self.value
        return self


class StatRep(Replacement):
    """class for representing replacement weights that look like statistics
    because Kai likes multiplication.
    """
    def __add__(self, other):
        return StatRep(self.weight * other.weight,
                       (self.value, other.value))


class ReplacementList(abc.MutableSequence):
    """a list of Replacements with a .key attribute containing the key to which
    they belong.
    """
    reptype = Replacement

    def __init__(self, key, values: list=None, weight=None):
        self.key = key
        self.data = []
        if values is not None:
            self.extend(values, weight)

    def _prep_value(self, weight, value):
        """Make sure any input is converted into a Replacement."""
        if isinstance(value, Replacement):
            return value
        elif isinstance(value, (tuple, list)) and len(value) == 2:
            return Replacement(*value)
        elif isinstance(value, str):
            return Replacement(weight, value)
        else:
            raise TypeError(
                '%s is not supported for insertion in ReplacementList'
                % type(value))

    def _value(self):
        for val in self.valuetree:
            if isinstance(val, str):
                yield val
            else:
                yield from val.value

    @reify
    def value(self):
        return list(self._value())

    @reify
    def str(self):
        return ''.join(self.value)

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
        """incrementally increase weight while extending"""
        if weight is None:
            super().extend(iterable)
        else:
            for i, value in enumerate(iterable):
                rep = self._prep_value(i, value)
                rep.weight += weight
                self.data.append(rep)

    def add_weight(self, weight):
        """add additional weight to each item in the list"""
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
            string += '%r, ' % ((i.weight, str(i)),)
        return string[:-2] + '])'

    def __str__(self):
        string = self.key + ':'
        for r in self:
            string += '\n{:2} {}'.format(r.weight, r)
        return string

    def sort(self, reverse=False, key=lambda rep: rep.weight, *args, **kwargs):
        """sort items by weight"""
        self.data.sort(key=key, reverse=reverse, *args, **kwargs)

    def prune(self, reverse=False):
        """sort items and prune repeats"""
        self.sort(reverse)
        repeats = []
        seen = set()
        for i, rep in enumerate(self):
            if rep.str in seen:
                repeats.append(i)
            seen.add(rep.str)
        for i in repeats[::-1]:
            self.data.remove(i)

    def __deepcopy__(self, memo=None):
        new = type(self)(self.key)
        new.data = self.data.copy()
        return new


class RepListList(list):
    """I'm to lazy to type deromanize.add_reps"""
    def add(self):
        return add_reps(self)


class ReplacementTrie(Trie):
    """a tree the only contains ReplacementLists. used for tokenizing Romanized
    strings.
    """
    template = 'ReplacementTrie(%r)'

    def __repr__(self):
        return self.template % self.simplify()

    def __setitem__(self, key, value, weight=None):
        super().__setitem__(key, self._ensurereplist(key, value, weight))

    def getallparts(self, key):
        return RepListList(super().getallparts(key))

    def update(self, dictionary, weight=None):
        for k, v in dictionary.items():
            self.__setitem__(k, v, weight)

    def extend(self, dictionary, weight=None, parent=None):
        """For each item in in the input dictionary, the coresponding
        replacement list in the trie is extended with the given replacemnts.
        """
        for k, v in dictionary.items():
            self.setdefault(k, ReplacementList(k)).extend(v, weight)

    def simplify(self):
        """reduces the tree to a dictionary and all special types to JSON
        serializable types. A new ReplacementTrie can be instantiated from this
        resulting object.
        """
        return {k: [(i.weight, str(i)) for i in v.data]
                for k, v in self.items()}

    def treesimplify(self):
        """reduces the tree to a dictionary and all special types to JSON
        serializable types. A new ReplacementTrie can be instantiated from this
        resulting object.
        """
        new = self.copy()
        self._ts_walk(new.root)
        return new.root

    @classmethod
    def _ts_walk(cls, node):
        if node[0] is empty:
            node[0] = None
        else:
            node[0] = (node[0].key, [(i.weight, str(i)) for i in node[0].data])
        for newnode in node[1].values():
            cls._ts_walk(newnode)

    @classmethod
    def tree_expand(cls, tree):
        cls._te_walk(tree)
        new = cls()
        new.root = tree
        return new

    @classmethod
    def _te_walk(cls, node, key=None):
        if node[0] is None:
            node[0] = empty
        else:
            node[0] = cls._ensurereplist(node[0][0], node[0][1])
        for k, newnode in node[1].items():
            cls._te_walk(newnode, k)

    def child(self, *dicts, weight=None, suffix=False):
        """creates a new tree containing starting from the elements in the
        parent, but updated from the supplied dicts.
        """
        child = ReplacementBackTrie() if suffix else ReplacementTrie()
        if type(self) is type(child):
            child = self.copy()
        else:
            child.update(copy.deepcopy(self.dict()))
        for d in dicts:
            child.update(d, weight)
        return child

    @staticmethod
    def _ensurereplist(key, value, weight=None):
        """make sure all input values are converted to ReplacementList"""
        if isinstance(value, ReplacementList):
            if weight is not None:
                value.add_weight(weight)
            return value
        elif not isinstance(value, list) or isinstance(value[0], int):
            value = [value]
        return ReplacementList(key, value, weight)


class ReplacementBackTrie(ReplacementTrie, BackTrie):
    """same as ReplacementTrie, but it will begin analysing a string from the
    end, so it can be used for identifying suffixes.
    """
    template = 'ReplacementBackTrie(%r)'


class CharSets:
    """A Container for character sets which can be used to generate replacement
    lists based on patterns.
    """
    def __init__(self, char_sets, key):
        self.unparsed = Trie(char_sets)
        self.parsed = Trie()
        self.key = key

    def __getitem__(self, key):
        try:
            return self.parsed[key]
        except KeyError:
            self.conf_parse(key)
        return self.parsed[key]

    def __setitem__(self, key, value):
        self.parsed[key] = value

    def __contains__(self, key):
        return key in self.unparsed

    def __iter__(self):
        return iter(self.unparsed)

    def getpart(self, key):
        """wrapper on getpart from the internal Trie, used to tokenize pattern
        strings by CharSets.parse_pattern()
        """
        try:
            return self.parsed.getpart(key)
        except KeyError:
            _, remainder = self.unparsed.getpart(key)
            matched = key[:len(key)-len(remainder)]
            self.conf_parse(matched)
        return self.parsed.getpart(key)

    getallparts = Trie.getallparts

    def parse_pattern(self, key):
        """tokenizes a pattern-based replacement definition and returns a
        tuple. the first item in the tuple is a list containg all the parts to
        be used in the replacement. the second item is a dictionary where each
        the shortcut for each capture group is the key, and the value is the
        index in the results list.
        """
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

    def conf_parse(self, key):
        # the charset definitions aren't parsed until they are actually
        # required, to ensure all the required keys have been built, so this
        # function is used throughout the class to parse charsets as needed.
        def_ = self.unparsed[key]
        if not isinstance(def_, dict):
            def_ = {'chars': def_}

        _chars = def_['chars']
        if isinstance(_chars, str):
            if 'key' not in def_ and _chars in self.key.profile['keys']:
                parent_key = _chars
                self.check_and_gen_key(parent_key)
                parent = self.key[_chars]
            else:
                parent_key = def_.get('key')
                parent = self.key.get_base(parent_key)
            chars = self.key.prof2[_chars]
        else:
            chars = def_['chars']
            parent_key = def_.get('key')
            parent = self.key.get_base(parent_key)
        self.check_and_gen_key(parent_key)
        for c in chars:
            if c not in parent:
                try:
                    self.getallparts(c)
                except KeyError:
                    raise CharSetsError(
                        '%r not in the %r key, parent of char set %r!'
                        % (c, self.key.base_key if parent_key is None
                           else parent_key, key))
        self.parsed[key] = [parent[c] for c in chars]

    def check_and_gen_key(self, key):
        if key and key not in self.key.keys:
            self.key.keygen(key)


class TransKey:
    """an object to build up a transliteration key from a config file. (or
    rather, a python dictionary unmarshalled from a config file.)
    """
    def __init__(self, profile, base_key='base', mtime=0, from_cache=False):
        self.mtime = mtime
        self.base_key = base_key
        self.keys = {}
        if from_cache:
            self.profile = profile['profile']
            self.normalize_profile()
            self.broken_clusters = profile.get('broken_clusters')
            for k, v in profile['keys'].items():
                if self.profile['keys'][k].get('suffix'):
                    trie = ReplacementBackTrie
                else:
                    trie = ReplacementTrie
                # self[k] = trie(v)
                self[k] = trie.tree_expand(v)
        else:
            self.profile = profile
            self.prof2 = copy.deepcopy(self.profile)
            self.normalize_profile()
            self.broken_clusters = profile.get('broken_clusters')
            if 'char_sets' in profile:
                self.char_sets = CharSets(profile['char_sets'], self)
            else:
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
        """There are shortcuts for leaving implied keys out of the profile
        definitions. This normalizes out those shortcuts.
        """
        keys = self.profile['keys']
        for k, v in keys.items():
            if isinstance(v, (list, str)):
                keys[k] = {'groups': v}
            if isinstance(keys[k]['groups'], str):
                keys[k]['groups'] = [keys[k]['groups']]

    def keygen(self, keyname):
        """generates a key from the `keys` section of a profile."""
        info = self.profile['keys'][keyname]
        suffix = info.get('suffix')
        parent = info.get(
            'parent', None if keyname == self.base_key else self.base_key)
        groups = info.get('groups', [])
        if parent not in self.keys and parent is not None:
            self.keygen(parent)
        self.new(keyname, parent=parent, suffix=suffix)
        for g in groups:
            if isinstance(g, str):
                self.update(keyname, g)
            else:
                if isinstance(g, dict):
                    g = g.items()
                else:
                    g = g[::-1]
                for k, v in g:
                    self.extend(keyname, self.profile[k], weight=v)
        # self[keyname] = key

    def new(self, key_name, *profile_groups,
            parent=None, weight=None, suffix=False):
        """create a new key based on `parent` key that is updated from the
        specified `profile_groups`.
        """
        if parent is None:
            parent = ReplacementTrie()
        else:
            parent = self.get_base(parent)
        dicts = (self.profile[g] for g in profile_groups)
        self[key_name] = parent.child(*dicts, weight=weight, suffix=suffix)
        return self[key_name]

    def extend(self, key_name, *profile_groups, weight=None):
        """extend a key with the specified profile groups. Keys containing
        char_set aliases will be expanded.
        """
        for g in profile_groups:
            if isinstance(g, str):
                g = self.prof2[g]
            profile_updates = []
            for k, v in g.items():
                if any(i in k for i in self.char_sets):
                    generated = self.patterngen(
                        k, v, broken_clusters=self.broken_clusters)
                    self[key_name].extend(generated, weight)
                    profile_updates.append((k, generated))
                else:
                    self[key_name].setdefault(
                        k, ReplacementList(k)).extend(v, weight)
            for key, generated in profile_updates:
                del g[key]
                g.update(generated)

    def update(self, key_name, *profile_groups, weight=None):
        """update a key with the specified profile groups. Keys containing
        char_set aliases will be expanded.
        """
        for g in profile_groups:
            if isinstance(g, str):
                g = self.prof2[g]
            profile_updates = []
            for k, v in g.items():
                if any(i in k for i in self.char_sets):
                    generated = self.patterngen(
                        k, v, broken_clusters=self.broken_clusters)
                    self[key_name].update(generated, weight)
                    profile_updates.append((k, generated))
                else:
                    self[key_name].__setitem__(k, v, weight)
            for key, generated in profile_updates:
                del g[key]
                g.update(generated)

    def definecharset(self, char, character_set, parent=None):
        """legacy way to define character sets. it might even still work!"""
        parent = self.get_base(parent)
        self.char_sets[char] = [parent[c] for c in character_set]

    def patterngen(self, key_pattern, rep_patterns,
                   weight=0, broken_clusters=None):
        """implement some kind of pattern-based replacement generation for character
        classes.
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
                    if isinstance(block, int):
                        try:
                            reps.append(keyparts[pattern_idx[block]])
                        except KeyError:
                            raise PatternError(
                                'found reference to capture-group %s, but '
                                "there aren't that many capture groups in "
                                'pattern %r'
                                % (block, key_pattern))
                    else:
                        reps.append(ReplacementList('', [(i, block)]))
                replacement = add_reps(reps)
                generated.setdefault(
                    key, ReplacementList(key)).extend(replacement.data, weight)

        return generated

    @staticmethod
    def _parse_rep(rep):
        """parse the replacement pattern"""
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
        results = RepListList()
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
            data['keys'][k] = v.treesimplify()

        file.write(json.dumps(data, *args, **kwargs))


def get_empty_replist():
    return ReplacementList('', [Replacement(0, '')])


def add_reps(reps):
    """Add together a bunch of ReplacementLists"""
    try:
        return functools.reduce(operator.add, reps)
    except TypeError:
        return get_empty_replist()


def cached_keys(loader, profile_file, cache_path, base_key='base'):
    stats = os.stat(profile_file.name)
    cache_path = pathlib.Path(cache_path)
    if not cache_path.exists():
        with cache_path.open('w', encoding='utf8') as cache:
            cache.write('0')
    cache_file = cache_path.open(encoding='utf8')
    cached_mtime = float(cache_file.readline())
    if stats.st_mtime == cached_mtime:
        try:
            return TransKey(json.loads(cache_file.readline()),
                            base_key=base_key,
                            mtime=stats.st_mtime,
                            from_cache=True)
            cache_file.close()
        except json.JSONDecodeError:
            cache_file.close()
            os.remove(cache_path)
            raise
    else:
        cache_file.close()
        key = TransKey(loader(profile_file),
                       base_key=base_key,
                       mtime=stats.st_mtime)
        with open(cache_file.name, 'w', encoding='utf8') as cache:
            key.serialize(cache, ensure_ascii=False, separators=(',', ':'))
        return key


# Just another Trie for parsing regex-like capture group syntax for
# substitutions.
esc_numbs = Trie()
for i in range(1, 10):
    s = str(i)
    esc_numbs['\\'+s] = i
    esc_numbs['\\\\'+s] = '\\' + s
del s, i
