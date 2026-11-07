#!/usr/bin/env bash
# Fully offline GroundCheck demo: a grounded answer passes the gates, an
# ungrounded one fails them, and both produce JSON and Markdown reports.
set -u
cd "$(dirname "$0")/.."

OUT="$(mktemp -d /tmp/groundcheck-demo-XXXX)"
trap 'echo "demo artifacts: $OUT"' EXIT

echo "== grounded answer (expect pass) =="
python3 -m groundcheck check \
  --sources examples/data/sources.jsonl \
  --answer-file examples/data/answer_grounded.txt \
  --min-support 0.8 --max-unsupported 0 --max-findings 0 \
  --json "$OUT/grounded.json" --markdown "$OUT/grounded.md" || { echo "FAIL grounded answer rejected"; exit 1; }
echo "grounded answer accepted"

echo "== ungrounded answer (expect findings and gate failure) =="
if python3 -m groundcheck check \
  --sources examples/data/sources.jsonl \
  --answer-file examples/data/answer_ungrounded.txt \
  --max-findings 0 \
  --json "$OUT/ungrounded.json" --markdown "$OUT/ungrounded.md"; then
  echo "FAIL ungrounded answer passed the gate"; exit 1
fi
echo "ungrounded answer rejected as expected"

python3 - "$OUT" <<'PY'
import json, sys
grounded = json.load(open(sys.argv[1] + "/grounded.json"))
ungrounded = json.load(open(sys.argv[1] + "/ungrounded.json"))
assert grounded["finding_count"] == 0, grounded["findings"]
assert grounded["unsupported_sentences"] == 0
assert grounded["sources_cited"] == 2
kinds = {f["kind"] for f in ungrounded["findings"]}
assert "number_not_in_sources" in kinds, kinds
assert "citation_unresolvable" in kinds, kinds
assert ungrounded["unsupported_sentences"] >= 1
print("assertions ok: grounded clean; ungrounded flagged %d findings across %d kinds"
      % (ungrounded["finding_count"], len(kinds)))
PY

echo "demo ok"
