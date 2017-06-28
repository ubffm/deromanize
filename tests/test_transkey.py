#!/usr/bin/env pytest
import deromanize
import pytest
import yaml
from deromanize import trees


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
    return trees.Trie(profile())


@pytest.fixture
def suffixtree():
    return trees.BackTrie(profile())


@pytest.fixture
def rep():
    return (deromanize.Replacement(2, 'foo'),
            deromanize.Replacement(3, 'bar'),
            deromanize.Replacement(4, 'spam'),
            deromanize.Replacement(5, 'eggs'))


@pytest.fixture
def key():
    key = deromanize.KeyGenerator(PROFILE)
    return key

#####################


def test_trie_getting(profile, trie):
    assert trie['sh'] == profile['sh']
    assert trie['a'] == profile['a']
    with pytest.raises(KeyError):
        trie['']
    assert trie._getnode('') is trie.root
    assert trie.getpart('shalom') == (profile['sh'], 'alom')
    assert trie.getallparts('shalom') == [
        profile['sh'],
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
    rlist1 = deromanize.ReplacementList('baz', [rep[0], rep[1]])
    rlist2 = deromanize.ReplacementList('fjords', [rep[2], rep[3]])
    rlist3 = rlist1 + rlist2
    rlist3.sort()
    print(rlist3)
    assert str(rlist3) == (
            'bazfjords:\n 6 foospam\n 7 fooeggs\n 7 barspam\n 8 bareggs')
    rlist4 = deromanize.add_reps((rlist1, rlist2))
    rlist4.sort()
    assert str(rlist4) == str(rlist3)


def test_transkey(key):
    rep = deromanize.add_reps(key['base'].getallparts('shalom'))
    print(rep)
    assert str(rep) == 'shalom:\n 0 שלומ\n 1 שלמ'
    rep = deromanize.add_reps(key['end'].getallparts('shalom'))
    assert isinstance(key['end'], trees.BackTrie)
    print(rep)
    assert str(rep) == 'shalom:\n 0 שלום'


def test_pattern_gen(key):
    pass
