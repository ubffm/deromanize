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
import unicodedata
from typing import (
    Callable,
    Dict,
    Set,
    Tuple,
    Iterable,
    Sequence,
    Union,
    List,
    Mapping,
    Optional,
)
from .keygenerator import ReplacementList
import sqlalchemy as sa
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.orm import sessionmaker, relationship, registry

RepKeyValue = Iterable[Tuple[str, str]]


def strip_chars(
    rep_keyvalue: RepKeyValue, chars: Set[str] = set("ieaou")
) -> RepKeyValue:
    """strips all diacritics off of certain chars in a Replacement.keyvalue.
    Returns the update keyvalue.
    """
    new_keyvalue = []
    for source, target in rep_keyvalue:
        new = ""
        for c in source:
            decomposed = unicodedata.normalize("NFD", c)
            if decomposed[0] in chars:
                new += decomposed[0]
            else:
                new += c
        new_keyvalue.append((new, target))
    return new_keyvalue


CONV_TEMP = "{!r} -> {!r}"


def replacer_maker(
    simple_replacements: Dict[str, str],
    pair_replacements: Dict[str, Sequence[str]],
) -> Callable[[RepKeyValue], RepKeyValue]:
    """returns a function which takes a Replacement.keyvalue and returns a new
    keyvalue which adheres to a new keyvalue where the Romanized part adheres
    to a new standard.

    - simple_replacements is a mapping where the key is the romanized source
      token, and the value is the romanized token in the target standard.

    - pair_replacements is reversed. The key is a the romanized token in the
      target standard, and the value is a pair of strings in which the
      romanized token in the source transcription is the first item and the
      second item is the orignal script. The reason for this reversal is to
      support storing this mapping in json or other serialization formats which
      only support strings as keys. Sorry that it's weird.

    The pair replacements in particular allow for producing *corrected* forms
    of transcription where human error may have occured.
    """
    pair_reps = {tuple(v): k for k, v in pair_replacements.items()}
    pairs_str = "\n".join(CONV_TEMP.format(k, v) for k, v in pair_reps.items())
    simple_str = "\n".join(
        CONV_TEMP.format(k, v) for k, v in simple_replacements.items()
    )

    def replace(rep_keyvalue: RepKeyValue) -> RepKeyValue:
        """takes a RepKeyValue as an argument and returns a new one with
        different romanized values.

        first, matching pairs are substituted:

        {pairs}

        Then, simple replaments are preformed:

        {simple}
        """.format(
            pairs=pairs_str, simple=simple_str
        )
        new_keyvalue = []
        for pair in rep_keyvalue:
            target = pair[1]
            if pair in pair_reps:
                new_keyvalue.append((pair_reps[pair], target))
            else:
                new = pair[0]
                for k, v in simple_replacements.items():
                    new = new.replace(k, v)
                new_keyvalue.append((new, target))
        return new_keyvalue

    return replace


def get_combos(rep_key: Mapping[str, ReplacementList]) -> Set[Tuple[str, str]]:
    """return a set of all keyvalue pairs generated by a standard."""
    return set(
        pair for replist in rep_key.values() for rep in replist for pair in rep.keyvalue
    )


CacheStorageDict = Dict[str, Dict[str, int]]


class CacheObject:
    """creates cache objects to track numbers of occurances of certain word
    pairs.
    """

    def __init__(self, seed: Optional[CacheStorageDict] = None):
        if seed:
            self.data = seed
        else:
            self.data = {}

    def add(self, source: str, target: str, count: Union[int, str] = 1) -> None:
        count = int(count)
        current = self.data.setdefault(source, {}).setdefault(target, 0)
        self.data[source][target] = current + count

    def update(self, matches: Iterable[Tuple[str, str, Union[int, str]]]) -> None:
        for row in matches:
            self.add(*row)

    def __getitem__(
        self, value: Union[str, Tuple[str, str]]
    ) -> Union[Dict[str, int], int]:

        if isinstance(value, tuple):
            return self.data[value[0]][value[1]]
        return self.data[value]

    def get(
        self,
        value: Union[str, Tuple[str, str]],
        default: Union[Dict[str, int], int, None] = None,
    ) -> Union[Dict[str, int], int, None]:

        try:
            return self[value]
        except KeyError:
            return default

    def __iter__(self):
        for source, targets in self.data.items():
            for target, count in targets.items():
                yield source, target, count

    def inverted(self, new=None):
        if new is None:
            new = CacheObject()
        for source, target, count in self:
            new.add(target, source, count)
        return new

    def serializable(self):
        return self.data


mapper_registry = registry()


class Base(metaclass=DeclarativeMeta):
    __abstract__ = True

    # these are supplied by the sqlalchemy2-stubs, so may be omitted
    # when they are installed
    registry = mapper_registry
    metadata = mapper_registry.metadata

    def __repr__(self):
        name = self.__class__.__name__
        attrs = (
            "%s=%r" % (attr, getattr(self, attr))
            for attr in self._sa_class_manager.keys()
            if not (attr[-2:] == "id" or isinstance(getattr(self, attr), list))
        )
        return name + "(%s)" % ", ".join(attrs)


