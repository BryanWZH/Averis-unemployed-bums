"""Checks where the AI-only buttons appear in the app, using a stand-in AI (nothing is spent).

    python tests/ui_ai_check.py

Covers: "Ask AI for a second opinion" on needs-review samples, and "Polish wording with AI"
under every draft reply (case views, Playground, and editable Outbox messages).
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["ANTHROPIC_API_KEY"] = "sk-fake"
os.environ["AI_ACCESS_CODE"] = "letmein"
os.environ.pop("SDOC_NO_AI", None)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from streamlit.testing.v1 import AppTest  # noqa: E402

results = []


def check(name, ok):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name)


at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=240).run()
at.sidebar.text_input[0].set_value("letmein").run()

import ai_extract  # noqa: E402  (the same module objects the app uses)
import ai_reply  # noqa: E402
import extract  # noqa: E402


def fake_reader(data, name):
    r = extract.ExtractResult()
    base = {"shipper": "APRIL FAR EAST (M) SDN BHD", "consignee": "AL GURQ STATIONERY LLC",
            "notify_party": "AL GURQ STATIONERY LLC", "port_of_loading": "NHAVA SHEVA, INDIA",
            "port_of_discharge": "TUTICORIN, INDIA", "container_count": "6", "gross_weight_kg": "128544"}
    if name.upper().endswith("_BL.PDF"):
        base = dict(base, consignee="AL GURG STATIONERY LLC", notify_party="AL GURG STATIONERY LLC")
    r.fields = base
    return r


ai_extract.ai_extract = fake_reader
ai_reply.polish = lambda body, facts, client=None: (body + chr(10) + "[polished by stand-in AI]", True)

labels = lambda tab: [b.label for b in tab.button]
compare = lambda: at.tabs[3]
open_sample = lambda title: [b for b in compare().button if title in b.label][0].click().run()

open_sample("Scanned image")
check("Scanned-image sample offers the second opinion", any("second opinion" in l for l in labels(compare())))
[b for b in compare().button if "second opinion" in b.label][0].click().run()
check("The advisory appears as a table and the verdict stays NEEDS REVIEW",
      any("second opinion" in i.value for i in compare().info)
      and any("sd-tbl" in m.value and "Consignee" in m.value for m in compare().markdown)
      and any("NEEDS REVIEW" in m.value for m in compare().markdown))
open_sample("Everything matches")
check("An OK case has no second-opinion button", not any("second opinion" in l for l in labels(compare())))

for title in ("Everything matches", "Wrong weight", "A field is left blank", "Wrong document attached"):
    open_sample(title)
    check(f"Polish button under the reply for '{title}'", any("Polish wording" in l for l in labels(compare())))
[b for b in compare().button if "Polish wording" in b.label][0].click().run()
area = [t for t in compare().text_area if t.label == "Message"][0]
check("Polish rewrites the message in place", "[polished by stand-in AI]" in area.value)
check("Playground reply has the polish button", any("Polish wording" in b.label for b in at.tabs[4].button))

ob = lambda: at.tabs[1]
ob().toggle[0].set_value(True).run()
[b for b in ob().button if "Process the inbox" in b.label][0].click().run()
for view, want in (("Awaiting approval", True), ("Left for a human", True), ("Sent (simulated)", False)):
    ob().radio[0].set_value(view).run()
    has = any("Polish wording" in b.label for b in ob().button)
    check(f"Outbox '{view}': polish button {'shown' if want else 'hidden (already sent)'}", has == want)
check("No app errors", len(at.exception) == 0)
print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
