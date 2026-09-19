"""Dashboard for the SDOC web app: KPI tiles, donuts, a pipeline funnel and an
emphasis bar chart. Colours come from a validated palette (light and dark
sets checked for colour-blind separation); identity is never colour alone,
so every chart carries labels and counts.
"""
import altair as alt
import pandas as pd
import streamlit as st

import report

# Categorical slots, in fixed order. Second value is the dark-mode step.
CATEGORY_STYLE = {
    "BL_COMPARISON": ("Document comparison", "#2a78d6", "#3987e5"),
    "SI_REQUEST": ("SI request", "#eb6834", "#d95926"),
    "INVOICE_QUERY": ("Invoice query", "#1baf7a", "#199e70"),
    "GENERAL": ("General", "#eda100", "#c98500"),
    "SPAM": ("Spam", "#e87ba4", "#d55181"),
}
# Fixed status palette: good / critical / warning. Always shown with icon + label.
STATUS_STYLE = {
    "OK": ("✔", "Matched", "#0ca30c"),
    "MISMATCH": ("✖", "Mismatch", "#d03b3b"),
    "NEEDS_REVIEW": ("⚠", "Needs review", "#fab219"),
}
FUNNEL_BLUES = ["#86b6ef", "#3987e5", "#256abf", "#184f95"]   # ordinal ramp, steps 250-600
EMPHASIS = "#2a78d6"
EMPHASIS_DARK = "#3987e5"
MUTED = "#9aa0a6"

REASON_LABEL = {
    "wrong_doc_type": ("📄", "Wrong document type"),
    "missing_attachment": ("📎", "Missing attachment"),
    "unreadable": ("🔍", "Unreadable or scanned"),
    "missing_value": ("✏️", "Blank field"),
}



def _is_dark():
    """The chart colours below are the mid-brightness set that reads well on both the cream and the
    navy theme, so charts never depend on guessing the visitor's theme."""
    return True


def _tile(value, label, accent):
    return (f"<div class='sd-tile' style='--accent:{accent}'>"
            f"<div class='v'>{value}</div><div class='l'>{label}</div></div>")


def _card_open(title, subtitle):
    st.markdown(f"<div class='sd-cardhead'><div class='ttl'>{title}</div><div class='sub'>{subtitle}</div></div>",
                unsafe_allow_html=True)


def _legend(items, total):
    """items: (label, value, color, icon or None). Direct labels with counts."""
    out = []
    for label, value, color, icon in items:
        pct = f"{100 * value / total:.0f}%" if total else "–"
        prefix = f"{icon} " if icon else ""
        out.append(f"<div class='sd-leg'><span class='sd-dot' style='background:{color}'></span>"
                   f"<span>{prefix}{label}</span><span class='n'>{value}</span>"
                   f"<span class='p'>{pct}</span></div>")
    return "".join(out)


def _donut(items, height=230):
    df = pd.DataFrame([{"label": l, "value": v, "color": c} for l, v, c, _ in items if v > 0])
    chart = (alt.Chart(df)
             .mark_arc(innerRadius=62, outerRadius=100, padAngle=0.03, cornerRadius=4)
             .encode(theta=alt.Theta("value:Q", stack=True),
                     color=alt.Color("label:N", legend=None,
                                     scale=alt.Scale(domain=list(df["label"]), range=list(df["color"]))),
                     tooltip=[alt.Tooltip("label:N", title=""), alt.Tooltip("value:Q", title="Emails")])
             .properties(height=height)
             .configure_view(strokeWidth=0))
    return chart


def _hbars(df, height, colors=None):
    """Horizontal bars with the value written into the axis label (theme-safe)."""
    df = df.copy()
    df["axis"] = df["label"] + "   " + df["value"].astype(str)
    order = list(df.sort_values("value", ascending=False)["axis"])
    color = alt.Color("color:N", scale=None, legend=None)
    return (alt.Chart(df)
            .mark_bar(cornerRadiusEnd=5, size=20)
            .encode(y=alt.Y("axis:N", sort=order, title=None, axis=alt.Axis(labelLimit=260, ticks=False, domain=False)),
                    x=alt.X("value:Q", title=None, axis=None),
                    color=color,
                    tooltip=[alt.Tooltip("label:N", title=""), alt.Tooltip("value:Q", title="Count")])
            .properties(height=height)
            .configure_view(strokeWidth=0))


