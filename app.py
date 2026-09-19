"""SDOC web app: inbox dashboard, review queue, document comparison with a
visual diff, and draft replies.

    streamlit run app.py
"""
import os
from datetime import datetime
from pathlib import Path

import streamlit as st

# On Streamlit Community Cloud the key lives in "Secrets", not the environment.
try:
    if "ANTHROPIC_API_KEY" in st.secrets and not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

import ai_extract
import ai_reply
import classify
import dashboard
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
cross_check = False
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
    cross_check = st.sidebar.toggle(
        "Cross-check AI with the rule-based reader", value=False, disabled=not use_ai,
        help="Both readers read every document. If they disagree on any field the case goes to a "
             "human instead of being decided.")
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


@st.cache_data(show_spinner=False, max_entries=64)
def cached_compare(si_bytes, si_name, bl_bytes, bl_name, use_ai=False, cross_check=False):
    """compare_documents, cached. Streamlit re-runs every tab on every click, so
    without this an AI read would be repeated (and billed) on each interaction."""
    return pipeline.compare_documents(si_bytes, si_name, bl_bytes, bl_name,
                                      use_ai=use_ai, cross_check=cross_check)


def clickable_table(data, items, table_key, pick_key):
    """A table where clicking any cell opens that row in the picker below it.
    `items` must line up row-for-row with `data`; `pick_key` is the session key of
    the selectbox that shows the chosen item. A click only changes the picker when
    it is a NEW click, so the picker can still be used on its own afterwards."""
    ev = st.dataframe(data, hide_index=True, width="stretch", on_select="rerun",
                      selection_mode="single-cell", key=table_key)
    cells = [tuple(c) for c in ev.selection.cells]
    last_key = table_key + "_last"
    clicked = report.selection_change(cells, st.session_state.get(last_key))
    st.session_state[last_key] = cells
    if clicked is not None and clicked[0] < len(items):
        st.session_state[pick_key] = items[clicked[0]]
    if st.session_state.get(pick_key) not in items:
        st.session_state.pop(pick_key, None)
    st.caption("Click any row to open it below.")


def docs_for(email):
    """(si_bytes, si_name, bl_bytes, bl_name) for an email with both attachments, else None."""
    atts = email.get("attachments", []) or []
    if len(atts) < 2:
        return None
    si_path, bl_path = pipeline._pick_si_bl(atts)
    if not (si_path and bl_path):
        return None
    inbox = Inbox(str(DATA_DIR))
    return inbox.read_bytes(si_path), si_path, inbox.read_bytes(bl_path), bl_path


def _apply_polish(key, body, facts):
    text, used = ai_reply.polish(body, facts)
    st.session_state[f"{key}_body"] = text
    st.session_state[f"{key}_polished"] = used


