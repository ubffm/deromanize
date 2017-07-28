import unicodedata


def strip_chars(rep_keyvalue, chars=set('ieaou')):
    for orig, target in rep_keyvalue:
        new = ''
        for c in orig:
            decomposed = unicodedata.normalize('NFD', c)
            if decomposed[0] in chars:
                new += decomposed[0]
            else:
                new += c
        yield new, target


def replacer_maker(simple_replacements, pair_replacements):
    set_reps = {tuple(v): k for k, v in pair_replacements.items()}

    def replace(rep_keyvalue):
        for pair in rep_keyvalue:
            target = pair[1]
            if pair in set_reps:
                yield set_reps[pair], target
            else:
                new = pair[0]
                for k, v in simple_replacements.items():
                    new = new.replace(k, v)
                yield new, target

    return replace


def get_combos(rep_key):
    return set(
        pair
        for replist in rep_key.values()
        for rep in replist
        for pair in rep.keyvalue)
