"""Presentation helpers for the web app: whole-inbox analysis, character-level
diffs, draft reply emails and downloadable reports. Pure functions, no
Streamlit and no AI, so they are cheap and unit-testable.
"""
import csv
import difflib
import html
import io
import json
import re
from urllib.parse import quote

import classify
import pipeline
from loader import Inbox
from normalize import COMPARE_FIELDS, is_blank_value, normalize_value

FIELD_NAMES = {
    "shipper": "Shipper", "consignee": "Consignee", "notify_party": "Notify party",
    "port_of_loading": "Port of loading", "port_of_discharge": "Port of discharge",
    "container_count": "Container count", "gross_weight_kg": "Gross weight (kg)",
}
REASONS = {
    "missing_attachment": "An SI/BL attachment is missing.",
    "unreadable": "A document could not be read (empty, corrupt or an image-only scan).",
    "wrong_doc_type": "A document is not an SI or BL (for example an invoice or packing list).",
    "missing_value": "A field is blank or a placeholder, so it can't be compared.",
    "reader_disagreement": "The AI reader and the rule-based reader read different values for the same field.",
}
NEXT_STEP = {
    "missing_attachment": "Ask the sender to resend both the SI and the draft BL.",
    "unreadable": "Ask for a text-based copy (not a scan) or check the documents manually.",
    "wrong_doc_type": "Ask the sender for the correct SI and draft BL.",
    "missing_value": "Ask the sender to fill in the blank field, then re-check.",
    "reader_disagreement": "Check the two readings against the original documents and confirm which is right.",
}


# ---------------------------------------------------------------- comparison
def field_rows(si_res, bl_res):
    """One row per compared field: raw values, verdict and normalised values."""
    rows = []
    for f in COMPARE_FIELDS:
        sv, bv = si_res.fields.get(f), bl_res.fields.get(f)
        if is_blank_value(sv) or is_blank_value(bv):
            verdict = "blank"
        else:
            verdict = "match" if normalize_value(f, sv) == normalize_value(f, bv) else "mismatch"
        blank = verdict == "blank"
        rows.append({"field": f, "label": FIELD_NAMES[f], "si": sv or "", "bl": bv or "",
                     "verdict": verdict,
                     "si_norm": None if blank else normalize_value(f, sv),
                     "bl_norm": None if blank else normalize_value(f, bv)})
    return rows


def diff_html(a, b):
    """Two HTML snippets (for the SI value and the BL value) with the
    characters that differ highlighted."""
    a, b = a or "", b or ""
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    left, right = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        seg_a, seg_b = html.escape(a[i1:i2]), html.escape(b[j1:j2])
        if op == "equal":
            left.append(seg_a)
            right.append(seg_b)
        else:
            if seg_a:
                left.append(f"<mark style='background:#f5b7b1;color:#7b241c;border-radius:3px'>{seg_a}</mark>")
            if seg_b:
                right.append(f"<mark style='background:#f5b7b1;color:#7b241c;border-radius:3px'>{seg_b}</mark>")
    return "".join(left), "".join(right)


def draft_reply(subject, result, rows, sender_name=None):
    """A ready-to-send reply to the sender describing what was found."""
    greeting = f"Hi {sender_name}," if sender_name else "Hi,"
    base = re.sub(r"^(re|fw|fwd)[:_]\s*", "", subject.strip(), flags=re.I)
    subj = f"RE: {base}"
    lines = [greeting, ""]
    status = result["status"]
    if status == "OK":
        lines += ["We have compared the Shipping Instruction against the draft Bill of Lading",
                  "and all checked fields match (shipper, consignee, notify party, ports,",
                  "container count and gross weight). The draft BL is in order.", ""]
    elif status == "MISMATCH":
        bad = [r for r in rows if r["verdict"] == "mismatch"]
        lines += ["We compared the Shipping Instruction against the draft Bill of Lading and",
                  f"found {len(bad)} discrepanc{'y' if len(bad) == 1 else 'ies'} that need correcting:", ""]
        for r in bad:
            lines += [f"  - {r['label']}", f"      SI : {r['si']}", f"      BL : {r['bl']}"]
        lines += ["", "Please confirm the correct details so we can amend the draft BL.", ""]
    else:
        reason = result.get("review_reason")
        lines += ["We could not complete the comparison of the Shipping Instruction and draft BL:",
                  f"  {REASONS.get(reason, 'The documents need a manual check.')}", "",
                  NEXT_STEP.get(reason, "Please resend the documents."), ""]
    lines += ["Best regards,", "Shipping Documentation"]
    return subj, "\n".join(lines)


