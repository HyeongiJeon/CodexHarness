# Synthetic sales CSV exercise

`sales.csv` uses a fixed schema: transaction ID, ISO calendar date, region,
whole-number units, and non-negative revenue with at most two decimal places.
`harness.data.clean_sales_csv` trims whitespace, retains the first valid row
for each case-sensitive transaction ID, and rejects rows with missing values,
extra columns, invalid dates, invalid numbers, or duplicate IDs. It returns a
structured issue per rejected row instead of silently guessing a replacement.

The expected clean output is `expected-clean.csv`. Summaries group by region,
sum units and exact decimal revenue, then calculate revenue per unit rounded
half-up to cents. A region with zero units has a blank ratio. Expected
aggregates are in `expected-regions.csv`.
