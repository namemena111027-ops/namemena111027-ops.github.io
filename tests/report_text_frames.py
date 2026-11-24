from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    for engine in [pw.webkit,pw.chromium]:
        browser=engine.launch()
        for file in ['baseline.html','index.html']:
            page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=3)
            page.goto(Path(file).resolve().as_uri())
            page.wait_for_timeout(1600)
            result=page.evaluate("""async () => {
              const next=document.querySelector('#tabs button:nth-of-type(4)');
              next.scrollIntoView({block:'center'});
              await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
              const heading=document.querySelector('#report-4 .bd h3');
              const frames=[];
              next.click();
              const start=performance.now();
              do {
                await new Promise(requestAnimationFrame);
                frames.push(Number(getComputedStyle(heading).opacity));
              } while(performance.now()-start<1200);
              return [frames.filter(x=>x>0.01&&x<0.99).length,frames.at(-1)]
            }""")
            print(engine.name,file,result,flush=True)
            assert result[1]==1
            assert (result[0]>0)==(file=='index.html')
            page.close()
        browser.close()
