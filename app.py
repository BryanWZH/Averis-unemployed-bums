"""DocHarbor web app: inbox dashboard, review queue, document comparison with a
visual diff, and draft replies.

    streamlit run app.py
"""
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# On Streamlit Community Cloud the key lives in "Secrets", not the environment.
try:
    if "ANTHROPIC_API_KEY" in st.secrets and not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

import importlib
import sys


def _refresh_local_modules():
    """After a redeploy, Streamlit Cloud can keep OLD copies of our helper modules in memory
    while running the NEW app.py (which then crashes with "no attribute ..."). Remember a
    signature of the source files; when it changes, or when modules are already loaded but we
    have never recorded one (a stale process), reload them all in dependency order."""
    here = Path(__file__).parent
    sig = tuple((f.name, f.stat().st_mtime_ns) for f in sorted(here.glob("*.py")))
    if getattr(sys, "_sdoc_sig", None) != sig:
        for name in ("loader", "normalize", "extract", "classify", "ai_extract", "ai_reply",
                     "pipeline", "report", "samples", "style", "dashboard"):
            if name in sys.modules:
                importlib.reload(sys.modules[name])
        sys._sdoc_sig = sig


_refresh_local_modules()

import ai_extract
import ai_reply
import classify
import dashboard
import extract
import pipeline
import report
import samples
import style
from loader import Inbox
from normalize import COMPARE_FIELDS

DATA_DIR = Path(__file__).parent
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
STATUS_LABEL = {"OK": "OK", "MISMATCH": "MISMATCH", "NEEDS_REVIEW": "NEEDS REVIEW"}

st.set_page_config(page_title="DocHarbor Verification", page_icon="🚢", layout="wide")
st.markdown(style.css(), unsafe_allow_html=True)


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
cross_check = False
with st.sidebar:
    components.html(style.theme_switch_html(), height=42)
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

st.markdown(style.hero("AI reader on" if use_ai else "Rule-based reader", use_ai), unsafe_allow_html=True)


@st.cache_data(show_spinner="Analysing the whole inbox...")
def load_analysis():
    return report.analyze_inbox(DATA_DIR, use_ai=False)


def badge(status):
    cls = {"OK": "ok", "MISMATCH": "bad", "NEEDS_REVIEW": "warn"}.get(status, "")
    st.markdown(f"<span class='sdoc-badge {cls}'>{STATUS_LABEL.get(status, status)}</span>",
                unsafe_allow_html=True)


@st.cache_data(show_spinner=False, max_entries=64)
def cached_compare(si_bytes, si_name, bl_bytes, bl_name, use_ai=False, cross_check=False):
    """compare_documents, cached. Streamlit re-runs every tab on every click, so
    without this an AI read would be repeated (and billed) on each interaction."""
    return pipeline.compare_documents(si_bytes, si_name, bl_bytes, bl_name,
                                      use_ai=use_ai, cross_check=cross_check)


def clickable_table(data, items, table_key, sel_key, id_fn):
    """A table where clicking any cell selects that row. The chosen item is stored
    by its own id under `sel_key` (see item_picker). `items` must line up
    row-for-row with `data`. A click only counts when it is a NEW click, so the
    dropdown below can still be used on its own afterwards."""
    # Streamlit keeps a table's selection tied to its key even after the rows change, and the
    # stale selection swallows the next click. Callers therefore put whatever decides the table's
    # contents (the active filter, the counts) into `table_key`, so each view starts clean.
    ev = st.dataframe(data, hide_index=True, width="stretch", on_select="rerun",
                      selection_mode="single-cell", key=table_key)
    cells = [tuple(c) for c in ev.selection.cells]
    last_key = table_key + "_last"
    clicked = report.selection_change(cells, st.session_state.get(last_key))
    st.session_state[last_key] = cells
    if clicked is not None and clicked[0] < len(items):
        st.session_state[sel_key] = id_fn(items[clicked[0]])
    st.caption("Click any row to open it below.")


