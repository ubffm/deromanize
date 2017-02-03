#!/usr/bin/env python3
import sys
from functools import reduce
from operator import add
from deromanize import classes
import pytest
import yaml

PROFILE = yaml.safe_load(open('../data/new.yml'))


def getbasesdict(*groups):
    new_dict = {}
    for group in groups:
        new_dict.update(PROFILE[group])
    return new_dict


####################
@pytest.fixture
def profile():
    return getbasesdict('consonants', 'vowels', 'clusters')


@pytest.fixture
def trie():
    return classes.Trie(profile())


@pytest.fixture
def suffixtree():
    return classes.SuffixTree(profile())
#####################


def test_trie_getting(profile, trie):
    assert trie['sh'] == profile['sh']
    assert trie['a'] == profile['a']
    with pytest.raises(KeyError):
        trie['']
    assert trie._getnode('') is trie.root


def test_trie_integ(profile, trie):
    assert dict(trie.items()) == profile


def test_suffixtree_getting(profile, suffixtree):
    assert suffixtree['sh'] == profile['sh']
    assert suffixtree['a'] == profile['a']
    assert dict(suffixtree.items()) == profile
