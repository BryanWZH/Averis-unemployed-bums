"""Optional end-to-end check of the click-a-row behaviour in a real browser.

    pip install playwright && python -m playwright install chromium
    SDOC_NO_AI=1 python -m streamlit run app.py --server.port 8599 --server.headless true &
    python tests/browser_check.py

Not part of requirements.txt: it needs a browser download.
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
URL = os.environ.get("SDOC_URL", "http://localhost:8599")


def mail(n):
    return json.load(open(os.path.join(ROOT, "inbox", f"email_{n}.json")))


def click_row(pg, r):
    bb = pg.locator('[data-testid="stDataFrame"]:visible').all()[0].bounding_box()
    pg.mouse.click(bb["x"] + 250, bb["y"] + 35 + 35 * r + 17)   # header 35px, rows 35px
    pg.wait_for_timeout(2500)


def main():
    results = []

    def check(name, ok):
        results.append(ok)
        print(("PASS  " if ok else "FAIL  ") + name)

    dom = lambda pg, t: pg.get_by_text(t, exact=False).count() > 0
    values = lambda pg: " || ".join(pg.eval_on_selector_all("input, textarea", "els => els.map(e => e.value)"))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1500, "height": 1500})
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(2500)
        pg.get_by_role("tab", name="📤 Outbox").click()
        pg.wait_for_timeout(600)
        pg.get_by_role("button", name="▶ Process the inbox").click()
        pg.wait_for_timeout(3500)
        click_row(pg, 3)
        check("Outbox: row 4 opens email_009's message", dom(pg, "5ALT-19136"))
        pg.get_by_role("tab", name="🚩 Review queue").click()
        pg.wait_for_timeout(1500)
        click_row(pg, 2)
        check("Review queue: row 3 opens email_503", "HOCHIMINH" in values(pg))
        pg.get_by_role("tab", name="📬 Inbox browser").click()
        pg.wait_for_timeout(1500)
        click_row(pg, 2)
        check("Inbox browser: row 3 opens email_003", mail("003")["from"] in pg.inner_text("body"))
        b.close()
    print(f"{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