def report_markdown(title, result, rows):
    out = [f"# SDOC verification report", "", f"**Case:** {title}", f"**Verdict:** {result['status']}"]
    if result.get("review_reason"):
        out.append(f"**Reason:** {REASONS.get(result['review_reason'], result['review_reason'])}")
    out += ["", "| Field | SI | BL | Result |", "|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['label']} | {r['si']} | {r['bl']} | {r['verdict']} |")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------- whole inbox
def analyze_inbox(data_dir, use_ai=False):
    """Run the full pipeline over every email and return one detail row each.
    Same decisions as pipeline.run(), plus the extracted values."""
    inbox = Inbox(str(data_dir))
    out = []
    for email in inbox:
        atts = email.get("attachments", []) or []
        category, _ = classify.classify(email, has_attachments=bool(atts))
        row = {"email_id": email["email_id"], "subject": email.get("subject", ""),
               "from": email.get("from", ""), "category": category,
               "status": "OK", "review_reason": None, "defect_fields": [], "rows": []}
        if category == "BL_COMPARISON":
            si_path, bl_path = pipeline._pick_si_bl(atts) if len(atts) >= 2 else (None, None)
            if si_path and bl_path:
                result, si_res, bl_res = pipeline.compare_documents(
                    inbox.read_bytes(si_path), si_path, inbox.read_bytes(bl_path), bl_path,
                    use_ai=use_ai)
                row["rows"] = field_rows(si_res, bl_res)
            else:
                result = pipeline.decide_comparison(email, inbox)
            row.update(status=result["status"], review_reason=result["review_reason"],
                       defect_fields=result["defect_fields"])
        out.append(row)
    return out


def summarize(rows):
    cats, status, reasons, fields = {}, {}, {}, {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
        status[r["status"]] = status.get(r["status"], 0) + 1
        if r["review_reason"]:
            reasons[r["review_reason"]] = reasons.get(r["review_reason"], 0) + 1
        for f in r["defect_fields"]:
            fields[f] = fields.get(f, 0) + 1
    compared = sum(1 for r in rows if r["category"] == "BL_COMPARISON")
    return {"total": len(rows), "compared": compared, "categories": cats, "status": status,
            "review_reasons": reasons, "defect_fields": fields}


def to_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["email_id", "category", "status", "review_reason", "defect_fields", "subject"])
    for r in rows:
        w.writerow([r["email_id"], r["category"], r["status"], r["review_reason"] or "",
                    ";".join(r["defect_fields"]), r["subject"]])
    return buf.getvalue()


def to_submission_json(rows):
    """The exact shape the hackathon scorer expects."""
    return json.dumps({r["email_id"]: {
        "category": r["category"], "status": r["status"],
        "review_reason": r["review_reason"], "has_defect": r["status"] == "MISMATCH",
        "defect_fields": r["defect_fields"]} for r in rows}, indent=2)


# ---------------------------------------------------------------- audit trail
RULES = {
    "shipper": "company name only (first line, address dropped), upper-cased, spaces collapsed",
    "consignee": "company name only (first line, address dropped), upper-cased, spaces collapsed",
    "notify_party": "company name only (first line, address dropped), upper-cased, spaces collapsed",
    "port_of_loading": "port text as printed, trailing (CODE) dropped, upper-cased",
    "port_of_discharge": "port text as printed, trailing (CODE) dropped, upper-cased",
    "container_count": "number of containers (from '3 x 40HC', '03', '40HC x 3'), leading zeros ignored",
    "gross_weight_kg": "converted to kilograms (handles 61,026.00 / 61.026,00 / MT / LBS)",
}


