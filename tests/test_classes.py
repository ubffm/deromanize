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
    assert trie.getpart('shalom') == (profile['sh'], 'alom')
    assert trie.getallparts('shalom') == [profile['sh'],
                                          profile['a'],
                                          profile['l'],
                                          profile['o'],
                                          profile['m']]


def test_trie_integ(profile, trie):
    assert dict(trie.items()) == profile


def test_suffixtree(profile, suffixtree):
    assert suffixtree['sh'] == profile['sh']
    assert suffixtree['a'] == profile['a']
    assert dict(suffixtree.items()) == profile
    assert suffixtree.getpart('shalom') == (profile['m'], 'shalo')
    assert suffixtree.getallparts('shalom') == [profile['sh'],
                                                profile['a'],
                                                profile['l'],
                                                profile['o'],
                                                profile['m']]

# def test_replacement(
