from __future__ import print_function

import time

from relativity import M2M, M2MChain, M2MGraph


def test_perf_report():
    print("performance of various operations")
    chunk = range(100)
    interval = 0.01
    nxt = 0
    s = time.time()
    data = M2M()
    while time.time() - s < interval:
        for i in chunk:
            nxt += 1
            data.add(nxt, nxt)
    dur_ms = 1000 * (time.time() - s)
    print("M2M.add(i, i) {} per ms".format(int(nxt / dur_ms)))
    nxt = 0
    s = time.time()
    data = M2M()
    while time.time() - s < interval:
        for i in chunk:
            nxt += 1
            data.add(1, nxt)
    dur_ms = 1000 * (time.time() - s)
    print("M2M.add(1, i) {} per ms".format(int(nxt / dur_ms)))
    nxt = 0
    s = time.time()
    data = M2MChain([M2M(), M2M()])
    while time.time() - s < interval:
        for i in chunk:
            nxt += 1
            data.add(i, i, i)
    dur_ms = 1000 * (time.time() - s)
    print("M2MChain.add(i, i, i) {} per ms".format(int(nxt / dur_ms)))
    nxt = 0
    s = time.time()
    data = M2MChain([M2M(), M2M()])
    while time.time() - s < interval:
        for i in chunk:
            nxt += 1
            data.update([(i, i, i)])
    dur_ms = 1000 * (time.time() - s)
    print("M2MChain.update([(i, i, i)]) {} per ms".format(int(nxt / dur_ms)))
