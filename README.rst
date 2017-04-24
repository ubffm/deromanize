Deromanize
==========
``deromanize`` is a set of tools to aid in converting Romanized text
back into original scripts.

.. contents::

Basic usage
-----------
The first step in working with ``deromanize`` is defining your decoding
keys in data through a profile.

A profile has fairly simple format. It is a dictionary which contains
dictionaries that have all the information needed to build up
transliteration rules. It can easily be stored as JSON or any format
can represent the same data structures as JSON. I like to use YAML
because it's easy to write.

The profile should contain at least one character group (the example
below has two) and a ``keys`` section.

.. code:: yaml

 keys:
   base:
     - consonants
     - vowels

 consonants:
  ʾ: א
  b: ב
  v: ב
  g: ג
  d: ד
  h: ה
  ṿ: [וו, ו]
  z: ז
  ḥ: ח
  ṭ: ט
  y: [יי, י]
  k: כ
  kh: כ
  l: ל
  m: מ
  n: נ
  s: ס
  ʿ: ע
  p: פ
  f: פ
  ts: צ
  ḳ: ק
  r: ר
  ś: ש
  sh: ש
  t: ת

 vowels:
  i: י
  e: ['', י]
  a: ''
  o: [ו, '']
  u: ו

Note:
  The letters in the arrays are reversed on this web page when viewed in
  most modern web browsers because of automatic bidi resolution. Most
  editors also pull these shenanigans, which is great for text, but not
  great for code. Emacs has options for this, and Vim doesn't even try
  to fix bidi (though your terminal might). I don't know what kind of
  options your favorite editor has for falling back to "stupid" LTR text
  flow when it screws up code readability.

Character groups:

Each character group is a dictionary containing the Romanized form
character as a key, and the original form as the value. If a Romanized
key can have multiple possible interpretations, they may be put in
lists. The person defining the standard ought to put these replacements
in the order they believe to most frequent in the actual language, as
results will ultimately be sorted based on the index numbers of these
lists.

Romanized forms can contain an arbitrary number of characters, so
digraphs will be fine. You may even wish to define longer clusters to,
for example, provide uniform handling of common morphological
affixes. ``deromanize`` uses greedy matching, so the longest possible
cluster will always be matched. There are also other uses for character
groups involving pattern matching which will be covered later. (You can
really stick any arbitrary data in this file that you think might be
helpful later; aside from two keys, ``keys`` and ``char_sets``, nothing
will be processed automatically)

Keys:

``keys`` is a dictionary of objects that allow you to compose the
different character groups in different ways. For one-to-one
transliteration standards, you'd theoretically only need one key (and
probably not need to mess around with this framework, though it would
get the job done just fine).

In this case, we create one key called ``base`` and a list of the groups
it will contain, ``consonants`` and ``vowels``.

Given the above configuration, we can do something like this:

.. code:: python

   >>> # TransKeys only deal with python objects, so we have to
   >>> # deserialize it from our chosen format.
   >>> import deromanize
   >>> import yaml
   >>> PROFILE = yaml.safe_load(open('above_profile.yml'))
   >>> key = deromanize.TransKey(PROFILE)

From here, we can start sending words to the ``base`` key and see what
comes out.

.. code:: python

  >>> key['base'].getallparts('shalom')
  [ReplacementList('sh', [Replacement(0, 'ש')]), ReplacementList('a',
  [Replacement(0, '')]), ReplacementList('l', [Replacement(0, 'ל')]),
  ReplacementList('o', [Replacement(0, 'ו'), Replacement(1, '')]),
  ReplacementList('m', [Replacement(0, 'מ')])]
  >>> # looks a little silly.
  >>> print(deromanize.add_reps(key['base'].getallparts('shalom')))
  shalom:
  0 שלומ
  1 שלמ

So, basically, the ``.getallparts()`` method takes a string as input and
decodes it bit by bit, grabbing all possible original versions for each
Romanization symbol. You can get all the possible version of the word
together. Ignore the numbers for now. They have to deal with
sorting. This is just to demonstrate the most basic use-case. The
Hebrew-speakers may observe that neither of these options is correct
(because it doesn't account for final letters), so we'll dive a bit
deeper into the system to see how more complex situations can be dealt
with.

Building Complex Profiles
-------------------------
Let's take a look at a more complex profile, bit by bit. (See the
profile in its entirety here_.)

