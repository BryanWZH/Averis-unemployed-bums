"""Tests for the AI-assisted features using a stand-in AI, so they cost nothing.
Run with: python tests/test_ai_features.py"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import ai_extract  # noqa: E402
import ai_reply  # noqa: E402
import extract  # noqa: E402
import pipeline  # noqa: E402
import report  # noqa: E402
from normalize import COMPARE_FIELDS  # noqa: E402

A = os.path.join(os.path.dirname(__file__), "..", "attachments")


def _read(name):
    return open(os.path.join(A, name), "rb").read()


def _fake_ai(fields_by_name):
    """An ai_extract stand-in that returns preset fields per file name."""
    def fake(data, name):
        r = extract.ExtractResult()
        r.fields = dict(fields_by_name[os.path.basename(name)])
        return r
    return fake


def test_cross_check_agreement_keeps_the_verdict():
    si, bl = "email_334_SI.txt", "email_334_BL.txt"
    rs, rb = extract.extract(_read(si), si), extract.extract(_read(bl), bl)
    ai_extract.ai_extract = _fake_ai({si: rs.fields, bl: rb.fields})   # AI == rule reader
    res, _, _ = pipeline.compare_documents(_read(si), si, _read(bl), bl, use_ai=True, cross_check=True)
    assert res["status"] == "MISMATCH" and res["defect_fields"] == ["consignee", "shipper"]


def test_cross_check_disagreement_escalates():
    si, bl = "email_335_SI.txt", "email_335_BL.txt"     # a clean OK pair
    rs, rb = extract.extract(_read(si), si), extract.extract(_read(bl), bl)
    wrong = dict(rs.fields)
    wrong["consignee"] = "SOMEONE ELSE LTD"                # AI misreads one field
    ai_extract.ai_extract = _fake_ai({si: wrong, bl: rb.fields})
    res, _, _ = pipeline.compare_documents(_read(si), si, _read(bl), bl, use_ai=True, cross_check=True)
    assert res["status"] == "NEEDS_REVIEW" and res["review_reason"] == "reader_disagreement"
    assert res["disagreements"]["si"] == ["consignee"]


def test_cross_check_off_by_default_does_not_escalate():
    si, bl = "email_335_SI.txt", "email_335_BL.txt"
    rs, rb = extract.extract(_read(si), si), extract.extract(_read(bl), bl)
    wrong = dict(rs.fields)
    wrong["consignee"] = "SOMEONE ELSE LTD"
    ai_extract.ai_extract = _fake_ai({si: wrong, bl: rb.fields})
    res, _, _ = pipeline.compare_documents(_read(si), si, _read(bl), bl, use_ai=True)
    assert res["status"] == "MISMATCH"                      # plain AI path, unchanged behaviour


def test_second_opinion_is_advisory_and_finds_the_difference():
    si, bl = "email_334_SI.txt", "email_334_BL.txt"
    rs, rb = extract.extract(_read(si), si), extract.extract(_read(bl), bl)
    ai_extract.ai_extract = _fake_ai({si: rs.fields, bl: rb.fields})
    op = pipeline.second_opinion(_read(si), si, _read(bl), bl)
    assert op["available"] and op["suggested_defects"] == ["consignee", "shipper"]


def test_polish_accepts_faithful_rewrite_and_rejects_unfaithful_ones():
    original = "Hi Sam,\nThe consignee differs:\n  SI : AL GURQ LLC\n  BL : AL GURG LLC\n3 containers."
    facts = ["AL GURQ LLC", "AL GURG LLC"]
    good = "Hi Sam,\nSmall difference on the consignee: SI says AL GURQ LLC but BL says AL GURG LLC. 3 containers."
    lost = "Hi Sam,\nThe consignee names differ slightly. 3 containers."
    invented = good + " We will need this by 15 October."
    assert ai_reply.facts_preserved(original, good, facts)
    assert not ai_reply.facts_preserved(original, lost, facts)
    assert not ai_reply.facts_preserved(original, invented, facts)


def _client_returning(text):
    msg = SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])
    return SimpleNamespace(messages=SimpleNamespace(create=lambda **k: msg))


def test_polish_falls_back_to_the_template():
    original = "Hi Sam,\nSI : ABC\nBL : ABD"
    text, used = ai_reply.polish(original, ["ABC", "ABD"], _client_returning("Hi Sam, something vague."))
    assert text == original and used is False
    text, used = ai_reply.polish(original, ["ABC", "ABD"], _client_returning("Hi Sam,\nSI says ABC, BL says ABD."))
    assert used is True and "ABC" in text

    class Boom:
        messages = SimpleNamespace(create=lambda **k: (_ for _ in ()).throw(RuntimeError("down")))
    text, used = ai_reply.polish(original, ["ABC"], Boom())
    assert text == original and used is False


def test_outbox_never_replies_to_reviews_and_can_hold_mismatches():
    rows = report.analyze_inbox(os.path.join(os.path.dirname(__file__), ".."))
    auto = report.plan_replies(rows)
    held = report.plan_replies(rows, hold_mismatch=True)
    assert all(p["delivery"] == report.DELIVERY_HUMAN for p in auto if p["verdict"] == "NEEDS_REVIEW")
    assert not any(p["delivery"] == report.DELIVERY_SENT for p in auto if p["verdict"] == "NEEDS_REVIEW")
    assert all(p["delivery"] == report.DELIVERY_HELD for p in held if p["verdict"] == "MISMATCH")
    assert sum(p["delivery"] == report.DELIVERY_SENT for p in auto) > sum(
        p["delivery"] == report.DELIVERY_SENT for p in held)


if __name__ == "__main__":
    real = ai_extract.ai_extract
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            ai_extract.ai_extract = real
            fn()
    print("ok")
