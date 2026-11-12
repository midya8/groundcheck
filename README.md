# GroundCheck

Offline lexical grounding checks with an evidence inspector for claim tokens, citation positions, source scores and numeric occurrences.

[Live inspector](https://midya8.github.io/groundcheck/) · [Evidence contract](EVIDENCE.md) · [Original README](docs/original-readme.md)

## Choose a check

| Question | Entry point | Scope |
| --- | --- | --- |
| Does an answer meet the original lexical gates? | `check` | Maximum single-source token containment, citation resolution and global numeric presence |
| Where does each score and numeric match come from? | `audit`, browser inspector | Complete bounded ASCII evidence under all-source or cited-only policies |

Neither result establishes truth, semantic entailment or source authenticity.
A resolved citation can still point to irrelevant or false content.

## Lexical limits

A marker can resolve while citing the wrong document. A number can exist in a source while belonging to a different claim. Every word can overlap while negation changes the meaning. GroundCheck makes those boundaries visible rather than presenting a clean lexical report as a truth certificate.

The original dependency-free checker, 43 original tests, corpus and offline demo remain. Its default is still maximum distinct-content-token containment in one document across all sources. Citation resolution and global numeric presence remain separate checks. Negation, attribution and coincidental-number false positives are still documented, not silently hidden by a stronger-looking metric.

## Evidence inspector

The independent scalar JavaScript browser computes from editable answer text, source documents, threshold and evidence scope. It shows the same units under all-source and cited-only policies; every source's matched/missing token fraction; full highlighted source documents; and every answer/source numeric match with exact offsets. Stale results hide on edit; export contains the full current computation, including an independently reconstructed original all-source report.

The audit has an explicit bounded ASCII profile: 8 sources, 4,096 characters per text, 64 units, 128 total numeric occurrences and six-digit citation positions. It rejects unsupported input rather than truncating evidence. The original check retains its historical Unicode behavior. See the contract for marker-attachment conventions, no-content/empty-answer conventions and parser limitations.

## CLI

Original default check and gates:

```bash
python -m groundcheck check \
  --sources examples/data/sources.jsonl \
  --answer-file examples/data/answer_grounded.txt \
  --min-support 0.8 --max-unsupported 0 --max-findings 0 \
  --json report.json --markdown report.md
```

Sources are JSONL, one `{"id": "...", "text": "..."}` per line. `doc_id` is accepted and missing ids default to `s1`, `s2`, ... . `[n]` refers to the source's 1-based position, not its id. Source identifiers do not authenticate authors.

Complete audit:

```bash
python -m groundcheck audit --spec examples/audit.json --json evidence.json
```

The audit spec uses `answer`, `sources`, `threshold` and `scope` (`all` or `cited`). Cited scope restricts the eligible documents in each raw sentence unit. It is an additional evidence policy, not a semantic judge or a new default for `check`.

## Corrected defects

- Exact finite decimal comparison replaces float equality, preventing distinct integers above 2^53 and huge finite numbers from aliasing. Equal decimal spellings still match.
- A number before terminal punctuation is recognized without treating dotted versions as numbers. Comma grouping and exponent notation remain limitations.
- Full-precision containment reaches JSON and gates before display rounding. Nonfinite/out-of-range thresholds and invalid count gates fail clearly.

## Verification

```bash
python -m unittest discover -s tests -v
bash examples/demo.sh
PYTHONPATH=. python tools/build_audits.py
npm test
bash tools/wheel_smoke.sh
```

66 Python tests retain all 43 originals unchanged. Exact Fraction references cover 800 decimal comparisons and exhaustive subset containment at four thresholds. Fifty complete audit reports preserve the failure controls. Independent JavaScript and actual headless Chrome check the full computations and rendered evidence, edit invalidation, export and mobile containment. Tests/regeneration run on Python 3.10-3.13; wheel reproduction runs outside the checkout. Node 22+ and Chrome are needed only for browser tests, not the Python library or live inspector.

The original fully offline demo passes its grounded gates and rejects its ungrounded answer using the same sources and answers. These are synthetic lexical/provenance tests, not measured model quality, a RAG factuality benchmark, semantic entailment, source authentication or a security guarantee.

## Prior work and license

Citation evaluation and lexical overlap are prior work. The [contract](EVIDENCE.md#prior-work) links ALCE research and code, its citation-metric discussion, Python numerical/regex documentation and Unicode guidance. No ALCE code or data copied; no ALCE score claimed. Implementation and original synthetic controls by Midya Rahmani. MIT.
