"""Grounding checks: citation validity, lexical support, numeric consistency."""

import re
import math

from .textutil import content_tokens, extract_numbers, numbers_present, split_sentences

CITATION_RE = re.compile(r"\[(\d+)\]")

# A sentence with at least this fraction of its content tokens present in a
# single source document counts as lexically supported. Support is measured
# at document granularity because RAG answers draw on whole retrieved
# passages, and one answer sentence often combines facts from several
# sentences of the same passage.
DEFAULT_SUPPORT_THRESHOLD = 0.6


def find_citations(answer):
    """Ordered, de-duplicated citation numbers referenced in the answer."""
    seen = []
    for num in CITATION_RE.findall(answer):
        if num not in seen:
            seen.append(num)
    return seen


def strip_citations(answer):
    return CITATION_RE.sub("", answer)


def support_score(sentence, source_docs):
    """Best containment of the sentence's content tokens in one source document.

    Containment is the fraction of the answer sentence's distinct content
    tokens that appear anywhere in a single source document. source_docs is a
    list of (index, text) pairs. Returns (score, best index, best matching
    sentence within that document for display).
    """
    tokens = set(content_tokens(sentence))
    if not tokens:
        return 1.0, -1, ""
    best = (0.0, -1, "")
    for idx, text in source_docs:
        doc_tokens = set(content_tokens(text))
        if not doc_tokens:
            continue
        score = len(tokens & doc_tokens) / len(tokens)
        if score > best[0]:
            sentences = split_sentences(text)
            excerpt = ""
            if sentences:
                excerpt = max(
                    sentences, key=lambda s: len(tokens & set(content_tokens(s)))
                )
            best = (score, idx, excerpt)
    return best


def check_grounding(answer, sources, support_threshold=DEFAULT_SUPPORT_THRESHOLD):
    """Run all checks. sources: list of {"id", "text"}. Returns a report dict."""
    if (isinstance(support_threshold, bool) or not isinstance(support_threshold, (int, float))
            or not 0 <= support_threshold <= 1 or not math.isfinite(support_threshold)):
        raise ValueError("support threshold must be finite and in [0, 1]")
    findings = []

    source_docs = [(idx, src["text"]) for idx, src in enumerate(sources)]

    citations = find_citations(answer)
    cited_indices = set()
    for num in citations:
        position = int(num)
        if 1 <= position <= len(sources):
            cited_indices.add(position - 1)
        else:
            findings.append(
                {
                    "kind": "citation_unresolvable",
                    "severity": "high",
                    "detail": "citation [%s] has no matching source (%d provided)"
                    % (num, len(sources)),
                }
            )

    body = strip_citations(answer)
    sentences = split_sentences(body)
    sentence_results = []
    unsupported = 0
    for sent in sentences:
        score, src_idx, src_sent = support_score(sent, source_docs)
        supported = score >= support_threshold
        if not supported:
            unsupported += 1
            findings.append(
                {
                    "kind": "unsupported_sentence",
                    "severity": "medium",
                    "detail": "sentence support %.2f below %.2f: %s"
                    % (score, support_threshold, _truncate(sent)),
                    "sentence": sent,
                    "support": score,
                }
            )
        sentence_results.append(
            {
                "sentence": sent,
                "support": score,
                "supported": supported,
                "source": sources[src_idx]["id"] if src_idx >= 0 else None,
                "source_excerpt": _truncate(src_sent) if src_sent else None,
            }
        )

    source_numbers = set()
    for src in sources:
        source_numbers.update(extract_numbers(src["text"]))
    numeric_findings = []
    for sent in sentences:
        for num in extract_numbers(sent):
            if not numbers_present(num, source_numbers):
                numeric_findings.append(num)
                findings.append(
                    {
                        "kind": "number_not_in_sources",
                        "severity": "high",
                        "detail": "number %s in answer appears in no source: %s"
                        % (num, _truncate(sent)),
                        "sentence": sent,
                        "number": num,
                    }
                )

    total = len(sentences)
    mean_support = (
        sum(r["support"] for r in sentence_results) / total if total else 1.0
    )
    return {
        "answer_sentences": total,
        "unsupported_sentences": unsupported,
        "mean_support": mean_support,
        "support_threshold": support_threshold,
        "citations": citations,
        "sources_cited": len(cited_indices),
        "sources_provided": len(sources),
        "sentences": sentence_results,
        "findings": findings,
        "finding_count": len(findings),
    }


def _truncate(text, limit=100):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"
