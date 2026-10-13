"""Feedback: ideas and problems, sent to the people who make Saldo.

Where it goes isn't set up yet. Until it is, every message waits in an outbox (feedback/ in the data
folder) and goes out once a sender is connected. To connect one, set ADDRESS to a support email (messages
then open in your email app, ready to send) or write a FeedbackSender and pass it to use().

What's in a message: what you typed, your email if you add it, and (only if you tick it) Saldo's
version and the kind of computer. Never your invoices or clients.
"""

from __future__ import annotations

import platform
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from saldo import __version__
from saldo.core.log import get_logger
from saldo.core.paths import data_dir

log = get_logger(__name__)

ADDRESS = ""  # a support email; "" until there is one
KINDS = [("idea", "Idea"), ("problem", "Problem"), ("other", "Other")]
MAX_CHARS = 5000


class FeedbackError(OSError):
    pass


@dataclass
class Feedback:
    kind: str
    message: str
    email: str = ""
    details: dict = field(default_factory=dict)
    written: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M"))


def details() -> dict:
    """The app version and the kind of computer (nothing personal)."""
    return {
        "saldo": __version__,
        "system": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
    }


class FeedbackSender:
    """Where feedback goes. This one isn't connected: messages wait in the outbox."""

    connected = False

    def send(self, fb: Feedback) -> None:
        raise FeedbackError("not connected")


_sender: FeedbackSender = FeedbackSender()


def sender() -> FeedbackSender:
    return _sender


def use(s: FeedbackSender) -> None:
    global _sender
    _sender = s


def make(kind: str, message: str, email: str = "", include_details: bool = True) -> Feedback:
    message = message.strip()
    if not message:
        raise FeedbackError("Write something first.")
    kind = kind if kind in dict(KINDS) else "other"
    return Feedback(kind, message[:MAX_CHARS], email.strip()[:200], details() if include_details else {})


def outbox() -> Path:
    return data_dir() / "feedback"


def send(fb: Feedback) -> bool:
    """Send it, or keep it in the outbox. True if it went out now."""
    if sender().connected:
        try:
            sender().send(fb)
            return True
        except OSError:
            log.info("feedback didn't send; keeping it in the outbox")
    keep(fb)
    return False


def keep(fb: Feedback) -> Path:
    from saldo.core.store import write_json

    path = outbox() / f"{time.strftime('%Y%m%d-%H%M%S')}-{fb.kind}-{uuid.uuid4().hex[:6]}.json"
    write_json(path, asdict(fb))  # a temp file, then moved into place: never half a message
    return path
