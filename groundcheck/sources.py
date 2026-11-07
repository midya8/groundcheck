"""Source document loading."""

import json


def load_sources(path):
    """Load sources from JSONL: {"id": ..., "text": ...} per line."""
    sources = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("%s:%d invalid JSON: %s" % (path, lineno, exc)) from exc
            if not isinstance(record, dict) or not isinstance(record.get("text"), str):
                raise ValueError("%s:%d source needs a string 'text' field" % (path, lineno))
            sid = record.get("id", record.get("doc_id", "s%d" % (len(sources) + 1)))
            if not isinstance(sid, str):
                raise ValueError("%s:%d source id must be a string" % (path, lineno))
            sources.append({"id": sid, "text": record["text"]})
    if not sources:
        raise ValueError("%s: no sources found" % path)
    return sources
