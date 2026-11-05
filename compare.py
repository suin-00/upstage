"""Studio 실행 결과와 정답지를 비교한다.

사용법: python3 compare.py results_v1/
비교: request_number, criteria_source, result, submitted_documents, missing_documents, rules(집합),
      checks((document_type, page, field, form)를 키로 rule·visibility·status), 정답에 없는 행
제외: review_reasons (자유 문장)
"""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SCALAR = ['request_number', 'criteria_source', 'result']
SETS = ['submitted_documents', 'missing_documents']
COLS = ['rule', 'visibility', 'status']


def n(v):
    return v.strip() if isinstance(v, str) else v


def key(c):
    page = c.get('page')
    try:
        page = int(page)
    except (TypeError, ValueError):
        pass
    return (n(c.get('document_type')), page, n(c.get('field')), n(c.get('form')))


def compare(ans, out):
    ok = total = 0
    rep = []
    for f in SCALAR:
        total += 1
        if n(ans.get(f)) == n(out.get(f)):
            ok += 1
        else:
            rep.append(f'{f}: 정답={ans.get(f)!r} 출력={out.get(f)!r}')
    for f in SETS:
        total += 1
        a, o = set(ans.get(f) or []), set(out.get(f) or [])
        if a == o:
            ok += 1
        else:
            rep.append(f'{f}: 빠짐={sorted(a - o)} 더함={sorted(o - a)}')
    total += 1
    ra = {(n(r['document_type']), n(r['field']), n(r['rule'])) for r in ans.get('rules') or []}
    ro = {(n(r.get('document_type')), n(r.get('field')), n(r.get('rule'))) for r in out.get('rules') or []}
    if ra == ro:
        ok += 1
    else:
        rep.append(f'rules: 빠짐={sorted(ra - ro)} 더함={sorted(ro - ra)}')
    am = {key(c): c for c in ans.get('checks') or []}
    om = {key(c): c for c in out.get('checks') or []}
    for k, ac in am.items():
        oc = om.get(k)
        if oc is None:
            total += len(COLS)
            rep.append(f'checks{k}: 행 없음 (정답 {ac["visibility"]}/{ac["status"]})')
            continue
        for col in COLS:
            total += 1
            if n(oc.get(col)) == n(ac.get(col)):
                ok += 1
            else:
                rep.append(f'checks{k}.{col}: 정답={ac.get(col)!r} 출력={oc.get(col)!r}')
    for k in om.keys() - am.keys():
        total += 1
        rep.append(f'checks{k}: 정답에 없는 행 ({om[k].get("visibility")}/{om[k].get("status")})')
    return ok, total, rep


def main(d):
    g_ok = g_tot = hits = 0
    files = sorted(f for f in os.listdir(d) if f.startswith('case_') and f.endswith('.json'))
    for fn in files:
        ans = json.load(open(os.path.join(ROOT, 'answers', fn), encoding='utf-8'))
        out = json.load(open(os.path.join(d, fn), encoding='utf-8'))
        ok, tot, rep = compare(ans, out)
        g_ok += ok
        g_tot += tot
        hits += ans['result'] == out.get('result')
        print(f"{'✓' if not rep else '✗'} {fn[:-5]}: {ok}/{tot}  판정 정답={ans['result']} 출력={out.get('result')}")
        for r in rep:
            print('    -', r)
    if g_tot:
        print(f'\n항목 정확도 {g_ok}/{g_tot} = {g_ok / g_tot:.1%} · 최종 판정 {hits}/{len(files)}')


if __name__ == '__main__':
    main(sys.argv[1])
