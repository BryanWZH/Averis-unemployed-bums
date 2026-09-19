"""Stage 1 — classify an inbox email into one of five categories.

Signal hierarchy (strongest first):
  1. Attachments present -> BL_COMPARISON. In this inbox only a document
     comparison request ever carries attachments (SI/BL pairs); every
     other category is attachment-free. This is checked first because
     it is close to deterministic and resolves the large "0-attachment
     BL_COMPARISON vs SI_REQUEST vs GENERAL" ambiguity for free.
  2. Subject-line signals — the coded subject formats used in this inbox
     are distinctive per category (carrier-code-in-parens for a BL
     request, an explicit "SI" token for an SI request, etc).
  3. Body keyword signals, weighted lower than subject because a couple
     of phrases (e.g. "draft BL") legitimately show up in more than one
     category's template.
"""
import re

CATEGORIES = ["BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"]

SUBJECT_KW = {
    "BL_COMPARISON": [
        "to confirm docs", "request bl draft", "amend bl", "draft bl",
        "bill of lading",
    ],
    "SI_REQUEST": [
        "cust si", "request si", "si needed", "latest si",
    ],
    "INVOICE_QUERY": [
        "billing", "missing gr", "cancel invoice", "local charges",
        "d & d", "d&d charges", "total freight",
    ],
    "GENERAL": [
        "update summary", "berthing report", "reminder", "rpa_",
        "outstanding bl", "pending bl release", "new year",
        "approval required", "delivery planning",
    ],
    "SPAM": [
        "won", "gift card", "prize", "% off", "verify", "suspension",
        "undelivered", "storage", "bitcoin", "singles", "iphone",
    ],
}

BODY_KW = {
    "BL_COMPARISON": [
        "draft bl", "bill of lading", "please check the details and confirm",
        "verify the bl matches the si", "check the draft bl against the si",
        "confirm the bl is in order", "please compare the si and draft bl",
    ],
    "SI_REQUEST": [
        "shipping instruction", "documents required", "packing list\n",
        "please revert with draft bl once available",
    ],
    "INVOICE_QUERY": [
        "invoice", "gr is still missing", "reverse the pgi",
        "detention", "demurrage", "d&d", "d & d", "thc", "breakdown",
    ],
    "GENERAL": [
        "berthing", "loading completed", "automated notification",
        "no action required", "outstanding bl", "office resumes",
        "submit si & aed",
    ],
    "SPAM": [
        "congratulations", "claim your", "customs fee", "confirm payment",
        "verify your account", "avoid deactivation", "avoid suspension",
        "bank details", "bitcoin", "guaranteed", "singles", "survey",
        "click here" ,"limited time offer",
    ],
}

# Subject patterns that are near-unique to one category.
CARRIER_CODE_PAREN = re.compile(
    r"\b(MSC|CMA|HAPAG|OOCL|EVER|ONE|YM|PIL|MONTER)\(", re.I)
SI_TOKEN = re.compile(r"(^|[\s_\-])SI([\s_\-]|$)", re.I)

PRIORITY = ["SPAM", "INVOICE_QUERY", "SI_REQUEST", "BL_COMPARISON", "GENERAL"]


def _score(text, kw_dict, weight):
    scores = {c: 0 for c in CATEGORIES}
    low = text.lower()
    for cat, kws in kw_dict.items():
        for kw in kws:
            if kw in low:
                scores[cat] += weight
    return scores


def classify(email, has_attachments):
    if has_attachments:
        return "BL_COMPARISON", "attachment_present"

    subject = email.get("subject", "") or ""
    body = email.get("body", "") or ""

    scores = {c: 0 for c in CATEGORIES}
    for c, s in _score(subject, SUBJECT_KW, 4).items():
        scores[c] += s
    for c, s in _score(body, BODY_KW, 1).items():
        scores[c] += s

    if CARRIER_CODE_PAREN.search(subject):
        scores["BL_COMPARISON"] += 5
    is_reminder_style = "submit" in subject.lower() or "reminder" in subject.lower()
    if SI_TOKEN.search(subject) and not is_reminder_style:
        scores["SI_REQUEST"] += 5
        # "SI -" style subjects can also contain a carrier code in parens
        # e.g. "SI - <bl> - DIRECT(MSC) - ..."; don't let that outweigh
        # the explicit SI token.
        scores["BL_COMPARISON"] = max(0, scores["BL_COMPARISON"] - 5)

    best = max(scores.values())
    if best == 0:
        return "GENERAL", "default_fallback"
    winners = [c for c in PRIORITY if scores[c] == best]
    return winners[0], "keyword_score"