def audit_rows(rows):
    """Why each field got its verdict: raw text, normalised value and the rule
    that produced it. Makes every decision traceable."""
    out = []
    for r in rows:
        if r["verdict"] == "blank":
            decision = "Blank or placeholder on one side: escalated, never guessed"
        elif r["verdict"] == "match":
            decision = "Normalised values are identical"
        else:
            decision = "Normalised values differ: flagged as a defect"
        out.append({"Field": r["label"],
                    "SI (normalised)": r.get("si_norm") or "—",
                    "BL (normalised)": r.get("bl_norm") or "—",
                    "Decision": decision, "Rule applied": RULES[r["field"]]})
    return out


# ------------------------------------------------------------------- batch
_ROLE_RE = re.compile(r"(?<![a-z0-9])(si|bl)(?![a-z0-9])", re.I)


def pair_documents(names):
    """Pair uploaded file names into (key, si_name, bl_name).

    A name is an SI or BL if it contains a standalone 'SI' or 'BL' token
    (email_004_SI.txt, 'ABC - BL.pdf'); the rest of the name is the pair key.
    Returns (pairs, unpaired_names)."""
    slots = {}
    unpaired = []
    for n in names:
        stem = n.rsplit(".", 1)[0]
        m = _ROLE_RE.search(stem)
        if not m:
            unpaired.append(n)
            continue
        key = re.sub(r"[\s_\-]+", " ", (stem[:m.start()] + " " + stem[m.end():])).strip().lower()
        slots.setdefault(key, {})[m.group(1).upper()] = n
    pairs = []
    for key, d in sorted(slots.items()):
        if "SI" in d and "BL" in d:
            pairs.append((key, d["SI"], d["BL"]))
        else:
            unpaired.extend(d.values())
    return pairs, unpaired


def mailto_link(to, subject, body):
    """A mailto: URL that opens the user's mail client pre-filled. Real
    functionality: nothing is sent until the user presses send there."""
    return f"mailto:{quote(to or '', safe='@,')}?subject={quote(subject, safe='')}&body={quote(body, safe='')}"


# ------------------------------------------------------------ simulated outbox
def sender_first_name(sender):
    """'hanna_azhari@aprilasia.com' -> 'Hanna Azhari' (best effort)."""
    local = (sender or "").split("@")[0].replace(".", " ").replace("_", " ").strip()
    return local.title() or None


DELIVERY_SENT = "Sent (simulated)"
DELIVERY_HELD = "Awaiting approval"
DELIVERY_HUMAN = "Left for a human"
DELIVERY_NONE = "No reply needed"


def plan_replies(rows_all, hold_mismatch=False):
    """Decide, for every email, whether the system replies on its own.

    - Comparison OK           -> reply automatically
    - Comparison MISMATCH     -> reply automatically (or hold for approval)
    - NEEDS_REVIEW            -> never auto-replied; left for a real person
    - Anything that was not an actual comparison needs no reply

    Nothing is ever really sent: delivery is a simulation. Returns one dict
    per email that needs attention, in inbox order.
    """
    plan = []
    for r in rows_all:
        if r["category"] != "BL_COMPARISON":
            continue
        result = {"status": r["status"], "review_reason": r["review_reason"],
                  "defect_fields": r["defect_fields"]}
        if r["status"] == "NEEDS_REVIEW":
            delivery = DELIVERY_HUMAN
        elif not r["rows"]:
            delivery = DELIVERY_NONE          # e.g. no attachments and no request to compare
        elif r["status"] == "MISMATCH" and hold_mismatch:
            delivery = DELIVERY_HELD
        else:
            delivery = DELIVERY_SENT
        if delivery == DELIVERY_NONE:
            continue
        subject, body = draft_reply(r["subject"], result, r["rows"], sender_first_name(r["from"]))
        plan.append({"email_id": r["email_id"], "to": r["from"], "subject": subject, "body": body,
                     "verdict": r["status"], "delivery": delivery})
    return plan


def outbox_csv(plan):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["email_id", "to", "verdict", "delivery", "subject"])
    for p in plan:
        w.writerow([p["email_id"], p["to"], p["verdict"], p["delivery"], p["subject"]])
    return buf.getvalue()


def selection_change(selected_rows, last_rows):
    """Row the user just clicked in a table, or None if the selection is unchanged.
    Lets a click drive a dropdown without overriding the dropdown afterwards."""
    if selected_rows and list(selected_rows) != list(last_rows or []):
        return selected_rows[0]
    return None
