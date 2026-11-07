# GroundCheck

Offline grounding checks for answers against their sources.

GroundCheck verifies that an answer is actually supported by the documents it claims to draw on: citations resolve to real sources, every answer sentence finds lexical support in a source document, and every number in the answer appears in the sources. It is dependency-free and runs fully offline, so grounding becomes a reproducible CI gate instead of a read-it-yourself review.

## Why

RAG pipelines answer with confidence whether or not the answer is grounded. Reviewing every answer by hand does not scale, so GroundCheck turns grounding into deterministic checks:

- **citation validation** - every `[n]` marker must resolve to a provided source, and the report shows how many sources were actually cited;
- **lexical support scoring** - each answer sentence is scored by content-token containment against every source document (stopwords removed); a sentence combining facts from several sentences of one passage is supported by that passage, while a sentence no passage supports is flagged;
- **numeric consistency** - every number in the answer must appear in the sources (exact or equal-value match), catching the most common fabrication: plausible-sounding figures;
- **CI gates** - `--min-support` on mean sentence support, `--max-unsupported` on unsupported sentence count, and `--max-findings` on total findings, each with a failing exit code;
- **reports for review** - terminal summaries, JSON artifacts for tooling, and Markdown reports with per-sentence support tables for CI job summaries.

## Usage

```bash
python3 -m groundcheck check \
  --sources sources.jsonl \
  --answer-file answer.txt \
  --min-support 0.8 --max-unsupported 0 --max-findings 0 \
  --json report.json --markdown report.md
```

Sources are JSONL, one `{"id": "...", "text": "..."}` object per line (`doc_id` also accepted; ids default to `s1`, `s2`, ...). Citation markers in the answer are 1-based positions into the source list.

## Verification

- 40 unit tests cover tokenization, decimal-safe sentence splitting, number extraction and matching, citation parsing, source loading validation, support scoring (including cross-sentence combinations), every finding kind, report escaping and the CLI end to end including all three gates.
- `bash examples/demo.sh` runs fully offline: a grounded answer passes all gates while an ungrounded one (a fabricated test count, a citation with no source, invented claims) is rejected, with JSON and Markdown reports asserted for both.
- CI runs the same suite across Python 3.10-3.13.

GroundCheck measures lexical grounding: token containment, citation resolution and number consistency. These are strong fabrication signals, but they are not semantic entailment - a fully paraphrased-but-true sentence can score low, and a lexically supported sentence can still be subtly wrong. Decimal numbers are handled so `1.57` is one number, not two sentences.

## License

MIT
