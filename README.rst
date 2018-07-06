Deromanize
==========
``deromanize`` is a set of tools to aid in converting Romanized text
back into original scripts.

.. contents::

Installation
------------
``deromanize`` requires Python 3.5 or better.


.. code:: bash

  $ git clone https://github.com/fid-judaica/deromanize
  $ cd deromanize
  $ pip3 install .

Or, to use the version in PyPI:

.. code:: bash

  $ pip3 install deromanize

This assumes you're working in a virtualenv, as you ought. Otherwise,
use the ``--user`` flag with ``pip``. There's no reason ever to install this as root.
Don't do it.

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

   >>> # KeyGenerators only deal with python objects, so we have to
   >>> # deserialize it from our chosen format.
   >>> import deromanize as dr
   >>> import yaml
   >>> PROFILE = yaml.safe_load(open('above_profile.yml'))
   >>> keys = dr.KeyGenerator(PROFILE)

From here, we can start sending words to the ``base`` key and see what
comes out.

.. code:: python

  >>> parts = keys['base'].getallparts('shalom')
  >>> parts
  [ReplacementList('sh', [(0, 'ש')]), ReplacementList('a', [(0, '')]), ReplacementList('l', [(0, 'ל')]), ReplacementList('o', [(0, 'ו'), (1, '')]), ReplacementList('m', [(0, 'מ')])]
  >>> # looks a little silly.
  >>> shalom = dr.add_rlists(parts)
  >>> shalom
  ReplacementList('shalom', [(0, 'שלומ'), (1, 'שלמ')])
  >>> # conversion to a string provides a more readable version
  >>> print(shalom)
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

.. _here: ./tests/test.yml

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

When we run this through the KeyGenerator instance we can see what happens
to it:

.. code:: python

  >>> key['base']['y']
  ReplacementList('y', [(0, 'יי'), (1, 'י')])
  >>> key['base']['y'][0]
  Replacement.new(0, 'יי')

Basically, each item is explicitly assigned its weight. When you add
two ``Replacement`` instances together, their weights are added, and
their strings are concatenated.

.. code:: python

  >>> key['base']['y'][0] + key['base']['o'][0]
  Replacement.new(0, 'ייו')

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

What ``infrequent: 10`` does is tell the ``KeyGenerator`` instance to add
``10`` to the index number of each Replacement to generate its
weight. Groups used in this way will not overwrite groups that already
values that already exist in the key. Instead, the replacement list will
be extended to include these values. This will drag less likely options
to the bottom of the list.

.. code:: python

  >>> shalom = add_rlists( key['base'].getallparts('shalom'))
  >>> print(shalom)
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
the replacement value. This is the only meaning the numbers have.

However, if you need to have these numbers look more scientific to use
with a statistical framework, they can be converted at any point:

.. code:: python

  >>> shalom.makestat()
  >>> print(shalom)
  shalom:
  0.6855870895937674 שלומ
  0.11426451493229456 שלמ
  0.06232609905397886 שלאמ
  0.06232609905397886 שאלומ
  0.04284919309961046 שאלמ
  0.03264700426636988 שאלאמ

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

Using Suffix Keys
~~~~~~~~~~~~~~~~~
Those of you who know Hebrew have noticed, dobutless, that we are still
unable to generate the word שלום as it is supposed to look, with a
proper *final mem*. Suffix keys are used to deal with word endings, such
as final letters (common in Semitic writing systems but also found in
Greek) or perhaps common morphological suffixes.

A suffix group is defined like this:

.. code:: yaml

  end:
    groups: [ some list of groups ]
    suffix: true

This will create a reversed tokenizer that begins looking for tokens at
the end of the word and moves forward. It can be used to deal with
endings separately.

.. code:: python

  >>> suffix, remainder = keys['end'].getpart('shalom')
  >>> suffix
  ReplacementList('m', [(0, 'ם')])
  >>> remainder
  'shalo'
  >>> front = add_rlists(keys['base'].getallparts(remainder))
  >>> shalom = front + suffix
  >>> print(shalom)
  shalom:
   0 שלום
   5 שלם
  10 שלאם
  10 שאלום
  15 שאלם
  20 שאלאם

