# V2.0 functional tests: booking state + event log, quiz scoring / reset / analysis, keyboard + inert focus,
# dialog focus return, duplicate ids, script errors. usage: python3 v2_test.py page.html
import asyncio, sys, json
from playwright.async_api import async_playwright
F = 'file://' + sys.argv[1]
ok = bad = 0
def chk(name, cond, info=''):
    global ok, bad
    if cond: ok += 1; print('PASS', name, info)
    else: bad += 1; print('FAIL', name, info)

ST = """()=>{const bk=document.querySelector('#bk');return{s:['s0','s1','s2'].find(c=>bk.classList.contains(c)),v:bk.classList.contains('vB')?'B':'A',
cn:+document.querySelector('#cn').textContent,tm:document.querySelector('#tm').textContent,sl:document.querySelector('#sl').textContent,
on:[...document.querySelectorAll('.tc.on')].map(x=>x.dataset.t),blog:document.querySelector('#blog').textContent,
edpInert:document.querySelector('#edp>div').inert,dnpInert:document.querySelector('#dnp>div').inert,mnInert:document.querySelector('.mn').inert,
menuOpen:document.querySelector('#menu').classList.contains('open'),menuInert:document.querySelector('#menu').inert}}"""

async def booking(pg, ver):
    await pg.goto(F); await pg.wait_for_timeout(900)
    await pg.evaluate("document.querySelector('#exploration').scrollIntoView()"); await pg.wait_for_timeout(400)
    if ver == 'B':
        await pg.click('#seg button:nth-of-type(2)'); await pg.wait_for_timeout(500)
    s = await pg.evaluate(ST)
    chk(f'[{ver}] initial state', s['s'] == 's0' and s['cn'] == 0 and s['tm'] == '10:00' and s['on'] == ['14:00'] and s['edpInert'] and s['dnpInert'] and not s['mnInert'] and s['menuInert'], json.dumps(s, ensure_ascii=False))
    async def enter():
        if ver == 'A':
            await pg.click('#mg'); await pg.wait_for_timeout(450); await pg.click('#mo')
        else:
            await pg.click('#dr')
        await pg.wait_for_timeout(700)
    # 1. normal modify
    await enter(); await pg.click('.tc[data-t="16:00"]'); await pg.wait_for_timeout(300); await pg.click('#ok'); await pg.wait_for_timeout(700)
    s = await pg.evaluate(ST)
    need = 4 if ver == 'A' else 3
    chk(f'[{ver}] normal modify: data + screen in sync', s['s'] == 's2' and s['tm'] == '16:00' and s['sl'] == '16:00' and s['cn'] == need and s['edpInert'] and not s['dnpInert'], json.dumps(s, ensure_ascii=False))
    log = await pg.evaluate("BL.cur.events.map(e=>e.event)")
    want = (['start', 'open-menu', 'find-edit', 'select-time', 'confirm', 'complete'] if ver == 'A' else ['start', 'find-edit', 'select-time', 'confirm', 'complete'])
    chk(f'[{ver}] event log sequence', log == want, str(log))
    ev = await pg.evaluate("BL.cur.events")
    chk(f'[{ver}] event fields', all(set(['sessionId', 'version', 'event', 'elapsedMs', 'actionIndex']) <= set(e) for e in ev) and all(e['version'] == ver for e in ev) and ev[-1]['actionIndex'] == need and all(ev[i]['elapsedMs'] <= ev[i+1]['elapsedMs'] for i in range(len(ev)-1)))
    chk(f'[{ver}] summary line shows completion', '完成' in s['blog'] and f'版本 {ver}' in s['blog'], s['blog'])
    # clicks after completion change nothing
    await pg.evaluate("document.querySelector('#ok').click();document.querySelector('#no').click();document.querySelector('.tc[data-t=\"14:00\"]').click()")
    s2 = await pg.evaluate(ST)
    chk(f'[{ver}] completed state ignores stale clicks', s2['cn'] == s['cn'] and s2['s'] == 's2' and s2['tm'] == '16:00')
    # 6. restart after completion
    await pg.click('#rs'); await pg.wait_for_timeout(700)
    s = await pg.evaluate(ST); runs = await pg.evaluate("BL.runs.length"); cur = await pg.evaluate("BL.cur.events.map(e=>e.event)")
    chk(f'[{ver}] reset after completion: everything initial', s['s'] == 's0' and s['cn'] == 0 and s['tm'] == '10:00' and s['sl'] == '14:00' and s['on'] == ['14:00'] and cur == ['start'], json.dumps(s, ensure_ascii=False) + str(cur))
    prev = await pg.evaluate("BL.runs[BL.runs.length-2].events.map(e=>e.event).slice(-1)[0]")
    chk(f'[{ver}] previous run closed with reset', prev == 'reset', prev)
    # 2. cancel restores pre-edit selection
    await enter(); await pg.click('.tc[data-t="16:00"]'); await pg.wait_for_timeout(250); await pg.click('#no'); await pg.wait_for_timeout(700)
    s = await pg.evaluate(ST)
    chk(f'[{ver}] cancel: back to pre-edit state', s['s'] == 's0' and s['tm'] == '10:00' and s['on'] == ['14:00'] and not s['mnInert'] and s['edpInert'], json.dumps(s, ensure_ascii=False))
    # 3. reset in the middle of editing
    await enter(); await pg.click('.tc[data-t="16:00"]'); await pg.wait_for_timeout(250); await pg.click('#rs'); await pg.wait_for_timeout(700)
    s = await pg.evaluate(ST)
    chk(f'[{ver}] reset mid-edit: full initial data', s['s'] == 's0' and s['cn'] == 0 and s['tm'] == '10:00' and s['sl'] == '14:00' and s['on'] == ['14:00'], json.dumps(s, ensure_ascii=False))
    # 4. rapid clicks on confirm: one submission
    await enter(); c0 = (await pg.evaluate(ST))['cn']
    await pg.evaluate("for(let i=0;i<6;i++)document.querySelector('#ok').click()"); await pg.wait_for_timeout(600)
    s = await pg.evaluate(ST); n = await pg.evaluate("BL.cur.events.filter(e=>e.event=='complete').length")
    chk(f'[{ver}] rapid confirm: single submission', s['cn'] == c0 + 1 and n == 1 and s['s'] == 's2', f"cn {c0}->{s['cn']} completes {n}")
    await pg.click('#rs'); await pg.wait_for_timeout(600)
    # current slot cannot be chosen
    await enter(); await pg.evaluate("document.querySelector('.tc.cur').click()"); await pg.wait_for_timeout(200)
    s = await pg.evaluate(ST)
    chk(f'[{ver}] current slot 10:00 not selectable', s['on'] == ['14:00'], str(s['on']))
    await pg.click('#rs'); await pg.wait_for_timeout(600)

