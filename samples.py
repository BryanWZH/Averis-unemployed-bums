"""Ready-made SI/BL pairs a visitor can try with one click. Each one points at
a pair already bundled with the sample inbox, and tests/test_samples.py checks
that it really produces the result it promises."""
import os

import pipeline
from loader import Inbox

# playground=True: readable by the rule-based reader, so its fields can be
# pre-filled into the "Break it yourself" editor.
SAMPLES = [
    {"id": "match_txt", "icon": "✅", "title": "Everything matches", "email": "email_001",
     "blurb": "Plain-text SI and BL that agree on all 7 fields.",
     "status": "OK", "reason": None, "playground": True},
    {"id": "match_pdf", "icon": "📄", "title": "Matching PDFs", "email": "email_059",
     "blurb": "The same check on PDF documents.",
     "status": "OK", "reason": None, "playground": True},
    {"id": "wrong_weight", "icon": "⚖️", "title": "Wrong weight and container count", "email": "email_313",
     "blurb": "PDFs where the gross weight and the number of containers differ.",
     "status": "MISMATCH", "reason": None, "playground": True},
    {"id": "wrong_party", "icon": "🏢", "title": "Different consignee", "email": "email_004",
     "blurb": "The consignee and notify party don't match.",
     "status": "MISMATCH", "reason": None, "playground": True},
    {"id": "wrong_port", "icon": "🚢", "title": "Wrong ports (Excel)", "email": "email_243",
     "blurb": "Excel files where the loading and discharge ports differ.",
     "status": "MISMATCH", "reason": None, "playground": True},
    {"id": "mixed_formats", "icon": "🔀", "title": "Word vs Excel", "email": "email_107",
     "blurb": "The SI and BL come in different file formats. The check still works.",
     "status": "MISMATCH", "reason": None, "playground": True},
    {"id": "blank_field", "icon": "⬜", "title": "A field is left blank", "email": "email_516",
     "blurb": "A blank field is never guessed: it goes to a human.",
     "status": "NEEDS_REVIEW", "reason": "missing_value", "playground": False},
    {"id": "wrong_doc", "icon": "🧾", "title": "Wrong document attached", "email": "email_501",
     "blurb": "An invoice or packing list sent instead of an SI or BL.",
     "status": "NEEDS_REVIEW", "reason": "wrong_doc_type", "playground": False},
    {"id": "scan", "icon": "🖼️", "title": "Scanned image", "email": "email_512",
     "blurb": "An image-only scan can't be trusted, so it is escalated.",
     "status": "NEEDS_REVIEW", "reason": "unreadable", "playground": False},
]
BY_ID = {s["id"]: s for s in SAMPLES}


def load(sample, data_dir):
    """(si_bytes, si_name, bl_bytes, bl_name) for a sample."""
    inbox = Inbox(str(data_dir))
    email = inbox.get(sample["email"])
    si, bl = pipeline._pick_si_bl(email["attachments"])
    return inbox.read_bytes(si), os.path.basename(si), inbox.read_bytes(bl), os.path.basename(bl)
