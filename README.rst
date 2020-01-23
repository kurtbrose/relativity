relativity
==========
multi-index data structures


Motivation
----------

We're going to take a mental journey of discovery to see why
relativity was written, and how you can use it to simplify
some of the most difficult problems that come up regularly
when programming.  Rather then leaping straight from programming
with python's standard data structures to programming with
relativistic data structures, we'll get a running start
by programming in a version of python that is missing
key data structures.  Then, we will draw a line from this
deficient bad version of python to regular python, and
then extend that line on into relativity.


Dict to List
''''''''''''

Imagine programming without hashmaps.  For example, let's say we have
a list of ``Restaurant`` objects and ``City`` objects, and we want to
get how many ``Restaurants`` are in each ``City``.

Normally this is simple:


.. code-block:: python

    restaurants_in_city = {}

    for restaurant in restaurants:
        city = restaurant.city
        restaurants_in_city[city] = restaurants_in_city.get(city, 0) + 1

    def get_restaurant_count(city):
        return restaurants_in_city.get(city, 0)


But, imagine how you would approach the problem if the only available
data structure was a list.


.. code-block:: python

    cities = []
    restaurants_in_city = []

    for restaurant in restaurants:
        missing = True
        for idx, city in enumerate(cities):
            if city == restaurant.city:
                restaurants_in_city[idx] += 1
                missing = False
        if missing:
            cities.append(restaurant.city)
            restaurants_in_city.append(1)

    def get_restaurant_count(city):
        for idx, city2 in enumerate(cities):
            if city == city2:
                return restaurants_in_city[idx]
        return 0


Comparing the two examples, there are a few key differences:

- there are more low value local values (``idx``)
- single data structures split into multiple, which must
  then be kept in sync
- the code is longer, therefore harder to read,
  modify, and debug

Let's leave this dystopian data structure wasteland behind
for now and go back to regular python.


Dict to M2M
'''''''''''

The same differences that showed up when programming with
and without hashmaps will come up again when comparing
programming with single-index hashmaps to relativistic
multi-index hashmaps.

Returning to the restaurants and cities example, what if
a restaurant can have multiple locations and we need to
keep track of which cities each restaurant is in,
as well as which restaurants are in each city.

Note that we allow a restaurant to have multiple
locations within the same city, so sets must be used
to avoid double counting.


.. code-block:: python

    restaurants_in_city = {}
    cities_of_restaurant = {}

    for restaurant in restaurants:
        for location in restaurant.locations:
            restaurants_in_city.setdefault(location.city, set()).add(restaurant)
            cities_of_restaurant.setdefault(restaurant, set()).add(location.city)

    def get_restaurants_in_city(city):
        return restaurants_in_city.get(city, set())

    def get_cities_of_restaurant(restaurant):
        return cities_of_restaurant.get(restaurant, set())



Relativity's most basic data structure is a many-to-many
mapping ``M2M``.  ``M2M`` is a systematic abstraction over
associating every key with a set of values, and every
value with a set of keys.  See how ``M2M`` simplifies
the problem:


.. code-block:: python

    restaurant_city_m2m = M2M()

    for restaurant in restaurants:
        for location in restaurant.locations:
            restaurant_city_m2m.add(restaurant, location.city)

    get_restaurants_in_city = restaurant_city_m2m.inv.get
    get_cities_of_restaurant = restaurant_city_m2m.get


Recall that the advantages of having single-index hashmaps
were shorter code, with fewer long lived data structures
and fewer local values.  ``M2M`` doesn't replace ``dict``
any more than ``dict`` replaces ``list``.  Rather it is
a new layer of abstraction that can greatly simplify
a broad class of problems.

Is it possible to go further?  Are there higher levels
of abstraction that can represent more complex relationships
in fewer data structures, and be manipulated with fewer
lines of code and intermediate values?


M2M to M2MGraph
'''''''''''''''

Where relativity really shines is releiving the programmer
of the burden of keeping data structures consistent with updates.
Let's consider our restaurant example if we need to be able
to add and remove locations one at a time and still be able
to query.

With ``M2M`` objects, the problem is doable, but fiddly to
implement:


.. code-block:: python

    restaurant_location = M2M()
    location_city = M2M()

    def add_location(location):
        restaurant_location.add(location.restaurant, location)
        location_city.add(location, location.city)

    def remove_location(location):
        del location_city[location]
        del restaurant_location.inv[location]

    def restaurants_in_city(city):
        restaurants = set()
        for location in location_city.inv[city]:
            for restaurant in restaurant_location.inv[location]:
                restaurants.add(restaurant)
        return restaurants

    def cities_of_restaurant(restaurant):
        cities = set()
        for location in restaurant_location[restaurant]:
            for city in location_city[location]:
                cities.add(city)
        return cities


