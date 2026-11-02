# Measurement rules and checklist

- Same machine, same input, same command for before and after. Record input size, repeat count, warmup, median and min–max, peak RSS (`max_rss_kb`; KiB on Linux), Python/runtime version.
- `measure` runs the command repeatedly, hashes stdout and refuses to compare when output differs (`output_changed`). Make the command print a deterministic result (e.g. a checksum of the output) so the hash is a correctness oracle.
- Treat `distinguishable=false` as noise. Do not report a ratio from one run.
- Complexity checklist: nested loops over the same collection; list membership vs set/dict; repeated sorting; string concatenation in loops; N+1 queries; missing index (check `EXPLAIN QUERY PLAN`); reading whole files instead of streaming; recomputation without caching; unnecessary copies.
- Memory: compare peak RSS, not only time. Streaming/chunking trades time for memory; state which was the goal.
- Limits to report: sampled sizes, warm cache effects, machine load, platform differences from the grading environment.
