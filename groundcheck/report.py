"""Terminal, JSON and Markdown reports for grounding checks."""

import json


def _escape_md(text):
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")


def render_terminal(report):
    lines = [
        "sentences    %d (%d unsupported)"
        % (report["answer_sentences"], report["unsupported_sentences"]),
        "mean support %.4f (threshold %.2f)"
        % (report["mean_support"], report["support_threshold"]),
        "citations    %d (%d/%d sources cited)"
        % (len(report["citations"]), report["sources_cited"], report["sources_provided"]),
        "findings     %d" % report["finding_count"],
    ]
    for finding in report["findings"]:
        lines.append("  [%s] %s: %s" % (finding["severity"], finding["kind"], finding["detail"]))
    return "\n".join(lines)


def render_markdown(report):
    lines = [
        "# GroundCheck report",
        "",
        "| metric | value |",
        "|---|---|",
        "| answer sentences | %d |" % report["answer_sentences"],
        "| unsupported sentences | %d |" % report["unsupported_sentences"],
        "| mean support | %.4f |" % report["mean_support"],
        "| support threshold | %.2f |" % report["support_threshold"],
        "| citations | %d |" % len(report["citations"]),
        "| sources cited | %d of %d |" % (report["sources_cited"], report["sources_provided"]),
        "| findings | %d |" % report["finding_count"],
        "",
    ]
    if report["findings"]:
        lines += ["## Findings", "", "| severity | kind | detail |", "|---|---|---|"]
        for finding in report["findings"]:
            lines.append(
                "| %s | %s | %s |"
                % (finding["severity"], finding["kind"], _escape_md(finding["detail"]))
            )
        lines.append("")
    if report["sentences"]:
        lines += [
            "## Sentence support",
            "",
            "| sentence | support | supported | best source |",
            "|---|---|---|---|",
        ]
        for row in report["sentences"]:
            lines.append(
                "| %s | %.4f | %s | %s |"
                % (
                    _escape_md(row["sentence"]),
                    row["support"],
                    "yes" if row["supported"] else "no",
                    _escape_md(row["source"] or "-"),
                )
            )
        lines.append("")
    return "\n".join(lines)


def write_json_report(report, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
