"""Send a rendered email through Resend's API.

Used by the owner's unattended daily check (a local wrapper kept outside the
repo) after `pacific-peering-status-email` has rendered the HTML and text.
Resend delivers the HTML as written, unlike the Gmail connector, whose
sanitizer strips CSS backgrounds. Recipient and sender are passed in, never
stored here; the API key comes from the gitignored `secrets.yaml`
(`resend_api_key`) and is never logged or echoed.

`uv run pacific-peering-send-email --to ADDR --from ADDR --subject S --html F --text F`
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import requests
import yaml

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"
DEFAULT_SECRETS_PATH = Path("secrets.yaml")
_SECRET_KEY_NAME = "resend_api_key"


def load_resend_api_key(path: Path = DEFAULT_SECRETS_PATH) -> str:
    """The Resend API key from `secrets.yaml`.

    Raises:
        FileNotFoundError: If `path` doesn't exist.
        KeyError: If it has no `resend_api_key` entry.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; expected a '{_SECRET_KEY_NAME}' entry")
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or not data.get(_SECRET_KEY_NAME):
        raise KeyError(f"{path} must contain a '{_SECRET_KEY_NAME}' entry")
    return data[_SECRET_KEY_NAME]


def send(to: str, sender: str, subject: str, html: str, text: str, api_key: str, timeout: float = 30.0) -> str:
    """Send one email; returns Resend's message id.

    Raises:
        RuntimeError: If Resend rejects the request (its error message, never the key).
    """
    response = requests.post(
        RESEND_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"from": sender, "to": [to], "subject": subject, "html": html, "text": text},
        timeout=timeout,
    )
    if response.status_code >= 300:
        try:
            message = response.json().get("message", response.text)
        except ValueError:
            message = response.text
        raise RuntimeError(f"Resend rejected the email (HTTP {response.status_code}): {message[:300]}")
    return response.json().get("id", "")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--to", required=True)
    parser.add_argument("--from", dest="sender", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--text", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        message_id = send(args.to, args.sender, args.subject, args.html.read_text(), args.text.read_text(),
                          load_resend_api_key())
    except (RuntimeError, requests.exceptions.RequestException, FileNotFoundError, KeyError) as exc:
        logger.error("Email not sent: %s", exc)
        sys.exit(1)
    print(f"Sent via Resend (id {message_id})")


if __name__ == "__main__":
    main()
