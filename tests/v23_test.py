import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

root = Path(sys.argv[1]).resolve().parent
with sync_playwright() as pw:
    for engine, width, height in [(pw.webkit,390,844),(pw.chromium,1280,800)]:
        browser=engine.launch()
        page=browser.new_page(viewport=dict(width=width,height=height),has_touch=width<500)
        errors=[]
        page.on("pageerror",lambda err: errors.append(str(err)))
        for f in ["work-site.html","work-fridge.html","work-booking.html","process.html","index.html"]:
            page.goto((root/f).as_uri())
            assert page.locator("h1").count() and page.title()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (engine.name,f)
        for answer in [0,1,2,0,1,2]:
            page.locator("#ch button").nth(answer).click()
            page.locator("#nx").click()
            page.wait_for_timeout(850)
        expect(page.locator("#sm")).to_contain_text("6 / 6")
        page.click("#rt")
        expect(page.locator("#qm")).to_contain_text("01 / 06")
        page.click("#report-4 .rh")
        page.wait_for_timeout(900)
        for i in [2,0,1]:
            page.locator(".bx").nth(i).click()
            page.wait_for_timeout(750)
        expect(page.locator("#fn")).to_have_text("3")
        page.click("#tryl")
        page.wait_for_timeout(500)
        page.locator(".bx").nth(2).click()
        expect(page.locator("#fn")).to_have_text("1")
        page.click("#frs")
        expect(page.locator("#fn")).to_have_text("0")
        assert not errors,errors
        print("PASS",engine.name,width,"five pages, quiz completion, restart, fridge modes and reset",flush=True)
        browser.close()
