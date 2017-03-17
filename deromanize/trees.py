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
from collections import abc


class Empty:
    def __repr__(self):
        return "empty"

    def __eq__(self, other):
        return isinstance(other, Empty)


empty = Empty()


class Trie(abc.MutableMapping):
    """a prefix tree for dealing with transliteration standards with digraphs.
    This could just be a dictionary if there weren't digraphs in
    transliteration standards.

    In addition to optionally being initialized with a dictionary, it supports
    a lot of the same methods and behaviors as a dictionary, along with special
    methods for use with transliteration stuff.
    """
    template = 'Trie(%r)'

    def __init__(self, dictionary=None):
        """Trie([dictionary])

        The optional dictionary parameter may be used to create a prefix tree
        with all nodes based on the dictionary keys, and all vaules as
        endpoints
        """
        self.root = [empty, {}]
        if dictionary is not None:
            self.update(dictionary)

    def __bool__(self):
        return bool(self.root[1])

    def __setitem__(self, key, value):
        """follow (and generate, if needed) all neccesary intermediate nodes to
        create a new endpoint.
        """
        node = self.root
        for char in key:
            node = node[1].setdefault(char, [empty, {}])

        node[0] = value

    def __repr__(self):
        return self.template % self.dict()

    def _getnode(self, key):
        """get a node out of the internal prefix tree. An implementation
        detail.
        """
        node = self.root
        for char in key:
            node = node[1][char]
        return node

    def _getstack(self, key):
        node = self.root
        stack = []
        for char in key:
            stack.append((node, char))
            node = node[1][char]
        return stack, node

    def __getitem__(self, key):
        node = self._getnode(key)
        if node[0] == empty:
            raise KeyError(key)
        return node[0]

    def __delitem__(self, key):
        stack, node = self._getstack(key)
        if node[0] == empty:
            raise KeyError(key)
        node[0] = empty

        for parent, key in reversed(stack):
            node = parent[1][key]
            if node[0] == empty and not node[1]:
                del parent[1][key]
            else:
                break

    def containsnode(self, key):
        """check if a node on the tree exists without regard for whether it
        contains anything.
        """
        try:
            self._getnode(key)
        except KeyError:
            return False
        return True

    def items(self):
        """return a generator yielding all keys and values with valid
        endpoints. if "key" argument is provided, yield all keys and values
        where the key starts with "key".

        This method traverses the tree structure with call-stack recursion, so
        it isn't the cheapest thing ever, on the other hand, it's lazy, so, eh.
        """
        return self._itemize(self.root)

    def _itemize(self, topnode, keypart=''):
        for key, node in topnode[1].items():
            newkeypart = keypart + key
            if node[0] != empty:
                yield (newkeypart, node[0])
            yield from self._itemize(node, newkeypart)

    def __iter__(self):
        return (k for k, _ in self.items())

    def values(self):
        return (v for _, v in self.items())

    def __len__(self):
        return len(list(self.__iter__()))

    def copy(self):
        """make a copy of the prefix tree. Note that, unlike builtins, this is
        a deep copy, because that is the only sane way to copy a tree. Be aware
        that it's not the cheapest operation.
        """
        new = type(self)()
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
                if value == empty:
                    raise
                else:
                    return value, remainder

            if node[0] != empty:
                value, remainder = node[0], key[i+1:]

        if value == empty:
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
    """Subclass of Trie that takes it from the back."""
    template = 'SuffixTree(%r)'

    def __setitem__(self, key, value):
        super().__setitem__(key[::-1], value)

    def _getnode(self, key):
        return super()._getnode(key[::-1])

    def _getstack(self, key):
        return super._getstack(key[::-1])

    def getpart(self, key):
        value, remainder = super().getpart(key[::-1])
        return value, remainder[::-1]

    def items(self):
        return ((k[::-1], v) for k, v in super().items())

    def getallparts(self, key):
        return super().getallparts(key)[::-1]