def item_picker(label, items, sel_key, id_fn, format_func):
    """The dropdown that shows the selected item. Streamlit resets a dropdown whenever
    its option list changes (for example when a filter is switched), so the choice is
    kept by id in session state and the widget is rebuilt from it every time."""
    ids = [id_fn(x) for x in items]
    cur = st.session_state.get(sel_key)
    index = ids.index(cur) if cur in ids else 0
    choice = st.selectbox(label, items, index=index, key=f"{sel_key}__{cur}", format_func=format_func)
    if id_fn(choice) != cur:
        st.session_state[sel_key] = id_fn(choice)      # the user used the dropdown itself
    return choice


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


def text_box(label, template, state_key, height, disabled=False):
    """A text area seeded from `template` and driven purely through session state.
    Passing value= AND writing to the same key (which the polish button does) makes
    Streamlit warn and can misbehave, so the seed is written once, and again only when
    the template itself changes (for example a new case, or an edited Playground field)."""
    seed_key = state_key + "__template"
    if st.session_state.get(seed_key) != template:
        st.session_state[seed_key] = template
        st.session_state[state_key] = template
    return st.text_area(label, key=state_key, height=height, disabled=disabled)


def _apply_polish(state_key, flag_key, fallback, facts):
    """Reword the message currently in the text box (so a person's edits are kept). The AI
    result is only used if it kept every value and added no numbers (see ai_reply)."""
    source = st.session_state.get(state_key, fallback)
    text, used = ai_reply.polish(source, facts)
    st.session_state[state_key] = text
    st.session_state[flag_key] = used


def polish_button(btn_key, state_key, flag_key, fallback, facts):
    """'Polish wording with AI', shown under every draft reply once AI is unlocked."""
    if not use_ai:
        return
    st.button("✨ Polish wording with AI", key=btn_key, on_click=_apply_polish,
              args=(state_key, flag_key, fallback, facts),
              help="Rewords the message. If the AI changes any value or adds a number, "
                   "the original wording is kept.")
    used = st.session_state.get(flag_key)
    if used is True:
        st.caption("✨ Reworded by AI. Every value was checked and is unchanged.")
    elif used is False:
        st.caption("The AI rewrite was rejected (it changed a fact or failed), so the wording is unchanged.")


def show_case(key, title, subject, sender, result, rows, docs=None):
    """Verdict, side-by-side field table with a character-level diff,
    then the draft reply and report downloads."""
    badge(result["status"])
    if result["status"] == "MISMATCH":
        names = ", ".join(report.FIELD_NAMES[f] for f in result["defect_fields"])
        st.markdown(f"**Differs in:** {names}")
    elif result["status"] == "NEEDS_REVIEW":
        reason = result.get("review_reason")
        pairs = [("Why", report.REASONS.get(reason, reason)),
                 ("Next step", report.NEXT_STEP.get(reason, "Check manually."))]
        dis = result.get("disagreements")
        if dis:
            names = sorted(set(dis["si"]) | set(dis["bl"]))
            pairs.append(("Readers disagree on", ", ".join(report.FIELD_NAMES[f] for f in names)))
        st.markdown(report.kv_html(pairs), unsafe_allow_html=True)
        if use_ai and docs:
            if st.button("🤖 Ask AI for a second opinion", key=f"{key}_op_btn"):
                with st.spinner("The AI is reading the documents..."):
                    st.session_state[f"{key}_op"] = pipeline.second_opinion(*docs)
            op = st.session_state.get(f"{key}_op")
            if op:
                if op["available"] and op["suggested_defects"]:
                    st.info("🤖 **AI second opinion (advisory only, the verdict above is unchanged).** "
                            "The AI thinks these fields differ; please confirm against the originals.")
                    st.markdown(report.field_table_html(
                        [{"label": report.FIELD_NAMES[f], "si": op["si_res"].fields.get(f) or "",
                          "bl": op["bl_res"].fields.get(f) or "", "verdict": "mismatch"}
                         for f in op["suggested_defects"]]), unsafe_allow_html=True)
                elif op["available"]:
                    st.info("🤖 **AI second opinion (advisory only).** The AI found no differences in the "
                            "fields it could read. A person should still confirm.")
                else:
                    st.info("🤖 **AI second opinion (advisory only).** " + op["note"])
    else:
        st.markdown("All 7 fields match.")

    if rows:
        st.markdown("**Field by field**")
        st.markdown(report.field_table_html(rows), unsafe_allow_html=True)

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
            body_val = text_box("Message", body, f"{key}_body", 280)
            facts = [v for r_ in rows if r_["verdict"] == "mismatch" for v in (r_["si"], r_["bl"])]
            polish_button(f"{key}_polish", f"{key}_body", f"{key}_polished", body, facts)
            to_addr = sender if sender and "@" in sender else ""
            st.link_button("✉️ Open in my email app", report.mailto_link(to_addr, subj_val, body_val))
            st.caption("Opens your own mail program with the recipient, subject and message filled in, "
                       "including any edits above. DocHarbor does not send email itself.")
    st.download_button("⬇️ Download report (Markdown)", report.report_markdown(title, result, rows),
                       file_name=f"{key}_report.md", key=f"{key}_dl")


