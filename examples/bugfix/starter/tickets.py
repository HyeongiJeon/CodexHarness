"""Starter fixture with one planted boundary bug for review practice."""


def count_open(tickets: list[dict[str, str]]) -> int:
    """Count open tickets in a small synthetic ticket queue."""
    # Planted defect: slicing off the last record loses an open ticket at the boundary.
    return sum(ticket.get("status") == "open" for ticket in tickets[:-1])
