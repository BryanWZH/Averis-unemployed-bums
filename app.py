"""SDOC web app: inbox dashboard, review queue, document comparison with a
visual diff, and draft replies.

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
import report
from loader import Inbox

DATA_DIR = Path(__file__).parent
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
STATUS_STYLE = {
    "OK": ("#1e8e5a", "#e3f4ea", "OK"),
    "MISMATCH": ("#c0392b", "#fbe7e4", "MISMATCH"),
    "NEEDS_REVIEW": ("#b9770e", "#fdf1dc", "NEEDS REVIEW"),
}

st.set_page_config(page_title="SDOC Verification", page_icon="🚢", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
.sdoc-badge {display:inline-block; padding:.35rem .9rem; border-radius:999px; font-weight:700;
             font-size:1.05rem; letter-spacing:.02em;}
.sdoc-diff {font-family: ui-monospace, Menlo, Consolas, monospace; font-size:.95rem;}
</style>
""", unsafe_allow_html=True)


def _secret(name):
    value = os.environ.get(name)
    if not value:
        try:
            value = st.secrets.get(name)
        except Exception:
            value = None
    return (value or "").strip()


st.title("🚢 SDOC: Shipping Document Verification")
st.caption("Reads every email in a shipping-ops inbox, compares each Shipping Instruction (SI) "
           "with its draft Bill of Lading (BL) across 7 fields, and hands anything uncertain to a human.")

# AI reading spends API credit, and this page is public. It stays OFF for
# everyone unless AI_ACCESS_CODE is configured AND the visitor enters it.
access_code = _secret("AI_ACCESS_CODE")
ai_ready = ai_extract.available() and bool(access_code)
use_ai = False
st.sidebar.header("Reader")
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
st.sidebar.markdown("---")
st.sidebar.caption("**How it decides.** Documents are read (by AI or rules), then plain, auditable "
                   "code compares the fields. A model never gets to talk itself out of a discrepancy.")


@st.cache_data(show_spinner="Analysing the whole inbox...")
def load_analysis():
    return report.analyze_inbox(DATA_DIR, use_ai=False)


def badge(status):
    fg, bg, label = STATUS_STYLE.get(status, ("#555", "#eee", status))
    st.markdown(f"<span class='sdoc-badge' style='color:{fg};background:{bg}'>{label}</span>",
                unsafe_allow_html=True)


def show_case(key, title, subject, sender, result, rows):
    """Verdict, side-by-side field table with a character-level diff,
    then the draft reply and report downloads."""
    badge(result["status"])
    if result["status"] == "MISMATCH":
        names = ", ".join(report.FIELD_NAMES[f] for f in result["defect_fields"])
        st.markdown(f"**Differs in:** {names}")
    elif result["status"] == "NEEDS_REVIEW":
        reason = result.get("review_reason")
        st.markdown(f"**Why:** {report.REASONS.get(reason, reason)}")
        st.markdown(f"**Suggested next step:** {report.NEXT_STEP.get(reason, 'Check manually.')}")
    else:
        st.markdown("All 7 fields match.")

    if rows:
        st.markdown("##### Field by field")
        h = st.columns([1.3, 3, 3, 0.9])
        for c, t in zip(h, ("Field", "Shipping Instruction", "Draft BL", "Result")):
            c.markdown(f"<span style='color:#6b7280;font-size:.85rem'>{t}</span>", unsafe_allow_html=True)
        for r in rows:
            c1, c2, c3, c4 = st.columns([1.3, 3, 3, 0.9])
            c1.markdown(f"**{r['label']}**")
            if r["verdict"] == "mismatch":
                a, b = report.diff_html(r["si"], r["bl"])
                c2.markdown(f"<div class='sdoc-diff'>{a}</div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='sdoc-diff'>{b}</div>", unsafe_allow_html=True)
                c4.markdown("❌")
            else:
                c2.markdown(f"<div class='sdoc-diff'>{r['si'] or '—'}</div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='sdoc-diff'>{r['bl'] or '—'}</div>", unsafe_allow_html=True)
                c4.markdown("✅" if r["verdict"] == "match" else "⚠️")

    if result["status"] != "OK" or rows:
        with st.expander("✉️ Draft reply to the sender", expanded=result["status"] != "OK"):
            first = (sender or "").split("@")[0].replace(".", " ").replace("_", " ").title() or None
            subj, body = report.draft_reply(subject or title, result, rows, first)
            st.text_input("Subject", subj, key=f"{key}_subj")
            st.text_area("Message", body, height=280, key=f"{key}_body")
    st.download_button("⬇️ Download report (Markdown)", report.report_markdown(title, result, rows),
                       file_name=f"{key}_report.md", key=f"{key}_dl")


tab_dash, tab_queue, tab_compare, tab_inbox = st.tabs(
    ["📊 Dashboard", "🚩 Review queue", "🔍 Compare documents", "📬 Inbox browser"])

