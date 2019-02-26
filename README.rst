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
        for idx, city in enumerate(cities):
            if city == restaurant.city:
                restaurants_in_city[idx] += 1
                break
        else:
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


List to Dict to M2M
'''''''''''''''''''

The same differences that showed up when programming with
and without hashmaps will come up again when comparing
programming with single-index hashmaps to relativistic
multi-index hashmaps.

Returning to the restaurants and cities example, what if
a restaurant can have multiple locations and we need to
keep track of how many cities each restaurant is in,
as well as how many restaurants are in each city.

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

    def get_restaurant_count(city):
        return len(restaurants_in_city.get(city, ()))

    def get_city_count(restaurant):
        return len(cities_of_restaurant.get(restaurant, ()))


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

    def get_restaurant_count(city):
        return len(restaurant_city_m2m.inv[city])

    def get_city_count(restaurant):
        return len(restaurant_city_m2m[restaurant])


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
