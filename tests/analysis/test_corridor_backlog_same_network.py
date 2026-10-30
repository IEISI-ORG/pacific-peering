"""Sibling ASNs of one operator never become a corridor.

Finding #221 (AS45345 -> AS136402, both Nautile) was filed as candidate
peering but traced Nautile's internal routing. The backlog's tested-pairs
file kept it from being re-proposed, but that file is gitignored; this
guard holds even if it's lost.
"""

from pacific_peering.analysis.corridor_backlog import _same_network


def test_nautile_siblings_are_one_network_both_ways() -> None:
    assert _same_network(45345, 136402)
    assert _same_network(136402, 45345)


def test_same_asn_is_one_network() -> None:
    assert _same_network(45345, 45345)


def test_unrelated_asns_are_not() -> None:
    # OPT-NC is the siblings' shared upstream, not part of the group.
    assert not _same_network(45345, 18200)
    assert not _same_network(136402, 18200)
    assert not _same_network(141197, 136402)
