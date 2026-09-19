"""Run with: python tests/test_report.py"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pipeline  # noqa: E402
import report  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..")


def test_diff_marks_only_the_changed_characters():
    a, b = report.diff_html("AL GURQ STATIONERY LLC", "AL GURG STATIONERY LLC")
    assert a.count("<mark") == 1 and ">Q<" in a
    assert b.count("<mark") == 1 and ">G<" in b


def test_diff_escapes_html():
    a, _ = report.diff_html("<b>x</b>", "<b>y</b>")
    assert "<b>" not in a


def test_draft_reply_lists_each_discrepancy():
    rows = [{"label": "Consignee", "si": "A", "bl": "B", "verdict": "mismatch"},
            {"label": "Shipper", "si": "S", "bl": "S", "verdict": "match"}]
    subj, body = report.draft_reply("RE_ TO CONFIRM DOCS", {"status": "MISMATCH"}, rows, "Sam")
    assert subj == "RE: TO CONFIRM DOCS"
    assert "1 discrepancy" in body and "SI : A" in body and "BL : B" in body
    assert "Shipper" not in body


def test_draft_reply_for_review_gives_reason_and_next_step():
    _, body = report.draft_reply("x", {"status": "NEEDS_REVIEW", "review_reason": "unreadable"}, [])
    assert "image-only scan" in body and "text-based copy" in body


def test_inbox_analysis_matches_the_batch_pipeline():
    rows = report.analyze_inbox(DATA)
    got = json.loads(report.to_submission_json(rows))
    ref = pipeline.run(DATA, None)
    keys = ("category", "status", "review_reason", "has_defect", "defect_fields")
    assert got == {k: {x: v[x] for x in keys} for k, v in ref.items()}


def test_mailto_link_is_prefilled_and_safe():
    url = report.mailto_link("a@b.com", "RE: Docs & more", "Line 1\nLine 2 & 100%")
    assert url.startswith("mailto:a@b.com?subject=")
    assert "%0A" in url and "%26" in url and " " not in url


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
