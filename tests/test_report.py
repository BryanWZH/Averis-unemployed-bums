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


def test_selection_change_only_fires_on_a_new_click():
    assert report.selection_change([(3, "Email")], None) == (3, "Email")     # first click
    assert report.selection_change([(3, "Email")], [(3, "Email")]) is None   # same selection re-run
    assert report.selection_change([(5, "Subject")], [(3, "Email")]) == (5, "Subject")
    assert report.selection_change([], [(3, "Email")]) is None               # deselected


def test_edited_result_uses_the_real_engine():
    same = {"shipper": "ACME LTD", "consignee": "BOB PTE LTD", "notify_party": "BOB PTE LTD",
            "port_of_loading": "SINGAPORE (SGSIN)", "port_of_discharge": "KOPER, SLOVENIA (SIKOP)",
            "container_count": "3 x 40'HC", "gross_weight_kg": "61,026 KG"}
    res, rows = report.edited_result(same, dict(same, gross_weight_kg="61,026.00 KGS"))
    assert res["status"] == "OK"                                     # same weight, written differently
    res, _ = report.edited_result(same, dict(same, gross_weight_kg=report.tweak_weight("61,026 KG")))
    assert res["status"] == "MISMATCH" and res["defect_fields"] == ["gross_weight_kg"]
    res, _ = report.edited_result(same, dict(same, consignee=report.tweak_typo("BOB PTE LTD")))
    assert res["status"] == "MISMATCH" and res["defect_fields"] == ["consignee"]
    res, _ = report.edited_result(same, dict(same, notify_party=""))
    assert res["status"] == "NEEDS_REVIEW" and res["review_reason"] == "missing_value"


def test_time_saved_only_counts_real_automatic_checks():
    rows = [
        {"category": "BL_COMPARISON", "rows": [1], "status": "OK"},
        {"category": "BL_COMPARISON", "rows": [1], "status": "MISMATCH"},
        {"category": "BL_COMPARISON", "rows": [], "status": "OK"},           # no documents: not a check
        {"category": "BL_COMPARISON", "rows": [], "status": "NEEDS_REVIEW"},
        {"category": "SPAM", "rows": [], "status": "OK"},
    ]
    t = report.time_saved(rows, minutes_per_check=5, minutes_per_reply=2)
    assert t["checks"] == 2 and t["escalated"] == 1 and t["minutes"] == 14 and round(t["hours"], 2) == 0.23


def test_field_table_flags_problems_with_icon_and_word_and_escapes_html():
    rows = [
        {"label": "Shipper", "si": "ACME", "bl": "ACME", "verdict": "match"},
        {"label": "Consignee", "si": "AL GURQ <b>X</b>", "bl": "AL GURG <b>X</b>", "verdict": "mismatch"},
        {"label": "Notify party", "si": "BOB", "bl": "", "verdict": "blank"},
    ]
    h = report.field_table_html(rows)
    assert h.count("<tr") == 4                                   # header + 3 rows
    assert h.count("class='bad'") == 1 and h.count("class='warn'") == 1
    assert "✔ Match" in h and "✖ Differs" in h and "⚠ Blank" in h
    assert "<b>" not in h and "&lt;b&gt;" in h                   # untrusted text is escaped
    assert "<mark" in h and chr(10) not in h                     # diff highlight, single line


def test_kv_html_escapes_values():
    h = report.kv_html([("To", "a@b.com"), ("Subject", "<script>x</script>")])
    assert "a@b.com" in h and "<script>" not in h


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
