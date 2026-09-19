"""SDOC web demo: compare a Shipping Instruction against a draft Bill of Lading
in the browser, or browse the sample inbox.

    streamlit run app.py
"""
import os
from pathlib import Path

import streamlit as st

# On Streamlit Community Cloud the key lives in "Secrets", not the environment.
try:
    if "ANTHROPIC_API_KEY" in st.secrets and not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

import ai_extract
import classify
import pipeline
from loader import Inbox
from normalize import COMPARE_FIELDS, normalize_value, is_blank_value

DATA_DIR = Path(__file__).parent
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
FIELD_NAMES = {
    "shipper": "Shipper", "consignee": "Consignee", "notify_party": "Notify party",
    "port_of_loading": "Port of loading", "port_of_discharge": "Port of discharge",
    "container_count": "Container count", "gross_weight_kg": "Gross weight (kg)",
}
REASONS = {
    "missing_attachment": "An SI/BL attachment is missing.",
    "unreadable": "A document could not be read (empty, corrupt or scanned).",
    "wrong_doc_type": "A document is not an SI or BL (e.g. an invoice or packing list).",
    "missing_value": "A field is blank or a placeholder, so it can't be compared.",
}

st.set_page_config(page_title="SDOC Verification", page_icon="🚢", layout="wide")
st.title("🚢 SDOC: Shipping Document Verification")
st.caption("Checks a Shipping Instruction (SI) against a draft Bill of Lading (BL) "
           "across 7 fields, and escalates to a human when it can't tell.")

def _secret(name):
    value = os.environ.get(name)
    if not value:
        try:
            value = st.secrets.get(name)
        except Exception:
            value = None
    return (value or "").strip()


# AI reading spends API credit, and this page is public. It stays OFF for
# everyone unless AI_ACCESS_CODE is configured AND the visitor enters it.
access_code = _secret("AI_ACCESS_CODE")
ai_ready = ai_extract.available() and bool(access_code)
use_ai = False
if ai_ready:
    entered = st.sidebar.text_input("AI access code", type="password",
                                    help="Optional. Unlocks AI document reading.")
    unlocked = bool(entered) and entered.strip() == access_code
    use_ai = st.sidebar.toggle(
        "Read documents with AI", value=unlocked, disabled=not unlocked,
        help="AI reads the documents; plain code does the comparing and deciding.")
    if not unlocked:
        st.sidebar.info("Using the free rule-based reader. Enter the access code to use AI reading.")
else:
    st.sidebar.info("Using the rule-based reader (no AI calls are made).")


def show_result(result, si_res, bl_res):
    status = result["status"]
    if status == "OK":
        st.success("OK: SI and BL match on all 7 fields.")
    elif status == "MISMATCH":
        names = ", ".join(FIELD_NAMES[f] for f in result["defect_fields"])
        st.error(f"MISMATCH in: {names}")
    else:
        st.warning(f"NEEDS REVIEW: {REASONS.get(result['review_reason'], result['review_reason'])}")
        for label, res in (("SI", si_res), ("BL", bl_res)):
            if not res.readable and res.unreadable_reason:
                st.caption(f"{label}: {res.unreadable_reason}")

    rows = []
    for f in COMPARE_FIELDS:
        sv, bv = si_res.fields.get(f), bl_res.fields.get(f)
        if is_blank_value(sv) or is_blank_value(bv):
            verdict = "blank"
        else:
            verdict = "✅" if normalize_value(f, sv) == normalize_value(f, bv) else "❌"
        rows.append({"Field": FIELD_NAMES[f], "SI": sv or "", "BL": bv or "", "Match": verdict})
    st.dataframe(rows, hide_index=True, width="stretch")


tab_upload, tab_inbox = st.tabs(["Upload two documents", "Browse sample inbox"])

with tab_upload:
    st.write("Upload an SI and a draft BL (txt, pdf, docx or xlsx, up to 5 MB each).")
    c1, c2 = st.columns(2)
    si_file = c1.file_uploader("Shipping Instruction (SI)", type=["txt", "pdf", "docx", "xlsx"])
    bl_file = c2.file_uploader("Draft Bill of Lading (BL)", type=["txt", "pdf", "docx", "xlsx"])
    if si_file and bl_file:
        if si_file.size > MAX_UPLOAD_BYTES or bl_file.size > MAX_UPLOAD_BYTES:
            st.error("Files must be 5 MB or smaller.")
        else:
            with st.spinner("Reading and comparing..."):
                out = pipeline.compare_documents(
                    si_file.getvalue(), si_file.name, bl_file.getvalue(), bl_file.name,
                    use_ai=use_ai)
            show_result(*out)


@st.cache_data
def _load_emails():
    return Inbox(str(DATA_DIR)).emails()


with tab_inbox:
    emails = _load_emails()
    if not emails:
        st.info("No sample inbox is bundled with this deployment.")
    else:
        choice = st.selectbox(
            "Pick an email", emails,
            format_func=lambda e: f"{e['email_id']}: {e['subject'][:80]}"
                                  + (" 📎" if e.get("attachments") else ""))
        category, _ = classify.classify(choice, has_attachments=bool(choice.get("attachments")))
        st.markdown(f"**Category:** `{category}`  ·  **From:** {choice['from']}")
        st.text_area("Body", choice.get("body", ""), height=180, disabled=True)
        if category == "BL_COMPARISON":
            atts = choice.get("attachments", [])
            inbox = Inbox(str(DATA_DIR))
            si_path, bl_path = pipeline._pick_si_bl(atts) if len(atts) >= 2 else (None, None)
            if si_path and bl_path:
                with st.spinner("Comparing attachments..."):
                    out = pipeline.compare_documents(
                        inbox.read_bytes(si_path), si_path,
                        inbox.read_bytes(bl_path), bl_path, use_ai=use_ai)
                show_result(*out)
            else:
                result = pipeline.decide_comparison(choice, inbox)
                if result["status"] == "OK":
                    st.info("No attachments and no comparison request, so nothing to check.")
                else:
                    st.warning(f"NEEDS REVIEW: {REASONS.get(result['review_reason'], result['review_reason'])}")
        else:
            st.info("No document comparison needed for this email.")
