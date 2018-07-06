import deromanize as dr
import functools
cfg = dr.Config()
keys = cfg.from_schema('new')
dec = functools.partial(dr.front_mid_end_decode, keys)


def test_mishna():
    mishnah = dec('mishnah')
    print()
    print(mishnah)
    assert mishnah.key == 'mishnah'
    assert len(mishnah) == 2
    for rep in mishnah:
        assert rep.key == 'mishnah'
        print(rep.keyvalue)
    rep1, rep2 = mishnah
    assert rep1.str == 'משנה'
    assert rep2.str == 'מישנה'
