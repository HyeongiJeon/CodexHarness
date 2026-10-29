"""Expected behavior for the starter bug fixture; this currently fails."""

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


if __name__ == "__main__":
    unittest.main()
