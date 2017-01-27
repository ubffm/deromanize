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
import copy
import collections


class _Empty:
    def __repr__(self):
        return "Empty"

empty = _Empty()


class TrieInitializationError(Exception): pass


class Trie:
    """a prefix tree for dealing with transliteration standards with digraphs.
    This could just be a dictionary if there weren't digraphs in
    transliteration standards.

    In addition to optionally being initialized with a dictionary, it supports
    a lot of the same methods and behaviors as a dictionary, along with special
    methods for use with transliteration stuff.
    """
    def __init__(self, dictionary=None):
        """Trie([dict])

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
        return 'Trie(%r)' % dict(self.items())

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

    def getpart(self, key):
        """takes a key and matches as much of it as possible. returns a tuple
        containing: (value of the node, part of the key that matched, the
        remainder of the key)
        """
        node = self.root
        for i, char in enumerate(key):
            try:
                node = node[1][char]
            except KeyError:
                if node is self.root or node[0] is empty:
                    raise
                else:
                    return node[0], key[i:]


        if node[0] is empty:
            raise KeyError(matched_key)
        else:
            return node[0], ''

    def getallparts(self, key):
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
        return 'SuffixTree(%r)' % dict(self.items())

    def __setitem__(self, key, value):
        super().__setitem__(key[::-1], value)

    def _getnode(self, key):
        return super()._getnode(key[::-1])

    def getpart(self, key):
        value, remainder = super().getpart(key[::-1])
        return value, remainder[::-1]

    def items(self, key=None):
        return ((k[::-1], v) for k, v in super().items(key))


class Replacement:
    """a type for holding a replacement and it's weight. A Replacment on its
    own doesn't know what it's replacing. It should be an item in a
    ReplacmentList.
    """
    def __init__(self, weight: int, value: str):
        self.weight, self.value = weight, value

    def __add__(self, other):
        return Replacement(self.weight + other.weight, self.value + other.value)

    def __repr__(self):
        return "Replacement({!r}, {!r})".format(self.weight, self.value)


class ReplacementList(collections.UserList):
    """a list of Replacements with a .key attribute containing the key to which
    they belong
    """
    def __init__(self, key, values: list=None):
        self.key = key
        self.data = values if values is not None else []

    def __add__(self, other):
        key = self.key + other.key
        composite_values = ReplacementList(key)

        for value in self:
            composite_values.extend(value + v for v in other)

        return composite_values

    def __repr__(self):
        return "ReplacementList({!r}, {!r})".format(self.key, self.data)


class TransKey:
    """an object to build up a transliteration key from a config file. (--or
    rather, serialized data unmarshalled from a config file.)
    """
    def __init__(self, profile):
        self.profile = profile
        self.consonants = set(profile['consonants'])
        self.vowels = set(profile['vowels'])
        self.chars = self.vowels | self.consonants

        self.groups = {}

    def __setitem__(self, key, value):
        self.groups[key] = value

    def __getitem__(self, key):
        return self.groups[key]

    def key2group(self, profile_key, group, weight=0):
        """Add a section from the profile into a character group
        """
        abstracted = abstract_reps(key, weight)
        group = self.groups.setdefault(key, Trie())

        for k, v in abstracted.items():
            group.setdefault(k, []).extend[v]





def abstract_reps(dictionary, weight=0):
    replacements = {}
    for key, values in dictionary.items():
        if isinstance(values, str):
            values = [values]
        replacements.setdefault(key, ReplacementList(key)).extend(
                Replacement(i + weight, v) for i, v in enumerate(values))

    return replacements

import yaml
