"""Drive scoring/pairs.html in Edge: picks, keys, csv, themes, phone width."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
URL = (ROOT / "scoring/pairs.html").as_uri()
SHOT = ROOT / "work/shots"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for scheme in ["light", "dark"]:
        pg = b.new_page(viewport={"width": 1100, "height": 700}, color_scheme=scheme)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL)
        pg.screenshot(path=str(SHOT / f"pairs-{scheme}.png"))
        pg.click("#pa"); pg.wait_for_timeout(300)
        assert pg.text_content("#count").startswith("2 /")
        pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(300)
        pg.keyboard.press("0"); pg.wait_for_timeout(300)
        rows = pg.evaluate("csv()").strip().splitlines()
        print(scheme, rows)
        assert [r.split(",")[3] for r in rows[1:]] == ["a", "b", "same"]
        pg.click("#prev"); pg.click("#prev"); pg.click("#prev")
        assert "on" in pg.get_attribute("#pa", "class")
        assert not errs, errs
        pg.close()
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.goto(URL)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 390
    pg.screenshot(path=str(SHOT / "pairs-phone.png"), full_page=True)
    b.close()
print("all checks passed")
