"""Optional end-to-end check of click-a-row in a real browser.

    pip install playwright && python -m playwright install chromium
    SDOC_NO_AI=1 python -m streamlit run app.py --server.port 8599 --server.headless true
    python tests/browser_check.py            (in another terminal)

Not part of requirements.txt: it needs a browser download. Make sure no OLD copy of the
app is still running on the port, or you will be testing stale code.
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
URL = os.environ.get("SDOC_URL", "http://localhost:8599")
ATT = os.path.join(ROOT, "attachments")


def mail(n):
    return json.load(open(os.path.join(ROOT, "inbox", f"email_{n}.json")))


def click_row(pg, r):
    bb = pg.locator('[data-testid="stDataFrame"]:visible').all()[0].bounding_box()
    pg.mouse.click(bb["x"] + 250, bb["y"] + 35 + 35 * r + 17)   # header 35px, rows 35px
    pg.wait_for_timeout(2500)


def main():
    results = []

    def check(name, ok):
        results.append(bool(ok))
        print(("PASS  " if ok else "FAIL  ") + name)

    dom = lambda pg, t: pg.get_by_text(t, exact=False).count() > 0
    values = lambda pg: " || ".join(pg.eval_on_selector_all("input, textarea", "els => els.map(e => e.value)"))
    body = lambda pg: pg.inner_text("body")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1500, "height": 1700})
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(2500)

        # ---- Outbox, including switching filters and approving (the tricky cases)
        pg.get_by_role("tab", name="📤 Outbox").click()
        pg.wait_for_timeout(800)
        pg.get_by_text("Hold mismatch replies for approval").click()
        pg.wait_for_timeout(800)
        pg.get_by_role("button", name="▶ Process the inbox").click()
        pg.wait_for_timeout(3500)
        click_row(pg, 1)
        check("Outbox: row 2 opens email_004", "docs@vitalsolutions.sg" in body(pg))
        pg.get_by_text("Awaiting approval").first.click()
        pg.wait_for_timeout(2500)
        click_row(pg, 3)
        check("Outbox: after switching filter, row 4 opens email_031", "hanna_azhari@aprilasia.com" in body(pg))
        pg.get_by_role("button", name="✅ Approve (simulated send)").click()
        pg.wait_for_timeout(3000)
        click_row(pg, 1)
        check("Outbox: after approving, clicking a row still works", "sales@roxcel.at" in body(pg))
        pg.get_by_text("Left for a human").first.click()
        pg.wait_for_timeout(2500)
        click_row(pg, 0)
        check("Outbox: 'Left for a human' row opens a person-needed case", dom(pg, "A person must resolve this case"))

        # ---- Review queue
        pg.get_by_role("tab", name="🚩 Review queue").click()
        pg.wait_for_timeout(1500)
        click_row(pg, 2)
        check("Review queue: row 3 opens email_503", "HOCHIMINH" in values(pg))
        click_row(pg, 0)
        check("Review queue: row 1 opens email_501", "HOUSTON" in values(pg))

        # ---- Inbox browser
        pg.get_by_role("tab", name="📬 Inbox browser").click()
        pg.wait_for_timeout(1500)
        click_row(pg, 2)
        check("Inbox browser: row 3 opens email_003", mail("003")["from"] in body(pg))
        click_row(pg, 5)
        check("Inbox browser: row 6 opens email_006", mail("006")["from"] in body(pg))

        # ---- Batch results
        pg.get_by_role("tab", name="🔍 Compare documents").click()
        pg.wait_for_timeout(1000)
        pg.get_by_text("Batch (many pairs)").click()
        pg.wait_for_timeout(1000)
        pg.set_input_files('input[type="file"]', [os.path.join(ATT, f) for f in (
            "email_334_SI.txt", "email_334_BL.txt", "email_335_SI.txt", "email_335_BL.txt")])
        pg.wait_for_timeout(3500)
        click_row(pg, 1)
        check("Batch: row 2 (email 335) opens the OK case", dom(pg, "All 7 fields match") and not dom(pg, "Differs in"))
        click_row(pg, 0)
        check("Batch: row 1 (email 334) opens the MISMATCH case", dom(pg, "Differs in"))
        b.close()
    print(f"{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