We've also seen the ``.getpart()`` method of a key for the first time.
This method takes a string as input returns a replist for the first
matching token (or the last matching token, if *suffix* was specified)
as well as the remaining string. This is useful if you want to have
different rules about the beginning, middle and end of a word, as I
typically do.

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
through.

A Little Hidden Metadata
------------------------
Each ``Replacement`` in a ``ReplacementList`` has an attribute called
``keyvalue``. This is a tuple where each item a two-tuple of the token
found and how it was interpreted in the case of the specific
``Replacment``. Continuing with our ``shalom`` variable from previous
examples:

.. code:: python

  >>> shalom[0]
  Replacement.new(0, 'שלום')
  >>> shalom[0].keyvalue
  (('sh', 'ש'), ('a', ''), ('l', 'ל'), ('o', 'ו'), ('m', 'ם'))

This can be useful for various things. Say we wanted to generate another
transliteration standard from this. Some outside source has verified
that the generated option ``שלום`` is the correct Hebrew form of
``shalom``, but now we want to create a more detail transliteration that
will show that the /o/ vowel was marked with the letter vav. Because we
can go back and specifically see that /o/ was realized as vav in this
case, it is easy to generate something like ``šalôm`` if we want to.

Additionally, this can be a way to detect errors in the transliteration.

In the system we use, the letter ק is supposed to be written as *ḳ*,
using the diacritic to distinguish it from hard *kaf* (כ). However,
sometimes people make mistakes. Assuming we have defined a
fault-tolerant standard which understands that sometimes people will
write k instead of ḳ, we can generate something like this:

.. code:: python

  >>> shuk = 'shuk' # oops! should be "shuḳ"
  >>> shuk = add_rlists(keys['base'].getallparts(shuk))
  print(shuk)
  shuk:
   0 שוכ
  20 שוק

When it has been verified that ``שוק`` is the correct Hebrew form, we
can look at how it was built up:

.. code:: python

  >>> shuk[1].keyvalue
  (('sh', 'ש'), ('u', 'ו'), ('k', 'ק')

At this point it is trivial for the computer to see that ק was
incorrectly transcribed as *k*, and it can easily go back and correct
the source if necessary. There is a function to aid in using this
key-value data in generating new forms in the ``cacheutils`` module. See
the following section for links to documentation about that.

Note that some of this data may be lost for tokens generated with
patterns if the keys have been cached with ``cached_keys`` and recalled.
``cached_keys`` should only be used to speed-up small utilities where
this information is not needed.

Extras: Caching Helpers, Miscellaneous Utilities, and Microservice
------------------------------------------------------------------
At the end of the day, ``deromanize`` is just a helpful tool taking data
in one script and generating all possible equivalents in another script.
For conversion between any systems that don't have one-to-one
correspondence. It's up to the user figure out how the correct
alternative will be selected. However, `deromanize.cacheutils`_ has some
simple utilities that can help with recall once the correct form has
been selected.

`deromanize.tools`_ has some other helper functions that have been very
useful to me while working with ``deromanize`` on real data in different
languages and scripts -- helpers to strip punctuation, remove
diacritics, correct mistakes in the source text, as well as a decoder
function that will work well with complex profiles which have different
rules for the beginning, middle and end of a word.

If you're using ``deromanize``, there is a good chance you'll want this
kind of stuff.  Check out the docs on those modules!

- `deromanize.cacheutils`_
- `deromanize.tools`_

Additionally, there is another package you can use to spin up
``deromanize`` as a microservice, `microdero`_. This primarily for
people who are interested using ``deromanize``, but cannot or do not
wish to have most of their project in Python, such web app that uses the
generated data on the client or a mature project in another language
that would like to integrate ``deromanize``.

.. _deromanize.cacheutils: doc/cacheutils.rst
.. _deromanize.tools: doc/tools.rst
.. _microdero: https://github.com/FID-Judaica/microdero