async def booking_extra(pg):
    await pg.goto(F); await pg.wait_for_timeout(900)
    await pg.evaluate("document.querySelector('#exploration').scrollIntoView()"); await pg.wait_for_timeout(400)
    # 130 ms menu→edit timer cancelled by reset
    await pg.click('#mg'); await pg.wait_for_timeout(450)
    await pg.evaluate("document.querySelector('#mo').click();document.querySelector('#rs').click()"); await pg.wait_for_timeout(500)
    s = await pg.evaluate(ST)
    chk('[A] reset during the 130 ms menu hand-off stays at start', s['s'] == 's0' and s['cn'] == 0, json.dumps(s, ensure_ascii=False))
    # version switch mid-edit does not carry state
    await pg.click('#mg'); await pg.wait_for_timeout(450); await pg.click('#mo'); await pg.wait_for_timeout(700)
    await pg.click('.tc[data-t="16:00"]'); await pg.wait_for_timeout(250)
    await pg.click('#seg button:nth-of-type(2)'); await pg.wait_for_timeout(600)
    s = await pg.evaluate(ST); v = await pg.evaluate("[BL.cur.version,BL.cur.events.map(e=>e.event)]")
    chk('A→B switch mid-edit: clean B state', s['v'] == 'B' and s['s'] == 's0' and s['cn'] == 0 and s['on'] == ['14:00'] and s['tm'] == '10:00' and v[0] == 'B' and v[1] == ['start'], json.dumps(s, ensure_ascii=False) + str(v))
    # same task / data in both versions
    same = await pg.evaluate("""()=>{const t=[...document.querySelectorAll('.tc')].map(b=>b.dataset.t+(b.disabled?'x':''));return t.join(',')}""")
    chk('A/B share the same time slots', same == '10:00x,14:00,16:00', same)
    # copy JSON
    await pg.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    await pg.click('#blc'); await pg.wait_for_timeout(200)
    txt = await pg.evaluate("navigator.clipboard.readText()")
    try:
        j = json.loads(txt); good = 'runs' in j and isinstance(j['runs'], list) and all('t0' not in r for r in j['runs'])
    except Exception as e:
        good = False
    chk('copy log produces valid JSON', good, txt[:80].replace('\n', ' '))

