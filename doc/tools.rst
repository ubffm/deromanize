``deromanize.tools``
====================
These are a couple of utility functions that I find myself needing very
frequently in the process of working on the converstion project. Note
that ``deromanize.tools`` doesn't have to be imported to get access to
them. They are imported directly into the top level of the package.

.. contents::

``front_mid_end_decode()``
--------------------------
This is a pre-built decoder for any ``KeyGenerator`` instance that
contains that keys ``front``, ``mid`` and ``end`` keys. Simpler profiles
can easily be adapted to this format. For example, say you have a simple
writing system and you only need to define a base key and a few special
endings. the ``keys`` section of your profile might look like this:

.. code:: yaml

  keys:

    base:
      - consonants
      - vowels
      - groups

    end:
      groups:
        - end_groups
        - end_patterns
      suffix: true

So, you could extend that into a form that could be used by
``front_mid_end_decode()`` by adding this to the keys section:

.. code:: yaml

  keys:

    # above stuff

    front: []
    mid: []

This will put the contents of ``base`` into ``front`` and ``mid``
without any additional groups.

Then you would do something like this in the code:

.. code:: python

  keys = deromanize.KeyGenerator(yaml.safe_load('myprofile.yml'))
  for word in words:
      replist = deromanize.front_mid_end_decode(keys, word)
      ...

Or something. This functions basically tries different orders in which
to apply the three different keys in the decoding process and returns a
replacement list for the word you gave it. It's a little complicated to
explain the order in which it tries to do things. If you want to know,
just read the code:

.. code:: python

  def front_mid_end_decode(keys, word):
      # get ending clusters, then beginning clusters, then whatever's left in the
      # middle.
      end, remainder = keys['end'].getpart(word)
      if remainder:
          try:
              front, remainder = keys['front'].getpart(remainder)
          except KeyError:
              return _no_end(keys, word)
      else:
          return _no_end(keys, word)

      if remainder:
          middle = keys['mid'].getallparts(remainder).add()
          return (front + middle + end)
      else:
          return (front + end)


  def _no_end(keys, word):
      # this is where words go when getting the ending first produces strange
      # results.
      front, remainder = keys['front'].getpart(word)
      if remainder:
          end, remainder = keys['end'].getpart(remainder)
          if remainder:
              middle = keys['mid'].getallparts(remainder).add()
              return (front + middle + end)
          else:
              return (front + end)
      else:
          return (front)

``stripper_factory()``
----------------------
Python's strings have a ``.strip()`` method. However, they take
characters as arguments and strip off all of those characters from the
beginning and end of the string. We'll call this "exclusive stripping",
since it exclusively strips characters in the string you give it.

The ``stripper_factory`` builds functions that strip every character
besides the ones you pass into it. This is useful for stripping off all
characters that shouldn't be transliterated, especially punctuation,
numbers, etc.

Also because I'm lazy, you can give it as many iterables as you want,
and they can be nested, and it will go through all of them recursively
and suck out every character. Note that there is one weakness:
when you iterate over dictionaries, you only get the *keys* out of them
and you won't recurse any deeper (unless you have hashable collection
object as the key). That's why there is also a ``dict_func`` parameter,
where you can do a little preprocessing on your mapping types. If you
wanted to iterate over the values, you'd set it to ``lambda d:
d.values()``. If you want keys and values, ``lambda d: d.items()``. I
usually do something like that; i.e.:

.. code:: python

  keys = deromanize.KeyGenerator(yaml.safe_load('myprofile.yml'))
  strip = deromanize.front_mid_end_decode(
          keys.profile['vowels'].items(),
          keys.profile['cosonants'].items()
  )


The resulting strip function, as mentioned will strip all characters
from the beginning and end of the word you give it until it hits one of
the characters that is allowed. However! it doesn't throw away the extra
parts; it returns them to you along with the core.

.. code:: python

  for word in words:
      front_junk, core, back_junk = strip(word)
      replist = deromanize.front_mid_end_decode(keys, core)

This is because you don't typically want to throw away the punctuation
and so forth -- you simply want it out of the way while you deal with
the actual word. You can add it back to the generated replacementlist
later. The way you do that is with ``get_self_rep``.

``get_self_rep``
----------------
Strings aren't good at being joined to with replacement lists, but
``get_self_rep()`` takes a string as an argument and returns a replist
where the same string is both the key and the value and the replacement
has a weight of zero. That means these strings can be added to other
replists without affecting their weight or content.

.. code:: python

  for word in words:
      front_junk, core, back_junk = strip(word)
      replist = deromanize.front_mid_end_decode(keys, core)
      final_list = (
          get_self_rep(front_junk) + replist + get_self_rep(back_junk)
      )

Should just about cover it.
