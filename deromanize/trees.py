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


class Empty:
    """Just a silly class that doesn't do anything but hold empty
    places. That's probably None's job, but, eh, since None is a valid value
    that could be in a dictionary, decided to whip up something else.
    """
    def __repr__(self):
        return "empty"

    def __eq__(self, other):
        return isinstance(other, Empty)

    def __copy__(self, *args):
        return self

    __deepcopy__ = __copy__


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

    def __init__(self, initializer=None):
        """Trie([initializer])

        The optional initializer parameter may be used to create a prefix tree
        the same way it is used to create a dictionary (argument should be a
        dictionary or an iterable with two-tuples.
        """
        self.root = [empty, {}]
        self._len = 0
        if initializer is not None:
            self.update(initializer)

    def __bool__(self):
        return bool(self.root[1])

    def __setitem__(self, key, value):
        """follow (and generate, if needed) all neccesary intermediate nodes to
        create a new endpoint.
        """
        node = self.root
        for char in key:
            node = node[1].setdefault(char, [empty, {}])
        if node[0] is empty:
            self._len += 1
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

    def getstack(self, key):
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

    def __getitem__(self, key):
        node = self._getnode(key)
        if node[0] is empty:
            raise KeyError(key)
        return node[0]

    def __delitem__(self, key):
        node, stack = self.getstack(key)
        if node[0] is empty:
            raise KeyError(key)
        self._len -= 1
        node[0] = empty

        for parent, key in reversed(stack):
            node = parent[1][key]
            if node[0] is empty and not node[1]:
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

    def items(self, prefix=None):
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
            keypart = ''
        return self._itemize(topnode, keypart)

    def _itemize(self, topnode, keypart=''):
        """traverse the tree recursively and get spit out the non-empty nodes
        along the way.
        """
        for key, node in topnode[1].items():
            newkeypart = keypart + key
            if node[0] is not empty:
                yield (newkeypart, node[0])
            yield from self._itemize(node, newkeypart)

    def keys(self, prefix=None):
        """Return an generator (not a dict view!) with all keys. optional
        `prefix` argument limits results to keys beginning with the given
        prefix.
        """
        return (k for k, _ in self.items(prefix))

    __iter__ = keys

    def values(self, prefix=None):
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

    def dict(self, prefix=None):
        """return a dictionary from the prefix tree. optional `prefix` argument
        limits results to keys beginning with the given prefix.
        """
        return dict(self.items(prefix))

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

    def serializable(self):
        root = self.copy().root
        self._put_none(root)
        return root

    def _put_none(self, node):
        if node[0] is empty:
            node[0] = None
        for node in node[1].values():
            self._put_none(node)


class BackTrie(Trie):
    """Subclass of Trie that takes it from the back. I used to call this a
    suffix tree, but I've since learned that that is incorrect.
    """
    template = 'BackTrie(%r)'

    def __setitem__(self, key, value):
        super().__setitem__(key[::-1], value)

    def _getnode(self, key):
        return super()._getnode(key[::-1])

    def getstack(self, key):
        return super._getstack(key[::-1])

    def getpart(self, key):
        value, remainder = super().getpart(key[::-1])
        return value, remainder[::-1]

    def items(self, key=None):
        return ((k[::-1], v) for k, v in super().items(key))

    def getallparts(self, key):
        return super().getallparts(key)[::-1]