async def quiz(pg):
    await pg.goto(F); await pg.wait_for_timeout(900)
    await pg.evaluate("document.querySelector('.qz').scrollIntoView()"); await pg.wait_for_timeout(500)
    chk('fb panel inert before answering', await pg.evaluate("document.querySelector('#fb>div').inert"))
    wrong = 0
    for k in range(6):
        ans = await pg.evaluate("Q[ord[ix]][2]")
        pick = ans if k % 2 == 0 else (ans + 1) % 3
        if pick != ans: wrong += 1
        # double click the choice quickly
        await pg.evaluate(f"(()=>{{const b=document.querySelectorAll('#ch button')[{pick}];b.click();b.click()}})()")
        await pg.wait_for_timeout(250)
        if k == 0:
            fx = await pg.evaluate("document.querySelectorAll('#ft .fx').length")
            chk('feedback explains why-not + evidence', fx == 2)
            chk('fb panel focusable after answering', not await pg.evaluate("document.querySelector('#fb>div').inert"))
        await pg.click('#nx'); await pg.wait_for_timeout(900)
    t = await pg.evaluate("document.querySelector('#sm').innerText")
    n_wrong = await pg.evaluate("document.querySelectorAll('#sm .qrw').length")
    chk('summary: correct count', f'{6-wrong} / 6' in t, f'{6-wrong}/6')
    chk('summary: wrong items listed once each (no double scoring)', n_wrong == wrong, f'{n_wrong} vs {wrong}')
    chk('summary: confusion + learning point', '最容易混淆' in t and '學習重點' in t and '本次練習進度' in t)
    await pg.click('#rt'); await pg.wait_for_timeout(1000)
    st = await pg.evaluate("({ix,ans:ans.length,qa:!document.querySelector('#qa').hidden,sm:document.querySelector('#sm').hidden,sg:[...document.querySelectorAll('.sg')].map(s=>s.className).join('|')})")
    chk('restart clears the previous round', st['ix'] == 0 and st['ans'] == 0 and st['qa'] and st['sm'] and st['sg'].startswith('sg c|sg|'), str(st))
    for k in range(6):
        ans = await pg.evaluate("Q[ord[ix]][2]")
        await pg.evaluate(f"document.querySelectorAll('#ch button')[{ans}].click()"); await pg.wait_for_timeout(200)
        await pg.click('#nx'); await pg.wait_for_timeout(900)
    t = await pg.evaluate("document.querySelector('#sm').innerText")
    chk('second round scored independently (6/6, no wrong list)', '6 / 6' in t and await pg.evaluate("document.querySelectorAll('#sm .qrw').length") == 0)