with st.expander("👋 New here? Four quick ways to explore", expanded=True):
    g = st.columns(4)
    g[0].markdown("**1 · The big picture**")
    g[0].caption("Open **📊 Dashboard**: every email in the inbox, checked and sorted, with the time it saves.")
    g[1].markdown("**2 · What happens next**")
    g[1].caption("Open **📤 Outbox**, press *Process the inbox*, then click any row to read the reply "
                 "DocHarbor drafts. Cases needing a person are left for one.")
    g[2].markdown("**3 · Try a document**")
    g[2].caption("Open **🔍 Compare documents** and click a ready-made sample: a match, a mismatch, "
                 "a blank field, a scan. Or upload your own.")
    g[3].markdown("**4 · Break it yourself**")
    g[3].caption("Open **🧪 Playground**, change a weight or a letter in a name, and watch DocHarbor catch it.")

tab_dash, tab_out, tab_queue, tab_compare, tab_play, tab_inbox = st.tabs(
    ["📊 Dashboard", "📤 Outbox", "🚩 Review queue", "🔍 Compare documents", "🧪 Playground", "📬 Inbox browser"])

# ------------------------------------------------------------------ dashboard
with tab_dash:
    dashboard.render(load_analysis())

# --------------------------------------------------------------------- outbox
def _approve(idx):
    item = st.session_state.outbox["plan"][idx]
    edited = st.session_state.get(f"ob_body_{idx}", item["body"])
    item["edited"] = edited != item["body"]
    item["body"] = edited
    item["delivery"] = report.DELIVERY_SENT
    item["approved"] = True


def _approve_all():
    for item in st.session_state.outbox["plan"]:
        if item["delivery"] == report.DELIVERY_HELD:
            item["delivery"] = report.DELIVERY_SENT
            item["approved"] = True


