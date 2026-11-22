# V2.2 checks: shadows fit inside their own box and their parent's box (no clipping), large cards keep their
# c-type outline in sync with their size during expand/collapse without clipping the whole card, layout and
# hit-testing are unchanged.  Usage: python3 v22_test.py index.html   (needs Python 3 + Playwright)
import sys, os
from playwright.sync_api import sync_playwright

F = 'file://' + os.path.abspath(sys.argv[1])
res = []
def ok(name, cond, info=''):
    cond = bool(cond); res.append(cond)
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f'  {info}'))

AUDIT = r'''
window.__au={n:0,bad:[]};
const pts=s=>{const o=[];const re=/([MLCAZ])([^MLCAZ]*)/gi;let m;while((m=re.exec(s))){const c=m[1].toUpperCase(),v=(m[2].match(/-?\d*\.?\d+(?:e-?\d+)?/g)||[]).map(Number);
 if(c=='M'||c=='L'||c=='C'){for(let i=0;i+1<v.length;i+=2)o.push([v[i],v[i+1]])}else if(c=='A'){for(let i=0;i+6<v.length;i+=7)o.push([v[i+5],v[i+6]])}}return o};
const chk=()=>{__au.n++;document.querySelectorAll('[data-sqb]').forEach(el=>{const r=el.getBoundingClientRect();if(r.bottom<0||r.top>innerHeight||r.height<2)return;
 const cp=(el._sq.bg||el).style.clipPath,m=cp.match(/path\("([^"]+)"/);if(!m){__au.bad.push(['missing',el.className]);return}
 const p=pts(m[1]),mx=Math.max(...p.map(q=>q[0])),my=Math.max(...p.map(q=>q[1]));
 if(Math.abs(mx-el.offsetWidth)>1.01||Math.abs(my-el.offsetHeight)>1.01)__au.bad.push(['size',el.className,mx,my,el.offsetWidth,el.offsetHeight])})};
const d=document.createElement('div');d.style.cssText='position:fixed;left:0;top:0;width:1px;height:1px;opacity:0;pointer-events:none';document.body.append(d);let k=0;
new ResizeObserver(chk).observe(d);const t=()=>{k^=1;d.style.width=(1+k)+'px';requestAnimationFrame(t)};requestAnimationFrame(t);
'''

def shadow_boxes(p):
    return p.evaluate('''()=>{const R=e=>{const r=e.getBoundingClientRect();return[r.left,r.top,r.right,r.bottom]};const out={};
      const q=document.querySelector('.qzw'),s=q.querySelector('.sqsh'),b=s.querySelector('b'),c=q.querySelector('.qz');
      const cr=R(c);out.quiz={parent:R(q),own:R(s),shape:[cr[0]+10,cr[1]+10,cr[2]-10,cr[3]+10],sigma:18,img:s.classList.contains('img')};
      const a=document.querySelector('.avw'),as=a.querySelector('.avsh'),av=R(document.querySelector('#av'));out.avatar={parent:R(a),own:R(as),shape:[av[0],av[1]+3,av[2],av[3]+3],sigma:4.5};
      const m=document.querySelector('#menu');m.style.transition='none';m.style.transform='none';void m.offsetWidth;const mi=R(m.querySelector('.mi'));out.menu={parent:R(m),own:R(m.querySelector('.msh')),shape:[mi[0],mi[1]+8,mi[2],mi[3]+8],sigma:11};m.style.transform='';m.style.transition='';
      out.vw=innerWidth;return out}''')

