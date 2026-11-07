import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from groundcheck import check_grounding, load_sources
from groundcheck.check import find_citations, strip_citations, support_score
from groundcheck.report import render_markdown, render_terminal
from groundcheck.textutil import (
    content_tokens,
    extract_numbers,
    numbers_present,
    split_sentences,
)

SOURCES = [
    {"id": "s1", "text": "The tokenizer trains 300 merges from raw text. "
                          "Encoding applies merges in rank order."},
    {"id": "s2", "text": "The demo corpus compresses to 1.57 bytes per token. "
                          "The test suite contains 40 unit tests."},
]


class TestTextUtil(unittest.TestCase):
    def test_content_tokens_strip_stopwords(self):
        self.assertEqual(content_tokens("The cat and the Dog"), ["cat", "dog"])

    def test_content_tokens_lowercase(self):
        self.assertEqual(content_tokens("BM25 BM25"), ["bm25", "bm25"])

    def test_split_sentences(self):
        self.assertEqual(split_sentences("One. Two! Three?"), ["One.", "Two!", "Three?"])

    def test_split_sentences_no_terminal_punct(self):
        self.assertEqual(split_sentences("trailing text"), ["trailing text"])

    def test_split_sentences_newlines(self):
        self.assertEqual(split_sentences("first line\nsecond line"),
                         ["first line", "second line"])

    def test_extract_numbers(self):
        self.assertEqual(extract_numbers("1.57 bytes and 40 tests"), ["1.57", "40"])

    def test_extract_numbers_commas(self):
        self.assertEqual(extract_numbers("1,000,000 rows"), ["1000000"])

    def test_extract_numbers_skips_versions(self):
        self.assertEqual(extract_numbers("python 3.10.1"), [])

    def test_numbers_present_exact(self):
        self.assertTrue(numbers_present("40", {"40"}))

    def test_numbers_present_float_equal(self):
        self.assertTrue(numbers_present("1.570", {"1.57"}))

    def test_numbers_present_missing(self):
        self.assertFalse(numbers_present("41", {"40"}))


class TestCitations(unittest.TestCase):
    def test_find_citations_deduped_ordered(self):
        self.assertEqual(find_citations("a [2] b [1] c [2]"), ["2", "1"])

    def test_strip_citations(self):
        self.assertEqual(strip_citations("fact [1] more [12]"), "fact  more ")


class TestSources(unittest.TestCase):
    def write(self, tmp, text):
        path = Path(tmp) / "sources.jsonl"
        path.write_text(text)
        return str(path)

    def test_load_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, '{"id": "a", "text": "hello"}\n{"text": "world"}\n')
            sources = load_sources(path)
        self.assertEqual([s["id"] for s in sources], ["a", "s2"])

    def test_load_sources_doc_id_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, '{"doc_id": "d1", "text": "hi"}\n')
            self.assertEqual(load_sources(path)[0]["id"], "d1")

    def test_load_sources_rejects_bad_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "not json\n")
            with self.assertRaises(ValueError):
                load_sources(path)

    def test_load_sources_rejects_missing_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, '{"id": "a"}\n')
            with self.assertRaises(ValueError):
                load_sources(path)

    def test_load_sources_rejects_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "\n")
            with self.assertRaises(ValueError):
                load_sources(path)


class TestSupportScore(unittest.TestCase):
    def test_full_overlap(self):
        score, idx, _ = support_score("the cat sat", [(0, "the cat sat on the mat")])
        self.assertEqual(score, 1.0)
        self.assertEqual(idx, 0)

    def test_no_overlap(self):
        score, _, _ = support_score("quantum entanglement", [(0, "the cat sat")])
        self.assertEqual(score, 0.0)

    def test_stopword_only_sentence_supported(self):
        score, _, _ = support_score("the and of", [(0, "unrelated words")])
        self.assertEqual(score, 1.0)

    def test_cross_sentence_combination_supported(self):
        doc = "Merges train from raw text. The demo compresses to 1.57 bytes per token."
        score, idx, _ = support_score(
            "merges train from raw text and the demo compresses to 1.57 bytes",
            [(0, doc)],
        )
        self.assertGreaterEqual(score, 0.8)