def show_case(key, title, subject, sender, result, rows, docs=None):
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
        dis = result.get("disagreements")
        if dis:
            names = sorted(set(dis["si"]) | set(dis["bl"]))
            st.markdown("**Readers disagree on:** " + ", ".join(report.FIELD_NAMES[f] for f in names))
        if use_ai and docs:
            if st.button("🤖 Ask AI for a second opinion", key=f"{key}_op_btn"):
                with st.spinner("The AI is reading the documents..."):
                    st.session_state[f"{key}_op"] = pipeline.second_opinion(*docs)
            op = st.session_state.get(f"{key}_op")
            if op:
                if op["available"] and op["suggested_defects"]:
                    lines = []
                    for f in op["suggested_defects"]:
                        lines.append(f"- **{report.FIELD_NAMES[f]}**: SI `{op['si_res'].fields.get(f)}` "
                                     f"vs BL `{op['bl_res'].fields.get(f)}`")
                    st.info("🤖 **AI second opinion (advisory only, the verdict above is unchanged).** "
                            "The AI thinks these fields differ; please confirm against the originals:"
                            + chr(10) * 2 + chr(10).join(lines))
                elif op["available"]:
                    st.info("🤖 **AI second opinion (advisory only).** The AI found no differences in the "
                            "fields it could read. A person should still confirm.")
                else:
                    st.info("🤖 **AI second opinion (advisory only).** " + op["note"])
    else:
        st.markdown("All 7 fields match.")

    if rows:
        st.markdown("**Field by field**")
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

    if rows:
        with st.expander("🔎 Audit trail: how each field was decided"):
            st.caption("Every verdict comes from these normalised values and rules, made by plain code, "
                       "not by a model's judgment.")
            st.dataframe(report.audit_rows(rows), hide_index=True, width="stretch")

    if result["status"] != "OK" or rows:
        with st.expander("✉️ Draft reply to the sender", expanded=result["status"] != "OK"):
            first = report.sender_first_name(sender)
            subj, body = report.draft_reply(subject or title, result, rows, first)
            subj_val = st.text_input("Subject", subj, key=f"{key}_subj")
            body_val = st.text_area("Message", body, height=280, key=f"{key}_body")
            if use_ai and result["status"] != "NEEDS_REVIEW":
                facts = [v for r_ in rows if r_["verdict"] == "mismatch" for v in (r_["si"], r_["bl"])]
                st.button("✨ Polish wording with AI", key=f"{key}_polish",
                          on_click=_apply_polish, args=(key, body, facts),
                          help="Rewords the message. If the AI changes any value or adds a number, "
                               "the original template is kept.")
                if st.session_state.get(f"{key}_polished") is False:
                    st.caption("The AI rewrite was rejected (it changed a fact or failed), so the "
                               "template is kept.")
            to_addr = sender if sender and "@" in sender else ""
            st.link_button("✉️ Open in my email app", report.mailto_link(to_addr, subj_val, body_val))
            st.caption("Opens your own mail program with the recipient, subject and message filled in, "
                       "including any edits above. SDOC does not send email itself.")
    st.download_button("⬇️ Download report (Markdown)", report.report_markdown(title, result, rows),
                       file_name=f"{key}_report.md", key=f"{key}_dl")


tab_dash, tab_out, tab_queue, tab_compare, tab_inbox = st.tabs(
    ["📊 Dashboard", "📤 Outbox", "🚩 Review queue", "🔍 Compare documents", "📬 Inbox browser"])

# ------------------------------------------------------------------ dashboard
with tab_dash:
    dashboard.render(load_analysis())

# --------------------------------------------------------------------- outbox
def _approve(idx):
    st.session_state.outbox["plan"][idx]["delivery"] = report.DELIVERY_SENT
    st.session_state.outbox["plan"][idx]["approved"] = True


def _approve_all():
    for item in st.session_state.outbox["plan"]:
        if item["delivery"] == report.DELIVERY_HELD:
            item["delivery"] = report.DELIVERY_SENT
            item["approved"] = True


