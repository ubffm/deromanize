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
import collections
import itertools
import functools
import operator
import re
import unicodedata


class _Empty:
    def __repr__(self):
        return "empty"

    def __eq__(self, other):
        return isinstance(other, _Empty)


empty = _Empty()


class Trie:
    """a prefix tree for dealing with transliteration standards with digraphs.
    This could just be a dictionary if there weren't digraphs in
    transliteration standards.

    In addition to optionally being initialized with a dictionary, it supports
    a lot of the same methods and behaviors as a dictionary, along with special
    methods for use with transliteration stuff.
    """
    def __init__(self, dictionary=None):
        """Trie([dictionary])

        The optional dictionary parameter may be used to create a prefix tree
        with all nodes based on the dictionary keys, and all vaules as
        endpoints
        """
        self.root = [empty, {}]
        if dictionary is not None:
            self.update(dictionary)

    def __setitem__(self, key, value):
        """follow (and generate, if needed) all neccesary intermediate nodes to
        create a new endpoint.
        """
        node = self.root
        for char in key:
            node = node[1].setdefault(char, [empty, {}])

        node[0] = value

    def __repr__(self):
        return 'Trie(%r)' % self.dict()

    def update(self, dictionary):
        """add new nodes and endpoints from keys and values in a dictionary."""
        for key, value in dictionary.items():
            self[key] = value

    def _getnode(self, key):
        """get a node out of the internal prefix tree. An implementation
        detail.
        """
        node = self.root
        for char in key:
            node = node[1][char]
        return node

    def __getitem__(self, key):
        node = self._getnode(key)

        if node[0] is empty:
            raise KeyError(key)
        return node[0]

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        return True

    def containsnode(self, key):
        """check if a node on the tree exists without regard for whether it
        contains anything.
        """
        try:
            self._getnode(key)
        except KeyError:
            return False
        return True

    def setdefault(self, key, default):
        """like dict.setdefault(). refer to the documentation."""
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def get(self, key, default):
        """like dict.get(). refer to the documentation."""
        try:
            return self[key]
        except KeyError:
            return default

    def items(self, key=None):
        """return a generator yielding all keys and values with valid
        endpoints. if "key" argument is provided, yield all keys and values
        where the key starts with "key".

        This method traverses the tree structure with call-stack recursion, so
        it isn't the cheapest thing ever, on the other hand, it's lazy, so, eh.
        """
        if key is None:
            node = self.root
            key = ''
        else:
            node = self._getnode(key)
        return self._itemize(node, key)

    def _itemize(self, topnode, keypart=''):
        for key, node in topnode[1].items():
            newkeypart = keypart + key
            if node[0] is not empty:
                yield (newkeypart, node[0])
            yield from self._itemize(node, newkeypart)

    def keys(self, key=None):
        return (k for k, _ in self.items(key))

    def __iter__(self):
        return self.keys()

    def values(self, key=None):
        node = self.root if key is None else self._getnode(key)
        return self._values(node)

    def _values(self, topnode):
        for key, node in topnode[1].items():
            if node[0] is not empty:
                yield node[0]
            yield from self._values(node)

    def copy(self):
        """make a copy of the prefix tree. Note that, unlike builtins, this is
        a deep copy, because that is the only sane way to copy a tree. Be aware
        that it's not the cheapest operation.
        """
        new = Trie()
        new.root = copy.deepcopy(self.root)
        return new

    def dict(self):
        return dict(self.items())

    def getpart(self, key):
        """takes a key and matches as much of it as possible. returns a tuple
        containing the value of the node and the remainder of the key.
        """
        node = self.root
        value = empty
        remainder = key
        for i, char in enumerate(key):
            try:
                node = node[1][char]
            except KeyError:
                if value is empty:
                    raise
                else:
                    return value, remainder

            if node[0] is not empty:
                value, remainder = node[0], key[i+1:]

        if value is empty:
            raise KeyError(key)
        else:
            return value, remainder

    def getallparts(self, key):
        """loop over a string, splitting the input string up by longest
        possible matches.
        """
        results = []
        remainder = key
        while remainder:
            value, remainder = self.getpart(remainder)
            results.append(value)
        return results


