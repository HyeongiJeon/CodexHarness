# Bug-fix fixture

`starter/tickets.py` contains a planted boundary bug. Its regression test
expects both open tickets to be counted, including the last item in the input.
Run it from the starter directory with:

```sh
cd examples/bugfix/starter
python3 -m unittest -v
```

The test is expected to fail before a fix. Keep the fixture source unchanged
until an independent reviewer has diagnosed and repaired it; then rerun the
same regression test and record the diagnosis in the review notes.
