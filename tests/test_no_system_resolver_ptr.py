"""Guard: no reverse lookup under src/ may go through the system resolver.

2026-11-06: glibc reverse lookups sent through lab's Pi-hole (::1) tripped its
per-client rate limit and took all of lab's DNS down twice. Every PTR lookup
goes through `analysis.ptr_lookup` (unbound 127.0.0.1:5335, rate-capped)."""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
FORBIDDEN = re.compile(r"gethostbyaddr|getnameinfo")


def test_src_never_uses_the_system_resolver_for_ptr():
    hits = [f"{p.relative_to(SRC)}:{i}" for p in SRC.rglob("*.py")
            for i, line in enumerate(p.read_text().splitlines(), 1) if FORBIDDEN.search(line)]
    assert hits == []
