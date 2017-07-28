import unicodedata


def strip_chars(rep_keyvalue, chars=set('ieaou')):
    for source, target in rep_keyvalue:
        new = ''
        for c in source:
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


class CacheObject:
    def __init__(self, seed=None):
        if isinstance(seed, dict):
            self.data = seed
        else:
            self.data = {}
            if seed:
                for row in seed:
                    self.add(*row)

    def __setitem__(self, source, target):
        self.add(source, target)

    def add(self, source, target, count=1):
        current = self.data.setdefault(source, {}).setdefault(target, 0)
        self.data[source][target] = current + count

    def __getitem__(self, value):
        if isinstance(value, tuple):
            return self.data[value[0]][value[1]]
        return self.data[value]

    def __iter__(self):
        for source, targets in self.data.items():
            for target, count in targets.items():
                yield source, target, count

    def inverted(self):
        new = CacheObject()
        for source, target, count in self:
            new.add(target, source, count)
        return new

    def serializable(self):
        return self.data


class CacheDB(CacheObject):
    def __init__(self, connection, seed=None, table='cache'):
        self.con = connection
        self.cur = connection.cursor()
        self.table = table
        with self:
            self.cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS ? (
                    source VARCHAR,
                    target VARCHAR,
                    count INTEGER,
                    PRIMARY KEY (source, target)
                )
                ''', (table,))
        if isinstance(seed, dict):
            seed = CacheObject(seed)

        if seed:
            with self:
                for row in seed:
                    self.add(*row)
