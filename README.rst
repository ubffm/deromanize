Deromanize
==========
``deromanize`` is a set of tools to aid in converting Romanized text
back into original scripts.

.. contents::

``TransKey``
------------
TransKey is a class to help parse a profile which describes a
Romanization standard. The programmer still must define how the contents
of the profile data will be used, but the TransKey is a helpful
mechanism for simplifying this process.

Creating a Profile
~~~~~~~~~~~~~~~~~~
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

Note::
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
cluster will always be matched.

These character classes are hooked into different places to enable some
fuzzy cluster generation (more on that later), and they can also be used
to interface with filter generation in the ``filtermaker`` module. If
you define a group called ``other``, any characters defined here will be
considered part of the base character set; for example, if there is any
punctuation that needs to be converted or something.

You can see each group is a dictionary where the Romanized form of the
character is the key, and the value is what it should convert to in the
original script, if it's a list, it should be because there is ambiguity
in the Romanization, and the Romanized character has multiple possible
realizations in the original script. The possibilities should be given
in order of likelihood of their appearance. Multiple results will be
sorted according to this order.

You can define as many other groups as you want, which can be used in
various ways, as we'll see. There's no harm in putting additional kinds
of data in the same profile data structure for your own use. Aside from
``consonants``, ``vowels`` and ``others``, nothing will be automatically
parsed.

Creating a TransKey Instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Given this profile_, let's start building our TransKey instance.

.. _profile: data/new.yml

.. code:: python

    # TransKeys only deal with python objects, so we have to unmarshall
    # from our serialization format of choice. I chose YAML, due to
    # brain damage.
    >>> import deromanize
    >>> import yaml
    >>> PROFILE = yaml.safe_load(open('./data/new.yml'))
    >>> key = deromanize.TransKey(PROFILE, 'base', 'consonants', 'vowels')

So what just happened there?

The first argument of the ``TransKey()`` constructor is the profile file
from which all the keys will be generated. Everything after that gets
passed to the ``.groups2key()`` method and becomes the default
"``base_key``" for the instance. The argument ``'base'`` tells the
TransKey instance that this is the name of the key, the rest of the
arguments tell which groups from the profile should be added to the
key.

I forgot there were two other groups I wanted to add to the ``'base'``
key, ``other`` and ``clusters``, so I'll do that now.

.. code:: python

  >>> key.groups2key('base', 'other', 'clusters')

Again, we specify which key we want to add to, and then the groups from
the profile to be added.

Using Keys
~~~~~~~~~~

Now, let's try to decode some Romanized Hebrew:

.. code:: python

  >>> key['base'].getallparts('shalom')
  [ReplacementList('sh', [Replacement(0, 'ש')]), ReplacementList('a',
  [Replacement(0, '')]), ReplacementList('l', [Replacement(0, 'ל')]),
  ReplacementList('o', [Replacement(0, 'ו'), Replacement(1, '')]),
  ReplacementList('m', [Replacement(0, 'מ')])]

OK, What is all that crap? I'll tell you in a minute. The first thing
we'll do is show you how to make sense of it.

.. code:: python

  >>> foo = key['base'].getallparts('shalom')
  >>> bar = deromanize.add_reps(foo)
  >>> print(bar)
  shalom:
   0 שלומ
   1 שלמ

So basically, we get the key, and we get all possible original
reconstructions with a *weight* attached. If you look at the ``vowels``
group in the profile, you'll see that ``o`` can be de-Romanized as
either ``ו`` (Hebrew letter *vav*) or the empty string, but the version
with *vav* is to be preferred. This is reflected in the ``__str__`` of
whatever kind of weird object we just got back.

Let's back it up one notch, before we added all the replacements
together:

.. code:: python

  >>> for i in foo:
  ...     print(i)
  ...
  sh:
   0 ש
  a:
   0 
  l:
   0 ל
  o:
   0 ו
   1 
  m:
   0 מ

So we get a list of possible replacements and weights for each
Romanization symbol we put in. In this case, most of the items only have
one possible, value, but the ``o`` has two. Each Romanized character
here represents a ``ReplacementList`` instance.

.. code:: python

  >>> foo[3]
  ReplacementList('o', [Replacement(0, 'ו'), Replacement(1, '')])

