"""Entry points that spend Atlas credits must parse their arguments and fire
only with an explicit `--fire`.

Regression, 2026-10-17: `pacific-peering-auto-classify --help` ran a real
classification pass (it had no argument parser); it stopped only because
the backlog happened to be empty. The two smoketest commands had the same
shape.
"""

from __future__ import annotations

import sys

import pytest

from pacific_peering.analysis import auto_classify
from pacific_peering.analysis.corridor_backlog import CorridorCandidate
from pacific_peering.atlas import smoketest


def _candidate() -> CorridorCandidate:
    return CorridorCandidate(17828, "PG", "Papua New Guinea", 55792, "PG", "Papua New Guinea", "test")


@pytest.fixture
def auto_classify_calls(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(auto_classify, "classify_next", lambda max_corridors=1: calls.append("classify_next") or [])
    monkeypatch.setattr(auto_classify, "classify_corridor", lambda *a, **k: calls.append("classify_corridor"))
    monkeypatch.setattr(auto_classify, "pick_next_corridor", lambda *a, **k: _candidate())
    return calls


def test_auto_classify_help_exits_without_classifying(monkeypatch, auto_classify_calls):
    monkeypatch.setattr(sys, "argv", ["pacific-peering-auto-classify", "--help"])
    with pytest.raises(SystemExit) as exc:
        auto_classify.main()
    assert exc.value.code == 0
    assert auto_classify_calls == []


def test_auto_classify_unknown_flag_errors_without_classifying(monkeypatch, auto_classify_calls):
    monkeypatch.setattr(sys, "argv", ["pacific-peering-auto-classify", "--fier"])
    with pytest.raises(SystemExit) as exc:
        auto_classify.main()
    assert exc.value.code == 2
    assert auto_classify_calls == []


def test_auto_classify_without_fire_is_a_dry_run(monkeypatch, auto_classify_calls):
    monkeypatch.setattr(sys, "argv", ["pacific-peering-auto-classify"])
    auto_classify.main()
    assert auto_classify_calls == []


def test_auto_classify_with_fire_classifies(monkeypatch, auto_classify_calls):
    monkeypatch.setattr(sys, "argv", ["pacific-peering-auto-classify", "--fire"])
    auto_classify.main()
    assert auto_classify_calls == ["classify_next"]


@pytest.fixture
def smoketest_calls(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(smoketest, "run_smoketest", lambda *a, **k: calls.append("outbound") or 1)
    monkeypatch.setattr(smoketest, "run_inbound_smoketest", lambda *a, **k: calls.append("inbound") or 1)
    monkeypatch.setattr(smoketest, "_log_measurement", lambda mid: None)
    return calls


@pytest.mark.parametrize("entry", ["main", "main_inbound"])
def test_smoketest_help_exits_without_firing(monkeypatch, smoketest_calls, entry):
    monkeypatch.setattr(sys, "argv", ["smoketest", "--help"])
    with pytest.raises(SystemExit) as exc:
        getattr(smoketest, entry)()
    assert exc.value.code == 0
    assert smoketest_calls == []


@pytest.mark.parametrize("entry", ["main", "main_inbound"])
def test_smoketest_without_fire_does_not_fire(monkeypatch, smoketest_calls, entry):
    monkeypatch.setattr(sys, "argv", ["smoketest"])
    getattr(smoketest, entry)()
    assert smoketest_calls == []


@pytest.mark.parametrize(("entry", "expected"), [("main", "outbound"), ("main_inbound", "inbound")])
def test_smoketest_with_fire_fires(monkeypatch, smoketest_calls, entry, expected):
    monkeypatch.setattr(sys, "argv", ["smoketest", "--fire"])
    getattr(smoketest, entry)()
    assert smoketest_calls == [expected]
