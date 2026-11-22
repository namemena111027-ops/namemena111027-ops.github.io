# V2.1 tests: nav highlight after hidden sections, quiz chosen-answer contrast, report copy link, story structure.
import asyncio, sys, json, re
from playwright.async_api import async_playwright
F = 'file://' + sys.argv[1]
ok = bad = 0
def chk(name, cond, info=''):
    global ok, bad
    if cond: ok += 1; print('PASS', name, info)
    else: bad += 1; print('FAIL', name, info)
def lum(c):
    r, g, b = [int(x) / 255 for x in re.findall(r'\d+', c)[:3]]
    f = lambda v: v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)
def cr(a, b):
    x, y = sorted([lum(a), lum(b)], reverse=True); return (x + .05) / (y + .05)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        # ---- nav: research → about (no item, hidden) → exploration: the highlight must appear ON 概念練習, not slide from UX 報告
        pg = await b.new_page(viewport=dict(width=1280, height=800)); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(F); await pg.wait_for_timeout(900)
        await pg.evaluate("scrollTo(0,document.querySelector('#research').offsetTop+40)"); await pg.wait_for_timeout(900)
        on1 = await pg.evaluate("document.querySelector('#lk a.on')?.textContent")
        await pg.evaluate("scrollTo(0,document.querySelector('#about').offsetTop+40)"); await pg.wait_for_timeout(700)
        on2 = await pg.evaluate("document.querySelector('#lk a.on')?.textContent||null")
        await pg.evaluate("scrollTo(0,document.querySelector('#exploration').offsetTop+200)")
        frames = await pg.evaluate("""async()=>{const out=[];const a=[...document.querySelectorAll('#lk a')].find(x=>x.textContent=='概念練習'),lk=document.querySelector('#lk');
          for(let i=0;i<20;i++){await new Promise(r=>requestAnimationFrame(r));const s=lk._pl&&lk._pl.o?lk._pl.o:null;const r=document.querySelector('#lk .pls');const pl=document.querySelector('#lk .pls path,#lk .pls rect');
          const bb=pl?pl.getBoundingClientRect():null,ab=a.getBoundingClientRect();out.push(bb?[Math.round(bb.left-ab.left),Math.round(bb.right-ab.right),document.querySelector('#lk a.on')?.textContent||'']:null)}return out}""")
        chk('nav: UX 報告 active in reports', on1 == 'UX 報告', on1)
        chk('nav: no item active in 關於我', on2 is None, str(on2))
        far = [f for f in frames if f and f[2] and (abs(f[0]) > 6 or abs(f[1]) > 6)]  # only frames where an item is active (highlight shown)
        chk('nav: highlight reappears on 概念練習 without sliding from UX 報告', not far and frames[-1] and frames[-1][2] == '概念練習', str(frames[:4]) + ' ... ' + str(frames[-1]))
        # link-to-link still slides (unchanged motion)
        await pg.evaluate("scrollTo(0,document.querySelector('#research').offsetTop+40)")
        fr2 = await pg.evaluate("""async()=>{const out=[];const a=[...document.querySelectorAll('#lk a')].find(x=>x.textContent=='UX 報告');for(let i=0;i<30;i++){await new Promise(r=>requestAnimationFrame(r));const pl=document.querySelector('#lk .pls path,#lk .pls rect');if(pl)out.push(Math.round(pl.getBoundingClientRect().left-a.getBoundingClientRect().left))}return out}""")
        chk('nav: moving between two items still slides (motion kept)', any(abs(v) > 6 for v in fr2[:10]) and abs(fr2[-1]) <= 6, str(fr2[:6]) + '...' + str(fr2[-2:]))
        chk('no script errors (nav)', not errs, str(errs)); await pg.close()
        # ---- quiz chosen answer contrast (correct + wrong), light & dark
        for sch in ['light', 'dark']:
            pg = await b.new_page(viewport=dict(width=390, height=844), color_scheme=sch)
            await pg.goto(F); await pg.wait_for_timeout(900)
            await pg.evaluate("document.querySelector('.qz').scrollIntoView()"); await pg.wait_for_timeout(400)
            for k, label in [(0, 'correct'), (1, 'wrong')]:
                ans = await pg.evaluate("Q[ord[ix]][2]"); pick = ans if k == 0 else (ans + 1) % 3
                await pg.evaluate(f"document.querySelectorAll('#ch button')[{pick}].click()"); await pg.wait_for_timeout(700)
                c = await pg.evaluate(f"(()=>{{const b=document.querySelectorAll('#ch button')[{pick}];return[getComputedStyle(b.querySelector('span')).color,getComputedStyle(b).backgroundColor,getComputedStyle(b.querySelector('small')).color]}})()")
                chk(f'quiz {label} answer text contrast ({sch})', cr(c[0], c[1]) >= 4.5 and cr(c[2], c[1]) >= 4.5, f'{c} → {cr(c[0], c[1]):.1f}:1')
                await pg.click('#nx'); await pg.wait_for_timeout(900)
            await pg.close()
        # ---- reports: copy link + story structure + closing block
        ctx = await b.new_context(viewport=dict(width=390, height=844)); await ctx.grant_permissions(['clipboard-read', 'clipboard-write'])
        pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(F); await pg.wait_for_timeout(900)
        for n in range(1, 5):
            await pg.evaluate(f"document.querySelectorAll('#tabs button')[{n-1}].click()"); await pg.wait_for_timeout(1500)
            await pg.click(f'#report-{n} .ft button:not(.cl)'); await pg.wait_for_timeout(300)
            txt = await pg.evaluate("navigator.clipboard.readText()")
            chk(f'report {n}: copy link', txt.endswith(f'#report-{n}'), txt[-30:])
            st = await pg.evaluate(f"""(()=>{{const bd=document.querySelector('#report-{n} .bd');const ps=[...bd.querySelectorAll(':scope>p:not(.note)')].map(p=>p.textContent).join('');
              return{{chars:ps.replace(/\\s/g,'').length,h3:bd.querySelectorAll(':scope>h3').length,fig:!!bd.querySelector(':scope>figure svg'),
              checklist:/待補|未記錄|研究限制|待驗證|研究問題|證據現況/.test(bd.innerText),hidden:[...bd.querySelectorAll('p,h3,figcaption')].filter(e=>{{let x=e,o=1;while(x&&x!==bd){{o*=+getComputedStyle(x).opacity;x=x.parentElement}}return o<.5}}).length}}}})()""")
            chk(f'report {n}: story (800–1400 chars, ≥3 chapters, sketch, no checklist, nothing hidden)', 800 <= st['chars'] <= 1400 and st['h3'] >= 3 and st['fig'] and not st['checklist'] and st['hidden'] == 0, json.dumps(st, ensure_ascii=False))
        r4 = await pg.evaluate("[!!document.querySelector('#report-4 .bd>.fd'),!!document.querySelector('#report-4 .bd>.cp'),document.querySelector('#report-4 .fd').innerText.includes('情境模擬')]")
        chk('report 4: interactive fridge demo + comparison kept inside the story', all(r4), str(r4))
        xp = await pg.evaluate("[...document.querySelectorAll('.xp .xpg>div')].map(d=>d.querySelector('b').textContent)")
        chk('closing block: exactly two directions', len(xp) == 2, str(xp))
        sq = await pg.evaluate("[...document.querySelectorAll('.bd.story figure .shot')].every(e=>e.style.clipPath.startsWith('path('))")
        chk('story sketches use the c-type corner', sq)
        chk('no script errors (reports)', not errs, str(errs)); await ctx.close()
        await b.close()
    print(f'\n{ok}/{ok+bad} passed')
asyncio.run(main())
