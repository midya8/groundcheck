"""Source-order controls for lexical evidence, not semantic support."""
import itertools
import re
import unittest

from groundcheck.audit import audit


SOURCES = [
    {"id": "alpha", "text": "alpha beta 43.0 and alpha 43"},
    {"id": "beta", "text": "beta gamma 7 and delta"},
    {"id": "gamma", "text": "alpha gamma 43.00"},
]


def by_identity(report):
    """Remove positional representation without removing any score or match."""
    ids = [source["id"] for source in report["sources"]]
    units = []
    for unit in report["units"]:
        scores = {}
        for row in unit["source_scores"]:
            scores[ids[row["source_index"]]] = {
                key: value for key, value in row.items() if key != "source_index"
            }
        numbers = []
        for number in unit["numbers"]:
            matches = sorted(
                (ids[row["source_index"]], row["literal"], row["number"],
                 row["start"], row["end"], row["eligible"])
                for row in number["matches"]
            )
            numbers.append((number["literal"], number["number"],
                            number["present"], matches))
        units.append({"tokens": unit["tokens"], "scores": scores,
                      "support": unit["support"], "supported": unit["supported"],
                      "eligible": sorted(ids[index] for index in unit["eligible_sources"]),
                      "numbers": numbers, "no_content": unit["no_content"]})
    return units


class SourceOrderTests(unittest.TestCase):
    def test_remapped_citations_preserve_evidence(self):
        answers = [
            "alpha beta 43 [1][3].",
            "alpha gamma 43 [2]. beta delta 7 [2][3].",
            "missing 99 [1][2][3].",
            "The and of [3].",
        ]
        for scope, answer in itertools.product(("all", "cited"), answers):
            baseline = audit({"answer": answer, "sources": SOURCES, "scope": scope})
            for order in itertools.permutations(range(3)):
                new_position = {old + 1: new + 1 for new, old in enumerate(order)}
                remapped = re.sub(r"\[(\d+)\]",
                                  lambda match: f"[{new_position[int(match[1])]}]", answer)
                report = audit({"answer": remapped,
                                "sources": [SOURCES[index] for index in order], "scope": scope})
                with self.subTest(scope=scope, answer=answer, order=order):
                    self.assertEqual(by_identity(report), by_identity(baseline))

    def test_tied_winner_is_first_eligible_not_fixed_source_id(self):
        for order in itertools.permutations(range(3)):
            sources = [SOURCES[index] for index in order]
            report = audit({"answer": "unknown [2][3].", "sources": sources, "scope": "cited"})
            unit = report["units"][0]
            self.assertEqual(unit["best_source"], 1)
            self.assertEqual(sources[unit["best_source"]]["id"], sources[1]["id"])
            self.assertEqual(unit["support"], 0)

    def test_duplicate_citations_preserve_eligibility_but_not_occurrences(self):
        for scope in ("all", "cited"):
            base = audit({"answer": "alpha 43 [1][3].", "sources": SOURCES, "scope": scope})
            repeated = audit({"answer": "alpha 43 [1][3][1][3].", "sources": SOURCES, "scope": scope})
            self.assertEqual(by_identity(base), by_identity(repeated))
            self.assertEqual(len(base["units"][0]["citations"]), 2)
            self.assertEqual(len(repeated["units"][0]["citations"]), 4)
            for citation in repeated["units"][0]["citations"]:
                self.assertEqual(repeated["spec"]["answer"][citation["start"]:citation["end"]],
                                 citation["marker"])

    def test_unremapped_citation_changes_scoped_evidence(self):
        answer = "alpha beta 43 [1]."
        base = audit({"answer": answer, "sources": SOURCES, "scope": "cited"})
        swapped = audit({"answer": answer, "sources": [SOURCES[1], SOURCES[0], SOURCES[2]],
                         "scope": "cited"})
        self.assertNotEqual(by_identity(base), by_identity(swapped))
        self.assertTrue(base["units"][0]["numbers"][0]["present"])
        self.assertFalse(swapped["units"][0]["numbers"][0]["present"])
        self.assertGreater(base["units"][0]["support"], swapped["units"][0]["support"])