async def keyboard(pg):
    await pg.goto(F); await pg.wait_for_timeout(900)
    # tab through the whole page: nothing focused may be invisible (collapsed / hidden)
    bads = await pg.evaluate("""async()=>{const out=[];const seen=new Set();document.body.focus();
    const els=[...document.querySelectorAll('a[href],button,[tabindex]')].filter(e=>e.tabIndex>=0);
    for(const e of els){const r=e.getBoundingClientRect();const inert=!!e.closest('[inert]');const hid=!e.getClientRects().length||getComputedStyle(e).visibility=='hidden';
      if(inert||hid)continue; // not reachable
      // reachable: make sure it is actually shown (not inside a collapsed panel)
      let p=e.parentElement,clip=false;while(p&&p!==document.body){const cs=getComputedStyle(p);if((cs.overflow!='visible'||cs.overflowY!='visible')&&p.getBoundingClientRect().height<2){clip=true;break}if(parseFloat(cs.opacity)===0&&!p.closest('#mm')&&!p.classList.contains('rv')&&!p.closest('.rv:not(.in)')){clip=true;break}p=p.parentElement}
      if(clip)out.push((e.id||e.className||e.tagName)+' '+(e.textContent||'').trim().slice(0,12))}
    return out}""")
    chk('no focusable control hidden inside collapsed content', not bads, str(bads))
    # zoom dialog: Enter opens, focus inside; Esc closes, focus returns to the portrait
    await pg.focus('#av'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(900)
    a = await pg.evaluate("[document.activeElement.id,document.querySelector('#zm').classList.contains('open')]")
    chk('portrait dialog: focus moves into the dialog', a == ['zm', True], str(a))
    await pg.keyboard.press('Tab'); a2 = await pg.evaluate("document.activeElement.id")
    chk('portrait dialog: Tab stays in the dialog', a2 == 'zm', a2)
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(700)
    a = await pg.evaluate("[document.activeElement.id,document.querySelector('#zm').classList.contains('open')]")
    chk('portrait dialog: Esc closes, focus back on portrait', a == ['av', False], str(a))
    # booking via keyboard (version B)
    await pg.evaluate("document.querySelector('#exploration').scrollIntoView()"); await pg.wait_for_timeout(300)
    await pg.click('#seg button:nth-of-type(2)'); await pg.wait_for_timeout(500)
    await pg.focus('#dr'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(700)
    a = await pg.evaluate("document.activeElement.dataset.t||document.activeElement.id")
    chk('keyboard: opening edit moves focus to the selected slot', a == '14:00', a)
    await pg.keyboard.press('Tab'); a = await pg.evaluate("document.activeElement.dataset.t||document.activeElement.id")
    chk('keyboard: next stop is 16:00 (10:00 is disabled)', a == '16:00', a)
    await pg.keyboard.press('Enter'); await pg.focus('#ok'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(700)
    a = await pg.evaluate("[document.activeElement.closest('#dnp')?'dnp':document.activeElement.id,document.querySelector('#tm').textContent]")
    chk('keyboard: confirming moves focus to the result', a == ['dnp', '16:00'], str(a))
    # dropdown (version A): Esc returns focus to 管理
    await pg.click('#seg button:nth-of-type(1)'); await pg.wait_for_timeout(500)
    await pg.focus('#mg'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(450)
    await pg.keyboard.press('Tab'); a = await pg.evaluate("document.activeElement.id")
    chk('keyboard: Tab goes from 管理 into the open menu', a == 'mo', a)
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
    a = await pg.evaluate("[document.activeElement.id,document.querySelector('#menu').classList.contains('open'),document.querySelector('#mg').getAttribute('aria-expanded')]")
    chk('keyboard: Esc closes menu, focus back on 管理', a == ['mg', False, 'false'], str(a))
    # report: collapse from inside returns focus to its header
    await pg.evaluate("document.querySelector('#research').scrollIntoView()"); await pg.wait_for_timeout(300)
    await pg.click('#report-2 .rh'); await pg.wait_for_timeout(1000)
    await pg.focus('#report-2 .cl'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(1000)
    a = await pg.evaluate("[document.activeElement.closest('.rp')?.id,document.activeElement.className,document.querySelector('#report-2 .bd').inert]")
    chk('keyboard: collapsing a report returns focus to its header', a == ['report-2', 'rh', True], str(a))
    ac = await pg.evaluate("[...document.querySelectorAll('.rh')].every(h=>document.getElementById(h.getAttribute('aria-controls')))")
    chk('report buttons have valid aria-controls', ac)

async def mobile_menu(pg):
    await pg.goto(F); await pg.wait_for_timeout(900)
    await pg.focus('#mb'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(700)
    await pg.keyboard.press('Tab'); a = await pg.evaluate("document.activeElement.textContent")
    chk('mobile menu: Tab reaches the first link', a == '精選作品', a)
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(600)
    a = await pg.evaluate("[document.activeElement.id,document.querySelector('#mm').classList.contains('open')]")
    chk('mobile menu: Esc closes, focus back on menu button', a == ['mb', False], str(a))
    links = await pg.evaluate("[...document.querySelectorAll('#mm a')].map(a=>a.getAttribute('href'))")
    chk('mobile menu links', links == ['#work', '#playground', '#exploration', '#research', 'process.html', '#about'], str(links))
    await pg.click('#mb'); await pg.wait_for_timeout(700); await pg.click('#mm a[href="#work"]'); await pg.wait_for_timeout(1400)
    top = await pg.evaluate("document.querySelector('#work').getBoundingClientRect().top-document.querySelector('header').getBoundingClientRect().bottom")
    chk('mobile menu → 精選作品 lands under the header', abs(top) <= 2, f'{top:.1f}px')

async def static(pg):
    await pg.goto(F); await pg.wait_for_timeout(900)
    d = await pg.evaluate("(()=>{const c={};document.querySelectorAll('[id]').forEach(e=>c[e.id]=(c[e.id]||0)+1);return Object.entries(c).filter(x=>x[1]>1)})()")
    chk('no duplicate ids', not d, str(d))
    hero = await pg.evaluate("[...document.querySelectorAll('.hero a')].map(a=>a.textContent+'→'+a.getAttribute('href'))")
    chk('hero: primary → 精選作品, secondary → 實驗室', hero == ['查看精選作品 ↓→#work', '體驗 UX 實驗室 ↗→#playground'], str(hero))
    cards = await pg.evaluate("[...document.querySelectorAll('#work .wk')].map(a=>[a.getAttribute('href'),a.querySelector('h3').textContent,a.querySelector('.tg').textContent])")
    chk('3 work cards with status + case page links', len(cards) == 3 and all(c[0].startswith('work-') for c in cards), json.dumps(cards, ensure_ascii=False))
    lk = await pg.evaluate("[...document.querySelectorAll('#lk a')].map(a=>a.textContent)")
    chk('desktop nav', lk == ['精選作品', '互動實驗室', '概念練習', 'UX 報告', '實作紀錄'], str(lk))
    sq = await pg.evaluate("[...document.querySelectorAll('#work .kc,#work .tg')].every(e=>e.style.clipPath.startsWith('path('))")
    chk('new cards / tags use the c-type corner', sq)
    sim = await pg.evaluate("document.querySelector('.fd').innerText")
    chk('fridge demo labelled as simulation', '情境模擬' in sim and '並非真實使用者測試結果' in sim)
    lab = await pg.evaluate("(document.querySelector('#research .rlab')||{}).textContent||''")
    chk('reports: one 情境重構 label at the top', lab.startswith('情境重構'), lab)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for vp, fn in [((390, 844), booking), ((1280, 800), booking)]:
            for ver in ['A', 'B']:
                ctx = await b.new_context(viewport=dict(width=vp[0], height=vp[1])); pg = await ctx.new_page(); errs = []
                pg.on('pageerror', lambda e: errs.append(str(e)))
                print(f'--- booking {ver} @{vp[0]}'); await fn(pg, ver)
                chk(f'no script errors (booking {ver} @{vp[0]})', not errs, str(errs)); await ctx.close()
        for name, fn, vp in [('booking extra', booking_extra, (390, 844)), ('quiz', quiz, (390, 844)), ('quiz desktop', quiz, (1280, 800)), ('keyboard', keyboard, (1280, 800)), ('mobile menu', mobile_menu, (390, 844)), ('static', static, (1280, 800))]:
            ctx = await b.new_context(viewport=dict(width=vp[0], height=vp[1])); pg = await ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            print('---', name); await fn(pg)
            chk(f'no script errors ({name})', not errs, str(errs)); await ctx.close()
        await b.close()
    print(f'\n{ok}/{ok+bad} passed')
asyncio.run(main())
