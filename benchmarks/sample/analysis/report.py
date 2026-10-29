"""CSV aggregation for the small regional-amount report."""

import csv
from decimal import Decimal, InvalidOperation
from io import StringIO


_HEADER = ("id", "region", "amount")
_ZERO = Decimal("0")


def _parse_amount(value):
    """Return a valid amount as an exact integer number of cents, or ``None``."""
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError):
        return None

    # Decimal accepts values such as NaN and Infinity, which are not amounts.
    if not amount.is_finite() or amount < _ZERO:
        return None

    # The exponent preserves stated precision, including trailing zeroes.
    # Therefore ``1.230`` is rejected instead of silently rounding it.
    if amount.as_tuple().exponent < -2:
        return None

    coefficient = 0
    for digit in amount.as_tuple().digits:
        coefficient = coefficient * 10 + digit
    return coefficient * (10 ** (amount.as_tuple().exponent + 2))


def _format_cents(cents):
    """Format a non-negative integer-cent total without Decimal quantization."""
    whole, fractional = divmod(cents, 100)
    return f"{whole}.{fractional:02d}"


def summarize(text):
    """Return valid CSV amounts summed by region, ordered by region name.

    Input requires the header ``id,region,amount``.  A row is ignored when it
    has the wrong number of columns, a blank required value, an invalid amount,
    or an id that already appeared in an earlier valid row.  Invalid rows do
    not claim an id, so a later valid row with that id can still be included.
    """
    try:
        reader = csv.reader(StringIO(text), strict=True)
        header = next(reader)
    except (csv.Error, StopIteration, TypeError):
        return {}

    if tuple(value.strip() for value in header) != _HEADER:
        return {}

    # Totals are integer cents rather than Decimal additions.  Decimal uses a
    # precision context for arithmetic; integer addition keeps arbitrarily
    # large valid input values exact without context rounding or quantization.
    totals = {}
    accepted_ids = set()
    while True:
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error:
            # The csv reader resumes at the next record after errors such as
            # text following a closing quote.  Skip that malformed record.
            continue

        if len(row) != len(_HEADER):
            continue

        identifier, region, amount_text = (value.strip() for value in row)
        if not identifier or not region or not amount_text:
            continue

        amount = _parse_amount(amount_text)
        if amount is None or identifier in accepted_ids:
            continue

        accepted_ids.add(identifier)
        totals[region] = totals.get(region, 0) + amount

    return {
        region: _format_cents(totals[region])
        for region in sorted(totals)
    }
