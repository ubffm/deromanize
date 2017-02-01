#!/usr/bin/env python3
from deromanize import classes
from functools import reduce
from operator import add
import yaml

def main():
    profile = yaml.safe_load(open('../data/new.yml'))

    key = classes.TransKey(profile)
    key.key2group('consonants', 'normal')
    key.key2group('vowels', 'normal')

    parts = key['normal'].getallparts('shalom')
    word = reduce(add, parts)
    print(word)

if __name__ == '__main__':
    main()
