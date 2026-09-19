"""SDOC pipeline: inbox -> per-email category + comparison result.

    python3 pipeline.py [data_dir] [out.json]

data_dir defaults to "." (expects inbox/ and attachments/ inside it, i.e.
run from the participant bundle folder, or point it at one).
"""
import json
import re
import sys
from pathlib import Path

from loader import Inbox
import classify
import extract
import ai_extract
from normalize import COMPARE_FIELDS, normalize_value, is_blank_value

COMPARE_KEYWORD_RE = re.compile(r"\bcompar(e|ed|ison)\b", re.I)
DROPPED_RE = re.compile(r"\b(dropped|missing)\b", re.I)


def _role(path):
    p = path.upper()
    if "_SI." in p:
        return "SI"
    if "_BL." in p:
        return "BL"
    return None


def _pick_si_bl(attachments):
    si = next((a for a in attachments if _role(a) == "SI"), None)
    bl = next((a for a in attachments if _role(a) == "BL"), None)
    if si is None and bl is None and len(attachments) >= 2:
        si, bl = attachments[0], attachments[1]
    return si, bl


def _empty_result(status, review_reason=None, defect_fields=None):
    return {
        "status": status,
        "review_reason": review_reason,
        "has_defect": status == "MISMATCH",
        "defect_fields": defect_fields or [],
    }


def decide_comparison(email, inbox):
    atts = email.get("attachments", []) or []
    n = len(atts)
    body = email.get("body", "") or ""

    if n == 0:
        if COMPARE_KEYWORD_RE.search(body) or DROPPED_RE.search(body):
            return _empty_result("NEEDS_REVIEW", "missing_attachment")
        return _empty_result("OK")

    if n == 1:
        return _empty_result("NEEDS_REVIEW", "missing_attachment")

    si_path, bl_path = _pick_si_bl(atts)
    if si_path is None or bl_path is None:
        return _empty_result("NEEDS_REVIEW", "missing_attachment")

    result, _si, _bl = compare_documents(
        inbox.read_bytes(si_path), si_path, inbox.read_bytes(bl_path), bl_path)
    return result


def _read(reader, data, name, use_ai):
    """Read one document. Whatever reader is used, a PDF with no text layer
    (an image-only scan) must be escalated to a human, not decided, so that
    check always comes from the deterministic reader."""
    if use_ai and name.lower().endswith(".pdf"):
        gate = extract.extract(data, name)
        if not gate.readable:
            return gate
    return reader(data, name)


def compare_documents(si_bytes, si_name, bl_bytes, bl_name, use_ai=None):
    """Read an SI and a draft BL and compare the 7 fields.

    Returns (result, si_res, bl_res); the extraction results let a UI show
    what was read. use_ai=None means "AI if a key is set".
    """
    if use_ai is None:
        use_ai = ai_extract.available()
    reader = ai_extract.ai_extract if use_ai else extract.extract
    si_res = _read(reader, si_bytes, si_name, use_ai)
    bl_res = _read(reader, bl_bytes, bl_name, use_ai)

    if not si_res.readable or not bl_res.readable:
        return _empty_result("NEEDS_REVIEW", "unreadable"), si_res, bl_res

    if si_res.wrong_doc_type or bl_res.wrong_doc_type:
        return _empty_result("NEEDS_REVIEW", "wrong_doc_type"), si_res, bl_res

    missing = []
    si_norm, bl_norm = {}, {}
    for f in COMPARE_FIELDS:
        si_raw = si_res.fields.get(f)
        bl_raw = bl_res.fields.get(f)
        if si_raw is None or is_blank_value(si_raw) or bl_raw is None or is_blank_value(bl_raw):
            missing.append(f)
            continue
        sv, bv = normalize_value(f, si_raw), normalize_value(f, bl_raw)
        if sv is None or bv is None:
            missing.append(f)
            continue
        si_norm[f], bl_norm[f] = sv, bv

    if missing:
        return _empty_result("NEEDS_REVIEW", "missing_value"), si_res, bl_res

    defect_fields = sorted(f for f in COMPARE_FIELDS if si_norm[f] != bl_norm[f])
    if defect_fields:
        return _empty_result("MISMATCH", None, defect_fields), si_res, bl_res
    return _empty_result("OK"), si_res, bl_res


def run(data_dir=".", out_path=None, limit=None):
    if ai_extract.available():
        print("AI reading: ON  (using your API key)")
    else:
        print("AI reading: OFF (no key detected in this terminal — using the backup method instead)")

    inbox = Inbox(data_dir)
    emails = list(inbox)
    if limit:
        emails = emails[:limit]
        print(f"(testing mode: only processing the first {limit} emails)")

    submission = {}
    for email in emails:
        eid = email["email_id"]
        atts = email.get("attachments", []) or []
        category, _reason = classify.classify(email, has_attachments=bool(atts))

        if category == "BL_COMPARISON":
            result = decide_comparison(email, inbox)
        else:
            result = _empty_result("OK")

        submission[eid] = {
            "category": category,
            "status": result["status"],
            "review_reason": result["review_reason"],
            "has_defect": result["has_defect"],
            "defect_fields": result["defect_fields"],
        }

    if out_path:
        Path(out_path).write_text(json.dumps(submission, indent=2))
    return submission


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    out_path = sys.argv[2] if len(sys.argv) > 2 else "submission.json"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    sub = run(data_dir, out_path, limit)
    print(f"Wrote {len(sub)} predictions to {out_path}")