with sync_playwright() as pw:
    br = pw.chromium.launch()
    for (W, H, dpr, mob) in [(280, 653, 3, True), (360, 780, 3, True), (390, 844, 3, True), (1440, 900, 1, False)]:
        tag = f'[{W}]'
        c = br.new_context(viewport={'width': W, 'height': H}, device_scale_factor=dpr, is_mobile=mob, has_touch=mob)
        p = c.new_page(); errs = []; p.on('pageerror', lambda e: errs.append(str(e)))
        p.goto(F); p.wait_for_timeout(900)
        # 1. every shadow's visible blur (3 sigma) fits inside its own box and inside its parent's box (viewport edge allowed)
        S = shadow_boxes(p)
        for k in ('quiz', 'avatar', 'menu'):
            o = S[k]; e = 3 * o['sigma'] - (22 if k == 'quiz' else 0) - (2 if (k == 'avatar' and W <= 300) else 0)   # quiz: horizontal tail past 32px is below one brightness level
            sx0, sy0, sx1, sy1 = o['shape']; ext = [sx0 - e, sy0 - 3 * o['sigma'], sx1 + e, sy1 + 3 * o['sigma']]
            for nm, bx in (('own box', o['own']), ('parent box', o['parent'])):
                inside = (bx[0] <= max(ext[0], 0) + 1 and bx[1] <= ext[1] + 1 and bx[2] >= min(ext[2], S['vw']) - 1 and bx[3] >= ext[3] - 1)
                ok(f'{tag} {k} shadow fits its {nm}', inside, f'box {[round(v) for v in bx]} needs {[round(v) for v in ext]}')
        ok(f'{tag} quiz shadow is a pre-rendered image (no per-frame blur)', S['quiz']['img'])
        # 2. layout unchanged around the practice card and the avatar row
        lay = p.evaluate('''()=>{const q=document.querySelector('.qz').getBoundingClientRect(),pr=document.querySelector('.qzw').previousElementSibling.getBoundingClientRect(),nx=document.querySelector('.qzw').nextElementSibling.getBoundingClientRect(),w=document.querySelector('.qzw').parentElement.getBoundingClientRect(),av=document.querySelector('#av').getBoundingClientRect(),id=document.querySelector('.id').getBoundingClientRect();
          return{gapTop:q.top-pr.bottom,gapBot:nx.top-q.bottom,left:q.left-w.left,width:q.width-w.width,avRow:id.height-av.height,docW:document.documentElement.scrollWidth-innerWidth}}''')
        ok(f'{tag} practice card keeps its 22px / 34px spacing and column width', abs(lay['gapTop'] - 22) < .5 and abs(lay['gapBot'] - 34) < .5 and abs(lay['left']) < .5 and abs(lay['width']) < .5, lay)
        ok(f'{tag} avatar row height unchanged', abs(lay['avRow']) < .5, lay)
        ok(f'{tag} no horizontal overflow', lay['docW'] <= 0, lay)
        # 3. hit-testing: the shadow room around the card and the avatar does not catch taps
        hit = p.evaluate('''()=>{const q=document.querySelector('.qz').getBoundingClientRect();scrollTo(0,scrollY+q.bottom-innerHeight/2);const r=document.querySelector('.qz').getBoundingClientRect();
          const below=document.elementFromPoint(r.left+40,r.bottom+30),inside=document.elementFromPoint(r.left+r.width/2,r.bottom-40);
          const a=document.querySelector('#av');a.scrollIntoView({block:'center'});const ar=a.getBoundingClientRect(),right=document.elementFromPoint(ar.right+6,ar.top+ar.height/2),onav=document.elementFromPoint(ar.left+20,ar.top+20);
          return{below:below&&!below.closest('.qzw'),inside:inside&&!!inside.closest('.qz'),right:right&&!right.closest('.avw'),onav:onav&&!!onav.closest('#av')}}''')
        ok(f'{tag} taps below the practice card reach the content there', hit['below'], hit)
        ok(f'{tag} the practice card itself is still tappable', hit['inside'], hit)
        ok(f'{tag} avatar shadow room does not cover the name beside it', hit['right'], hit)
        ok(f'{tag} avatar is still tappable', hit['onav'], hit)
        # 4. large cards: c-type outline drawn on a background layer, never on the card itself
        cards = p.evaluate('''()=>[...document.querySelectorAll('.rp,.dc,.qz,.ph')].map(e=>({c:e.className.split(' ')[0],own:e.style.clipPath||'',bg:!!(e._sq&&e._sq.bg),bgcp:e._sq&&e._sq.bg?e._sq.bg.style.clipPath.slice(0,6):''}))''')
        ok(f'{tag} report, idea, practice and booking cards are not clipped as a whole', all(x['own'] == '' and x['bg'] for x in cards), [x for x in cards if x['own'] or not x['bg']][:3])
        ok(f'{tag} their c-type outline is on the background layer', all(x['bgcp'].startswith('path(') for x in cards if x['bg']), cards[:2])
        # 5. outline stays in sync with the card size on every frame of expand / collapse
        p.evaluate(AUDIT)
        p.evaluate("document.querySelector('#report-2').scrollIntoView({block:'start'})"); p.wait_for_timeout(500)
        for _ in range(2):
            p.evaluate("document.querySelector('#report-2 .rh').click()"); p.wait_for_timeout(1300)
        p.evaluate("document.querySelector('.ex').scrollIntoView({block:'center'})"); p.wait_for_timeout(500)
        for i in (0, 1, 1):
            p.evaluate(f"document.querySelectorAll('.ex .chip')[{i}].click()"); p.wait_for_timeout(1100)
        p.evaluate("document.querySelector('.qz').scrollIntoView({block:'center'})"); p.wait_for_timeout(500)
        p.evaluate("document.querySelectorAll('#ch button')[0].click()"); p.wait_for_timeout(1500)
        p.evaluate("document.querySelector('#nx').click()"); p.wait_for_timeout(1500)
        au = p.evaluate('__au')
        ok(f'{tag} outline matches card size on every frame ({au["n"]} frames)', au['n'] > 200 and not au['bad'], au['bad'][:3])
        # 6. report paragraphs: on-screen ones animate, off-screen ones skip the invisible transition, flag removed afterwards
        nt = p.evaluate('''async()=>{const r=document.querySelector('#report-3');if(r.classList.contains('open')){r.querySelector('.rh').click();await new Promise(z=>setTimeout(z,1300))}
          r.scrollIntoView({block:'start'});await new Promise(z=>setTimeout(z,300));r.querySelector('.rh').click();await new Promise(z=>requestAnimationFrame(()=>z()));
          const ch=[...r.querySelector('.bd').children],top=r.getBoundingClientRect().top;const vis=ch.filter(c=>top+c.offsetTop<innerHeight*.9),far=ch.filter(c=>top+c.offsetTop>innerHeight*1.4);
          const a={visAnimated:vis.length>0&&vis.every(c=>!c.classList.contains('nt')),farSkipped:far.length>0&&far.every(c=>c.classList.contains('nt'))};
          await new Promise(z=>setTimeout(z,1600));a.cleared=!r.querySelector('.bd>.nt');a.allShown=ch.every(c=>getComputedStyle(c).opacity=='1');return a}''')
        ok(f'{tag} report paragraphs in view keep their animation', nt['visAnimated'], nt)
        ok(f'{tag} paragraphs far outside the view skip the invisible transition', nt['farSkipped'], nt)
        ok(f'{tag} every paragraph ends fully visible and the flag is removed', nt['cleared'] and nt['allShown'], nt)
        # 7. booking menu still opens, closes and is tappable through its shadow room
        bk = p.evaluate('''async()=>{const w=ms=>new Promise(z=>setTimeout(z,ms));const bk=document.querySelector('#bk');bk.scrollIntoView({block:'center'});await w(400);
          const seg=document.querySelector('#seg>button');seg&&seg.click();await w(500);const mg=document.querySelector('#mg');mg.click();await w(800);
          const m=document.querySelector('#menu'),mo=document.querySelector('#mo'),r=mo.getBoundingClientRect(),hitItem=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2)===mo;
          const g=mg.getBoundingClientRect(),hitBtn=document.elementFromPoint(g.left+g.width/2,g.top+g.height/2);const open=m.classList.contains('open');
          hitBtn&&hitBtn.click();await w(800);return{open,hitItem,hitBtn:!!hitBtn&&!!hitBtn.closest('#mg'),closed:!m.classList.contains('open')}}''')
        ok(f'{tag} booking menu opens and its items are tappable', bk['open'] and bk['hitItem'], bk)
        ok(f'{tag} the 管理 button stays tappable while the menu is open, and closes it', bk['hitBtn'] and bk['closed'], bk)
        ok(f'{tag} no script errors', not errs, errs[:2])
        c.close()
    br.close()
print(f'{sum(res)}/{len(res)} passed')
