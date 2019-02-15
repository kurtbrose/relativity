# relativity
relational python object data structures

## Example

## Design Philosophy
### DB Feature Sets
A typical SQL database, such as PostGres, MySQL, SQLServer, Oracle, or DB2
offers many features which can be split into four categories:

* relational data model and queries
* network protocol and multiple concurrent connections
* transactions, atomic updates, and [MVCC](https://en.wikipedia.org/wiki/Multiversion_concurrency_control)
* persistent storage, backups, and read replicas

Let's call these "relational", "network", "transactional", and "persistence" feature sets.

### "Alternative" Databases
The most widely used alternative is probably [SQLite](https://www.sqlite.org/).  SQLite
has relational, transactional, and persistence feature sets but does not have
a network protocol.  Instead it must be [embedded](https://docs.python.org/3/library/sqlite3.html)
as a library inside another application.

Another example is the venerable [ZODB](http://www.zodb.org/en/latest/).  ZODB has
network, transactional, and persistence feature sets but replaces the relational data model
with an object data model.

As an extreme example of how less can be more, [memcached](https://memcached.org/) has
only network features.  Data is stored ephemerally in the form of opaque blobs without
any data model.  There is no atomicity of updates: there is no way to ensure that
two writes either both succeed or both fail.

The so-called "NoSQL" databases ([cassandra](http://cassandra.apache.org/),
[couchdb](http://couchdb.apache.org/), [mongodb](https://www.mongodb.com/), etc)
generally provide network and persistence features but lack a relational data model
and transactionality.

## Relativity: Relational à la carte

In this design space, Relativity offers a relational feature set and nothing else.
Relativity allows you to build in-memory data structures that represent relationships
among arbitrary Python objects and then execute queries over those objects and
relationships via a very natural and pythonic API.


SQL | Relativity
--- | ---
result-set | sets and M2Ms
join | chain and attach
order by | sort and sorted
where-clause | list comprehension