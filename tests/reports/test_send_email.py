"""Tests for the Resend sender (reports/send_email.py); no network."""

from __future__ import annotations

import pytest

from pacific_peering.reports import send_email


class _Resp:
    def __init__(self, status, payload):
        self.status_code, self._payload, self.text = status, payload, str(payload)

    def json(self):
        return self._payload


def test_send_posts_html_and_text_with_bearer_key(monkeypatch):
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, json=json)
        return _Resp(200, {"id": "abc123"})

    monkeypatch.setattr(send_email.requests, "post", fake_post)
    assert send_email.send("to@example.org", "from@example.org", "S", "<b>h</b>", "t", "KEY") == "abc123"
    assert seen["url"] == send_email.RESEND_URL
    assert seen["headers"] == {"Authorization": "Bearer KEY"}
    assert seen["json"] == {"from": "from@example.org", "to": ["to@example.org"], "subject": "S",
                            "html": "<b>h</b>", "text": "t"}


def test_rejection_raises_without_leaking_the_key(monkeypatch):
    monkeypatch.setattr(send_email.requests, "post",
                        lambda *a, **k: _Resp(403, {"message": "The domain is not verified."}))
    with pytest.raises(RuntimeError) as err:
        send_email.send("to@example.org", "from@example.org", "S", "h", "t", "SECRET-KEY")
    assert "not verified" in str(err.value) and "SECRET-KEY" not in str(err.value)


def test_missing_key_entry(tmp_path):
    secrets = tmp_path / "secrets.yaml"
    secrets.write_text("ripe_atlas_key: x\n")
    with pytest.raises(KeyError):
        send_email.load_resend_api_key(secrets)
