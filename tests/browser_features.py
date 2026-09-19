"""Optional browser test of the samples, playground, time-saved panel, guide and editable Outbox.
See tests/browser_check.py for how to run it (needs playwright and a running app).
"""
import sys
import os
from playwright.sync_api import sync_playwright

import os
URL = os.environ.get("SDOC_URL", "http://localhost:8599")
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".browser_shots")
os.makedirs(SHOTS, exist_ok=True)
results = []


def check(name, ok):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name)


def dom(pg, text):
    return pg.get_by_text(text, exact=False).count() > 0


def click_row(pg, r):
    bb = pg.locator('[data-testid="stDataFrame"]:visible').all()[0].bounding_box()
    pg.mouse.click(bb["x"] + 250, bb["y"] + 35 + 35 * r + 17)
    pg.wait_for_timeout(2500)


def tab(pg, name):
    pg.get_by_role("tab", name=name).click()
    pg.wait_for_timeout(1200)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1500, "height": 1700})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(2500)

    # ---- 3. start-here guide
    check("Guide: 'New here?' panel is visible", dom(pg, "New here? Four quick ways to explore"))
    pg.screenshot(path=SHOTS + "/f_guide.png")

    # ---- 5. time saved (dashboard)
    check("Time saved: panel and hours figure shown", dom(pg, "What this saves") and dom(pg, "hours"))
    before = pg.locator(".sd-hero").all_inner_texts()
    pg.get_by_role("slider").first.focus()
    for _ in range(5):
        pg.keyboard.press("ArrowRight")
    pg.wait_for_timeout(2500)
    after = pg.locator(".sd-hero").all_inner_texts()
    check("Time saved: moving the slider changes the estimate", before != after)
    pg.screenshot(path=SHOTS + "/f_value.png", full_page=True)

    # ---- 1. samples
    tab(pg, "🔍 Compare documents")
    pg.get_by_role("button", name="✅ Everything matches").click()
    pg.wait_for_timeout(2500)
    check("Sample: 'Everything matches' shows OK", dom(pg, "All 7 fields match") and dom(pg, "Sample: Everything matches"))
    check("Sample: download buttons for the SI and BL are offered", dom(pg, "Sample SI") and dom(pg, "Sample BL"))
    pg.get_by_role("button", name="⚖️ Wrong weight and container count").click()
    pg.wait_for_timeout(2500)
    check("Sample: wrong weight shows the mismatch", dom(pg, "Differs in") and dom(pg, "Gross weight"))
    pg.get_by_role("button", name="⬜ A field is left blank").click()
    pg.wait_for_timeout(2500)
    check("Sample: blank field goes to a human", dom(pg, "NEEDS REVIEW") and dom(pg, "blank or a placeholder"))
    pg.get_by_role("button", name="🖼️ Scanned image").click()
    pg.wait_for_timeout(3000)
    check("Sample: scanned image is escalated", dom(pg, "NEEDS REVIEW") and dom(pg, "image-only scan"))
    pg.screenshot(path=SHOTS + "/f_samples.png", full_page=True)
    pg.get_by_role("button", name="✖ Clear sample").click()
    pg.wait_for_timeout(1500)
    check("Sample: 'Clear sample' removes it", not dom(pg, "Sample: Scanned image"))

    # ---- 2. playground
    tab(pg, "🧪 Playground")
    check("Playground: starts as a matching pair", dom(pg, "All 7 fields match"))
    pg.get_by_role("button", name="⚖️ Change the weight").click()
    pg.wait_for_timeout(2500)
    check("Playground: changing the weight is caught", dom(pg, "Differs in") and dom(pg, "Gross weight"))
    pg.screenshot(path=SHOTS + "/f_play.png", full_page=True)
    pg.get_by_role("button", name="↩️ Reset").click()
    pg.wait_for_timeout(2500)
    check("Playground: Reset restores the match", dom(pg, "All 7 fields match"))
    pg.get_by_role("button", name="🔧 Reformat weight").click()
    pg.wait_for_timeout(2500)
    check("Playground: same weight written differently still MATCHES", dom(pg, "All 7 fields match"))
    pg.get_by_role("button", name="🔤 Typo in consignee").click()
    pg.wait_for_timeout(2500)
    check("Playground: a one-letter typo in a name is caught", dom(pg, "Differs in") and dom(pg, "Consignee"))
    pg.get_by_role("button", name="↩️ Reset").click()
    pg.wait_for_timeout(2000)
    pg.get_by_role("button", name="⬜ Blank a field").click()
    pg.wait_for_timeout(2500)
    check("Playground: a blank field is escalated, not guessed", dom(pg, "NEEDS REVIEW"))
    pg.get_by_role("button", name="↩️ Reset").click()
    pg.wait_for_timeout(2000)
    boxes = pg.locator('input[aria-label="Container count"]:visible')
    boxes.nth(1).fill("99 x 40'HC")
    boxes.nth(1).press("Enter")
    pg.wait_for_timeout(2500)
    check("Playground: typing your own value is checked live", dom(pg, "Differs in") and dom(pg, "Container count"))

    # ---- 6. editable outbox
    tab(pg, "📤 Outbox")
    pg.get_by_text("Hold mismatch replies for approval").click()
    pg.wait_for_timeout(1000)
    pg.get_by_role("button", name="▶ Process the inbox").click()
    pg.wait_for_timeout(3500)
    check("Outbox: 46 replies wait for approval", dom(pg, "Awaiting your approval"))
    pg.get_by_text("Awaiting approval").first.click()
    pg.wait_for_timeout(2500)
    click_row(pg, 0)
    area = pg.get_by_label("Message (you can edit it before approving)")
    check("Outbox: a held message is editable", area.count() == 1)
    area.fill("EDITED BY A HUMAN before sending. Please confirm the consignee.")
    area.press("Control+Enter")
    pg.wait_for_timeout(1500)
    pg.get_by_role("button", name="✅ Approve (simulated send)").click()
    pg.wait_for_timeout(3000)
    check("Outbox: approving moves it out of 'awaiting' (45 left)", dom(pg, "45"))
    pg.get_by_text("All", exact=True).first.click()
    pg.wait_for_timeout(2500)
    click_row(pg, 1)
    check("Outbox: the approved message keeps the human's edit", dom(pg, "Approved with your edits"))
    pg.screenshot(path=SHOTS + "/f_outbox.png", full_page=True)
    b.close()

print(f"{sum(results)}/{len(results)} passed")
