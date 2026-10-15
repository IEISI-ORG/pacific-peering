"""`corridor_backlog.md` keeps its timestamp when nothing else changed.

The session-start check regenerates the backlog every session; bumping
"Last regenerated" on an otherwise identical file left the tree dirty and
gave the cron jobs a timestamp-only diff to commit.
"""

from pathlib import Path

from pacific_peering.analysis.corridor_backlog import _write_backlog_if_changed

OLD = (
    "# Corridor Backlog\n\nLast regenerated: 2026-10-12T21:42:26+00:00\n"
    "Candidates: 0 | New probes since last run: 0 | New RIS relationships since last run: 0\n"
)


def test_timestamp_only_change_leaves_file_untouched(tmp_path: Path) -> None:
    path = tmp_path / "corridor_backlog.md"
    path.write_text(OLD)
    new = OLD.replace("2026-10-12T21:42:26", "2026-10-15T07:13:11")

    assert _write_backlog_if_changed(path, new) is False
    assert path.read_text() == OLD


def test_real_change_rewrites_file_with_new_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "corridor_backlog.md"
    path.write_text(OLD)
    new = OLD.replace("2026-10-12T21:42:26", "2026-10-15T07:13:11").replace(
        "Candidates: 0", "Candidates: 1"
    )

    assert _write_backlog_if_changed(path, new) is True
    assert path.read_text() == new


def test_missing_file_is_written(tmp_path: Path) -> None:
    path = tmp_path / "corridor_backlog.md"

    assert _write_backlog_if_changed(path, OLD) is True
    assert path.read_text() == OLD


def test_default_run_is_read_only(monkeypatch) -> None:
    """The session-start check is a query: it must not regenerate anything."""
    from pacific_peering.analysis import corridor_backlog

    def _no_write(*args, **kwargs):
        raise AssertionError("read-only run called build_corridor_backlog")

    monkeypatch.setattr(corridor_backlog, "build_corridor_backlog", _no_write)
    monkeypatch.setattr(corridor_backlog, "enumerate_candidate_corridors", lambda: [])

    corridor_backlog.main([])


def test_write_flag_regenerates(monkeypatch) -> None:
    from pacific_peering.analysis import corridor_backlog

    calls: list[bool] = []
    monkeypatch.setattr(
        corridor_backlog, "build_corridor_backlog", lambda: calls.append(True) or []
    )

    corridor_backlog.main(["--write"])

    assert calls == [True]
