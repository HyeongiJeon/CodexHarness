"""Corrected synthetic ticket-counting exercise."""


def count_open(tickets: list[dict[str, str]]) -> int:
    """Count every open ticket, including the final record, without mutation."""
    return sum(ticket.get("status") == "open" for ticket in tickets)
