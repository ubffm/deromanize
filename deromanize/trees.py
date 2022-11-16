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
"""Prefix trees with dictionary-like interfaces"""
import copy
from collections import abc
from typing import Optional


class Trie:
    """a prefix tree for dealing with transliteration standards with digraphs.
    This could just be a dictionary if there weren't digraphs in
    transliteration standards.

    In addition to optionally being initialized with a dictionary, it supports
    a lot of the same methods and behaviors as a dictionary, along with special
    methods for use with transliteration stuff.
    """

    __slots__ = "root", "_len"

    def __init__(self, initializer=None):
        """Trie([initializer])

        The optional initializer parameter may be used to create a prefix tree
        the same way it is used to create a dictionary (argument should be a
        dictionary or an iterable with two-tuples.
        """
        self.root = [..., {}]
        self._len = 0
        if initializer is not None:
            self.update(initializer)

    def clear(self):
        self.root[1].clear()

    def __bool__(self):
        return bool(self.root[1])

    def __eq__(self, other):
        return self.items() == other.items()

    def __ne__(self, other):
        return self.items() != other.items()

    def _mknode(self, key):
        node = self.root
        for char in key:
            node = node[1].setdefault(char, [..., {}])
        return node

    def __setitem__(self, key: str, value):
        """follow (and generate, if needed) all neccesary intermediate nodes to
        create a new endpoint.
        """
        node = self._mknode(key)
        if node[0] is ...:
            self._len += 1
        node[0] = value

    def setdefault(self, key, default=None):
        node = self._mknode(key)
        if node[0] is ...:
            self._len += 1
            node[0] = default
            return default

        return node[0]

    def update(self, mapping):
        for k, v in mapping.items():
            self[k] = v

    def _getnode(self, key: str):
        """get a node out of the internal prefix tree. An implementation
        detail.
        """
        node = self.root
        for char in key:
            node = node[1][char]
        return node

    def __getitem__(self, key: str):
        node = self._getnode(key)
        if node[0] is ...:
            raise KeyError(key)
        return node[0]

    def get(self, key: str, default):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.dict())

    def getstack(self, key: str):
        """given a key, return a tuple containing the final node along with a
        stack of all the parent nodes (starting from the root). This stack is a
        list of tuples where the first item is the node itself and the second
        is the key that leads to the child. The only reason this function
        exists is so the __delitem__ function could be written, so
        MutableMapping could be leveraged as base class. Still, might be other
        interesting things to do with a stack of nodes.
        """
        node = self.root
        stack = []
        for char in key:
            stack.append((node, char))
            node = node[1][char]
        return node, stack

    def pop(self, key: str):
        node, stack = self.getstack(key)
        val = node[0]
        if val is ...:
            raise KeyError(key)
        self._len -= 1
        node[0] = ...

        for parent, key in reversed(stack):
            node = parent[1][key]
            if node[0] is ... and not node[1]:
                del parent[1][key]
            else:
                break
        return val

    def popitem(self):
        try:
            k, v = next(iter(self))
        except StopIteration:
            raise KeyError(self.__class__.__name__ + " is empty")
        del self[k]
        return k, v

    def __delitem__(self, key: str):
        self.pop(key)

    def containsnode(self, key: str):
        """check if a node on the tree exists without regard for whether it
        contains anything.
        """
        try:
            self._getnode(key)
        except KeyError:
            return False
        return True

    def items(self, prefix: Optional[str] = None):
        """return a generator yielding all keys and values with valid endpoints.
        "prefix" argument is provided, yield all keys and values where the key
        starts with "prefix".

        This method traverses the tree structure with call-stack recursion, so
        it isn't the cheapest thing ever, on the other hand, it's lazy, so, eh.
        """
        if prefix:
            topnode = self._getnode(prefix)
            keypart = prefix
        else:
            topnode = self.root
            keypart = ""
        return self._itemize(topnode, keypart)

    def _itemize(self, topnode, keypart: str = ""):
        """traverse the tree recursively and get spit out the non-empty nodes
        along the way.
        """
        for key, node in topnode[1].items():
            newkeypart = keypart + key
            if node[0] is not ...:
                yield (newkeypart, node[0])
            yield from self._itemize(node, newkeypart)

    def keys(self, prefix: Optional[str] = None):
        """Return an generator (not a dict view!) with all keys. optional
        `prefix` argument limits results to keys beginning with the given
        prefix.
        """
        return (k for k, _ in self.items(prefix))

    __iter__ = keys

    def values(self, prefix: Optional[str] = None):
        """Return an generator (not a dict view!) with all values. optional
        `prefix` argument limits results to keys beginning with the given
        prefix.
        """
        return (v for _, v in self.items(prefix))

    def __len__(self):
        return self._len

    def copy(self):
        """make a copy of the prefix tree. Note that, unlike builtins, this is
        a deep copy, because that is the only sane way to copy a tree. Be aware
        that it's not the cheapest operation.
        """
        new = type(self)()
        new.root = copy.deepcopy(self.root)
        new._len = self._len
        return new

    def dict(self, prefix: Optional[str] = None):
        """return a dictionary from the prefix tree. optional `prefix` argument
        limits results to keys beginning with the given prefix.
        """
        return dict(self.items(prefix))

    def getpart(self, key: str):
        """takes a key and matches as much of it as possible. returns a tuple
        containing the value of the node and the remainder of the key.
        """
        node = self.root
        value = ...
        remainder = key
        for i, char in enumerate(key):
            try:
                node = node[1][char]
            except KeyError:
                break

            if node[0] is not ...:
                value, remainder = node[0], key[i + 1 :]

        if value is ...:
            raise KeyError(key)
        else:
            return value, remainder

    def getallparts(self, key: str):
        """loop over a string, splitting the input string up by longest
        possible matches.
        """
        results = []
        remainder = key
        while remainder:
            value, remainder = self.getpart(remainder)
            results.append(value)
        return results

    def serializable(self):
        root = self.copy().root
        self._put_none(root)
        return root

    def _put_none(self, node):
        if node[0] is ...:
            node[0] = None
        for node in node[1].values():
            self._put_none(node)


abc.MutableMapping.register(Trie)


class BackTrie(Trie):
    """Subclass of Trie that takes it from the back. I used to call this a
    suffix tree, but I've since learned that that is incorrect.
    """

    __slots__ = ()

    def _mknode(self, key: str):
        return super()._mknode(key[::-1])

    def _getnode(self, key: str):
        return super()._getnode(key[::-1])

    def getstack(self, key: str):
        return super().getstack(key[::-1])

    def getpart(self, key: str):
        value, remainder = super().getpart(key[::-1])
        return value, remainder[::-1]

    def items(self, key: Optional[str] = None):
        return ((k[::-1], v) for k, v in super().items(key))

    def getallparts(self, key: str):
        return super().getallparts(key)[::-1]
