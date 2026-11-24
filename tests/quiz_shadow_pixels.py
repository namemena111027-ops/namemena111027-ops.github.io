from io import BytesIO
from pathlib import Path
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as pw:
    for engine in [pw.webkit, pw.chromium]:
        browser = engine.launch()
        for width in [390, 440]:
            page = browser.new_page(viewport={"width":width,"height":844}, device_scale_factor=3, has_touch=True)
            page.goto(Path("index.html").resolve().as_uri())
            page.locator("#ch button").first.click()
            page.click("#nx")
            expect(page.locator("#qt")).to_contain_text("我起初懷疑人手不足")
            page.wait_for_timeout(1200)
            page.locator(".qz").evaluate("(el)=>scrollBy(0,el.getBoundingClientRect().bottom-560)")
            page.wait_for_timeout(1000)
            card = page.locator(".qz").bounding_box()
            y = round(card["y"] + card["height"])
            clip = dict(x=0,y=0,width=width,height=844)
            def capture():
                return Image.open(BytesIO(page.screenshot(scale="device"))).convert("RGB")
            before = capture()
            before.save(f"question-2-{engine.name}-{width}.png")
            page.locator(".sqsh").evaluate("el=>el.style.visibility='hidden'")
            diff = ImageChops.difference(before,capture())
            center = width*3//2
            assert diff.crop((center-20,(y+1)*3,center+20,(y+10)*3)).getbbox(), "expected a visible soft shadow beneath the card"
            assert not diff.crop((0,(y+28)*3,width*3,(y+70)*3)).getbbox(), "shadow leaked into the following section"
            print("PASS",engine.name,width,"DPR 3, second question, no shadow pixels from +28 to +70")
            page.close()
        browser.close()
