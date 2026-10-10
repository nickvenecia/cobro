"""Dates the way invoices show them ("Oct 10, 2026") and due dates from payment terms."""

from __future__ import annotations

from datetime import date, timedelta

MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def today() -> date:
    return date.today()


def parse(s: str) -> date | None:
    try:
        return date.fromisoformat(s.strip()) if s else None
    except ValueError:
        return None


def iso(d: date) -> str:
    return d.isoformat()


def fmt(d: date | None) -> str:
    """date(2026, 10, 10) -> "Oct 10, 2026" (the same on every computer, whatever its language)."""
    if d is None:
        return ""
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def due(issued: str, terms_days: int) -> date | None:
    d = parse(issued)
    return d + timedelta(days=max(0, terms_days)) if d else None


def terms_label(days: int) -> str:
    return "Due on Receipt" if days <= 0 else f"Net {days}"
