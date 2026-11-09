# Evidence contract

GroundCheck is a lexical tripwire, not semantic entailment. A report can be clean while its claim is false. The original all-document checker remains the default CLI. This audit exposes complete evidence and a separate citation-scoped policy, not a replacement judge model.

## Preserved baseline and corrected arithmetic

The original 43 tests, example sources, grounded/ungrounded answers and offline demo remain byte-identical. The original README is retained at [docs/original-readme.md](docs/original-readme.md). The default still chooses the document with maximum distinct-content-token containment, not a union of documents. Its documented negation, attribution and coincidental-number limitations remain.

Three implementation defects are corrected:

1. Numeric equality previously converted different decimal strings to floats. `9007199254740993` equaled `9007199254740992`, and two different 310-digit finite integers both became infinity. Finite `Decimal` construction and comparison now preserve literal value. No decimal arithmetic operation rounds those comparisons; construction from strings keeps all digits. Equal decimal spellings such as `1.570` and `1.57`, including negative zero, still match.
2. The numeric regex previously excluded a number immediately followed by a terminal period. Its final boundary now rejects a word character or a dot followed by a digit, rather than every dot. `40.` and `1.57.` are recognized; `3.10.1` is still excluded. This is not a general numeric parser: comma grouping is not validated and exponent notation is not recognized as one number.
3. Per-sentence support and the mean are no longer rounded before JSON output and gates. For two of three content tokens, the real score is below a `.66668` gate even though four-decimal display is `.6667`. Report displays remain four-decimal, but decisions use full precision. Nonfinite, Boolean, negative and above-one support thresholds are rejected. CLI minimum-support gates must be finite in [0,1], and count gates nonnegative.

The historical default strips all answer citation markers before sentence splitting. Its best source is the first document with a strictly better positive score, or none for a zero score. A no-content sentence has support 1 without a source. Its citations are answer-wide, de-duplicated as marker strings, with positions resolved against the supplied source order. Source ids do not authenticate a publisher.

## Complete provenance audit

`python -m groundcheck audit --spec examples/audit.json --json evidence.json`

A spec contains `answer`, `sources` (unique `id` and `text`), optional `threshold` (default .6), and `scope` (`all`, the default, or `cited`). Unknown fields, duplicate JSON keys and nonfinite JSON are rejected by the Python file loader. The browser source editor uses standard JSON parsing, then validates the resulting objects; duplicate object keys in editor text follow standard last-value JSON parsing, so use the exported canonical spec to see what was evaluated.

The independent audit units use the same decimal-masked punctuation/newline regex on the raw answer before removing citations, so offsets remain in the original input. Citation markers belong only to the unit in which they occur. `Claim [1].` has a marker on the claim. `Claim. [1]` has a separate citation-only unit, or its marker begins the next unit if text follows. This explicit convention is not a general citation attachment algorithm. The original report, included separately in every exported witness, can have a different unit count because it strips citations first.

For each raw unit the witness includes:

- exact zero-based, end-exclusive input offsets, raw and citation-stripped text;
- all content-token occurrences with offsets, plus sorted distinct tokens for the denominator;
- every citation occurrence, its position and resolution;
- every source's matched and missing tokens, exact integer numerator/denominator and floating ratio, including sources outside the chosen scope;
- all recognized answer numbers and every equal-valued source occurrence with offsets and eligibility;
- best eligible source, threshold decision, missing-scope/lexical/citation/number findings.

Every source includes its full text, every content-token occurrence and every numeric occurrence. No top-matches-only shortcut or truncated excerpt is used in the audit. The historical report retains its historical 100-character excerpt display, explicitly separate from this complete evidence.

`all` considers every source for each unit. `cited` considers only resolved citation positions in that unit. Both use the best single document, never a union. Ties in the audit choose the first eligible document, including when all scores are zero. No eligible source yields score zero. A no-content unit scores one when any source is eligible. The empty-answer mean is one. These vacuous conventions are shown, not represented as evidence. Invalid citations are still findings even if another citation resolves. A zero threshold can admit zero overlap, but missing resolved citations and numeric evidence still produce their own findings.

