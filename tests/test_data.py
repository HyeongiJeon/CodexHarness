from __future__ import annotations

import csv
import io
import unittest
from pathlib import Path

from harness.data import aggregate_by_region, clean_sales_csv, format_ratio


ROOT = Path(__file__).resolve().parents[1]


class SalesDataTests(unittest.TestCase):
    def test_sample_cleaning_and_aggregate_match_expected_files(self) -> None:
        source = (ROOT / "examples/data/sales.csv").read_text(encoding="utf-8")
        expected_clean = (ROOT / "examples/data/expected-clean.csv").read_text(encoding="utf-8")
        with (ROOT / "examples/data/expected-regions.csv").open(encoding="utf-8", newline="") as expected_file:
            expected_regions = list(csv.DictReader(expected_file))

        result = clean_sales_csv(source)

        self.assertEqual(result.to_csv(), expected_clean)
        self.assertEqual([(issue.row, issue.code) for issue in result.issues], [
            (6, "duplicate_id"), (7, "missing_value"), (8, "invalid_date"), (9, "invalid_number")
        ])
        self.assertEqual(aggregate_by_region(result.rows), expected_regions)

    def test_malformed_header_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected columns"):
            clean_sales_csv("transaction_id,date,region,units\n")

    def test_noncanonical_dates_and_extreme_currency_are_row_issues(self) -> None:
        header = "transaction_id,date,region,units,revenue\n"
        result = clean_sales_csv(header + "a,20260101,East,1,1\nb,2026-W01-1,East,1,1\nc,2026-01-01,East,1," + "9" * 37 + "\nd,2026-01-01,East,1,0.10\n")
        self.assertEqual([x.code for x in result.issues], ["invalid_date", "invalid_date", "invalid_number"])
        self.assertEqual(result.rows[0]["revenue"], "0.10")

    def test_aggregation_preserves_large_accepted_currency(self) -> None:
        source = "transaction_id,date,region,units,revenue\na,2026-01-01,East,1,99999999999999999999999999.99\nb,2026-01-01,East,1,99999999999999999999999999.99\n"
        result = clean_sales_csv(source)
        self.assertEqual(result.issues, ())
        totals = aggregate_by_region(result.rows)[0]
        self.assertEqual(totals["revenue"], "199999999999999999999999999.98")
        self.assertEqual(totals["revenue_per_unit"], "99999999999999999999999999.99")

    def test_extra_columns_and_zero_unit_group_are_handled_explicitly(self) -> None:
        source = "transaction_id,date,region,units,revenue\nA,2026-01-01,Zero,0,0.00\nB,2026-01-01,Other,1,2.00,unexpected\n"
        result = clean_sales_csv(source)
        self.assertEqual([(issue.row, issue.code) for issue in result.issues], [(3, "extra_columns")])
        self.assertEqual(aggregate_by_region(result.rows), [{
            "region": "Zero", "units": "0", "revenue": "0.00", "revenue_per_unit": ""
        }])

    def test_ratio_rounding_and_zero_denominator(self) -> None:
        self.assertEqual(format_ratio(1, 8, 2), "0.13")
        self.assertEqual(format_ratio(0, 0), "")
        self.assertEqual(format_ratio(1, 0), "undefined")


if __name__ == "__main__":
    unittest.main()