This problem can be simplified by stepping up a level of
abstraction.
Where ``M2M`` is a data structure of keys and values, ``M2MGraph``
is a higher-level data structure of ``M2M`` s.
With ``M2MGraph``, this problem becomes simple and
intuitive:


.. code-block:: python

    data = M2MGraph([('restaurant', 'location'), ('location', 'city')])

    def add_location(location):
        data['restaurant', 'location', 'city'].add(
            location.restaurant, location, location.city)

    def remove_location(location):
        data.remove('location', location)

    def restaurants_in_city(city):
        return data.pairs('city', 'restaurant').get(city)

    def cities_of_restaurant(restaurant):
        return data.pairs('restaurant', 'city').get(restaurant)


Introducing Chain
'''''''''''''''''

Graphs are good for representing arbitrary sets of data, but they
are awkward to query overy.  ``M2MChain``s sequences of ``M2M``s, where
the keys of ``M2M`` n are meant to be drawn from the same pool
as the values of ``M2M`` n - 1.

A simple way to construct a chain is with the ``chain`` helper function.

.. code-block:: python

    students2classes = M2M([
        ('alice', 'math'),
        ('alice', 'english'),
        ('bob', 'english'),
        ('carol', 'math'),
        ('doug', 'chemistry')])

    classmates = chain(students2clases, students2classes.inv)


By chaining the student:class map to itself, we can easily
query which students have classes together.


.. code-block:: python

    >>> classmates.only('alice')
    M2MChain([M2M([('alice', 'math'), ('alice', 'english')]), M2M([('math', 'carol'), ('math', 'alice'), ('english', 'bob'), ('english', 'alice')])])

    >>> classmates.only('alice').m2ms[1]
    M2M([('math', 'carol'), ('math', 'alice'), ('english', 'bob'), ('english', 'alice')])

    >>> classmates.only('alice').m2ms[1].inv.keys()
    ['bob', 'carol', 'alice']


Relativity and DataBases
------------------------

Relativity is excellent at representing many-to-many relationships
from databases which are otherwise awkward to handle.

M2M + ORM
'''''''''

Let's consider an example from Django to start.


.. code-block:: python

    from django.db import models

    class Student(models.model):
        name = models.StringField()

    class Course(models.model):
        name = models.StringField()
        students = models.ManyToMany(Student)


Students take many courses, and each course has many students.

Construting an ``M2M`` over these relationships is very natural:


.. code-block:: python

    from relativity import M2M
    StudentCourse = Course.students.through

    enrollments = M2M(
        StudentCourse.objects.all().values_list('student', 'course'))




Design Philosophy
-----------------


DB Feature Sets
'''''''''''''''

A typical SQL database, such as PostGres, MySQL, SQLServer, Oracle, or DB2
offers many features which can be split into four categories:

- relational data model and queries
- network protocol and multiple concurrent connections
- transactions, atomic updates, and MVCC_
- persistent storage, backups, and read replicas

Let's call these "relational", "network", "transactional",
and "persistence" feature sets.

.. _MVCC: https://en.wikipedia.org/wiki/Multiversion_concurrency_control


"Alternative" Databases
'''''''''''''''''''''''

The most widely used alternative is probably SQLite_.  SQLite
has relational, transactional, and persistence feature sets but does not have
a network protocol.  Instead it must be embedded_
as a library inside another application.

Another example is the venerable ZODB_.  ZODB has
network, transactional, and persistence feature sets
but replaces the relational data model
with an object data model.

As an extreme example of how less can be more, memcached_ has
only network features.  Data is stored ephemerally in the form of opaque blobs without
any data model.  There is no atomicity of updates: there is no way to ensure that
two writes either both succeed or both fail.

The so-called "NoSQL" databases (cassandra_, couchdb_, mongodb_, etc)
generally provide network and persistence features but lack a relational data model
and transactionality.

.. _embedded: https://docs.python.org/3/library/sqlite3.html
.. _SQLite: https://www.sqlite.org/
.. _ZODB: http://www.zodb.org/en/latest/
.. _memcached: https://memcached.org/
.. _cassandra: http://cassandra.apache.org/
.. _couchdb: http://couchdb.apache.org/
.. _mongodb: https://www.mongodb.com/


Relativity: Relational à la carte
'''''''''''''''''''''''''''''''''

In this design space, Relativity offers a relational feature set and nothing else.
Relativity allows you to build in-memory data structures that represent relationships
among arbitrary Python objects and then execute queries over those objects and
relationships via a very natural and pythonic API.


=============  ====================
  SQL            Relativity
-------------  --------------------
result-set     sets and M2Ms
join           chain and attach
order by       sort and sorted
where-clause   list comprehension
=============  ====================


Architecture
------------

The fundamental unit of Relativity is the *relation*, in the form of
the ``M2M``.  All other data structures are
various types of ``M2M`` containers.  An ``M2M`` is a very simple
data structure that can be represented as two dicts:

.. code-block:: python

    {key: set(vals)}
    {val: set(keys)}

The main job of the ``M2M`` is to broadcast changes to the
underlying ``dict`` and ``set`` instances such that they are kept in
sync, and to enumerate all of the key, val pairs.

Similarly, the higher order data structures --
``M2MGraph``, ``M2MChain``, and ``M2MStar`` -- broadcast changes to
underlying ``M2M`` s and can return and enumerate them.

``M2MChain`` and ``M2MStar``: rows of relations
'''''''''''''''''''''''''''''''''''''''''''''''