class SuffixTree(Trie):
    """Subclass of Trie that shouldn't technically be. I just want a cheap way
    to inherit all it's methods. :(
    """
    def __repr__(self):
        return 'SuffixTree(%r)' % self.dict()

    def __setitem__(self, key, value):
        super().__setitem__(key[::-1], value)

    def _getnode(self, key):
        return super()._getnode(key[::-1])

    def getpart(self, key):
        value, remainder = super().getpart(key[::-1])
        return value, remainder[::-1]

    def items(self, key=None):
        return ((k[::-1], v) for k, v in super().items(key))

    def getallparts(self, key):
        return super().getallparts(key)[::-1]


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


class ReplacementList(collections.UserList):
    """a list of Replacements with a .key attribute containing the key to which
    they belong
    """
    def __init__(self, key, values: list=None):
        self.key = key
        self.data = values if values is not None else []

    def __add__(self, other):
        """When two ReplacementList instances are added together, the keys are
        concatinated, and all combinations of the replacements are also added
        together. It's a bit multiplicative, really.
        """
        key = self.key + other.key
        composite_values = [x + y for x, y in itertools.product(self, other)]

        return ReplacementList(key, composite_values)

    def __repr__(self):
        return "ReplacementList({!r}, {!r})".format(self.key, self.data)

    def __str__(self):
        string = self.key + ':'
        for r in self:
            string += '\n{:2} {}'.format(r.weight, r.value)
        return string

    def sort(self):
        self.data.sort(key=lambda rep: rep.weight)


