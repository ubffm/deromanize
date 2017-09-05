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
Classes for implementing the KeyGenerator type.
"""
import copy
import functools
import itertools
import json
import operator
from collections import abc
from typing import Tuple
from .trees import Trie, BackTrie, empty


class KeyGeneratorError(Exception):
    pass


class CharSetsError(KeyGeneratorError):
    pass


class PatternError(KeyGeneratorError):
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
    """a type for holding a replacement and it's weight. A Replacement on its
    own doesn't know what it's replacing. It should be an item in a
    ReplacementList.
    """
    def __init__(self,
                 weight: int,
                 value: str=None,
                 key: str=None,
                 keyvalue: Tuple[Tuple[str, str], ...]=None):
        """A string with some metadata

            weight - an integer to determine how the item will be sorted.

            values - the actual text values of the replacement.

            key - what the values is replacing in the original script.
                  (optional)

            keyvalue - a tuple of of the keys and values from parent
                       replacements. Used by the __add__ method

        """
        if (value and keyvalue) or (value is None and keyvalue is None):
            raise KeyGeneratorError(
                "Either values or parts must be supplied, but not both!")
        if value is not None:
            self.str = value
            self.keyvalue = ((key, value),)
        else:
            self.keyvalue = keyvalue
        self.weight = weight
        self.key = key

    def __add__(self, other):
        """adding one Replacement to another results in them combining their
        weight and string values.
        """
        return Replacement(self.weight + other.weight,
                           keyvalue=self.keyvalue + other.keyvalue)

    def __repr__(self):
        return "Replacement({!r}, {!r})".format(self.weight, self.str)

    def __str__(self):
        return self.str

    @property
    def values(self):
        return tuple(i[1] for i in self.keyvalue)

    @property
    def keyparts(self):
        return tuple(i[0] for i in self.keyvalue)

    @reify
    def str(self):
        return ''.join(self.values)

    def __deepcopy__(self, memo=None):
        return self

    def copy(self):
        return type(self)(self.weight, (self,), self.key)

    def simplify(self):
        return dict(weight=self.weight, str=self.str, keyvalues=self.keyvalue)


class StatRep(Replacement):
    """class for representing replacement weights that look like statistics
    because Kai likes multiplication.
    """
    def __add__(self, other):
        return StatRep(self.weight * other.weight,
                       keyvalue=self.keyvalue + other.keyvalue)


class ReplacementList(abc.MutableSequence):
    """a list of Replacements with a .key attribute containing the key to which
    they belong.
    """
    reptype = Replacement

    def __init__(self, key=None, values: list=None, weight=None,
                 parents=None, profile=None):
        self.profile = profile or {}
        if key is not None:
            self.key = key
        elif parents is None:
            raise KeyGeneratorError('unable to define key for ReplacementList')

        if parents is None:
            self.keytree = key
            self.keyparts = (key,)
        else:
            self.keytree = parents
        self.data = []
        if values is not None:
            self.extend(values, weight)

    def _prep_value(self, weight, value):
        """Make sure any input is converted into a Replacement."""
        if isinstance(value, Replacement):
            return value
        elif isinstance(value, (tuple, list)) and len(value) == 2:
            return Replacement(*value, key=self.key)
        elif isinstance(value, str):
            return Replacement(weight, value, key=self.key)
        else:
            raise KeyGeneratorError(
                '%s is not supported for insertion in ReplacementList'
                % type(value))

    def _keyparts(self):
        for part in self.keytree:
            if isinstance(part, str):
                yield part
            else:
                yield from part.keyparts

    @reify
    def keyparts(self):
        this = tuple(self._keyparts())
        del self.keytree
        return this

    @reify
    def key(self):
        broken_clusters = self.profile.get('broken_clusters')
        if not broken_clusters:
            return ''.join(self.keyparts)

        newparts = [self.keyparts[0]]
        for i, part in enumerate(self.keyparts[1:]):
            prev = self.keyparts[i]
            cluster = prev + part
            if cluster in broken_clusters:
                newparts[i] = broken_clusters[cluster]
            else:
                newparts.append(part)
        return ''.join(newparts)

    def __add__(self, other):
        """When two ReplacementList instances are added together, the keys are
        concatinated, and all combinations of the replacements are also added
        together. It's a bit multiplicative, really.
        """
        composite_values = [x + y for x, y in itertools.product(self, other)]

        return ReplacementList(
            values=composite_values,
            parents=(self, other),
            profile=self.profile)

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
            del self.data[i]

    def __deepcopy__(self, memo=None):
        new = type(self)(self.key)
        new.data = self.data.copy()
        return new

    copy = __deepcopy__

    def simplify(self):
        return (self.key, [(i.weight, i.values) for i in self])

    def makestat(self):
        """convert all weights to faux statistical values because my boss told
        me to.
        """
        # for rep in self:
        #     rep.weight += 1
        # subtotal = sum(r.weight for r in self)
        # total = sum(subtotal-r.weight for r in self)
        # for i, rep in enumerate(self):
        #     self.data[i] = StatRep((subtotal-rep.weight)/total,
        #                            keyvalue=rep.keyvalue)
        for rep in self:
            rep.weight = 1/(rep.weight+1)
        total = sum(r.weight for r in self)
        for i, rep in enumerate(self):
            self.data[i] = StatRep((rep.weight)/total,
                                   keyvalue=rep.keyvalue)


class RepListList(list):
    """I'm to lazy to type deromanize.add_reps"""
    def add(self):
        return add_reps(self)

    def __repr__(self):
        return 'RepListList(%r)' % [i.simplify() for i in self]


