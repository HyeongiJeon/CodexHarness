"""Regression coverage for the repaired ticket-counting fixture."""

import unittest

from tickets import count_open


class TicketCountRegression(unittest.TestCase):
    def test_counts_open_ticket_at_end_of_queue(self) -> None:
        tickets = [
            {"id": "T-1", "status": "closed"},
            {"id": "T-2", "status": "open"},
            {"id": "T-3", "status": "open"},
        ]
        self.assertEqual(count_open(tickets), 2)

    def test_empty_and_single_ticket_queues(self) -> None:
        for tickets, expected in [([], 0), ([{"status": "open"}], 1), ([{"status": "closed"}], 0)]:
            with self.subTest(tickets=tickets):
                self.assertEqual(count_open(tickets), expected)

    def test_other_statuses_are_excluded_and_input_is_preserved(self) -> None:
        tickets = [{"status": "open"}, {"status": "closed"}, {}, {"status": "OPEN"}, {"status": "open"}]
        original = [ticket.copy() for ticket in tickets]
        self.assertEqual(count_open(tickets), 2)
        self.assertEqual(tickets, original)


if __name__ == "__main__":
    unittest.main()
