import sys
from functools import reduce
from operator import add
from deromanize import classes
import pytest
import yaml

# PROJECT_DIR = os.path.dirname(os.path.dirname(deromanize.__file__))
# CONFIG_FILE = os.path.join(PROJECT_DIR, 'data', 'test.yml')
PROFILE = yaml.safe_load(open('test.yml'))


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
def rep():
    return (classes.Replacement(2, 'foo'),
            classes.Replacement(3, 'bar'),
            classes.Replacement(4, 'spam'),
            classes.Replacement(5, 'eggs'))

@pytest.fixture
def basekey():
    key = classes.TransKey(PROFILE)
    key.groups2key('base', 'consonants', 'vowels', 'clusters')
    return key

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


def test_replacement_addition(rep):
    rep3 = rep[0] + rep[1]
    assert rep3.weight == rep[0].weight + rep[1].weight
    assert rep3.value == rep[0].value + rep[1].value


def test_replacement_list_addition(rep):
    rlist1 = classes.ReplacementList('baz', [rep[0], rep[1]])
    rlist2 = classes.ReplacementList('fjords', [rep[2], rep[3]])
    rlist3 = rlist1 + rlist2
    rlist3.sort()
    print(rlist3)
    assert str(rlist3) == (
            'bazfjords:\n 6 foospam\n 7 fooeggs\n 7 barspam\n 8 bareggs')
    rlist4 = classes.add_reps((rlist1, rlist2))
    rlist4.sort()
    assert str(rlist4) == str(rlist3)


def test_transkey(basekey):
    rep = classes.add_reps(basekey['base'].getallparts('shalom'))
    print(rep)
    assert str(rep) == 'shalom:\n 0 שלומ\n 1 שלמ'
    basekey.basekey2new('base', 'endings', 'final', endings=True)
    rep = classes.add_reps(basekey['endings'].getallparts('shalom'))
    assert isinstance(basekey['endings'], classes.SuffixTree)
    print(rep)
    assert str(rep) == 'shalom:\n 0 שלום'
