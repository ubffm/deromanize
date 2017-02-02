#!/usr/bin/env python3
import sys
import unittest
from functools import reduce
from operator import add
from deromanize import classes
import yaml

PROFILE = yaml.safe_load(open('../data/new.yml'))


class TrieCorrect(unittest.TestCase):
    def setUp(self):
        self.profile = PROFILE['consonants']
        self.profile.update(PROFILE['vowels'])
        self.profile.update(PROFILE['clusters'])
        self.trie = classes.Trie(self.profile)

    def testtrie(self):
        self.assertEqual(dict(self.trie.items()), self.profile)

    def testget(self):
        self.assertEqual(self.trie['sh'], self.profile['sh'])
        self.assertEqual(self.trie['a'], self.profile['a'])
        with self.assertRaises(KeyError):
            self.trie['']
        self.assertIs(self.trie._getnode('')[0], classes.empty)
        self.assertIs(self.trie._getnode(''), self.trie.root)

# def main():

#     key = classes.TransKey(profile)
#     key.key2group('consonants', 'normal')
#     key.key2group('vowels', 'normal')
#     key.key2group('clusters', 'normal')

#     parts = key['normal'].getallparts(sys.argv[1])
#     word = reduce(add, parts)
#     print(word)

if __name__ == '__main__':
    unittest.main()