So, each replacement list has a ``.key`` attribute which marks the
Romanization symbol it treats, and it contains a list of ``Replacement``
instances (now you see how creatively these things are named). Each
replacement has a ``.weight`` attribute and a ``value`` attribute.

Now, when you add two ReplacementLists together, you get the keys of
each concatenated, and all the possible combinations of the
replacements with their weights being combined. Thus:

.. code:: python

  >>> print(key['base']['y'])
  y:
   0 יי
   1 י
  >>> print(key['base']['o'])
  o:
   0 ו
   1 
  >>> print(key['base']['y'] + key['base']['o'])
  yo:
   0 ייו
   1 יי
   1 יו
   2 י

Indeed, ``deromanize.add_reps(reps)`` is just a shortcut for
``functools.reduce(operator.add, reps)`` with error checking. ``sum()``
would have worked just as well, but it's only for numeric types. Results
are not automatically sorted, but ``ReplacementList`` has a sort method
which will order the results by weight.

Creating a New Key from an Existing Key (and Suffixes)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Returning to the example of *shalom*, we see that the two de-Romanized
options are שלומ and שלמ, neither of which is actually correct. Those
familiar with Hebrew will know that certain letters have special forms
at the ends of words.

The ``'base'`` key we've created can't deal with those. However, we can
create a new key:

.. code:: python

  >>> key.basekey2new('endings', 'final', suffix=True)

Creating a new key based on an existing key is similar to creating a key
from scratch. You specify the name of the new key and any groups you
want to add to it from the configuration file. These new items will
overwrite any old values. By default, it uses the group that you created
at instantiation time, but you can specify another base with the
``base_key`` keyword argument. Setting ``suffix`` to ``True`` means that
the key will start decoding a string from the back instead of the front,
as we see:

.. code:: python

  >>> end, remainder = key['endings'].getpart('shalom')
  >>> remainder, end
  ('shalo', ReplacementList('m', [Replacement(0, 'ם')]))

So far, we have seen the ``.getallparts`` method used with the
``'base'`` key, which returns a list of transliteration symbols and
their possible replacements. ``.getpart`` is the singular to this
plural. It gets the replacement for the first transliteration symbol it
sees and returns the remainder of the original string. If ``suffix`` was
specified when the group was created the "first part" of the string it
sees is the end. From here, we can get the rest of the parts from the
``'base'`` key and add up all the results:

.. code:: python

  >>> beginning = key['base'].getallparts(remainder)
  >>> print(deromanize.add_reps(beginning) + end)
  shalom:
   0 שלום
   1 שלם

Perfect!

``.processor`` decorator
~~~~~~~~~~~~~~~~~~~~~~~~
It's a bit boring to type all this, so let's turn it into a function.
``TransKey`` instances come with a decorator.

.. code:: python

  >>> @key.processor
  ... def decode(key, word):
  ...     end, remainder = key['endings'].getpart(word)
  ...     beginning = key['base'].getallparts(remainder)
  ...     return deromanize.add_reps(beginning) + end
  ...
  >>> print(decode('ḥayim'))
  ḥayim:
   0 חיים
   1 חים

``.processor`` just automatically includes the key when you call the
function and passes any other \*args or \*\*kwargs. It's not really a
big deal.

Weighted Replacements
~~~~~~~~~~~~~~~~~~~~~
Let's look at another example:

.. code:: python

  >>> print(decode('rosh'))
  rosh:
   0 רוש
   1 רש

Oops! Turns out none of these are right. I forgot that, every now and
then, the *o* sound in Hebrew can be represented with א, as it is in
*rosh*. However, I don't want that to be the first (or even second)
choice in most cases. I have this replacement defined in the group
``infrequent``, so lets add it:

.. code:: python

  >>> key.groups2key('base', 'infrequent', weight=15)
  >>> print(decode('rosh'))
  rosh:
   0 רוש
   1 רש
  15 ראש

Better! Now, this unlikely Replacement appears, but it is weighted
heavily, so such variations will usually be at the bottom of the
list.

*rishon* is a similar kind of word, so let's see what happens:

.. code:: python

  >>> print(decode('rishon'))
  rishon:
   0 רישון
   1 רישן
  15 רישאן
  15 ראשון
  16 ראשן
  30 ראשאן

In this case, the fourth option is the correct result. The ``weight``
argument allows you to account for rare normalizations or common
mistakes without letting them be more highly prioritized than more
common variants.

Pattern-Based Replacement Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
... coming soon...