class TransKey:
    """an object to build up a transliteration key from a config file. (or
    rather, a python dictionary unmarshalled from a config file.)
    """
    def __init__(self, profile, base_key, *args, **kwargs):
        self.profile = profile
        self.consonants = set(profile['consonants'])
        self.vowels = set(profile['vowels'])
        self.allchars = (
            self.consonants | self.vowels | set(profile.get('other', set())))
        self.fuzzies = {}
        self.keys = {}
        self.base_key = base_key
        if args or kwargs:
            self.groups2key(base_key, *args, **kwargs)
        self.definefuzzychar('C', self.consonants)
        self.definefuzzychar('V', self.vowels)
        for v in self.vowels:
            basev = unicodedata.normalize('NFD', v)[0].upper()
            self.fuzzies.setdefault(basev, set()).add(v)

    def __setitem__(self, key, value):
        self.keys[key] = value

    def __getitem__(self, key):
        return self.keys[key]

    def keymaker(self, *profile_groups, key=None, weight=0):
        key = {} if key is None else key
        for group in profile_groups:
            abstracted = self._abstract_reps(group, weight)

            for k, v in abstracted.items():
                key.setdefault(k, ReplacementList(k)).extend(v)
        return key

    def _abstract_reps(self, group, weight=0):
        """Turn groups from a profile data structure (a dictionary with some
        strings and lists) into a dictionary of ReplacementList instances with
        weighted replacements.
        """
        replacements = {}
        for key, values in self.profile[group].items():
            if isinstance(values, str):
                values = [values]
            replacements.setdefault(key, ReplacementList(key)).extend(
                    Replacement(i + weight, v) for i, v in enumerate(values))
        return replacements

    def groups2key(self, key_name, *profile_groups, weight=0, suffix=False):
        """Add a section from the profile into a character group. If any keys
        already exist in the group, their values will be added to a
        ReplacementList.
        """
        treetype = SuffixTree if suffix else Trie
        key = self.keys.setdefault(key_name, treetype())
        self.keymaker(*profile_groups, key=key, weight=weight)

    def basekey2new(self, new_key, *profile_groups, base_key=None, weight=0,
                    suffix=False):
        """create a new key from an existing one where the new profile groups
        override the old ones (groups2key appends)
        """
        treetype = SuffixTree if suffix else Trie
        new_base = copy.deepcopy(self[base_key or self.base_key].dict())
        new_updates = self.keymaker(*profile_groups, weight=weight)
        new_base.update(new_updates)
        self[new_key] = treetype(new_base)

    def definefuzzychar(self, char, character_set, base_key=None):
        base = self[base_key or self.base_key]
        self.fuzzies[char] = [base[c] for c in character_set]

    def generatefuzzy(self, fuzzy_key, fuzzy_reps, base_key=None,
                      weight=0, bad_digraphs=None):
        """implement some kind of fuzzy matching for character classes that
        generates all possible matches ahead of time.
        """
        base = self[base_key or self.base_key]
        # parse fuzzy strings
        fuzzy_key = [i for i in
                     re.split('(' + '|'.join(self.fuzzies) + ')', fuzzy_key)
                     if i]
        if isinstance(fuzzy_reps, str):
            fuzzy_reps = [fuzzy_reps]
        fuzzy_reps = [[i for i in re.split(r'(\d)', r) if i]
                      for r in fuzzy_reps]

        blocks, fuzzies = self._parse_key_blocks(fuzzy_key, base)

        # generate replacement lists (and keys) for each product
        fuzzy_dict = {}
        for keyparts in itertools.product(*blocks):
            key = self._get_sane_key(base, keyparts, bad_digraphs)
            for i, fuzzy_rep in enumerate(fuzzy_reps):
                reps = []
                for block in fuzzy_rep:
                    try:
                        reps.append(keyparts[fuzzies[int(block)]])
                    except ValueError:
                        reps.append(
                            ReplacementList(
                                '', [Replacement(weight+i, block)]))
                replacement = add_reps(reps)
                fuzzy_dict.setdefault(
                    key, ReplacementList(key)).extend(replacement.data)

        return fuzzy_dict

    def _parse_key_blocks(self, fuzzy_key, base):
        """Turn fuzzy_key in to a list of iterables. make a dict that keeps
        track of the indicies of fuzzy characters.
        """
        counter = 1
        fuzzies = {}
        blocks = []
        for i, part in enumerate(fuzzy_key):
            try:
                blocks.append(self.fuzzies[part])
                fuzzies[counter] = i
                counter += 1
            except KeyError:
                blocks.extend([p.key] for p in base.getallparts(part))
        return blocks, fuzzies

    def _get_sane_key(self, base, keyparts, bad_digraphs=None):
        """Helper function for TransKey.generatefuzzy(), so the keys actually
        make sense (i.e. don't create any unintentional digraphs).
        """
        if not bad_digraphs:
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
                newparts.append(bad_digraphs[part + nextpart])
                oldparts[i+1] = ''
            except KeyError:
                newparts.append(part)
        newparts.append(oldparts[-1])
        return ''.join(newparts)

    def fuzzies2key(self, target_key, fuzzy_dict, base_key=None,
                    weight=0, bad_digraphs=None):
        base_key = base_key or self.base_key
        new_fuzzies = {}
        for i, parts in enumerate(fuzzy_dict.items()):
            fuzzy_key, fuzzy_reps = parts
            new_fuzzies.update(self.generatefuzzy(
                fuzzy_key, fuzzy_reps, base_key,
                weight=weight+i, bad_digraphs=None))
        new_fuzzies.update(self[target_key].dict())
        self[target_key] = Trie(new_fuzzies)

    def processor(self, func):
        """decorator to define the process for decoding words. Basicaly just
        sugar for separating concerns.
        """
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            return func(self, *args, **kwargs)
        return wrapped


def get_empty_replist():
    return ReplacementList('', [Replacement(0, '')])


def add_reps(reps):
    """Add together a bunch of ReplacementLists"""
    try:
        return functools.reduce(operator.add, reps)
    except TypeError:
        return get_empty_replist()


if __name__ == '__main__':
    import yaml
    prof = yaml.safe_load(open('../data/new.yml'))
    key = TransKey(prof, 'base', 'consonants', 'vowels', 'other', 'clusters')
    key.groups2key('base', 'infrequent', weight=15)
    key.basekey2new('front', 'beginning')