``M2MChain`` and ``M2MStar`` are implemented as thin wrappers over a ``list``
of ``M2M``.  The main feature they bring provide "row-iteration".  The difference
between them is how they defined a row.  ``M2MChain`` represents relationships
that connect end-to-end.  ``M2MStar`` represents relationships that all
point to the same base object, similar to a `star schema`_.

.. _star schema: https://en.wikipedia.org/wiki/Star_schema

Shared ``M2M`` s
''''''''''''''''

All of the higher order data structures are concerned with the structure
between and among ``M2M`` s.  The contents within a particular ``M2M`` does
not need to maintain any invariants.  That is, if all of the ``M2M`` s within
one of the higher order data structures were scrambled up, the higher order
data structure would still be valid.

(Contrast with, if you were to scramble
the key sets and val sets around within an ``M2M``, it would be totally
inconsistent.)

This has important consequences, because it means that various instances
of ``M2MGraph``, ``M2MChain``, and ``M2MStar`` may *share* their underlying
``M2M`` s, and continue to update them.  This means that all of these higher
order data structures can be treated as cheap and ephemeral.

For example, ``M2MGraph.chain(*cols)`` will construct and return a new
``M2MChain`` over the ``M2M`` s linking the passed columns.  All that
actually happens here is the ``M2MGraph`` is queried for the underlying
``M2M`` s, then the list of ``M2M`` s is passed to the ``M2MChain``
constructor which simply holds a reference to them.

Another way to think of ``M2MGraph``, ``M2MChain`` and ``M2MStar`` is
as cheap views over the underlying ``M2M`` s.  No matter how much data is in
the underlying ``M2M`` s, assembling one of these higher order data structures
over top has a fixed, low cost.


Relativity & Python Ecosystem
-----------------------------

Pandas_
'''''''

Both Relativity and Pandas enable clean extraction of data from a SQL database
to an in-memory data structure which may be further processed.  Both libraries
provide data structures that can easily express queries over the in-memory
data-set that would otherwise be very difficult and tempt a developer to go
back to the database multiple times.

This sounds like Relativity and Pandas should be in competition; but, in practice
they are complementary.  Whereas Pandas is excellent at representing tabular
data in rows and columns, Relativity excels at representing the foreign key
relationships that connect rows in different tables.  Pandas makes it easy
to take a SQL result set and further refine it by filtering rows and addding
columns.  Relativity makes it easy to extract the foreign key relationships
among many tables and further refine them by filtering by connectedness and
adding additional relationships.

.. _Pandas: http://pandas.pydata.org/pandas-docs/stable/getting_started/overview.html


When to Use
"""""""""""

Use Pandas_ for doing analysis of data within rows of a table; use
Relativity for doing analysis of the relationships between rows of
different tables.

Coming back to the students-and-classes example:

.. code-block:: python

    class Enrollment(models.Model):
         student = models.ForeignKey(Student)
         class = models.ForeignKey(Class)
         grade = models.FloatField()  # 0.0 - 5.0

    # Pandas is great at determining each students GPA
    enrollments_data_frame.group_by(['student']).mean()


Better Together
"""""""""""""""

At a low-level, a Pandas_ ``Series`` and a Relaitivity ``M2M`` can
both represent multiple values per key, so it is easy to convert
between the two.

.. code-block:: python

    >>> import pandas
    >>> import relativity
    >>> s = pandas.Series(data=[1, 2, 2], index=['a', 'a', 'b'])
    >>> s
    a    1
    a    2
    b    2
    dtype: int64
    >>> m2m = relativity.M2M(s.items())
    >>> m2m
    M2M([('a', 1L), ('a', 2L), ('b', 2L)])
    >>> keys, vals = zip(*m2m.iteritems())
    >>> s2 = pandas.Series(data=vals, index=keys)
    >>> s2
    a    1
    a    2
    b    2
    dtype: int64


NetworkX_
'''''''''

NetworkX_ is the "graph theory library" of Python:

"NetworkX is a Python package for the creation, manipulation,
and study of the structure, dynamics, and functions of complex networks."

NetworkX_ is great at representing arbitrarily connections among a group
of nodes.  Relativity has relationship-centric APIs and data-structures,
wehere the ``M2M`` represents a single relationship, and ``M2MChain``,
``M2MStar``, and ``M2MGraph`` build higher order connections.  

Underneath, both are backed by ``dict``.


.. _NetworkX: https://networkx.github.io/

