"""Studio 결과를 대회 형식 정답지(answer.json의 cases[].answer)와 비교한다.

사용법: python3 compare_answer.py ANSWER.json RESULTS_DIR
  RESULTS_DIR/<PDF 이름에서 .pdf를 뺀 것>.json 을 해당 케이스의 출력으로 읽는다.
비교: request_number, criteria_source, result, submitted_documents·missing_documents(집합), rules(집합),
      checks 행: (document_type, page, field, form)으로 묶고, 같은 묶음 안에서는 visibility가 같은 행끼리 먼저 짝짓는다.
      짝지은 행은 rule·visibility·status를 비교하고, 짝이 없는 행은 '행 없음'/'정답에 없는 행'으로 센다.
제외: review_reasons (자유 문장)
"""
import json, os, sys
from collections import defaultdict

SCALAR = ['request_number', 'criteria_source', 'result']
SETS = ['submitted_documents', 'missing_documents']
COLS = ['rule', 'visibility', 'status']


def n(v):
    return v.strip() if isinstance(v, str) else v


def gkey(c):
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
    ga, go = defaultdict(list), defaultdict(list)
    for c in ans.get('checks') or []:
        ga[gkey(c)].append(c)
    for c in out.get('checks') or []:
        go[gkey(c)].append(c)
    for k in sorted(set(ga) | set(go), key=str):
        A, O = list(ga.get(k, [])), list(go.get(k, []))
        pairs = []
        for a in A[:]:                      # 같은 visibility끼리 먼저
            m = next((o for o in O if n(o.get('visibility')) == n(a.get('visibility'))), None)
            if m is not None:
                pairs.append((a, m)); A.remove(a); O.remove(m)
        while A and O:                      # 남은 것끼리 순서대로
            pairs.append((A.pop(0), O.pop(0)))
        for a, o in pairs:
            for col in COLS:
                total += 1
                if n(o.get(col)) == n(a.get(col)):
                    ok += 1
                else:
                    rep.append(f'checks{k}.{col}: 정답={a.get(col)!r} 출력={o.get(col)!r}')
        for a in A:
            total += len(COLS)
            rep.append(f'checks{k}: 행 없음 (정답 {a["visibility"]}/{a["status"]})')
        for o in O:
            total += 1
            rep.append(f'checks{k}: 정답에 없는 행 ({o.get("visibility")}/{o.get("status")})')
    return ok, total, rep


def main(answer_path, d):
    spec = json.load(open(answer_path, encoding='utf-8'))
    g_ok = g_tot = hits = n_case = 0
    for case in spec['cases']:
        files = case['file'] if isinstance(case['file'], list) else [case['file']]
        stem = os.path.splitext(files[0])[0]
        p = os.path.join(d, stem + '.json')
        if not os.path.exists(p):
            print(f'- {case["case_id"]}: 결과 없음 ({stem}.json)')
            continue
        out = json.load(open(p, encoding='utf-8'))
        ans = case['answer']
        ok, tot, rep = compare(ans, out)
        n_case += 1
        g_ok += ok
        g_tot += tot
        hit = n(ans['result']) == n(out.get('result'))
        hits += hit
        print(f"{'✓' if ok == tot else '✗'} {case['case_id']}: {ok}/{tot}  판정 정답={ans['result']} 출력={out.get('result')}")
        for r in rep:
            print('    -', r)
    if g_tot:
        print(f'\n항목 정확도 {g_ok}/{g_tot} = {g_ok / g_tot:.1%} · 최종 판정 {hits}/{n_case}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