with tab_out:
    st.warning("**Simulation mode: no email is actually sent.** This shows what DocHarbor would send back to "
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
        st.info("Press **Process the inbox** to run every check and see the replies DocHarbor would send.")
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
                        shown, f"ob_table_{view}_{n_sent}_{n_held}", "ob_pick", lambda t: t[0])
        st.download_button("⬇️ Outbox log (CSV)", report.outbox_csv(plan), "docharbor_outbox.csv")
        if shown:
            idx, item = item_picker("Preview a message", shown, "ob_pick", lambda t: t[0],
                                    lambda t: f"{t[1]['email_id']}: {t[1]['delivery']}")
            st.markdown(report.kv_html([("To", item["to"]), ("Subject", item["subject"]),
                                        ("Verdict", "OK" if item["verdict"] == "OK"
                                         else item["verdict"].replace("_", " ").capitalize()),
                                        ("Delivery", item["delivery"])]), unsafe_allow_html=True)
            can_edit = item["delivery"] in (report.DELIVERY_HELD, report.DELIVERY_HUMAN)
            body_now = text_box("Message (you can edit it before approving)" if can_edit else "Message",
                                item["body"], f"ob_body_{idx}", 260, disabled=not can_edit)
            if can_edit:
                polish_button(f"ob_polish_{idx}", f"ob_body_{idx}", f"ob_polished_{idx}",
                              item["body"], item.get("facts", []))
            if item.get("edited"):
                st.caption("✏️ Approved with your edits.")
            if item["delivery"] == report.DELIVERY_HELD:
                st.button("✅ Approve (simulated send)", key=f"ob_ok_{idx}", on_click=_approve, args=(idx,))
            elif item["delivery"] == report.DELIVERY_HUMAN:
                st.info("A person must resolve this case. The message above is only a starting point.")
                st.link_button("✉️ Open in my email app",
                               report.mailto_link(item["to"], item["subject"], body_now))

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
             for r in items], items, f"q_table_{view}_{reason_filter}", "q_pick", lambda r: r["email_id"])
        pick = item_picker("Open a case", items, "q_pick", lambda r: r["email_id"],
                           lambda r: f"{r['email_id']}: {r['subject'][:70]}")
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
        st.markdown("**Try a ready-made sample** (one click, no files needed):")
        sc = st.columns(3)
        for i, sm in enumerate(samples.SAMPLES):
            if sc[i % 3].button(f"{sm['icon']} {sm['title']}", key=f"sm_{sm['id']}", help=sm["blurb"],
                                width="stretch"):
                st.session_state["sample_id"] = sm["id"]
        st.write("Or upload an SI and a draft BL (txt, pdf, docx or xlsx, up to 5 MB each).")
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
        elif st.session_state.get("sample_id"):
            sm = samples.BY_ID[st.session_state["sample_id"]]
            si_b, si_n, bl_b, bl_n = samples.load(sm, DATA_DIR)
            st.info(f"**Sample: {sm['title']}.** {sm['blurb']}")
            d1, d2, d3 = st.columns([1, 1, 1])
            d1.download_button("⬇️ Sample SI", si_b, si_n, key="sm_dl_si")
            d2.download_button("⬇️ Sample BL", bl_b, bl_n, key="sm_dl_bl")
            d3.button("✖ Clear sample", key="sm_clear", on_click=lambda: st.session_state.pop("sample_id", None))
            result, si_res, bl_res = cached_compare(si_b, si_n, bl_b, bl_n, use_ai=use_ai,
                                                    cross_check=cross_check)
            show_case(f"sample_{sm['id']}", sm["title"], sm["title"], None, result,
                      report.field_rows(si_res, bl_res), docs=(si_b, si_n, bl_b, bl_n))
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
                counts = {k: sum(r["status"] == k for _, r, _ in results) for k in STATUS_LABEL}
                m1, m2, m3 = st.columns(3)
                m1.metric("OK", counts["OK"])
                m2.metric("Mismatch", counts["MISMATCH"])
                m3.metric("Needs review", counts["NEEDS_REVIEW"])
                table = [{"Pair": k, "Verdict": STATUS_LABEL[r["status"]],
                          "Details": (", ".join(report.FIELD_NAMES[f] for f in r["defect_fields"])
                                      if r["status"] == "MISMATCH"
                                      else report.REASONS.get(r["review_reason"], "") if r["status"] == "NEEDS_REVIEW"
                                      else "All 7 fields match")}
                         for k, r, _ in results]
                clickable_table(table, results, f"batch_table_{len(results)}", "batch_pick", lambda t: t[0])
                import csv, io
                buf = io.StringIO()
                w = csv.DictWriter(buf, fieldnames=["Pair", "Verdict", "Details"])
                w.writeheader()
                w.writerows(table)
                st.download_button("⬇️ Batch results (CSV)", buf.getvalue(), "docharbor_batch_results.csv")
                pick = item_picker("Open a pair", results, "batch_pick", lambda t: t[0], lambda t: t[0])
                show_case(f"batch_{pick[0]}", pick[0], pick[0], None, pick[1], pick[2])

# ------------------------------------------------------------------ playground
PG_SAMPLES = [x for x in samples.SAMPLES if x["playground"]]


