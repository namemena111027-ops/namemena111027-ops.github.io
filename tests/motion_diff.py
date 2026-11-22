# Parameter-exact motion comparison between two pages (usage: python3 motion_diff.py old.html new.html).
# CSS: every transition*/animation* declaration (media context + selector + value) and every @keyframes body.
# JS : every .animate(keyframes, options) call (keyframes + options text), every tween(duration, easing, ...) head,
#      every bz(...) easing curve, and every numeric setTimeout delay that schedules a state/animation step.
import re, sys, json
from collections import Counter
def css_rules(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    out = []; stack = []; buf = ''; i = 0
    while i < len(css):
        c = css[i]
        if c == '{':
            stack.append(buf.strip()); buf = ''
        elif c == '}':
            if stack:
                sel = stack.pop()
                if buf.strip() and not sel.startswith('@media') and not sel.startswith('@supports'):
                    ctx = ' | '.join(s for s in stack)
                    out.append((ctx, sel, buf.strip()))
                elif sel.startswith('@keyframes') or (stack and stack[-1].startswith('@keyframes')):
                    pass
            buf = ''
        else:
            buf += c
        i += 1
    return out
def bal(s, i, o='(', c=')'):
    d = 0
    for j in range(i, len(s)):
        if s[j] == o: d += 1
        elif s[j] == c:
            d -= 1
            if d == 0: return s[i:j+1]
    return s[i:]
def params(html):
    css = ''.join(re.findall(r'<style>(.*?)</style>', html, flags=re.S))
    js = ''.join(re.findall(r'<script>(.*?)</script>', html, flags=re.S))
    out = Counter()
    for ctx, sel, body in css_rules(css):
        for d in body.split(';'):
            if ':' in d:
                p, v = d.split(':', 1); p = p.strip()
                if p.startswith(('transition', 'animation')):
                    out[('css', ctx, sel.strip(), p, re.sub(r'\s+', ' ', v.strip()))] += 1
    for n, b in re.findall(r'@keyframes\s+([\w-]+)\s*\{((?:[^{}]*\{[^{}]*\})*)\s*\}', css):
        out[('keyframes', n, re.sub(r'\s+', '', b))] += 1
    for m in re.finditer(r'\.animate\(', js):
        out[('animate', re.sub(r'\s+', '', bal(js, m.end() - 1)))] += 1
    for m in re.finditer(r'\btween\(', js):
        a = bal(js, m.end() - 1); out[('tween', a[:a.find(',', a.find(',') + 1)] if a.count(',') > 1 else a)] += 1
    for m in re.finditer(r'\bbz\(([^)]*)\)', js): out[('bezier', m.group(1))] += 1
    for m in re.finditer(r'--(sp|ea|ez)\s*:\s*([^;}]+)', css): out[('var', m.group(1), m.group(2).strip())] += 1
    for m in re.finditer(r'setTimeout\(', js):
        a = bal(js, m.end() - 1); n = re.search(r',\s*(\d+)\)$', a)
        out[('timer', n.group(1) if n else '?')] += 1
    for m in re.finditer(r'\bdur\s*\?\s*\d+|\bopen\s*\?\s*\d+\s*:\s*\d+|inst\?0:\d+', js): out[('dur', m.group(0))] += 1
    return out
if __name__ == '__main__':
    A = params(open(sys.argv[1], encoding='utf-8').read()); B = params(open(sys.argv[2], encoding='utf-8').read())
    rem, add = A - B, B - A
    kinds = Counter(k[0] for k in A.elements())
    print('before:', dict(kinds), ' total', sum(A.values()))
    print('after :', dict(Counter(k[0] for k in B.elements())), ' total', sum(B.values()))
    print('REMOVED/CHANGED:', sum(rem.values())); [print('  -', k) for k in rem]
    print('ADDED:', sum(add.values())); [print('  +', k) for k in add]
    if len(sys.argv) > 3: json.dump({'removed': [list(k) for k in rem], 'added': [list(k) for k in add], 'before': dict(kinds), 'total': sum(A.values())}, open(sys.argv[3], 'w'), ensure_ascii=False, indent=1)
