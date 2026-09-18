# Contributing

The most useful thing you can send is a bench-readiness answer that looks wrong: a
capability the engine calls ready when nobody on the bench could do the work, or
the other way round. Open an issue with the demand line and the profiles it was
matched against.

Before pushing, run what CI runs:

```bash
python -m unittest discover -s tests -v   # the engine, with tests for the bugs already fixed
python engine.py > /dev/null              # the whole pipeline end to end, no key needed
```

The engine runs on a deterministic stub when there is no API key, so none of this
needs one.

## Adding a capability alias

`data/taxonomy.json` says which names for a capability mean the same thing, for
example that a demand signal called "Claude Cowork / GenAI tooling" is what people's
profiles call "Data & AI / GenAI". It is a hand-kept list and it is deliberately not
a fuzzy match: a wrong alias claims bench readiness that does not exist. Add a line
only when the two names truly mean the same capability, and add a test in
`tests/test_engine.py` that shows the readiness answer changing because of it.

## The classifier's second opinion

The rules in `engine.classify()` are the reference answer. The model only gives a
second opinion and is never allowed to override them. `eval/cases.json` holds the
labelled notes used to measure how sure it is. A new case should be a made-up
person and a made-up firm, and should say `expect_confidence` only where a human
would call the note clearly clear or clearly ambiguous.

Live readings come from the manual `calibrate classifier` workflow, which needs an
`ANTHROPIC_API_KEY` repository secret. A number goes into the README by hand, after
reading the run, and never from a script.
