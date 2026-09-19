"""Look and feel for the web app: one place for every colour and every custom CSS rule.

The two palettes are set in .streamlit/config.toml (Streamlit's own widgets) and mirrored here
as CSS variables (our cards, tables and header), so both themes stay consistent.
  light: warm cream paper, deep teal and terracotta accents
  dark : deep navy, glowing teal accents
"""

PALETTE = {
    "light": {
        "bg": "#FAF3E8", "card": "#FFFBF4", "soft": "rgba(120,84,30,.075)", "line": "rgba(120,84,30,.20)",
        "ink": "#2E2417", "ink2": "rgba(46,36,23,.68)", "brand": "#0F766E", "brand2": "#C2571A",
        "shadow": "0 1px 2px rgba(90,60,20,.07), 0 10px 28px rgba(90,60,20,.08)",
        "hero": "linear-gradient(120deg,#0B5D63 0%,#0F766E 48%,#D98E3F 135%)",
        "glow": "rgba(217,142,63,.35)", "side": "#F3E8D4", "tab_on": "#0F766E", "onbrand": "#FFFFFF",
    },
    "dark": {
        "bg": "#0A1120", "card": "#111B30", "soft": "rgba(148,180,255,.07)", "line": "rgba(148,180,255,.16)",
        "ink": "#E7EDF6", "ink2": "rgba(231,237,246,.66)", "brand": "#2DD4BF", "brand2": "#F59E5B",
        "shadow": "0 1px 2px rgba(0,0,0,.4), 0 14px 34px rgba(0,0,0,.42)",
        "hero": "linear-gradient(120deg,#0E2A47 0%,#0B4A5A 52%,#0F766E 135%)",
        "glow": "rgba(45,212,191,.28)", "side": "#0D1628", "tab_on": "#2DD4BF", "onbrand": "#052B29",
    },
}

# status colours: readable text colour + translucent tint, per theme
STATUS = {
    "light": {"OK": ("#177A4B", "rgba(23,122,75,.14)"), "MISMATCH": ("#B3261E", "rgba(179,38,30,.13)"),
              "NEEDS_REVIEW": ("#A2650A", "rgba(217,142,10,.18)")},
    "dark": {"OK": ("#4ADE9B", "rgba(74,222,155,.16)"), "MISMATCH": ("#FF8A80", "rgba(255,138,128,.16)"),
             "NEEDS_REVIEW": ("#FFC24D", "rgba(255,194,77,.16)")},
}


def is_dark():
    """True when the visitor is looking at Streamlit's dark theme."""
    try:
        import streamlit as st
        return st.context.theme.type == "dark"
    except Exception:
        return False


def css(dark):
    p = PALETTE["dark" if dark else "light"]
    v = ";".join(f"--{k}:{val}" for k, val in p.items())
    return "<style>" + _RULES.replace("@@VARS@@", v) + "</style>"


def hero(reader_label, ai_on):
    chips = (f"<span class='sd-chip'><b>5</b> email categories</span>"
             f"<span class='sd-chip'><b>7</b> fields checked</span>"
             f"<span class='sd-chip live'><i class='sd-pulse{' ai' if ai_on else ''}'></i>{reader_label}</span>")
    return ("<div class='sd-top'><div class='sd-top-l'><div class='sd-logo'>🚢</div><div>"
            "<div class='sd-h1'>SDOC</div><div class='sd-h2'>Shipping Document Verification</div></div></div>"
            f"<div class='sd-chips'>{chips}</div>"
            "<div class='sd-top-p'>Reads every email in a shipping-ops inbox, compares each Shipping "
            "Instruction with its draft Bill of Lading across 7 fields, and hands anything uncertain "
            "to a human. <b>AI reads. Plain code decides.</b></div></div>")


_RULES = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{@@VARS@@}
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp button, .stApp input, .stApp textarea, .stApp table {font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;}
.stApp {background:
   radial-gradient(1000px 420px at 92% -8%, var(--glow), transparent 60%),
   radial-gradient(700px 380px at -6% 8%, var(--soft), transparent 60%), var(--bg);}
header[data-testid="stHeader"] {background:transparent;}
footer {visibility:hidden;}
.block-container {padding-top:1.4rem; padding-bottom:3rem; max-width:1240px;}
h1,h2,h3 {letter-spacing:-.02em; font-weight:700;}

/* ---- header banner ---- */
.sd-top {background:var(--hero); color:#fff; border-radius:22px; padding:1.5rem 1.7rem 1.35rem;
         box-shadow:var(--shadow); position:relative; overflow:hidden; margin-bottom:1.1rem;}