All-source versus cited-source comparisons change only eligibility for a fixed unit, not the source text, claim or tokenizer. This is a controlled policy contrast, not a quality comparison. A source containing all words can negate the claim, mention a different entity, or place the number in an unrelated relation. Cited scope does not fix those problems. A correct paraphrase can have low overlap. No source freshness, authenticity, publisher trust, URL validity, factuality, units or entity binding is checked.

## Bounded independent browser

The Python audit and independent scalar JavaScript engine accept the same explicit ASCII profile: 1..8 unique sources, at most 4,096 characters per source and answer, 64 raw units, 128 numeric occurrences across all texts and at most six digits in each answer citation position. Text excludes control characters except tab, CR and LF. The Python spec file is additionally capped at 64 KiB. Unsupported or oversized inputs fail rather than returning a partial witness. The original check is not newly restricted to ASCII and retains its historical Unicode tokenizer semantics. No multilingual parity is claimed.

Within the profile, ASCII character offsets are code-point and UTF-16 offsets simultaneously. Tokens are lowercased `[a-z0-9']+`, with the retained small stopword list removed. Stopword-only and punctuation-only units are not claims of evidence. The JavaScript numeric comparator canonicalizes sign, leading integer zeros and trailing fractional zeros as strings, without converting numeric literals to Number. This independently checks Python Decimal equality. The browser also independently reconstructs the historical all-source report, not only the new policy. Source ids and text are inserted as text nodes, not interpreted as HTML.

The browser recomputes after edits to answer, sources, scope or threshold; it hides stale results and disables export until recomputed. Full JSON export is the actual current computation, not the stored fixture. Stored fixtures are test controls, not precomputed values used to score new input.

## Reproduction and controls

- 66 Python tests, including all 43 originals unchanged. New checks include 800 comparisons against exact Fraction equality for 400 seeded decimal pairs, exhaustive 64-subset containment at four thresholds, precision/overflow/terminal-period controls, full offsets, citation scope, ties, vacuity, strict bounds, CLI gates and export regeneration.
- 50 retained reports: 25 synthetic controls in both scopes. They include resolved/wrong/missing/repeated/unresolvable/post-period citations, negation, wrong entity, coincidental number, paraphrase, cross-document non-union, source ties, decimal/large-integer/overflow/negative-zero/comma/version controls, empty/no-content input and HTML-as-text.
- Independent JavaScript full-report comparisons, including all scalar values, occurrence spans, source scores, citation resolution, findings and the original all-source report.
- Actual Chrome checks every retained computation and displayed source-score row, claim text, complete source text, numeric-group count, stale-input behavior, invalid input, export and 320/390/1280 page containment.
- Regeneration and tests run on Python 3.10-3.13. An isolated installed wheel is imported outside the checkout, verifies eight module origins, regenerates all 50 reports, and runs the audit and original check CLIs. Original offline demo and all three original gates remain.

These are synthetic lexical/number/provenance controls, not a benchmark of RAG factuality. Same-environment byte regeneration does not promise all-platform determinism. Python and JavaScript numerical ratios are compared within 1e-12; decimal equality itself is not a floating tolerance match.

## Prior work

- [Gao, Yen, Yu and Chen, ALCE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.398/) evaluates fluency, answer correctness and citation quality as distinct dimensions. GroundCheck does not run ALCE or reproduce its semantic evaluators or benchmark scores.
- [ALCE repository](https://github.com/princeton-nlp/ALCE/) provides the original research implementation and benchmark. No code or data copied here.
- [ALCE citation/sentence precision discussion](https://github.com/princeton-nlp/ALCE/issues/30) illustrates why citation-level and sentence-level measures need explicit definitions. Our lexical policies are not those metrics.
- [Python Decimal documentation](https://docs.python.org/3/library/decimal.html) explains exact string construction and when arithmetic context affects rounding.
- [Python re documentation](https://docs.python.org/3/library/re.html) defines Unicode/ASCII character classes, lookarounds and multiline matching. Our audit explicitly narrows the cross-runtime contract rather than silently equating regex engines.
- [Unicode Technical Standard #18](https://www.unicode.org/reports/tr18/) describes Unicode regex support levels. This ASCII audit does not claim that level of multilingual support.

Implementation, original synthetic fixtures and inspector by Midya Rahmani. Lexical overlap and citation evaluation are prior work, not newly invented algorithms.
