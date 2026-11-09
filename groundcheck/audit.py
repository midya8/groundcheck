"""Complete bounded lexical evidence, not semantic entailment.

The cross-runtime audit profile is deliberately ASCII. The original check CLI
remains Unicode-capable under its historical tokenizer. No evidence is truncated.
"""
import json
import math
from pathlib import Path
from .check import CITATION_RE, check_grounding, strip_citations
from .textutil import (WORD_RE, NUMBER_RE, SENTENCE_RE, DECIMAL_RE, STOPWORDS,
                       content_tokens, split_sentences, numbers_present)


def load_spec(path):
    data = Path(path).read_bytes()
    if len(data) > 65536:
        raise ValueError("spec exceeds 64 KiB")
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate JSON key")
            out[key] = value
        return out
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def validate(spec):
    if not isinstance(spec, dict) or set(spec) - {"answer", "sources", "threshold", "scope"}:
        raise ValueError("unknown spec fields")
    for key in ("answer", "sources"):
        if key not in spec:
            raise ValueError("missing " + key)
    threshold = spec.get("threshold", .6)
    if (isinstance(threshold, bool) or not isinstance(threshold, (int, float))
            or not 0 <= threshold <= 1 or not math.isfinite(threshold)):
        raise ValueError("threshold must be finite in [0,1]")
    if spec.get("scope", "all") not in ("all", "cited"):
        raise ValueError("scope must be all or cited")
    sources = spec["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 8:
        raise ValueError("audit needs 1..8 sources")
    texts = [spec["answer"]]
    ids = []
    for source in sources:
        if (not isinstance(source, dict) or set(source) != {"id", "text"}
                or not isinstance(source["id"], str) or not 1 <= len(source["id"]) <= 64
                or not source["id"].isascii()):
            raise ValueError("source requires unique ASCII id and text")
        ids.append(source["id"])
        texts.append(source["text"])
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate source id")
    for text in texts:
        if (not isinstance(text, str) or len(text) > 4096 or not text.isascii()
                or any(ord(c) < 32 and c not in '\t\n\r' for c in text)):
            raise ValueError("audit text must be ASCII, <=4096 chars, no control characters")
    if any(len(m.group(1)) > 6 for m in CITATION_RE.finditer(spec["answer"])):
        raise ValueError("citation positions limited to six digits")
    if len(split_sentences(spec["answer"])) > 64:
        raise ValueError("audit needs <=64 sentence units")
    if sum(len(number_spans(text)) for text in texts) > 128:
        raise ValueError("audit needs <=128 numeric occurrences in total")
    return {"answer": spec["answer"], "sources": sources,
            "threshold": threshold, "scope": spec.get("scope", "all")}


def token_spans(text):
    return [{"token": m.group(), "start": m.start(), "end": m.end()}
            for m in WORD_RE.finditer(text.lower()) if m.group() not in STOPWORDS]


def number_spans(text):
    return [{"literal": m.group(), "number": m.group().replace(',', ''),
             "start": m.start(), "end": m.end()} for m in NUMBER_RE.finditer(text)]


def audit(spec):
    spec = validate(spec)
    answer, sources, threshold, scope = (spec[k] for k in ("answer", "sources", "threshold", "scope"))
    source_rows = []
    for index, source in enumerate(sources):
        source_rows.append({"index": index, **source, "tokens": token_spans(source["text"]),
                            "numbers": number_spans(source["text"])})
    units, findings = [], []
    masked = DECIMAL_RE.sub('\x00', answer)
    for match in SENTENCE_RE.finditer(masked):
        lo, hi = match.span()
        raw = answer[lo:hi]
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        lo, hi = lo + left, lo + right
        raw = answer[lo:hi]
        if not raw:
            continue
        claim = strip_citations(raw)
        # Replace citation positions with spaces to retain exact input offsets.
        plain = CITATION_RE.sub(lambda m: ' ' * len(m.group()), raw)
        words = sorted(set(content_tokens(plain)))
        cites = [{"marker": m.group(), "position": int(m.group(1)),
                  "start": lo + m.start(), "end": lo + m.end(),
                  "valid": 1 <= int(m.group(1)) <= len(sources)}
                 for m in CITATION_RE.finditer(raw)]
        cited = sorted({c["position"] - 1 for c in cites if c["valid"]})
        eligible = list(range(len(sources))) if scope == 'all' else cited
        rows = []
        for source in source_rows:
            available = {t['token'] for t in source['tokens']}
            overlap = sorted(set(words) & available)
            score = len(overlap) / len(words) if words else 1.0
            rows.append({"source_index": source['index'], "eligible": source['index'] in eligible,
                         "matched": overlap, "missing": sorted(set(words) - available),
                         "numerator": len(overlap), "denominator": len(words), "score": score})
        # Match original no-content convention only for all-source scope or a resolved citation.
        best = None
        for row in rows:
            if row['eligible'] and (best is None or row['score'] > best['score']):
                best = row
        score = best['score'] if best else 0.0
        supported = score >= threshold
        nums = []
        for number in number_spans(plain):
            matches = []
            for source in source_rows:
                for occurrence in source['numbers']:
                    if numbers_present(number['number'], [occurrence['number']]):
                        matches.append({"source_index": source['index'], **occurrence,
                                        "eligible": source['index'] in eligible})
            nums.append({**number, "start": number['start'] + lo, "end": number['end'] + lo,
                         "matches": matches, "present": any(m['eligible'] for m in matches)})
        unit = {"index": len(units), "start": lo, "end": hi, "raw": raw, "claim": claim,
                "tokens": words, "token_occurrences": [{**t, "start": lo+t['start'], "end": lo+t['end']}
                                                         for t in token_spans(plain)],
                "citations": cites, "eligible_sources": eligible, "source_scores": rows,
                "best_source": best['source_index'] if best else None,
                "support": score, "supported": supported, "no_content": not words,
                "numbers": nums}
        units.append(unit)
        if scope == 'cited' and not eligible:
            findings.append({"kind": "no_resolved_citation", "unit": unit['index']})
        if not supported:
            findings.append({"kind": "lexical_below_threshold", "unit": unit['index']})
        for citation in cites:
            if not citation['valid']:
                findings.append({"kind": "citation_unresolvable", "unit": unit['index'],
                                 "marker": citation['marker']})
        for number in nums:
            if not number['present']:
                findings.append({"kind": "number_absent_in_scope", "unit": unit['index'],
                                 "number": number['number'], "start": number['start']})
    return {"schema": "groundcheck.evidence.v1", "spec": spec, "sources": source_rows,
            "units": units, "findings": findings,
            "mean_support": sum(u['support'] for u in units) / len(units) if units else 1.0,
            "legacy_all_source_report": check_grounding(answer, sources, threshold)}
