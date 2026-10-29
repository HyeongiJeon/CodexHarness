# Synthetic benchmark evidence

`sample/` is the actual output of the successful multi-agent practice run, copied
after completion using an explicit allowlist of three source modules and TASK.md.
It is an unrelated synthetic exercise, never a replacement for an exam project.
`evidence.json` is a newly generated selection of nonsecret measurement facts;
raw session messages, tool payloads, authentication and private logs are excluded.

Replay without any AI or network access:

```sh
python3 -m harness benchmark-check benchmarks/sample
```

Hashes in `evidence.json` identify the preserved output. The evaluator is
`harness/benchmark.py`; scenarios cover actual HTTP create/update/error flows,
exact CSV aggregation and ticket-counter regression/state isolation.

The original multi summary's per-scenario A flag was wrong because its loaded
text parser encountered HTTP logs between unittest's label and `ok`. Its CLI
exit and overall acceptance were successful. Original records are retained
locally; the final structured offline recheck reports all three scenarios true.
The original single/smoke runs predate the final orchestration-predicate field;
the public evidence explicitly labels the predicate recomputation.

See [measurement report](../docs/benchmark-results.md) for timing, token scope,
the earlier quota interruption and limitations. Raw evidence remains under the
ignored `.harness/runs/` directories on the preparation machine.