def _pg_load():
    sm = st.session_state.get("pg_sample") or PG_SAMPLES[0]
    si_b, si_n, bl_b, bl_n = samples.load(sm, DATA_DIR)
    si_res, bl_res = extract.extract(si_b, si_n), extract.extract(bl_b, bl_n)
    for f in COMPARE_FIELDS:
        st.session_state[f"pg_si_{f}"] = si_res.fields.get(f, "")
        st.session_state[f"pg_bl_{f}"] = bl_res.fields.get(f, "")


def _pg_set(field, value):
    st.session_state[f"pg_bl_{field}"] = value


def _pg_break(kind):
    si = lambda f: st.session_state.get(f"pg_si_{f}", "")
    if kind == "weight":
        _pg_set("gross_weight_kg", report.tweak_weight(si("gross_weight_kg")))
    elif kind == "typo":
        _pg_set("consignee", report.tweak_typo(si("consignee")))
    elif kind == "port":
        _pg_set("port_of_discharge", "ROTTERDAM, NETHERLANDS (NLRTM)")
    elif kind == "blank":
        _pg_set("notify_party", "")
    elif kind == "format":
        digits = "".join(ch for ch in si("gross_weight_kg") if ch.isdigit())
        if digits:
            _pg_set("gross_weight_kg", f"{int(digits)}.00 KGS")


with tab_play:
    st.markdown("Pick a starting pair, then **change any value** on either document. "
                "The real decision engine re-checks instantly, so you can see exactly what it catches "
                "and what it lets through.")
    st.selectbox("Start from", PG_SAMPLES, key="pg_sample", on_change=_pg_load,
                 format_func=lambda x: f"{x['icon']} {x['title']}")
    if "pg_bl_shipper" not in st.session_state:
        _pg_load()
    st.markdown("**Quick edits to the BL:**")
    q = st.columns(6)
    q[0].button("⚖️ Weight", key="pgb_w", on_click=_pg_break, args=("weight",), width="stretch",
                help="Adds 1,000 kg to the BL gross weight")
    q[1].button("🔤 Name typo", key="pgb_t", on_click=_pg_break, args=("typo",), width="stretch",
                help="Changes one letter in the BL consignee name")
    q[2].button("🚢 Swap port", key="pgb_p", on_click=_pg_break, args=("port",), width="stretch",
                help="Sets the BL port of discharge to Rotterdam")
    q[3].button("⬜ Blank field", key="pgb_b", on_click=_pg_break, args=("blank",), width="stretch",
                help="Empties the BL notify party")
    q[4].button("🔧 Reformat", key="pgb_f", on_click=_pg_break, args=("format",), width="stretch",
                help="Writes the same weight a different way. It should still match.")
    q[5].button("↩️ Reset", key="pgb_r", on_click=_pg_load, width="stretch")
    left, right = st.columns(2)
    left.markdown("##### Shipping Instruction")
    right.markdown("##### Draft Bill of Lading")
    for f in COMPARE_FIELDS:
        left.text_input(report.FIELD_NAMES[f], key=f"pg_si_{f}")
        right.text_input(report.FIELD_NAMES[f], key=f"pg_bl_{f}")
    st.markdown("---")
    pg_res, pg_rows = report.edited_result(
        {f: st.session_state.get(f"pg_si_{f}", "") for f in COMPARE_FIELDS},
        {f: st.session_state.get(f"pg_bl_{f}", "") for f in COMPARE_FIELDS})
    show_case("pg", "Playground", "Playground", None, pg_res, pg_rows)

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
                         for r in shown], shown, f"ib_table_{cat_sel}_{text_sel}", "ib_pick", lambda r: r["email_id"])
        pick = item_picker("Pick an email", shown, "ib_pick", lambda r: r["email_id"],
                           lambda r: f"{r['email_id']}: {r['subject'][:80]}")
        email = Inbox(str(DATA_DIR)).get(pick["email_id"])
        pairs = [("From", email.get("from", "")), ("Category", pick["category"].replace("_", " ").title())]
        if pick["category"] == "BL_COMPARISON":       # other emails have no verdict to show
            pairs.append(("Verdict", STATUS_LABEL[pick["status"]].title() if pick["status"] != "OK" else "OK"))
        st.markdown(report.kv_html(pairs), unsafe_allow_html=True)
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