class Source(Base):
    __tablename__ = "sources"
    id = sa.Column(sa.Integer, primary_key=True)
    address = sa.Column(sa.String, index=True)
    match_id = sa.Column(sa.Integer, sa.ForeignKey("matches.id"))

    match: "Match" = relationship("Match", back_populates="sources")


class Match(Base):
    __tablename__ = "matches"
    id = sa.Column(sa.Integer, primary_key=True)
    original_id = sa.Column(sa.Integer, sa.ForeignKey("original.id"))
    romanized_id = sa.Column(sa.Integer, sa.ForeignKey("romanized.id"))
    count = sa.Column(sa.Integer)

    original: "Original" = relationship("Original", back_populates="matches")
    romanized: "Romanized" = relationship("Romanized", back_populates="matches")
    sources: List["Source"] = relationship("Source", back_populates="match")


sa.Index("matches_idx", Match.original_id, Match.romanized_id, unique=True)


class Standard(Base):
    __tablename__ = "standards"
    id = sa.Column(sa.Integer, primary_key=True)
    st = sa.Column(sa.String, index=True, unique=True)


class Original(Base):
    __tablename__ = "original"
    id = sa.Column(sa.Integer, primary_key=True)
    form = sa.Column(sa.String, index=True, unique=True)

    matches: List["Match"] = relationship("Match", back_populates="original")


class Romanized(Base):
    __tablename__ = "romanized"
    id = sa.Column(sa.Integer, primary_key=True)
    form = sa.Column(sa.String, index=True)
    standard_id = sa.Column(sa.Integer, sa.ForeignKey("standards.id"))

    standard: Standard = relationship(Standard)
    matches: List["Match"] = relationship("Match", back_populates="romanized")


sa.Index("standard_form", Romanized.form, Romanized.standard_id, unique=True)


class DBWrapper:
    def __init__(self, sqlachemy_url, echo=False):
        self.engine = sa.create_engine(sqlachemy_url, echo=echo)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        with self:
            Base.metadata.create_all(self.engine)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if type:
            self.session.rollback()
        else:
            self.session.commit()

    def get(self, orig=None, rom=None, standard=None):
        args = []
        if orig:
            args.append(Original.form == orig)
        if rom:
            args.append(Romanized.form == rom)
        if standard:
            args.append(Standard.st == standard)

        query = (
            self.session.query(Match, Romanized, Standard, Original)
            .join(Romanized, Romanized.id == Match.romanized_id)
            .join(Standard)
            .join(Original)
            .filter(*args)
        )
        if orig and rom and standard:
            return query.first()
        else:
            return query

    def construct_match(self, orig, rom, standard):
        original = self.session.query(Original).filter(
            Original.form == orig
        ).first() or Original(form=orig)
        romanized = (
            self.session.query(Romanized)
            .join(Standard)
            .filter(Romanized.form == rom, Standard.st == standard)
            .first()
        )
        if not romanized:
            st = self.session.query(Standard).filter(
                Standard.st == standard
            ).first() or Standard(st=standard)
            romanized = Romanized(form=rom, standard=st)

        return Match(original=original, romanized=romanized, count=1)

    def add(self, orig, rom, standard, count=1, source=None):
        match = self.get(orig, rom, standard)
        if match:
            match = match[0]
            match.count += count
            if source:
                self.session.add(Source(address=source, match_id=match.id))
        else:
            match = self.construct_match(orig, rom, standard)
            if source:
                match.sources = [Source(address=source)]
            self.session.add(match)

    def __iter__(self):
        query = (
            self.session.query(Original.form, Romanized.form, Standard.st, Match.count)
            .join(Match)
            .join(Romanized)
            .join(Standard)
        )
        yield from query

    def mkcache(self, standard, seed=None):
        return CacheDB(self, standard, seed)


class CacheDB(CacheObject):
    def __init__(self, db_wrapper, standard, seed=None):
        if isinstance(db_wrapper, DBWrapper):
            self.db = db_wrapper
        else:
            self.db = DBWrapper(db_wrapper)

        self.standard = standard

    def add(self, source, target, count=1, addr=None):
        self.db.add(target, source, self.standard, count, addr)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.db.__exit__(*args)

    def __iter__(self):
        query = self.db.get(standard=self.standard)
        return ((r.form, o.form, m.count) for m, r, s, o in query)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            return self.db.get(key[1], key[0], self.standard)[0].count
        results = self.db.get(rom=key, standard=self.standard)
        return {o.form: m.count for m, r, s, o in results}

    def get_target(self, key):
        results = self.db.get(key, standard=self.standard)
        return {r.form: m.count for m, r, s, o in results}

    def serializable(self) -> Dict[str, Dict[str, int]]:
        obj = CacheObject()
        obj.update(self)
        return obj.data
