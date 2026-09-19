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

CSS = """
<style>
.sd-tile {border-radius:14px; padding:1rem 1.2rem; background:rgba(128,128,128,.10);
          border-top:4px solid var(--accent); height:100%;}
.sd-tile .v {font-size:2.5rem; font-weight:800; line-height:1.1;}
.sd-tile .l {font-size:.9rem; opacity:.75; margin-top:.15rem;}
.sd-card {border-radius:14px; padding:1rem 1.2rem .4rem; background:rgba(128,128,128,.07);
          margin-bottom:.9rem;}
.sd-card .ttl {margin:0 0 .1rem; font-size:1.1rem; font-weight:700;}
.sd-card .sub {font-size:.85rem; opacity:.7; margin-bottom:.4rem;}
.sd-leg {display:flex; align-items:center; gap:.55rem; padding:.28rem 0;}
.sd-dot {width:.8rem; height:.8rem; border-radius:50%; flex:none;}
.sd-leg .n {margin-left:auto; font-weight:700; font-variant-numeric:tabular-nums;}
.sd-leg .p {opacity:.6; width:3.2rem; text-align:right; font-variant-numeric:tabular-nums;}
.sd-hero {font-size:3rem; font-weight:800; line-height:1;}
.sd-mini {border-radius:12px; padding:.8rem 1rem; background:rgba(128,128,128,.10); text-align:center;}
.sd-mini .v {font-size:1.9rem; font-weight:800;}
.sd-mini .l {font-size:.85rem; opacity:.8;}
</style>
"""


def _is_dark():
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


def _tile(value, label, accent):
    return (f"<div class='sd-tile' style='--accent:{accent}'>"
            f"<div class='v'>{value}</div><div class='l'>{label}</div></div>")


def _card_open(title, subtitle):
    st.markdown(f"<div class='sd-card'><div class='ttl'>{title}</div><div class='sub'>{subtitle}</div></div>",
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
    st.markdown(CSS, unsafe_allow_html=True)
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
    k[3].markdown(_tile(status.get("NEEDS_REVIEW", 0), "Sent to a human, not guessed",
                        STATUS_STYLE["NEEDS_REVIEW"][2]), unsafe_allow_html=True)
    st.write("")

    # ---- row 1: outcome donut + pipeline funnel ---------------------------
    a, b = st.columns([1.05, 1])
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
    c, d = st.columns([1.05, 1])
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
    _card_open("Why documents went to a human",
               "The system never guesses: anything it cannot read or verify is escalated with a reason")
    reasons = s["review_reasons"]
    cols = st.columns(4)
    for col, (key, (icon, label)) in zip(cols, REASON_LABEL.items()):
        col.markdown(f"<div class='sd-mini'><div class='v'>{icon} {reasons.get(key, 0)}</div>"
                     f"<div class='l'>{label}</div></div>", unsafe_allow_html=True)
    st.write("")

    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("⬇️ Results (CSV)", report.to_csv(rows_all), "sdoc_results.csv")
    d2.download_button("⬇️ submission.json", report.to_submission_json(rows_all), "submission.json")