.. _here: data/new.yml

Defining Keys
~~~~~~~~~~~~~

.. code:: yaml

  keys:
    base:
      groups:
        - consonants
        - vowels
        - other
        - clusters
        - infrequent: 10

    front:
      parent: base
      groups:
        - beginning
        - beginning patterns

    end:
      parent: base
      groups: final
      suffix: true

The first thing to know is that there are a few configuration shortcuts
if a key only contains a list, that list is automatically assigned to
``groups``. Therefore:

 .. code:: yaml

  base:
    - consonants
    - vowels
    - other
    - clusters
    - infrequent: 10

is the same as...

.. code:: yaml

 base:
   groups:
     - consonants
     - vowels
     - other
     - clusters
     - infrequent: 10

The other shortcut is that ``base`` is actually a special key name.  If
it is defined, all other character groups will inherit the default
character set from it as a prototype which you can selectively override
and extend with other character groups to build all the groups you need.

Therefore:

.. code:: yaml

  front:
    - beginning
    - beginning patterns

\... is the same as...

.. code:: yaml

  front:
    base: base
    groups:
      - beginning
      - beginning patterns

If you don't want this behavior for any of your keys, you can simply
choose not to define ``base``. If you find it useful, but you want to
get out of it for a particular key, you can set it to ``None`` (which
happens to be spelled ``null`` in JSON and YAML).

.. code:: yaml

  front:
    base: null
    groups: (some groups here)

You can, of course, use any other key as your base and get into some
rather sophisticated composition if you wish. Just don't create a
dependency cycle or you'll end up in a never-ending loop. (Well, I guess
it will end when Python hits its recursion limit.)

One last thing you may notice that's odd in this section is that one of
the groups in ``base`` is ``infrequent: 10``. This is a way to
manipulate the sort order of results. It might be a good time to explain
that in a little more detail.

Sorting and "Weight"
~~~~~~~~~~~~~~~~~~~~
Each possible replacement for any Romanization symbol or cluster may
have one or more possible replacements, and therefore can be given as
lists. As shorthand, if there is only one possible replacement, it may
be a string, but it will be converted to a list containing that one
item at runtime.

As the items are added, they are assigned a ``weight``. In the common
case, that weight is simply the index number in the list.

Let's go back and pretend that are working with the simple profile at
the top of this README. We have a line like this in the file:

.. code:: yaml

   y: [יי, י]

When we run this through the TransKey instance we can see what happens
to it:

.. code:: python

  >>> key['base']['y']
  ReplacementList('y', [(0, 'יי'), (1, 'י')])
  >>> key['base']['y'][0]
  Replacement(0, 'יי')

Basically, each item is explicitly assigned its weight. When you add
two ``Replacement`` instances together, their weights are added, and
their strings are concatenated.

.. code:: python

  >>> key['base']['y'][0] + key['base']['o'][0]
  Replacement(0, 'ייו')

Likewise, when two ``ReplacemntList`` items are added together, the
Romanized strings are concatenated, and all the permutations of their
original forms are combined as well:

.. code:: python

  >>> print(key['base']['y'] + key['base']['o'])
  yo:
   0 ייו
   1 יי
   1 יו
   2 י

Note:
 As you may observe, the ``ReplacementList`` comes with pretty
 formatting when used with ``print()`` for easier debugging.

After all the variations have been generated, the resulting
``ReplacementList`` can be sorted with its ``.sort()`` method according
to these weights, from least to greatest.

However (coming back to the real config file), certain normalizations
may appear infrequently, so that one wants to try everything else
before resorting for that. These may be rare cases as is the case with
my ``infrequent`` character group, or it may be a way to hedge bets
against human error in input data.

What ``infrequent: 10`` does is tell the ``TransKey`` instance to add
``10`` to the index number of each Replacement to generate its
weight. Groups used in this way will not overwrite groups that already
values that already exist in the key. Instead, the replacement list will
be extended to include these values. This will drag less likely options
to the bottom of the list.

.. code:: python

  >>> print(add_reps( key['base'].getallparts('shalom')))
  shalom:
   0 שלומ
   5 שלמ
  10 שלאמ
  10 שאלומ
  15 שאלמ
  20 שאלאמ

