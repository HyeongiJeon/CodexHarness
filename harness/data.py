"""Small, deterministic CSV cleaning helpers for the synthetic sales exercise.

The exercise intentionally uses only Python's standard library. It accepts a
fixed five-column CSV, keeps the first valid row for each transaction ID, and
reports (rather than silently coercing) incomplete or malformed rows.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from typing import Iterable


FIELDS = ("transaction_id", "date", "region", "units", "revenue")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class DataIssue:
    row: int
    code: str
    message: str


@dataclass(frozen=True)
class CleanResult:
    rows: tuple[dict[str, str], ...]
    issues: tuple[DataIssue, ...]

    def to_csv(self) -> str:
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(self.rows)
        return output.getvalue()


def clean_sales_csv(source: str) -> CleanResult:
    """Clean the sample sales schema and return accepted rows plus row issues.

    Required fields are trimmed. Missing fields, invalid ISO dates, negative
    units/revenue, malformed numbers, and duplicate transaction IDs are
    rejected. Duplicate detection is case-sensitive and applies to valid rows;
    the first valid occurrence wins. Currency is restricted to two decimals.
    """

    reader = csv.DictReader(io.StringIO(source, newline=""))
    if reader.fieldnames is None:
        raise ValueError("CSV must include a header row")
    header = [name.strip() if name is not None else "" for name in reader.fieldnames]
    if tuple(header) != FIELDS:
        raise ValueError(f"expected columns in this order: {', '.join(FIELDS)}")
    reader.fieldnames = header

    rows: list[dict[str, str]] = []
    issues: list[DataIssue] = []
    seen_ids: set[str] = set()
    for row_number, raw in enumerate(reader, start=2):
        values = {key: (raw.get(key) or "").strip() for key in FIELDS}
        if None in raw:
            issues.append(DataIssue(row_number, "extra_columns", "row has extra columns"))
            continue
        missing = [key for key, value in values.items() if not value]
        if missing:
            issues.append(DataIssue(row_number, "missing_value", f"missing: {', '.join(missing)}"))
            continue
        if values["transaction_id"] in seen_ids:
            issues.append(DataIssue(row_number, "duplicate_id", "duplicate transaction_id; first valid row kept"))
            continue
        try:
            parsed_date = date.fromisoformat(values["date"])
            if parsed_date.isoformat() != values["date"]:
                raise ValueError("noncanonical date")
        except ValueError:
            issues.append(DataIssue(row_number, "invalid_date", "date must use YYYY-MM-DD"))
            continue
        try:
            units = int(values["units"])
            revenue = Decimal(values["revenue"])
            if not revenue.is_finite():
                raise InvalidOperation
            if units < 0 or revenue < 0:
                raise ValueError
            if revenue.as_tuple().exponent < -2:
                raise InvalidOperation
            # Reject values outside this small helper's supported Decimal context
            # as row issues; never let malformed/extreme input abort the import.
            formatted_revenue = format(revenue.quantize(CENT), ".2f")
        except (ValueError, InvalidOperation):
            issues.append(DataIssue(row_number, "invalid_number", "units must be a non-negative integer and revenue non-negative currency with at most two decimals"))
            continue
        seen_ids.add(values["transaction_id"])
        rows.append({
            "transaction_id": values["transaction_id"],
            "date": parsed_date.isoformat(),
            "region": values["region"],
            "units": str(units),
            "revenue": formatted_revenue,
        })
    return CleanResult(tuple(rows), tuple(issues))


def aggregate_by_region(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    """Return stable region totals and cents-rounded revenue per unit."""

    totals: dict[str, tuple[int, Decimal]] = {}
    for row in rows:
        region = row["region"]
        units, revenue = totals.get(region, (0, Decimal("0.00")))
        amount = Decimal(row["revenue"])
        with localcontext() as context:
            context.prec = max(28, len(revenue.as_tuple().digits), len(amount.as_tuple().digits)) + 2
            total = revenue + amount
        totals[region] = (units + int(row["units"]), total)
    result = []
    for region in sorted(totals):
        units, revenue = totals[region]
        with localcontext() as context:
            context.prec = max(28, len(revenue.as_tuple().digits) + len(str(units)) + 4)
            per_unit = (revenue / units).quantize(CENT, rounding=ROUND_HALF_UP) if units else None
        result.append({
            "region": region,
            "units": str(units),
            "revenue": format(revenue, ".2f"),
            "revenue_per_unit": format(per_unit, ".2f") if per_unit is not None else "",
        })
    return result


def format_ratio(numerator: Decimal | int, denominator: Decimal | int, places: int = 2) -> str:
    """Format a ratio with half-up rounding; return an empty value for 0/0."""

    if places < 0:
        raise ValueError("places must be non-negative")
    denominator = Decimal(denominator)
    if denominator == 0:
        return "" if Decimal(numerator) == 0 else "undefined"
    quantum = Decimal(1).scaleb(-places)
    return format((Decimal(numerator) / denominator).quantize(quantum, rounding=ROUND_HALF_UP), f".{places}f")