.sd-top:after {content:""; position:absolute; right:-70px; top:-90px; width:300px; height:300px; border-radius:50%;
               background:radial-gradient(circle, rgba(255,255,255,.20), transparent 68%);}
.sd-top-l {display:flex; align-items:center; gap:.9rem;}
.sd-logo {width:3.1rem; height:3.1rem; border-radius:16px; display:flex; align-items:center; justify-content:center;
          font-size:1.7rem; background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.30);}
.sd-h1 {font-size:2rem; font-weight:800; letter-spacing:.04em; line-height:1;}
.sd-h2 {font-size:1.02rem; opacity:.88; margin-top:.2rem; font-weight:500;}
.sd-chips {display:flex; flex-wrap:wrap; gap:.5rem; margin:.95rem 0 .75rem;}
.sd-chip {background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.26); border-radius:999px;
          padding:.28rem .8rem; font-size:.85rem; display:inline-flex; align-items:center; gap:.4rem;}
.sd-chip b {font-weight:800;}
.sd-pulse {width:.55rem; height:.55rem; border-radius:50%; background:#FDE68A; display:inline-block;
           box-shadow:0 0 0 0 rgba(253,230,138,.7); animation:sdp 2s infinite;}
.sd-pulse.ai {background:#6EE7B7; box-shadow:0 0 0 0 rgba(110,231,183,.7);}
@keyframes sdp {70% {box-shadow:0 0 0 8px rgba(255,255,255,0);} 100% {box-shadow:0 0 0 0 rgba(255,255,255,0);}}
.sd-top-p {max-width:52rem; font-size:.97rem; line-height:1.5; opacity:.94; position:relative; z-index:1;}

/* ---- tabs ---- */
.stTabs [data-baseweb="tab-list"] {gap:.35rem; border-bottom:1px solid var(--line); padding-bottom:.1rem;}
.stTabs [data-baseweb="tab"] {height:2.9rem; padding:0 1rem; border-radius:12px 12px 0 0; font-weight:600;
                              color:var(--ink2);}
.stTabs [data-baseweb="tab"]:hover {background:var(--soft); color:var(--ink);}
.stTabs [aria-selected="true"] {color:var(--tab_on) !important; background:var(--soft);}
.stTabs [data-baseweb="tab-highlight"] {background:var(--tab_on); height:3px; border-radius:3px;}
.stTabs [data-baseweb="tab-panel"] {padding-top:1.3rem;}

/* ---- cards (bordered containers) ---- */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] .sd-cardhead) {
   background:var(--card); border:1px solid var(--line); border-radius:18px; box-shadow:var(--shadow);
   padding:.35rem .5rem .2rem;}
.sd-cardhead .ttl {font-size:1.08rem; font-weight:700; letter-spacing:-.01em;}
.sd-cardhead .sub {font-size:.85rem; color:var(--ink2); margin:.1rem 0 .5rem;}
[data-testid="stExpander"] {border:1px solid var(--line) !important; border-radius:14px !important;
                            background:var(--card); box-shadow:var(--shadow); overflow:hidden;}
[data-testid="stExpander"] summary {font-weight:600;}
[data-testid="stAlert"] {border-radius:14px; border:1px solid var(--line);}
[data-testid="stDataFrame"] {border-radius:14px; overflow:hidden; border:1px solid var(--line);}

/* ---- buttons ---- */
.stButton > button, .stDownloadButton > button, [data-testid="stBaseButton-secondary"] {
   border-radius:12px; font-weight:600; border:1px solid var(--line); background:var(--card);
   transition:transform .12s ease, border-color .12s ease, box-shadow .12s ease;}
.stButton > button:hover, .stDownloadButton > button:hover {
   border-color:var(--brand); color:var(--brand); transform:translateY(-1px); box-shadow:var(--shadow);}
button[kind="primary"], [data-testid="stBaseButton-primary"] {
   background:linear-gradient(120deg,var(--brand),var(--brand2)) !important; color:var(--onbrand) !important;
   border:none !important; border-radius:12px; font-weight:700;}
[data-testid="stSidebar"] {background:var(--side); border-right:1px solid var(--line);}
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input {border-radius:12px;}

/* ---- tiles, tables ---- */
.sd-tile {border-radius:18px; padding:1.05rem 1.25rem; background:var(--card); border:1px solid var(--line);
          box-shadow:var(--shadow); position:relative; overflow:hidden; height:100%;}
