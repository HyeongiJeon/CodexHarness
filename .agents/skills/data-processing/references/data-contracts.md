# Data contracts

## Large dataset analysis

Use the local harness commands when they fit the requested operation. They avoid loading every record into the conversation and provide a bounded profile or grouped result:

```sh
python3 -m harness data profile FILE --sample-rows 1000 --encoding cp949
python3 -m harness data aggregate FILE... --config CONFIG.json
```

`profile` reports schema and quality indicators from a bounded sample; state the sample limit and encoding in conclusions. A sample can miss rare categories or late-file defects, so inspect a larger or full-file profile when the decision requires it. Choose encoding from source evidence; `cp949` is an example for a known Korean legacy CSV, not a universal default. Keep the original file unchanged.

`aggregate` takes a JSON config with these supported keys: `group_by`, `value`, `id_column`, `required`, `join` (`path`, `left_key`, `right_key`, optional `columns` and `how`), `where`, `units`, `date_columns`, and `max_groups`. Specify only applicable keys. Record grain and key expectations before joining, ensure the join does not multiply rows unexpectedly, set `max_groups` when cardinality could be high, and state units and date interpretation. Reconcile important totals against source-level calculations and hand-check representative groups. Preserve the config with the result for reproducibility.

The legacy form `python3 -m harness data examples/data/sales.csv` remains available for the bundled sales example.

## Data contracts

Before joins or derived metrics, record input grain, candidate key, expected cardinality, units, timezone, null policy, duplicate policy, and filters. Measure key uniqueness on both join sides and compare row counts before and after. Define whether malformed records are rejected, quarantined, or retained with explicit status; do not silently impute. Reconcile totals to source-level calculations and hand-check representative records. For large inputs, use streaming or chunks without changing semantics.

**Output contract:** Include the input paths, chosen encoding, profile/sample coverage, config, units, filters, join/cardinality checks, and limitations alongside derived results. Distinguish observed values from estimates and sample-based findings. Do not claim a full-file property from a sample alone.
