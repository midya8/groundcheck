# groundcheck

A quick sanity check for RAG answers: does each sentence actually overlap with one of the sources, do the `[n]` citations point at a source that exists, and do the numbers in the answer show up anywhere in the sources? It's purely lexical and runs offline with no dependencies.

I wrote it after seeing too many generated answers cite `[3]` when only two documents were retrieved, or invent a number that appears nowhere.

```bash
python -m groundcheck check \
  --sources examples/data/sources.jsonl \
  --answer-file examples/data/answer_grounded.txt \
  --min-support 0.8 --max-unsupported 0 --max-findings 0
```

Sources are JSONL, one `{"id": ..., "text": ...}` per line, and `[n]` means the n-th source. Add `--json` or `--markdown` to save a report. The gates make it exit non-zero, so it can sit in a test suite.

On the bundled examples, the grounded answer gets 3/3 sentences supported with no findings. The ungrounded one gets flagged for a citation `[3]` with only two sources, a sentence at 0.18 support, and three numbers (97, 50000, 12) that aren't in any source.

## What it can't do

Word overlap isn't meaning. A sentence can share every word with a source and still flip it with a "not". A number can appear in a source but belong to a different claim. A citation can resolve and still point at the wrong document. So treat a clean report as "nothing obviously wrong", not "true".

## Other bits

`python -m groundcheck audit --spec examples/audit.json --json evidence.json` dumps the full per-source scores and number matches. There's a browser version at https://midya8.github.io/groundcheck/ where you can edit the answer and sources and watch the scores change.

Tests: `python -m unittest discover -s tests` (70 tests). `npm test` runs the browser ones.