# ------------------------------------------------------------------ dashboard
with tab_dash:
    rows_all = load_analysis()
    s = report.summarize(rows_all)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Emails processed", s["total"])
    m2.metric("Document comparisons", s["compared"])
    m3.metric("Mismatches caught", s["status"].get("MISMATCH", 0))
    m4.metric("Sent to a human", s["status"].get("NEEDS_REVIEW", 0))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Emails by category")
        st.bar_chart(s["categories"], horizontal=True, color="#0e9f9a")
    with c2:
        st.markdown("##### Which fields go wrong most")
        st.bar_chart({report.FIELD_NAMES[k]: v for k, v in s["defect_fields"].items()},
                     horizontal=True, color="#c0392b")
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("##### Outcome of the comparisons")
        comp = [r for r in rows_all if r["category"] == "BL_COMPARISON"]
        st.bar_chart({"OK": sum(r["status"] == "OK" for r in comp),
                      "Mismatch": sum(r["status"] == "MISMATCH" for r in comp),
                      "Needs review": sum(r["status"] == "NEEDS_REVIEW" for r in comp)},
                     horizontal=True)
    with c4:
        st.markdown("##### Why documents went to a human")
        st.bar_chart({k.replace("_", " "): v for k, v in s["review_reasons"].items()},
                     horizontal=True, color="#b9770e")

    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("⬇️ Results (CSV)", report.to_csv(rows_all), "sdoc_results.csv")
    d2.download_button("⬇️ submission.json", report.to_submission_json(rows_all), "submission.json")

# --------------------------------------------------------------- review queue
with tab_queue:
    rows_all = load_analysis()
    queue = [r for r in rows_all if r["status"] == "NEEDS_REVIEW"]
    flagged = [r for r in rows_all if r["status"] == "MISMATCH"]
    st.markdown(f"**{len(queue)}** emails need a human because the system could not decide "
                f"confidently, and **{len(flagged)}** have confirmed mismatches. "
                "Nothing is guessed: unreadable, blank or wrong documents are escalated.")
    view = st.radio("Show", ["Needs review", "Mismatches"], horizontal=True)
    items = queue if view == "Needs review" else flagged
    reason_filter = None
    if view == "Needs review":
        reasons = sorted({r["review_reason"] for r in queue})
        reason_filter = st.multiselect("Filter by reason", reasons, default=reasons,
                                       format_func=lambda x: x.replace("_", " "))
        items = [r for r in items if r["review_reason"] in reason_filter]
    if items:
        st.dataframe(
            [{"Email": r["email_id"], "Subject": r["subject"][:70],
              "Reason / fields": (r["review_reason"] or "").replace("_", " ") if view == "Needs review"
              else ", ".join(report.FIELD_NAMES[f] for f in r["defect_fields"]),
              "Next step": report.NEXT_STEP.get(r["review_reason"], "Correct the flagged fields.")}
             for r in items], hide_index=True, width="stretch")
        pick = st.selectbox("Open a case", items,
                            format_func=lambda r: f"{r['email_id']}: {r['subject'][:70]}")
        email = Inbox(str(DATA_DIR)).get(pick["email_id"])
        show_case(f"q_{pick['email_id']}", pick["email_id"], pick["subject"], email.get("from"),
                  {"status": pick["status"], "review_reason": pick["review_reason"],
                   "defect_fields": pick["defect_fields"]}, pick["rows"])
    else:
        st.success("Nothing to review.")

# ------------------------------------------------------------ compare uploads
with tab_compare:
    st.write("Upload an SI and a draft BL (txt, pdf, docx or xlsx, up to 5 MB each).")
    u1, u2 = st.columns(2)
    si_file = u1.file_uploader("Shipping Instruction (SI)", type=["txt", "pdf", "docx", "xlsx"])
    bl_file = u2.file_uploader("Draft Bill of Lading (BL)", type=["txt", "pdf", "docx", "xlsx"])
    if si_file and bl_file:
        if si_file.size > MAX_UPLOAD_BYTES or bl_file.size > MAX_UPLOAD_BYTES:
            st.error("Files must be 5 MB or smaller.")
        else:
            with st.spinner("Reading and comparing..."):
                result, si_res, bl_res = pipeline.compare_documents(
                    si_file.getvalue(), si_file.name, bl_file.getvalue(), bl_file.name, use_ai=use_ai)
            show_case("upload", f"{si_file.name} vs {bl_file.name}", "Your documents", None,
                      result, report.field_rows(si_res, bl_res))

# --------------------------------------------------------------- inbox browser
with tab_inbox:
    rows_all = load_analysis()
    by_id = {r["email_id"]: r for r in rows_all}
    cats = sorted({r["category"] for r in rows_all})
    f1, f2 = st.columns([1, 2])
    cat_sel = f1.multiselect("Category", cats, default=cats)
    text_sel = f2.text_input("Search subject", "")
    shown = [r for r in rows_all if r["category"] in cat_sel and text_sel.lower() in r["subject"].lower()]
    st.caption(f"{len(shown)} emails")
    if shown:
        pick = st.selectbox("Pick an email", shown,
                            format_func=lambda r: f"{r['email_id']}: {r['subject'][:80]}")
        email = Inbox(str(DATA_DIR)).get(pick["email_id"])
        st.markdown(f"**Category:** `{pick['category']}`  ·  **From:** {email.get('from', '')}")
        st.text_area("Body", email.get("body", ""), height=180, disabled=True,
                     key=f"body_{pick['email_id']}")
        if pick["category"] == "BL_COMPARISON":
            result = {"status": pick["status"], "review_reason": pick["review_reason"],
                      "defect_fields": pick["defect_fields"]}
            rows = pick["rows"]
            atts = email.get("attachments", [])
            if use_ai and len(atts) >= 2:
                si_path, bl_path = pipeline._pick_si_bl(atts)
                if si_path and bl_path:
                    inbox = Inbox(str(DATA_DIR))
                    with st.spinner("Reading with AI..."):
                        result, si_res, bl_res = pipeline.compare_documents(
                            inbox.read_bytes(si_path), si_path, inbox.read_bytes(bl_path), bl_path,
                            use_ai=True)
                    rows = report.field_rows(si_res, bl_res)
            show_case(f"in_{pick['email_id']}", pick["email_id"], email.get("subject"),
                      email.get("from"), result, rows)
        else:
            st.info("No document comparison needed for this email.")