def render(rows_all):
    dark = _is_dark()
    s = report.summarize(rows_all)
    status = s["status"]
    comp = [r for r in rows_all if r["category"] == "BL_COMPARISON"]
    ok = sum(r["status"] == "OK" for r in comp)
    mis = sum(r["status"] == "MISMATCH" for r in comp)
    rev = sum(r["status"] == "NEEDS_REVIEW" for r in comp)
    decided = ok + mis
    accent = EMPHASIS_DARK if dark else EMPHASIS

    # ---- KPI tiles ---------------------------------------------------------
    k = st.columns(4)
    k[0].markdown(_tile(s["total"], "Emails processed", accent), unsafe_allow_html=True)
    k[1].markdown(_tile(s["compared"], "SI vs BL comparisons", "#eb6834" if not dark else "#d95926"),
                  unsafe_allow_html=True)
    k[2].markdown(_tile(status.get("MISMATCH", 0), "Mismatches caught", STATUS_STYLE["MISMATCH"][2]),
                  unsafe_allow_html=True)
    k[3].markdown(_tile(status.get("NEEDS_REVIEW", 0), "Escalated to a human",
                        STATUS_STYLE["NEEDS_REVIEW"][2]), unsafe_allow_html=True)
    st.write("")

    # ---- row 1: outcome donut + pipeline funnel ---------------------------
    a, b = st.columns([1.05, 1], border=True)
    with a:
        _card_open("How the comparisons ended", "Every SI vs draft BL check, by verdict")
        items = [(STATUS_STYLE[k_][1], v, STATUS_STYLE[k_][2], STATUS_STYLE[k_][0])
                 for k_, v in (("OK", ok), ("MISMATCH", mis), ("NEEDS_REVIEW", rev))]
        c1, c2 = st.columns([1, 1.1])
        with c1:
            st.altair_chart(_donut(items), width="stretch")
        with c2:
            st.markdown(f"<div class='sd-hero'>{len(comp)}</div><div style='opacity:.7;margin-bottom:.6rem'>"
                        "comparisons</div>" + _legend(items, len(comp)), unsafe_allow_html=True)
    with b:
        _card_open("From inbox to verdict", "How many emails reach each stage")
        stages = [("Emails received", s["total"]), ("Need a comparison", len(comp)),
                  ("Decided automatically", decided), ("Defects caught", mis)]
        df = pd.DataFrame([{"label": n, "value": v, "color": FUNNEL_BLUES[i]}
                           for i, (n, v) in enumerate(stages)])
        df["axis"] = df["label"] + "   " + df["value"].astype(str)
        chart = (alt.Chart(df).mark_bar(cornerRadiusEnd=6, size=34)
                 .encode(y=alt.Y("axis:N", sort=list(df["axis"]), title=None,
                                 axis=alt.Axis(labelLimit=260, ticks=False, domain=False)),
                         x=alt.X("value:Q", axis=None),
                         color=alt.Color("color:N", scale=None, legend=None),
                         tooltip=[alt.Tooltip("label:N", title=""), alt.Tooltip("value:Q", title="Emails")])
                 .properties(height=232)
                 .configure_view(strokeWidth=0))
        st.altair_chart(chart, width="stretch")

    # ---- row 2: inbox mix donut + defect fields ---------------------------
    c, d = st.columns([1.05, 1], border=True)
    with c:
        _card_open("What is in the inbox", "Every email, sorted into 5 categories")
        cats = s["categories"]
        items = [(CATEGORY_STYLE[k_][0], cats.get(k_, 0), CATEGORY_STYLE[k_][2 if dark else 1], None)
                 for k_ in CATEGORY_STYLE]
        c1, c2 = st.columns([1, 1.1])
        with c1:
            st.altair_chart(_donut(items), width="stretch")
        with c2:
            st.markdown("<div style='height:.5rem'></div>" + _legend(items, s["total"]),
                        unsafe_allow_html=True)
    with d:
        _card_open("Where the defects are", "Which field differs between SI and BL, most common highlighted")
        fields = s["defect_fields"]
        if fields:
            top = max(fields, key=fields.get)
            hi = EMPHASIS_DARK if dark else EMPHASIS
            df = pd.DataFrame([{"label": report.FIELD_NAMES[f], "value": v,
                                "color": hi if f == top else MUTED} for f, v in fields.items()])
            st.altair_chart(_hbars(df, height=232), width="stretch")
        else:
            st.info("No defects found.")

    # ---- row 3: why humans were needed ------------------------------------
    with st.container(border=True):
        _card_open("Why documents went to a human",
                   "The system never guesses: anything it cannot read or verify is escalated with a reason")
        reasons = s["review_reasons"]
        cols = st.columns(4)
        for col, (key, (icon, label)) in zip(cols, REASON_LABEL.items()):
            col.markdown(f"<div class='sd-mini'><div class='v'>{icon} {reasons.get(key, 0)}</div>"
                         f"<div class='l'>{label}</div></div>", unsafe_allow_html=True)
        st.write("")

    # ---- what this saves ---------------------------------------------------
    with st.container(border=True):
        _card_open("What this saves", "An estimate: move the sliders to match how long your team really takes")
        v1, v2 = st.columns([1.2, 1])
        with v1:
            m_check = st.slider("Minutes to check one SI against its BL by hand", 1, 20, 5, key="vs_check")
            m_reply = st.slider("Minutes to write the reply to the sender", 0, 10, 2, key="vs_reply")
        saved = report.time_saved(rows_all, m_check, m_reply)
        with v2:
            st.markdown(f"<div class='sd-hero'>{saved['hours']:.1f} hours</div>"
                        f"<div style='opacity:.8;margin:.3rem 0 .5rem'>of manual work handled automatically</div>"
                        f"<div style='opacity:.75;font-size:.9rem'>{saved['checks']} SI vs BL checks decided and "
                        f"answered on their own. The other {saved['escalated']} cases still go to a person, and "
                        f"are not counted as saved.</div>", unsafe_allow_html=True)
        st.caption("Estimate based on the assumptions above, not a measurement.")
        st.write("")

    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("⬇️ Results (CSV)", report.to_csv(rows_all), "sdoc_results.csv",
                    help="A spreadsheet of every email: category, verdict, reason and differing fields. Opens in Excel.")
    d2.download_button("⬇️ submission.json", report.to_submission_json(rows_all), "submission.json",
                    help="The same results in the exact format the hackathon scorer reads.")
