"""Drive scoring/review.html in Edge: votes, notes, csv, themes, phone width."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
import sys
PAGE = sys.argv[1] if len(sys.argv) > 1 else "review.html"
URL = (ROOT / "scoring" / PAGE).as_uri()
SHOT = ROOT / "work/shots"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for scheme in ["light", "dark"]:
        pg = b.new_page(viewport={"width": 1000, "height": 760}, color_scheme=scheme)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL)
        assert pg.locator("#bars .row").count() == 7
        pg.fill("#note", "level too high")
        pg.screenshot(path=str(SHOT / f"review-{scheme}.png"))
        pg.click("#down")
        pg.wait_for_timeout(400)
        assert pg.text_content("#count").startswith("2 /")
        pg.click("#up")
        pg.wait_for_timeout(400)
        rows = pg.evaluate("csv()").strip().splitlines()
        print(scheme, rows)
        assert len(rows) == 3 and rows[1].endswith(",0,level too high") and rows[2].endswith(",1,")
        pg.click("#prev"); pg.click("#prev")
        assert "on" in pg.get_attribute("#down", "class") and pg.input_value("#note") == "level too high"
        assert not errs, errs
        pg.close()
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.goto(URL)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 390
    pg.screenshot(path=str(SHOT / "review-phone.png"), full_page=True)
    b.close()
print("all checks passed")
