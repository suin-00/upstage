"""Studio 실행 결과(JSON)와 정답지를 비교한다.

사용법: python3 compare.py results/   (results/case_XX.json 파일들)
비교 대상: applicant_name, criteria_source, required_documents, rules, submitted_documents,
          missing_documents, checks(행 단위), result
제외: review_reasons, request_message (자유 문장)
"""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SET_FIELDS = ['required_documents', 'submitted_documents', 'missing_documents']
SCALAR_FIELDS = ['applicant_name', 'criteria_source', 'result']
CHECK_COLS = ['page', 'rule', 'visibility', 'status']


def norm(v):
    return v.strip() if isinstance(v, str) else v


def rule_set(rules):
    return {(norm(r.get('document_type')), norm(r.get('field')), norm(r.get('rule'))) for r in rules or []}


def check_map(checks):
    return {(norm(c.get('document_type')), norm(c.get('field')), norm(c.get('person_name'))): c for c in checks or []}


def compare(ans, out):
    rep, ok, total = [], 0, 0
    for f in SCALAR_FIELDS:
        total += 1
        if norm(ans.get(f)) == norm(out.get(f)):
            ok += 1
        else:
            rep.append(f'{f}: 정답={ans.get(f)!r} 출력={out.get(f)!r}')
    for f in SET_FIELDS:
        total += 1
        a, o = set(ans.get(f) or []), set(out.get(f) or [])
        if a == o:
            ok += 1
        else:
            rep.append(f'{f}: 누락={sorted(a - o)} 추가={sorted(o - a)}')
    total += 1
    a, o = rule_set(ans.get('rules')), rule_set(out.get('rules'))
    if a == o:
        ok += 1
    else:
        rep.append(f'rules: 누락={sorted(a - o)} 추가={sorted(o - a)}')
    am, om = check_map(ans.get('checks')), check_map(out.get('checks'))
    for k, ac in am.items():
        oc = om.get(k)
        for col in CHECK_COLS:
            total += 1
            if oc is not None and norm(oc.get(col)) == norm(ac.get(col)):
                ok += 1
            elif oc is None:
                if col == 'page':
                    rep.append(f'checks{k}: 행 없음')
            else:
                rep.append(f'checks{k}.{col}: 정답={ac.get(col)!r} 출력={oc.get(col)!r}')
    for k in om.keys() - am.keys():
        total += 1
        rep.append(f'checks{k}: 정답에 없는 행')
    return ok, total, rep


def main(result_dir):
    grand_ok = grand_total = 0
    result_hits = 0
    files = sorted(f for f in os.listdir(result_dir) if f.startswith('case_') and f.endswith('.json'))
    for fn in files:
        cid = fn[:-5]
        ans = json.load(open(os.path.join(ROOT, 'dataset', cid, 'answer.json'), encoding='utf-8'))
        out = json.load(open(os.path.join(result_dir, fn), encoding='utf-8'))
        ok, total, rep = compare(ans, out)
        grand_ok += ok
        grand_total += total
        result_hits += ans['result'] == out.get('result')
        mark = '✓' if not rep else '✗'
        print(f'{mark} {cid}: {ok}/{total}  최종판정 정답={ans["result"]} 출력={out.get("result")}')
        for r in rep:
            print('    -', r)
    if grand_total:
        print(f'\n항목 정확도 {grand_ok}/{grand_total} = {grand_ok / grand_total:.1%}')
        print(f'최종 판정 일치 {result_hits}/{len(files)}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'results'))
