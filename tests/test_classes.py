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

@pytest.fixture
def rep1():
    return classes.Replacement(2, 'foo')

@pytest.fixture
def rep2():
    return classes.Replacement(3, 'bar')
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
    assert "k'h" in trie
    assert "k'" not in trie
    assert trie.containsnode("k'")
    copy = trie.copy()
    assert trie.root == copy.root
    assert trie._getnode('sh') is not copy._getnode('sh')


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
    assert "k'h" in suffixtree
    assert "'h" not in suffixtree
    assert suffixtree.containsnode("'h")


def test_replacement_addition(rep1, rep2):
    rep3 = rep1 + rep2
    assert rep3.weight == rep1.weight + rep2.weight
    assert rep3.value == rep1.value + rep2.value


def test_replacement_list_addition(rep1, rep2):
    rlist1 = classes.ReplacementList('baz', [rep1, rep2])
    rlist2 = classes.ReplacementList('spam', [rep2, rep1])
    rlist3 = rlist1 + rlist2
    rlist3.sort()
    assert str(rlist3) == 'bazspam:\n 4 foofoo\n 5 foobar\n 5 barfoo\n 6 barbar'
    rlist4 = classes.add_reps(rlist1, rlist2)
    rlist4.sort()
    assert str(rlist4) == str(rlist3)


# def test_transkey(profile):
#     pass
