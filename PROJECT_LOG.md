GOALS
-----

* indexing
  * add indexing / listener attach to M2MGraph
  * when data is overwritten in M2MGraph, need to "unlisten" as well
  * read-only data structures for indexes
  * pairs() turns into an indexing scheme
* consistent, predictable APIs
  * all accessors return "live" sub-objects by default; use .copy() to copy
  * make M2M members private with leading underscores
* tests
  * doctest example
* docs
  * up-to-date for now; need to build up APIs more


2020-01-24
----------
* start measuring coverage
* tox
* travis-ci

COMPLETED
---------

* indexing
  * index data structure
  * M2Ms have "listeners" that can attach to indexes
* make it easier to predict what types come out
  * change .data to .m2ms on chain and graph
  * .chain() on graph
* consistent, predictable APIs
  * M2M.copy(), copy.copy(m2m), M2M.__init__()
    all give decent behaviors now
  * M2MChain has good copy semantics
* star / table data structure
  * where chains are connected left-to-right, stars are
    connected left-to-left
    * that is, a star is a list of m2ms where all keys are
      considered to come from the same domain and all
      values are considered to come from different domains
  * stars are iterable: for key in (all-m2m-keys): yield [m2m.get(key)]
* docs
  * simple example that introduces M2M, Graph, and Chain
