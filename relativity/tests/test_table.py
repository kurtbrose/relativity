import pytest

from relativity.table import Table


def test():
    users = Table(['name', 'age'])
    users.insert('alice', 42)
    users.insert('bob', 42)
    users.insert('carol', 42)
    assert set(users) == set([
        (0, 'alice', 42),
        (1, 'bob', 42),
        (2, 'carol', 42),
    ])
    del users[0]
    del users[1]
    assert set(users) == set([(2, 'carol', 42)])



def test_new_api():
    # 1 - fill in base rows
    # structure for switchboard is constant per namespace
    # and is filled by one DB hit up front
    switchboard = namespace2switchboard_table(target, namespace)

    # 2 - analyze ruleset to get all required fetchers
    fetchers = derive_fetchers(ruleset)

    # 3 - perform database ops via fetchers, grab data
    fetched_tables = []
    for fetcher in fetchers:
        # things FROM switchboard
        # maybe we can give the whole switchboard
        # and they extract what they need (e.g. matter-id)
        fetched_tables.append(fetcher.fetch(switchboard))

    # 4 - build big combo table
    full_table = switchboard
    for fetched_table in fetched_tables:
        # maybe we can avoid explicit "on" by natural join
        # -- join on columns with the same name
        full_table = full_table.join(
            fetched_table, on=fetched_table.inputs)

    # 5 - evaluate expressions row-by-row
    for row in full_table:
        if eval("foo > 10 and bar == 3", row):
            result.add(row)
        # extra credit -- use set intersection for perf


