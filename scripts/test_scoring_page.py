"""Drive scoring/score.html in Edge: sliders, thumbs, save and next, csv, themes, phone width."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
URL = (ROOT / "scoring/score.html").as_uri()
SHOT = ROOT / "work/shots"
SHOT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for scheme in ["light", "dark"]:
        pg = b.new_page(viewport={"width": 1000, "height": 760}, color_scheme=scheme)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL)
        assert pg.is_disabled("#next"), "next should start disabled"
        assert pg.locator(".dim.unset").count() == 7
        for i, frac in enumerate([0.9, 0.5, 0.1, 0.75, 0.3, 1.0, 0.0]):
            box = pg.locator("#dims input").nth(i).bounding_box()
            pg.mouse.click(box["x"] + 8 + (box["width"] - 16) * frac, box["y"] + box["height"] / 2)
        assert pg.locator(".dim.unset").count() == 0
        assert not pg.is_disabled("#next")
        pg.click("#up")
        assert "on" in pg.get_attribute("#up", "class")
        pg.screenshot(path=str(SHOT / f"score-{scheme}.png"))
        first = pg.text_content("#count")
        pg.click("#next")
        assert pg.text_content("#count") != first and pg.is_disabled("#next")
        csv = pg.evaluate("csv()")
        lines = csv.strip().splitlines()
        print(scheme, "csv header:", lines[0])
        print(scheme, "row:", lines[1])
        vals = [float(x) for x in lines[1].split(",")[4:11]]
        assert vals[0] > 4 and vals[2] < 1 and vals[5] == 5 and vals[6] == 0, vals
        assert lines[1].split(",")[11] == "1"
        pg.click("#prev")
        assert pg.locator(".dim.unset").count() == 0, "values should come back on Back"
        assert not errs, errs
        pg.close()
    pg = b.new_page(viewport={"width": 390, "height": 844}, color_scheme="light")
    pg.goto(URL)
    w = pg.evaluate("document.documentElement.scrollWidth")
    print("phone scrollWidth", w)
    assert w <= 390
    pg.screenshot(path=str(SHOT / "score-phone.png"), full_page=True)
    b.close()
print("all checks passed")