class ReplacementKey(Trie):
    """a tree the only contains ReplacementLists. used for tokenizing Romanized
    strings.
    """
    template = 'ReplacementKey(%r)'

    def __repr__(self):
        return self.template % self.simplify()

    def __setitem__(self, key, value, weight=None):
        super().__setitem__(key, _ensurereplist(key, value, weight))

    def getallparts(self, key):
        return RepListList(super().getallparts(key))

    def update(self, dictionary, weight=None):
        for k, v in dictionary.items():
            self.__setitem__(k, v, weight)

    def extend(self, dictionary, weight=None, parent=None):
        """For each item in in the input dictionary, the coresponding
        replacement list in the trie is extended with the given replacemnts.
        """
        print('here')
        for k, v in dictionary.items():
            self.setdefault(k, ReplacementList(k)).extend(
                _ensurereplist(k, v, weight))

    def simplify(self):
        """reduces the tree to a dictionary and all special types to JSON
        serializable types. A new ReplacementKey can be instantiated from this
        resulting object.
        """
        return {k: [(i.weight, str(i)) for i in v.data]
                for k, v in self.items()}

    def treesimplify(self):
        """reduces the tree to and all special types to JSON serializable types. A new
        ReplacementKey can be instantiated from this resulting object.
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
        child = ReplacementBackKey() if suffix else ReplacementKey()
        if type(self) is type(child):
            child = self.copy()
        else:
            child.update(copy.deepcopy(self.dict()))
        for d in dicts:
            child.update(d, weight)
        return child


def _ensurereplist(key, value, weight=None):
    """make sure all input values are converted to ReplacementList"""
    if isinstance(value, ReplacementList):
        if weight is not None:
            value.add_weight(weight)
        return value
    elif not isinstance(value, list) or isinstance(value[0], int):
        value = [value]
    return ReplacementList(key, value, weight)


class ReplacementBackKey(ReplacementKey, BackTrie):
    """same as ReplacementKey, but it will begin analysing a string from the
    end, so it can be used for identifying suffixes.
    """
    template = 'ReplacementBackKey(%r)'


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
        the shortcut for each capture group is the key, and the values is the
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
                index[value] = len(results)
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


class KeyGenerator:
    """an object to build up a transliteration key from a config file. (or
    rather, a python dictionary unmarshalled from a config file.)
    """
    def __init__(self, profile, base_key='base', mtime=0,
                 from_cache=False, tree_cache=False):
        self.mtime = mtime
        self.base_key = base_key
        self.keys = {}
        self.tree_cache = tree_cache
        if from_cache:
            self.profile = profile['profile']
            self.normalize_profile()
            self.broken_clusters = profile.get('broken_clusters')
            for k, v in profile['keys'].items():
                if self.profile['keys'][k].get('suffix'):
                    trie = ReplacementBackKey
                else:
                    trie = ReplacementKey
                self[k] = trie.tree_expand(v) if tree_cache else trie(v)
        else:
            # profile is static. prof2 is modified while the keys are generated
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
                    self[base_key] = ReplacementKey()
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

    def __iter__(self):
        return iter(self.keys)

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
            parent = ReplacementKey()
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
                        k, ReplacementList(k)).extend(
                            _ensurereplist(k, v, weight))
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

    def patterngen(self, key_pattern, rep_patterns,
                   weight=0, broken_clusters=None):
        """implement some kind of pattern-based replacement generation for character
        classes.
        """
        # parse pattern strings
        blocks, pattern_idx = self.char_sets.parse_pattern(key_pattern)
        if isinstance(rep_patterns, str) or isinstance(rep_patterns[0], int):
            rep_patterns = [rep_patterns]
        rep_patterns = self._normalize_rp(
            [self._parse_rep(i) for i in rep_patterns])
        generated = {}
        for keyparts in itertools.product(*blocks):
            replist = ReplacementList(parents=keyparts, profile=self.profile)
            generated[replist.key] = replist
            for i, rep_group in enumerate(rep_patterns):
                reps = []
                for j, block in enumerate(rep_group):
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
                        reps.append(ReplacementList(
                            blocks[j], [(i, block)], profile=self.profile))
                replacement = add_reps(reps)
                replist.extend(replacement.data, weight)

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
    def _normalize_rp(rep_pats):
        if len(rep_pats) == 1 or all(
                len(i) == len(rep_pats[0]) for i in rep_pats[1:]):
            return rep_pats
        by_len = sorted(rep_pats, key=len, reverse=True)
        for i, group in enumerate(by_len[0]):
            if isinstance(group, str):
                for pat in by_len[1:]:
                    if isinstance(pat[i], int):
                        pat.insert(i, '')
        return rep_pats

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
        intermediate = [(max_i - i.weight, i.values) for i in reps]
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
        elif isinstance(base, ReplacementKey):
            return base
        elif base is None:
            try:
                return self[self.base_key]
            except KeyError:
                return ReplacementKey()
        else:
            raise TypeError('%s is not supported as "base" argument.'
                            % type(base))

    def serialize(self, file, *args, **kwargs):
        file.write(str(self.mtime) + '\n')
        data = {'keys': {}, 'profile': self.profile}

        for k, v in self.keys.items():
            key = v.treesimplify() if self.tree_cache else v.simplify()
            data['keys'][k] = key

        file.write(json.dumps(data, *args, **kwargs))


# Just another Trie for parsing regex-like capture group syntax for
# substitutions.
esc_numbs = Trie()
for i in range(1, 10):
    s = str(i)
    esc_numbs['\\'+s] = i
    esc_numbs['\\\\'+s] = '\\' + s
del s, i


def add_reps(reps):
    """Add together a bunch of ReplacementLists"""
    try:
        return functools.reduce(operator.add, reps)
    except TypeError:
        return get_empty_replist()


def get_empty_replist():
    return ReplacementList('', [Replacement(0, '', '')])