with tab_out:
    st.warning("**Simulation mode: no email is actually sent.** This shows what SDOC would send back to "
               "each sender after every check, and which cases it leaves for a real person. "
               "Real sending is deliberately not connected.")
    o1, o2 = st.columns([1, 1])
    hold = o1.toggle("Hold mismatch replies for approval", value=False,
                     help="Off: OK and mismatch replies go out automatically. "
                          "On: mismatch replies wait for a person to approve them.")
    if o2.button("▶ Process the inbox", type="primary"):
        st.session_state.outbox = {"plan": report.plan_replies(load_analysis(), hold_mismatch=hold),
                                   "at": datetime.now().strftime("%H:%M:%S")}
    ob = st.session_state.get("outbox")
    if not ob:
        st.info("Press **Process the inbox** to run every check and see the replies SDOC would send.")
    else:
        plan = ob["plan"]
        n_sent = sum(p["delivery"] == report.DELIVERY_SENT for p in plan)
        n_held = sum(p["delivery"] == report.DELIVERY_HELD for p in plan)
        n_human = sum(p["delivery"] == report.DELIVERY_HUMAN for p in plan)
        m1, m2, m3 = st.columns(3)
        m1.metric("Replied automatically (simulated)", n_sent)
        m2.metric("Awaiting your approval", n_held)
        m3.metric("Left for a real person", n_human)
        st.caption(f"Processed at {ob['at']}. Cases that need a human are never answered automatically.")
        if n_held:
            st.button(f"✅ Approve all {n_held} held replies", on_click=_approve_all)

        view = st.radio("Show", ["All", report.DELIVERY_SENT, report.DELIVERY_HELD, report.DELIVERY_HUMAN],
                        horizontal=True)
        shown = [(i, p) for i, p in enumerate(plan) if view == "All" or p["delivery"] == view]
        icon = {report.DELIVERY_SENT: "📤", report.DELIVERY_HELD: "⏳", report.DELIVERY_HUMAN: "🧑"}
        clickable_table([{"": icon[p["delivery"]], "Email": p["email_id"], "To": p["to"],
                          "Verdict": p["verdict"].replace("_", " "), "Delivery": p["delivery"],
                          "Subject": p["subject"][:70]} for _, p in shown],
                        shown, "ob_table", "ob_pick")
        st.download_button("⬇️ Outbox log (CSV)", report.outbox_csv(plan), "sdoc_outbox.csv")
        if shown:
            idx, item = st.selectbox("Preview a message", shown, key="ob_pick",
                                     format_func=lambda t: f"{t[1]['email_id']}: {t[1]['delivery']}")
            st.markdown(f"**To:** {item['to']}")
            st.markdown(f"**Subject:** {item['subject']}")
            st.text_area("Message", item["body"], height=260, disabled=True, key=f"ob_body_{idx}")
            if item["delivery"] == report.DELIVERY_HELD:
                st.button("✅ Approve (simulated send)", key=f"ob_ok_{idx}", on_click=_approve, args=(idx,))
            elif item["delivery"] == report.DELIVERY_HUMAN:
                st.info("A person must resolve this case. The message above is only a starting point.")
                st.link_button("✉️ Open in my email app",
                               report.mailto_link(item["to"], item["subject"], item["body"]))

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
        clickable_table(
            [{"Email": r["email_id"], "Subject": r["subject"][:70],
              "Reason / fields": (r["review_reason"] or "").replace("_", " ") if view == "Needs review"
              else ", ".join(report.FIELD_NAMES[f] for f in r["defect_fields"]),
              "Next step": report.NEXT_STEP.get(r["review_reason"], "Correct the flagged fields.")}
             for r in items], items, "q_table", "q_pick")
        pick = st.selectbox("Open a case", items, key="q_pick",
                            format_func=lambda r: f"{r['email_id']}: {r['subject'][:70]}")
        email = Inbox(str(DATA_DIR)).get(pick["email_id"])
        show_case(f"q_{pick['email_id']}", pick["email_id"], pick["subject"], email.get("from"),
                  {"status": pick["status"], "review_reason": pick["review_reason"],
                   "defect_fields": pick["defect_fields"]}, pick["rows"], docs=docs_for(email))
    else:
        st.success("Nothing to review.")