.sd-tile:before {content:""; position:absolute; left:0; top:0; bottom:0; width:5px; background:var(--accent);}
.sd-tile .v {font-size:2.6rem; font-weight:800; line-height:1.05; letter-spacing:-.03em;}
.sd-tile .l {font-size:.9rem; color:var(--ink2); margin-top:.2rem;}
.sd-leg {display:flex; align-items:center; gap:.55rem; padding:.3rem 0;}
.sd-dot {width:.8rem; height:.8rem; border-radius:50%; flex:none;}
.sd-leg .n {margin-left:auto; font-weight:700; font-variant-numeric:tabular-nums;}
.sd-leg .p {color:var(--ink2); width:3.2rem; text-align:right; font-variant-numeric:tabular-nums;}
.sd-hero {font-size:3rem; font-weight:800; line-height:1; letter-spacing:-.03em;}
.sd-mini {border-radius:14px; padding:.85rem 1rem; background:var(--soft); text-align:center;
          border:1px solid var(--line);}
.sd-mini .v {font-size:1.9rem; font-weight:800;}
.sd-mini .l {font-size:.85rem; color:var(--ink2);}
.sdoc-badge {display:inline-block; padding:.4rem 1rem; border-radius:999px; font-weight:800; font-size:1.05rem;
             letter-spacing:.03em; border:1px solid currentColor;}
.sdoc-diff {font-family: ui-monospace, Menlo, Consolas, monospace; font-size:.95rem;}
.sd-tblwrap {overflow-x:auto; margin:.4rem 0 1rem;}
.sd-tbl, .sd-kv {width:100%; border-collapse:separate; border-spacing:0; background:var(--card);
                 border:1px solid var(--line); border-radius:14px; overflow:hidden; box-shadow:var(--shadow);}
.sd-tbl th {text-align:left; padding:.65rem .9rem; font-size:.74rem; text-transform:uppercase;
            letter-spacing:.07em; color:var(--ink2); background:var(--soft);}
.sd-tbl td, .sd-kv td {padding:.65rem .9rem; border-top:1px solid var(--line); vertical-align:top; word-break:break-word;}
.sd-tbl tbody tr:first-child td, .sd-kv tbody tr:first-child td {border-top:none;}
.sd-tbl td.f {font-weight:700; white-space:nowrap;}
.sd-tbl td.v {font-family: ui-monospace, Menlo, Consolas, monospace; font-size:.9rem;}
.sd-tbl tr.bad td {background:rgba(208,59,59,.10);}
.sd-tbl tr.bad td.f {box-shadow: inset 4px 0 0 #d03b3b;}
.sd-tbl tr.warn td {background:rgba(250,178,25,.12);}
.sd-tbl tr.warn td.f {box-shadow: inset 4px 0 0 #fab219;}
.sd-pill {display:inline-block; padding:.15rem .65rem; border-radius:999px; font-weight:700;
          font-size:.82rem; white-space:nowrap;}
.sd-pill.ok {background:rgba(30,142,90,.20);}
.sd-pill.bad {background:rgba(208,59,59,.22);}
.sd-pill.warn {background:rgba(250,178,25,.28);}
.sd-kv td.k {width:9.5rem; font-weight:700; color:var(--ink2); background:var(--soft); white-space:nowrap;}
@media (max-width:640px) {.sd-h1 {font-size:1.6rem;} .block-container {padding-left:1rem; padding-right:1rem;}}
"""


def theme_switch_html(dark):
    """A small Light/Dark button. Streamlit has no official call to change theme, but it remembers
    the visitor's choice in the browser under 'stActiveTheme-<path>-v2', so the button writes that
    and reloads the page. If the browser blocks it the button simply does nothing."""
    target, label = ("Light", "☀️  Switch to light") if dark else ("Dark", "🌙  Switch to dark")
    ink, line = ("#E7EDF6", "rgba(148,180,255,.35)") if dark else ("#2E2417", "rgba(120,84,30,.35)")
    return ("<style>html,body{margin:0;background:transparent;overflow:hidden}"
            "button{font:600 14px Inter,system-ui,sans-serif;color:%s;background:transparent;cursor:pointer;"
            "border:1px solid %s;border-radius:999px;padding:7px 16px;float:left}"
            "button:hover{border-color:#0F766E;color:#0F766E}</style>"
            "<button id='b'>%s</button><script>"
            "document.getElementById('b').onclick=function(){try{var p=window.parent;"
            "p.localStorage.setItem('stActiveTheme-'+p.location.pathname+'-v2',JSON.stringify('%s'));"
            "p.location.reload();}catch(e){}};</script>" % (ink, line, label, target))
