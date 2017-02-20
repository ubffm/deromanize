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
dictionaries with strings or lists of strings. It can easily be stored
as JSON, or a .ini file could be used with little post processing. I
like to use YAML because it's easy to write (though I do not mean to
endorse the abomination that is the YAML standard in so doing; Perhaps
hjson would be a saner choice).

The profile, at the very least, must define all consonants and vowels
used in the Romanization standard (including digraphs).

.. code:: yaml

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

These character classes are hooked into different places to enable some
fuzzy cluster generation (more on that later), and they can also be used
to interface with filter generation in the ``filtermaker`` module. If
you define a group called ``other``, any characters defined here will be
considered part of the base character set; for example, if there is any
punctuation that needs to be converted or something.

You can see each group is a dictionary where the Romanized form of the
character is the key, and the value is what it shold convert to in the
original script, if it's a list, it should be because there is ambiguity
in the Romanization, and the Romanized character has multiple
possible realizations in the original script. The possibilites should be
given in order of likelihood of their appearance. multiple results will
be sorted according to this order.

You can define as many other groups as you want, which can be used in
various ways, as we'll see. There's no harm in putting additional kinds
of data in the same profile data structure for your own use. Aside from
``consonants``, ``vowels`` and ``others``, nothing will be automatically
parsed.

Given this profile_, let's start bulding our TransKey instance.

.. _profile: data/new.yml

Creating a TransKey Instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Ok, What is all that crap? I'll tell you in a minute. The first thing
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

Let's back it up one notch, before we added all the replacments
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

So, each replacment list has a ``.key`` attribute which marks the
Romanization symbol it treats, and it contains a list of ``Replacement``
instances (now you see how creatively these things are named). Each
replacement has a ``.weight`` attribute and a ``value`` attribute.

Now, when you add two ReplacementLists together, you get the keys of
each concatinated, and all the possible combinations of the two 