# ------------------------------------------------------------ compare uploads
with tab_compare:
    mode = st.radio("Mode", ["One pair", "Batch (many pairs)"], horizontal=True)
    if mode == "One pair":
        st.write("Upload an SI and a draft BL (txt, pdf, docx or xlsx, up to 5 MB each).")
        u1, u2 = st.columns(2)
        si_file = u1.file_uploader("Shipping Instruction (SI)", type=["txt", "pdf", "docx", "xlsx"])
        bl_file = u2.file_uploader("Draft Bill of Lading (BL)", type=["txt", "pdf", "docx", "xlsx"])
        if si_file and bl_file:
            if si_file.size > MAX_UPLOAD_BYTES or bl_file.size > MAX_UPLOAD_BYTES:
                st.error("Files must be 5 MB or smaller.")
            else:
                with st.spinner("Reading and comparing..."):
                    result, si_res, bl_res = cached_compare(
                        si_file.getvalue(), si_file.name, bl_file.getvalue(), bl_file.name, use_ai=use_ai,
                        cross_check=cross_check)
                show_case("upload", f"{si_file.name} vs {bl_file.name}", "Your documents", None,
                          result, report.field_rows(si_res, bl_res))
    else:
        st.write("Drop many documents at once. Files are paired automatically by name: each pair "
                 "needs one file with a standalone **SI** and one with **BL** in its name "
                 "(for example `PO123_SI.pdf` and `PO123_BL.pdf`).")
        files = st.file_uploader("SI and BL files", type=["txt", "pdf", "docx", "xlsx"],
                                 accept_multiple_files=True, key="batch_files")
        if files:
            by_name = {f.name: f for f in files}
            pairs, unpaired = report.pair_documents(list(by_name))
            if unpaired:
                st.warning("Could not pair: " + ", ".join(unpaired))
            results = []
            for key, si_name, bl_name in pairs[:50]:
                si_f, bl_f = by_name[si_name], by_name[bl_name]
                if si_f.size > MAX_UPLOAD_BYTES or bl_f.size > MAX_UPLOAD_BYTES:
                    results.append((key, {"status": "NEEDS_REVIEW", "review_reason": "unreadable",
                                          "defect_fields": []}, []))
                    continue
                res, si_res, bl_res = cached_compare(
                    si_f.getvalue(), si_name, bl_f.getvalue(), bl_name, use_ai=use_ai, cross_check=cross_check)
                results.append((key, res, report.field_rows(si_res, bl_res)))
            if len(pairs) > 50:
                st.info("Showing the first 50 pairs.")
            if results:
                counts = {k: sum(r["status"] == k for _, r, _ in results) for k in STATUS_STYLE}
                m1, m2, m3 = st.columns(3)
                m1.metric("OK", counts["OK"])
                m2.metric("Mismatch", counts["MISMATCH"])
                m3.metric("Needs review", counts["NEEDS_REVIEW"])
                table = [{"Pair": k, "Verdict": STATUS_STYLE[r["status"]][2],
                          "Details": (", ".join(report.FIELD_NAMES[f] for f in r["defect_fields"])
                                      if r["status"] == "MISMATCH"
                                      else report.REASONS.get(r["review_reason"], "") if r["status"] == "NEEDS_REVIEW"
                                      else "All 7 fields match")}
                         for k, r, _ in results]
                clickable_table(table, results, "batch_table", "batch_pick")
                import csv, io
                buf = io.StringIO()
                w = csv.DictWriter(buf, fieldnames=["Pair", "Verdict", "Details"])
                w.writeheader()
                w.writerows(table)
                st.download_button("⬇️ Batch results (CSV)", buf.getvalue(), "sdoc_batch_results.csv")
                pick = st.selectbox("Open a pair", results, key="batch_pick", format_func=lambda t: t[0])
                show_case(f"batch_{pick[0]}", pick[0], pick[0], None, pick[1], pick[2])

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
        clickable_table([{"Email": r["email_id"], "Category": r["category"].replace("_", " ").title(),
                          "Verdict": r["status"].replace("_", " "), "Subject": r["subject"][:80]}
                         for r in shown], shown, "ib_table", "ib_pick")
        pick = st.selectbox("Pick an email", shown, key="ib_pick",
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
                        result, si_res, bl_res = cached_compare(
                            inbox.read_bytes(si_path), si_path, inbox.read_bytes(bl_path), bl_path,
                            use_ai=True, cross_check=cross_check)
                    rows = report.field_rows(si_res, bl_res)
            show_case(f"in_{pick['email_id']}", pick["email_id"], email.get("subject"),
                      email.get("from"), result, rows, docs=docs_for(email))
        else:
            st.info("No document comparison needed for this email.")
