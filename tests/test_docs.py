import pathlib
import deromanize as dr
import pytest
import yaml

DIR = pathlib.Path(__file__).parent


def get_prof(name):
    path = DIR / (name + ".yml")
    with path.open(encoding="utf8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture
def basic_keys():
    return dr.KeyGenerator(get_prof("basic"))


def test_base_shalom(basic_keys):
    parts = basic_keys["base"].getallparts("shalom")
    print(parts)
    print("\n%r" % parts[0][0])
    assert (
        repr(parts)
        == "[ReplacementList('sh', [(0, 'ש')]), ReplacementList('a', [(0, '')]), ReplacementList('l', [(0, 'ל')]), ReplacementList('o', [(0, 'ו'), (1, '')]), ReplacementList('m', [(0, 'מ')])]"
    )
    shalom = dr.add_rlists(parts)
    print("\n%r" % shalom)
    assert (
        repr(shalom) == "ReplacementList('shalom', [(0, 'שלומ'), (1, 'שלמ')])"
    )
    print("\n" + repr(str(shalom)))
    print("\n" + str(shalom))
    assert str(shalom) == "shalom:\n 0 שלומ\n 1 שלמ"


def main():
    keys = basic_keys()
    test_base_shalom(keys)


if __name__ == "__main__":
    main()
