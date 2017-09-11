``cacheutils``
==============
The cacheutils module has simple utilities to help you keep track of
"the right answers" once you've figured out what they are. There are
currently two main cache, but they mostly offer the same interfaces.

.. contents::

Cache types
-----------
The first is ``CacheObject`` which simply stores the cache in RAM as a
python object. it has a ``.serializable()`` method which returns a
representation of the object in a form that can be serialized as JSON
(though it doesn't preform the serialzation).

.. code:: python

  >>> from deromanize import cacheutils
  >>> cache = cacheutils.CacheObject()

The second is a ``CacheDB``, which provides the same interfaces as a
wrapper on a ``sqlite`` database. It also has a context manager for
transactional write operations:

.. code:: python

  >>> import sqlite
  >>> conn = sqlite.connection('mydatabase')
  >>> dbcache = cacheutils.CacheDB(conn, 'name_of_table')
  >>> with dbcache:
  ...     dbcache.add('shalom', 'שלום')

This will modify the database in memory, and commit if the operations
succeed without error, but role back if there is a failure. The database
connection is stored in ``cachinstance.con``, and the cursor is
``cacheinstance.cur``.

Aside from that, they present more or less the same interfaces.

Inserting Data
~~~~~~~~~~~~~~
An instance of a cache type is essentially a counter. You give it a word
in the source script and the correctly identified eqivalent in the
target script, and it keeps track of how many times each pair has been
seen. The simplest way to add a sighting is to use the ``.add()``
method.

.. code:: python

  >>> cache.add('shalom', 'שלום')

You can also use a count argument to increase it by more than one.

.. code:: python

  >>> cache.add('qore', 'קורה', 5)
  >>> cache.add('qore', 'קורא', 2)

(This should look like ``cache.add('source', 'target', number)``, but
bidi in the browser)

Reading Data
~~~~~~~~~~~~
You can get data using bracket syntax. Giving a single argument in the
source script will return a dictionary of all matching words in the
target language:

.. code:: python

  >>> cache['shalom']
  {'שלום': 1}
  >>> cache['qore']
  {'קורה': 5, 'קורא': 2}

Beware of bidi shenanigans in the way the browser renders the above
dictionaries.

You can also use two arguments in the bracket to get directly to the
number:

.. code:: python

  >>> cache['qore', 'קורא']
  2

This is functionally the same as doing ``cache['qore']['קורא']``, the
only difference is that it only requires one database operation if
you're using a database backend for the cache.

Iterating on a cache instance returns 3-tuples with ``(source, target,
number)`` (again, forgive the bidi shenanigans):

.. code:: python

  >>> for i in cache:
  ...     print(i)
  ('shalom', 'שלום', 1)
  ('qore', 'קורה', 5)
  ('qore', 'קורא', 2)

This is so the data can easily be transfered into a CSV file or other
tabular format.

Building a Cache from a TSV File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A cache instance can also be instantiated from different kinds of
tabular data. For example, one might use this with a TSV file (though
note that this is not entirely "safe" if the file contains tabs inside
of fields):

.. code:: python

  >>> with open('cache.tsv') as cachefile:
  ...     cache = CacheObject(line.rstrip().split('\t') for line in cachefile)

Reversing a Cache
~~~~~~~~~~~~~~~~~
There may be reason to want to look up words by their form in the target
script. In this case a cache may be inverted:

.. code:: python

  >>> newcache = cache.inverted()

Be aware that if this is preformed on a database cache, it will create a
new in memory cache, which could be problematic if the cache is very
large. Since the database is, well, a database, it has an additional
method for querying based on the target script, so creating a new,
in-memory cache is unnecessary):

.. code:: python

  >>> cache.get_target('קורה')
  {'qore': 2}

This behavior is not available for a CacheObject instance because it
would require iterating over the whole data structure for each query.

Generating Simplified Caching Formats
-------------------------------------
Because of factors like human error in the source script, it is
sometimes desirable to make simplified or alternate formats that will
are at least partially tolerant of human error. All of the tools here
work on the ``.keyvalue`` attribute of a ``deromanize.Replacement``
instance.

``strip_chars``
~~~~~~~~~~~~~~~
The first function, ``strip_chars`` simply strips diacritics off certain
characters in the source script. The characters should be in a set:

.. code:: python

  >>> newkeyvalues = strip_chars(rep.keyvalue, set('aeiou'))

This will strip diacritics off of any characters that have 'a', 'e',
'i', 'o' or 'u' as their base character. As it happens, this is the
default behavior if no ``chars`` argument is provided. Note that the
return value is a *generator object*, so you may want to turn it into a
list if you want it to stick around.

``replacer_maker``
~~~~~~~~~~~~~~~~~~
``replacer_maker()`` is a factory for token replacement functions. The
first argument, ``simple_replacements`` is simply dictionary of tokens
that need to be converted into another character. For example, In the
old transliteration standard used in our library 'שׁ' is transliterated
as *š*, but in the new standard (Library of Congress) the same consonant
is represented as ``sh``, so one of the items in the
``simple_replacements`` dictionary would be ``'š': 'sh'``, so each token
of the first would be replaced with the second.

The second parameter, ``pair_replacements`` can be used to change tokens
that are ambiguous in the transliteration standard, but are more clear
once one sees the proper version in the original script.

For example, in the old transliteration a final *segol-he'* is simply
*e*, but is *eh* in LOC. However, if we have the letter *ה* matched to
the consonant *e*, we know it should be *eh* after it is converted. In
this case, the dictionary item will look like this ``'eh': ['e', 'ה']``
that is the key is the target form and the value is the two correlated
symbols that represent should be converted into it.

The output of ``replacer_maker`` is a function that will take
``Replacement.keyvalue`` attributes and spit out a new one with the
required replacements complete.
