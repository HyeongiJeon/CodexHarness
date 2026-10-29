# Data contracts

Before joins or derived metrics, record input grain, candidate key, expected cardinality, units, timezone, null policy, duplicate policy, and filters. Measure key uniqueness on both join sides and compare row counts before and after. Define whether malformed records are rejected, quarantined, or retained with explicit status; do not silently impute. Reconcile totals to source-level calculations and hand-check representative records. For large inputs, use streaming or chunks without changing semantics.