A couple of colleagues pointed out to me that this weighting system
seems very arbitrary in and it should be based on values between 0 and
1 for a more scientific and statistical approach. However, the purpose
of the weighting system is simply to allow the person defining to have
a greater control over how results are sorted and have nothing to do
with science or statistics. If you want to sink items in a particular
group lower in the final sort order, stick a big fat number besides
the replacement value. This is the only meaning the numbers have. Fear
not!  They only print to help you debug and for refinement of the
sorting. There are some tricky methods you can use to convert the
index-generated weights into something that looks statistical
currently in the skunk works.

Also note that weights can arbitrary be added to any replacement
directly when it is defined. We could get a similar result for the word
above if, instead of using the ``infrequent`` group, we had defined the
letters like this:

.. code:: yaml

  ...
  a: ['' [10, 'א']]
  o: [ו, '', [10, א]]
  ...

Note:
 Here are those bidi shenanigans I mention earlier. Paste into Vim or
 something to see the correct character order.

Any replacement that is a list or tuple of two beginning with an integer
will use that integer as its weight assignment. In this way, one can
have very direct control over how results are sorted.

This is also what is done for the case when ``o`` should be replaced
with the empty string. It is manually weighted at ``5``.

Pattern-Based Replacement Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``deromanize`` profiles also allow the user to generate large numbers
of replacements from pattern-based definitions. Patterns rely on the
use of special characters that will generate sets of characters
defined elsewhere in the profile.

This somewhat analogous to ranges of characters like ``\w`` or ``\s``
in regex. However, unlike regex, which characters will be treated as
special are not yet defined (nor are there values). To create these
character sets and their aliases, the ``char_sets`` group must be
defined in the profile.

.. code:: yaml

 char_sets:
   C:
     key: base 
     chars: consonants
   F:
     key: front
     chars: consonants

What this says is that ``C`` will be an alias for all the characters
defined in the group ``consonants`` and replacements will be drawn
from the ``base`` key. Likewise ``F`` will stand for the same
character set, ``consonants``, but replacements will be drawn from the
key called ``front``. The value of ``chars`` may also be a list of
literal characters instead of the name of a character group. ``key``,
however must be a key defined in the ``keys`` group. If no ``base`` is
defined for the character set alias, it defaults to the base
key. Likewise, if the value of any character alias is not a dictionary
(containing at least a ``chars`` value), its value will be assigned to
for ``chars``, so a shorthand for the above is:

.. code:: yaml

 char_sets:
   C: consonants
   F:
     key: front
     chars: consonants

Also note that the character aliases themselves (``C`` and ``F``
above) can be arbitrary length. You should try to chose sequences that
cannot possibly appear in your transliteration. Capitals have no
meaning in the standard I've defined, so I use them, but you could
also use something like ``\c`` and ``\v`` if you needed. Just note
that there is no mechanism for escaping special characters once
defined.

When it comes to actually using these in replacement definitions, it
goes something like this...

.. code:: yaml

  beginning patterns:
    FiCC: [\1\2\3, \1י\2\3]
    FoCC: [\1ו\2\3, \1\2\3]
    FeCC: [\1\2\3]

Each alias character becomes something like a 'capture group' in
regex, and can be recalled int the replacement string with a
backslashed number (like regex). The appropriate replacements will be
generated for all characters in the group.

Please be aware that you can generate a LOT of replacements this way
(the above groups, with the rest of this config file, generate over
50,000 new replacements). This can take a few seconds to chug
through. This time can be cut by more than half by caching the
generated keys. Below is code from scripts/dr which will handle the
use of cached keys.

.. code:: python

    PROJECT_DIR = Path(deromanize.__file__).parents[1]
    CONFIG_FILE = PROJECT_DIR/'data'/'new.yml'
    CACHE = Path('.cache')

    with CONFIG_FILE.open() as config:
        key = deromanize.cached_keys(yaml.safe_load, config, cache)

The ``cached_keys`` function take the profile loader function as it's
first argument (some kind of deserializer), an open, readable file
object of the profile as the second, and a string of the path or
pathlib.Path instance pointing to the cache file third. Basically if
the profile has been modified since the last cache was created, it
will generate all new keys and dump what it made into the
cache. Otherwise, it will just load the cache.
