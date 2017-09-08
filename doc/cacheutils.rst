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
succeed without error, but role back if there is a failure.

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

As syntactic sugar, it's also possible to use assignment syntax.

.. code:: python

  >>> cache['qore'] = 'קורא'
