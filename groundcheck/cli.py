"""Command line interface for GroundCheck."""

import argparse
import sys

from .check import DEFAULT_SUPPORT_THRESHOLD, check_grounding
from .report import render_markdown, render_terminal, write_json_report
from .sources import load_sources


def _read_answer(args):
    if args.answer is not None:
        return args.answer
    with open(args.answer_file, "r", encoding="utf-8") as fh:
        return fh.read()


def _cmd_check(args):
    sources = load_sources(args.sources)
    answer = _read_answer(args)
    report = check_grounding(answer, sources, support_threshold=args.support_threshold)
    print(render_terminal(report))
    if args.json:
        write_json_report(report, args.json)
    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as fh:
            fh.write(render_markdown(report))
    failed = False
    if report["mean_support"] < args.min_support:
        print(
            "FAIL mean support %.4f below gate %.4f" % (report["mean_support"], args.min_support),
            file=sys.stderr,
        )
        failed = True
    if report["unsupported_sentences"] > args.max_unsupported:
        print(
            "FAIL %d unsupported sentences above gate %d"
            % (report["unsupported_sentences"], args.max_unsupported),
            file=sys.stderr,
        )
        failed = True
    if args.max_findings is not None and report["finding_count"] > args.max_findings:
        print(
            "FAIL %d findings above gate %d" % (report["finding_count"], args.max_findings),
            file=sys.stderr,
        )
        failed = True
    return 1 if failed else 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="groundcheck",
        description="Check whether an answer is grounded in its sources.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("check", help="check an answer against sources")
    p.add_argument("--sources", required=True, help="JSONL sources ({id, text} per line)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--answer", help="answer text")
    src.add_argument("--answer-file", help="file containing the answer")
    p.add_argument("--support-threshold", type=float, default=DEFAULT_SUPPORT_THRESHOLD,
                   help="per-sentence containment needed to count as supported")
    p.add_argument("--min-support", type=float, default=0.0,
                   help="fail unless mean support reaches this value")
    p.add_argument("--max-unsupported", type=int, default=2**31 - 1,
                   help="fail when unsupported sentences exceed this count")
    p.add_argument("--max-findings", type=int, default=None,
                   help="fail when total findings exceed this count")
    p.add_argument("--json", help="write JSON report")
    p.add_argument("--markdown", help="write Markdown report")
    p.set_defaults(func=_cmd_check)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)