class TestCheckGrounding(unittest.TestCase):
    def test_grounded_answer_clean(self):
        answer = ("The tokenizer trains 300 merges from raw text [1]. "
                  "The test suite contains 40 unit tests [2].")
        report = check_grounding(answer, SOURCES)
        self.assertEqual(report["finding_count"], 0)
        self.assertEqual(report["unsupported_sentences"], 0)
        self.assertEqual(report["sources_cited"], 2)

    def test_unresolvable_citation(self):
        report = check_grounding("A fact [9].", SOURCES)
        kinds = [f["kind"] for f in report["findings"]]
        self.assertIn("citation_unresolvable", kinds)

    def test_unsupported_sentence_flagged(self):
        report = check_grounding("Bananas grow on underground orchards.", SOURCES)
        self.assertEqual(report["unsupported_sentences"], 1)
        self.assertIn("unsupported_sentence", [f["kind"] for f in report["findings"]])

    def test_fabricated_number_flagged(self):
        report = check_grounding("The suite contains 99 unit tests.", SOURCES)
        kinds = [f["kind"] for f in report["findings"]]
        self.assertIn("number_not_in_sources", kinds)

    def test_sourced_number_not_flagged(self):
        report = check_grounding("The corpus compresses to 1.57 bytes per token.", SOURCES)
        self.assertNotIn("number_not_in_sources", [f["kind"] for f in report["findings"]])

    def test_mean_support(self):
        report = check_grounding("The tokenizer trains 300 merges from raw text.", SOURCES)
        self.assertGreater(report["mean_support"], 0.9)

    def test_threshold_changes_outcome(self):
        answer = "The tokenizer trains 300 merges from raw text quickly."
        loose = check_grounding(answer, SOURCES, support_threshold=0.5)
        strict = check_grounding(answer, SOURCES, support_threshold=0.99)
        self.assertGreaterEqual(strict["unsupported_sentences"], loose["unsupported_sentences"])

    def test_sentence_records_best_source(self):
        report = check_grounding("The test suite contains 40 unit tests.", SOURCES)
        self.assertEqual(report["sentences"][0]["source"], "s2")

    def test_empty_answer(self):
        report = check_grounding("", SOURCES)
        self.assertEqual(report["answer_sentences"], 0)
        self.assertEqual(report["mean_support"], 1.0)


class TestDocumentedLimitations(unittest.TestCase):
    """These tests pin the lexical-only bound documented in the README:
    each case is wrong or misleading but passes every check."""

    def test_negation_passes(self):
        # containment ignores word order and negation
        report = check_grounding("The test suite does not contain 40 unit tests.", SOURCES)
        self.assertEqual(report["finding_count"], 0)

    def test_wrong_attribution_passes(self):
        # 1.57 belongs to the tokenizer corpus; assigning it to retrieval passes
        report = check_grounding("The retrieval demo compresses to 1.57 bytes per token.", SOURCES)
        self.assertNotIn("number_not_in_sources", [f["kind"] for f in report["findings"]])

    def test_coincidental_number_passes(self):
        sources = [{"id": "s1", "text": "The launch is on day 40 of the program."}]
        report = check_grounding("The pipeline has 40 stages.", sources)
        self.assertNotIn("number_not_in_sources", [f["kind"] for f in report["findings"]])


class TestReports(unittest.TestCase):
    def setUp(self):
        self.report = check_grounding(
            "The tokenizer trains 300 merges from raw text [1]. Aliens wrote it [7].",
            SOURCES,
        )

    def test_terminal(self):
        out = render_terminal(self.report)
        self.assertIn("mean support", out)
        self.assertIn("citation_unresolvable", out)

    def test_markdown(self):
        md = render_markdown(self.report)
        self.assertIn("# GroundCheck report", md)
        self.assertIn("| severity | kind | detail |", md)
        self.assertIn("Sentence support", md)

    def test_markdown_escapes_pipes(self):
        report = check_grounding("a|b factoid [7].", SOURCES)
        md = render_markdown(report)
        self.assertNotIn("| a|b ", md)

    def test_clean_report_has_no_findings_section(self):
        report = check_grounding("The test suite contains 40 unit tests [2].", SOURCES)
        self.assertNotIn("## Findings", render_markdown(report))


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sources = Path(self.tmp.name) / "sources.jsonl"
        with self.sources.open("w") as fh:
            for src in SOURCES:
                fh.write(json.dumps(src) + "\n")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "groundcheck", *args], capture_output=True, text=True
        )

    def test_check_grounded_passes_gates(self):
        out_json = Path(self.tmp.name) / "report.json"
        out_md = Path(self.tmp.name) / "report.md"
        r = self.run_cli(
            "check", "--sources", str(self.sources),
            "--answer", "The test suite contains 40 unit tests [2].",
            "--min-support", "0.5", "--max-unsupported", "0", "--max-findings", "0",
            "--json", str(out_json), "--markdown", str(out_md),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(out_json.read_text())
        self.assertEqual(data["finding_count"], 0)
        self.assertIn("GroundCheck", out_md.read_text())

    def test_gate_failure_returns_1(self):
        r = self.run_cli(
            "check", "--sources", str(self.sources),
            "--answer", "Bananas grow on underground orchards with 77 farmers.",
            "--max-findings", "0",
        )
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL", r.stderr)

    def test_min_support_gate(self):
        r = self.run_cli(
            "check", "--sources", str(self.sources),
            "--answer", "Completely unrelated claim about geology.",
            "--min-support", "0.9",
        )
        self.assertEqual(r.returncode, 1)
        self.assertIn("mean support", r.stderr)

    def test_answer_from_file(self):
        answer = Path(self.tmp.name) / "answer.txt"
        answer.write_text("The tokenizer trains 300 merges from raw text [1].")
        r = self.run_cli("check", "--sources", str(self.sources), "--answer-file", str(answer))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_missing_sources_file(self):
        r = self.run_cli("check", "--sources", "/nonexistent.jsonl", "--answer", "hi")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
