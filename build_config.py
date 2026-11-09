"""정보공개 문서 개인정보 가림 점검 워크플로우 설정 생성기 (Studio 설정 #20).

원본 PDF를 한 번 실행하면 점검과 공개본 만들기가 함께 돈다.
  Parse(OCR 강제, 좌표)
  → Classify(분할, 겹침 허용: 같은 쪽 전체를 "점검용"·"공개본용" 두 조각으로 복제)
      ├ 점검용   → Extract 점검(disclosure_check_schema, 고급형) → Validate(검증-1) → Instruct 판정(instruct-default)
      └ 공개본용 → Extract 문서 마스킹하기(disclosure_mask) → Instruct 가림 처리 내역서(processing_log)
  → Merge(병합-1) → Instruct 최종 처리 결과(final_report: 판정 + 자동 가림 대조 + 담당자 처리 항목)
Studio는 한 경로에 Extract를 하나만 허용해서(마스킹도 Extract) Classify 분할로 갈래를 나눴다.
겹침 허용(allowOverlap)은 편집기 화면에 없는 설정이라, Studio에서 Classify 노드를 고치면 풀릴 수 있다.

workflow/정보공개점검_workflow_config.json : Studio '워크플로우 설정 가져오기'용 (설정 #20 내보내기와 같은 내용)
workflow/정보공개점검_extract_schema.json  : 점검 추출 항목만
"""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'workflow')
NAME = '당신의눈동자에치얼스_미션2_정보공개 문서 개인정보 가림 점검'

DOC = ('문서 코드: decision_notice(정보공개 결정통지서), complaint_form(민원 신청서), reply_letter(민원 회신문·처리 결과 '
       '알림), id_card_copy(신분증 사본), site_inspection_report(현장 조사보고서)')
FIELD = ('항목 코드: name(민원인·제3자 등 개인의 성명. 영문 성명 포함), resident_number(주민등록번호), address(개인 주소), '
         'phone(개인 연락처·전화번호), account_number(계좌번호·금융계좌), photo(인물사진·신분증 사진), '
         'official_name(직무를 수행한 담당 공무원의 성명·직위, 예: "도로과 주무관 OOO")')
FORM = ('형태 코드: text(인쇄된 글자. 영문 성명도 text), handwriting(자필 서명란의 손글씨 서명), seal(붉은 원형 개인 '
        '인장·도장), photo(인물사진)')
RULE = '규칙 코드: mask(비공개라 가려야 함), keep(공개 항목이라 가리면 안 됨)'
ITEMS = 'name, resident_number, address, phone, account_number, photo'


def s(desc):
    return {'type': 'string', 'description': desc}


def arr(desc):
    # Studio는 문자열 목록의 설명을 items.description만 쓴다.
    return {'type': 'array', 'items': s(desc), 'description': ''}


SCHEMA = {'type': 'object', 'properties': {
    'request_number': s('정보공개 결정통지서의 청구 접수번호를 그대로 적는다(예: 공개접수-2026-4101, 2026-가상-0412). 결정통지서가 '
                        '없으면 빈 문자열 "".'),
    'criteria_source': s('가림 기준. 묶음에 정보공개 결정통지서가 있으면 decision_notice, 없으면 default(기본 항목).'),
    'rules': {'type': 'array',
              'description': '가림 규칙을 항목마다 한 행씩 적는다. document_type은 모두 all. 결정통지서의 "비공개 대상"·"비공개 '
                             '부분"에 적힌 항목은 rule=mask: 성명(민원인·제3자 성명, 서명·도장 포함)은 name, 주민등록번호는 '
                             'resident_number, 주소는 address, 연락처·전화번호는 phone, 금융계좌·계좌번호는 account_number, '
                             '인물사진·신분증 사진은 photo. "공개 가능 정보"·"공개 부분"에 적힌 직무 수행 공무원의 성명·직위는 '
                             'official_name rule=keep(민원인 성명이 공개로 적혀 있으면 name도 keep). 비공개 목록에 없는 항목은 '
                             '행을 만들지 않는다(예: 금융계좌가 없으면 account_number 행 없음). "그 밖의 내용"·"처리 경과" 같은 '
                             f'일반 문장은 행으로 만들지 않는다. 결정통지서가 없으면 기본 항목 7행: {ITEMS}는 mask, '
                             'official_name은 keep.',
              'items': {'type': 'object', 'properties': {
                  'document_type': s('항상 all'),
                  'field': s(FIELD),
                  'rule': s(RULE)}}},
    'submitted_documents': arr('묶음에 들어 있는 문서 코드(중복 없이 쪽 순서대로). 결정통지서도 포함한다. ' + DOC),
    'missing_documents': arr('결정통지서의 "공개 예정 자료"·"공개 대상 문서"에 적힌 문서 중 묶음에 없는 문서 코드. 다 있거나 '
                             '결정통지서가 없으면 빈 목록. ' + DOC),
    'checks': {'type': 'array',
               'description': '결정통지서를 뺀 문서에서 rules 항목이 나오는 곳마다 한 행씩 적는다. 표의 라벨 칸(민원인 성명·'
                              '성명(영문)·수신자(민원인)·주민등록번호·주소·연락처·수신자 연락처·계좌번호·인물사진·담당 공무원 '
                              '성명·직위·접수 담당 등)과 자필 서명란, 개인 인장, 본문 속 제3자 성명·계좌번호가 대상이다. 문서에 '
                              '없는 칸은 만들지 않는다. 라벨 칸은 검은 박스나 흰 덮개로 덮여 있어도 빼지 않고 hidden으로 적는다. '
                              '같은 쪽·항목·형태가 여러 곳에 나오면 가림 상태(visibility)가 같으면 한 행, 다르면 상태마다 한 행씩 '
                              '적는다(예: 국문 성명은 가려지고 영문 성명은 보이면 name·text 두 행, 민원인 성명은 가려지고 본문의 '
                              '제3자 성명은 보이면 name·text 두 행). 신분증 주소 두 줄처럼 상태가 같으면 한 행이다. 기관장 명의, '
                              '"기관" 직인, 신분증 발급기관은 개인정보가 아니므로 행을 만들지 않는다. rules에 없는 항목은 보여도 '
                              '행을 만들지 않는다. 문장 중간의 가림 박스처럼 무엇을 가렸는지 라벨·위치로 알 수 없는 박스는 행을 '
                              '만들지 않고 review_reasons에 적는다.',
               'items': {'type': 'object', 'properties': {
                   'document_type': s(DOC),
                   'page': {'type': 'number', 'description': '그 항목이 있는 쪽 번호(묶음 PDF 전체 기준, 1부터)'},
                   'field': s(FIELD),
                   'form': s(FORM),
                   'rule': s('rules에서 이 항목에 해당하는 규칙(mask 또는 keep)'),
                   'visibility': s('이미지에서 그 자리가 사람 눈에 어떻게 보이는지. rule과 상관없이 아래 순서로 정한다. '
                                   '① 검은 박스, 흰 덮개(배경과 비슷한 흰 사각형에 옅은 회색 테두리만 남고 글자 획이 하나도 '
                                   '안 보이는 칸), * 기호로 값 전체가 안 보이면 hidden. 덮개 아래 글자를 읽을 수 없다고 '
                                   'unreadable로 적지 않는다. ② 박스·*·○가 값의 일부만 덮고 값의 숫자·글자가 하나 이상 실제로 '
                                   '읽히면 partial(예: 주민등록번호 앞자리와 뒷자리 첫 숫자만 보임, "서○○"처럼 성만 보임). 값 전체가 '
                                   '덮이고 옆의 "귀하"·라벨·은행명(예: "가상은행" 뒤 번호가 박스로 덮임)처럼 값이 아닌 글자만 보이면 '
                                   'partial이 아니라 hidden. 색이 조금 다른 박스 두 개 이상이 이어 붙어 값을 덮은 경우도 숫자·글자가 '
                                   '하나도 안 보이면 hidden. ③ 덮개 없이 값이 '
                                   '읽히면 full(반투명 형광펜 아래로 비치는 글자도 full). ④ 덮개 없이 글자 획이 흐리게 번져 '
                                   '보이지만 읽을 수 없으면 unreadable. 옅은 회색으로 뿌옇게 번져 경계가 흐릿한 자리도 '
                                   'unreadable이다(덮개는 검은색이나 흰색이고 경계가 또렷하다). 블러는 덮개가 아니므로 hidden으로 '
                                   '적지 않는다. ⑤ 칸은 '
                                   '있지만 값이 "(기재 없음)"처럼 비어 있으면 absent.'),
                   'status': s('판정. rule=mask: full·partial → auto_masked, hidden·absent → ok, unreadable → 검토 필요. '
                               'rule=keep: full → ok, partial·hidden → over_masked, unreadable·absent → 검토 필요.')}}},
    'review_reasons': arr('수정 필요·검토 필요의 근거를 빠짐없이 한 줄씩, 문서·쪽·항목·이유를 넣어 적는다. 이 값은 checks보다 '
                          '먼저 적히므로 문서 이미지에서 직접 아래 순서로 확인한다. ① 번짐: 결정통지서를 뺀 문서의 성명·'
                          '주민등록번호·주소·연락처·계좌번호 값 자리를 하나씩 보고, 검은 박스·흰 덮개·*가 아니라 뿌옇게 번진 회색 얼룩(블러)이라 글자를 읽을 수 없는 칸이 있으면 '
                          '"[쪽]쪽 [문서] [항목]: 번져서 판독할 수 없음"을 적는다. 블러는 가린 것으로 보지 않는다. 스캔이 '
                          '흐리거나 배경이 회색이어도 글자가 읽히면 번짐이 아니다. ② 결정통지서의 공개 예정 자료 중 빠진 문서. '
                          '③ 공개 항목 가림: 민원 회신문·현장 조사보고서의 "담당 공무원"·"담당"·"담당자"·"작성자"·"접수 담당" 칸(직무 '
                          '수행 공무원의 성명·직위)과 결정통지서가 공개로 정한 항목을 하나씩 보고, 검은 박스·흰 덮개·*로 가려져 있으면 '
                          '"[쪽]쪽 [문서] official_name: 공개 항목이 가려짐"을 적는다. 이름·직위 글자가 읽히면 가려진 것이 아니므로 '
                          '적지 않는다. 위아래 다른 칸(민원인 연락처 등)의 박스는 이 칸의 가림으로 보지 않는다. ④ 무엇을 가렸는지 알 수 없는 가림 박스. '
                          '⑤ 결정통지서 없음(기본 항목으로 점검). ⑥ 개인을 추정할 수 있는 간접 단서(민원인·제3자의 가게·직업·지역·'
                          '연령 조합, 근무처 등 비공개 항목이 아닌 서술). 민원이 가리키는 장소(신고한 도로·학교 앞·공원·공사장)와 처리 '
                          '내용은 단서가 아니다. 노출된 성명·주소·연락처 같은 비공개 항목(auto_masked)은 자동으로 가리므로 단서나 사유로 적지 않는다. 개인정보의 실제 값은 '
                          '적지 않는다. 사유가 없으면(공개 가능) 빈 목록.'),
    'result': s('최종 판정. 이 값은 checks보다 먼저 적히므로 checks를 기다리지 말고, 바로 앞의 review_reasons와 문서 이미지를 '
                '보고 아래 순서로 정한다. ① 결정통지서의 공개 예정 자료 중 묶음에 없는 문서가 있으면 "수정 필요". ② 공개 항목이 '
                '검은 박스·흰 덮개·*로 가려진 곳이 하나라도 있으면 "수정 필요"(예: "담당 공무원 성명·직위"·"접수 담당"·"담당" '
                '칸이 가려짐, 통지서가 민원인 성명을 공개로 정했는데 성명·서명이 가려짐). ③ 아니고 다음 중 하나라도 있으면 '
                '"검토 필요": 비공개 항목 값 자리가 검은 박스·흰 덮개·*가 아니라 뿌옇게 번진 회색 얼룩(블러)이라 글자를 읽을 수 없는 칸(블러는 가림으로 인정하지 않는다), 무엇을 가렸는지 '
                '알 수 없는 가림 박스, 결정통지서 없음, 개인을 추정할 수 있는 간접 단서(비공개 항목이 아닌 서술). ④ 나머지는 '
                '"공개 가능". review_reasons가 하나라도 있으면 "공개 가능"이 아니다. 비공개 항목이 가려져 있거나 비어 있는("기재 '
                '없음") 것은 정상이고, 비공개 항목이 노출된 것은 자동으로 가릴 대상(auto_masked)일 뿐이라 수정 필요나 검토 '
                '필요의 이유가 되지 않는다(노출만 있으면 공개 가능). 흰 덮개·*로 가린 것은 번진 것이 아니다.'),
}}

SYSTEM_PROMPT = (
    '이 PDF는 정보공개 청구 1건의 공개 준비 문서 묶음이다. 스캔 품질이 낮은 문서도 들어온다. 먼저 쪽마다 개인정보 칸(성명·주민등록번호·주소·연락처·계좌번호·사진)의 값 자리를 '
    '하나씩 보고 가림(검은 박스·흰 덮개·*), 노출(또렷한 글자), 번짐(뿌옇게 번진 회색 얼룩이라 읽을 수 없음), 빈칸(기재 없음) '
    '중 무엇인지 정한다. 번짐은 가림이 아니므로 하나라도 있으면 review_reasons에 적고 result는 검토 필요다(빠진 문서·공개 '
    '항목 가림이 있으면 수정 필요가 우선). 정보공개 결정통지서가 있으면 그 "비공개 대상"과 "공개 가능 정보"가 '
    '기준이고, 없으면 기본 항목(성명·주민등록번호·주소·연락처·계좌번호·사진은 가림, 직무를 수행한 공무원의 성명·직위는 '
    '공개)이 기준이다. 결정통지서마다 공개 범위가 다를 수 있으니 묶음에 든 통지서를 그대로 따른다. 결정통지서 외의 민원 '
    '신청서, 민원 회신문, 신분증 사본, 현장 조사보고서가 공개 대상 문서다. 가려졌는지는 OCR 글자가 아니라 이미지에서 사람 '
    '눈에 보이는 대로 판단한다. 검은 박스, 흰 덮개·수정테이프 자국, 별표(*)가 늘어선 값은 가린 것이다. 반투명 형광펜 아래로 '
    '글자가 읽히면 가리지 않은 것이다. 성명은 형태와 위치마다 따로 본다. 국문 성명이 가려져도 영문 성명, 자필 서명, 개인 '
    '인장, 본문 속 제3자 성명이 보이면 그 자리는 full이다. 흐림(블러)은 덮개가 아니다. 글자가 흐리게 번져 읽을 수 없으면 '
    'unreadable이며, 이를 가려진 것으로 바꾸지 않는다. 기관장 명의와 기관 직인은 개인정보가 아니다. 가린 부분의 원래 내용은 '
    '추측하지 않고, 라벨과 위치로 어떤 항목인지 정한다. 계좌번호는 숫자 부분만 값으로 본다. 은행명(예: 가상은행)은 값이 아니므로 '
    '숫자가 모두 가려지고 은행명만 보이면 hidden이다. 개인정보의 실제 값은 어떤 필드에도 적지 않는다. checks는 rules에 있는 '
    '항목만 넣고, 같은 쪽·항목·형태라도 가림 상태가 다르면 상태마다 한 행으로 적는다.')

INSTRUCT_PROMPT = "너는 공공기관 정보공개 담당자가 문서를 공개하기 전에 개인정보 가림을 점검하도록 돕는 도우미다. 앞 단계의 추출 결과(missing_documents, checks, review_reasons, result)와 검증 신호등(빨강=수정 필요, 노랑=검토 필요, 초록=공개 가능)을 보고 최종 판정을 하나 고른 뒤, 담당자가 처리할 순서대로 한국어 안내문을 만든다.\n\n판정 규칙\n① missing_documents가 있거나 checks의 status에 over_masked가 있으면 수정 필요(빨강).\n② 아니고 checks의 status에 검토 필요가 있거나 review_reasons가 있으면 검토 필요(노랑).\n③ 나머지는 공개 가능(초록).\n\n출력 순서\n1. 첫 줄: \"판정: 공개 가능\", \"판정: 수정 필요\", \"판정: 검토 필요\" 중 하나.\n2. 둘째 줄: \"처리 우선순위: 긴급/높음/보통/없음\" 중 하나.\n- 긴급: 노출된 주민등록번호, 계좌번호 또는 사진이 auto_masked에 있음.\n- 높음: 노출된 주소·전화번호·성명이 auto_masked에 있거나, missing_documents·over_masked·판독 불가 항목이 있음.\n- 보통: 결정통지서 없음, 간접 식별 단서 등 담당자 검토 사유만 있음.\n- 없음: 별도 조치가 없음.\n3. auto_masked가 하나라도 있으면 \"공개 조건: 아래 자동 가림 대상을 실제로 가리고 재점검한 뒤 공개\"라고 쓴다. auto_masked가 없으면 \"공개 조건: 담당자 최종 확인 후 공개\"라고 쓴다. 이 판정은 최종 반출 승인이 아니며, 실제 파일 마스킹이 끝났다고 표현하지 않는다.\n4. 필요한 절만 아래 순서로 쓴다.\n[자동 가림 대상] auto_masked 항목을 한 줄씩 쓴다. 형식은 \"- [긴급/높음/보통] [문서] [쪽]쪽 [항목]([형태])\"이다. 주민등록번호·계좌번호·사진을 먼저, 주소·전화번호를 다음, 성명을 마지막에 둔다.\n[재제출 요청] missing_documents와 over_masked 항목을 한 줄씩 쓴다.\n[담당자 확인] 검토 필요 항목과 review_reasons를 한 줄씩 쓴다.\n[공개본] auto_masked가 하나라도 있으면 \"같은 실행의 공개본 결과에서 주민등록번호·주소·전화번호·계좌번호를 가린 공개본 PDF와 가림 처리 내역서를 받을 수 있습니다. 성명·사진은 직접 가려 주세요.\"라고 쓴다.\n\n세부 문구\n- missing_documents의 각 문서: \"- [문서]가 빠져 있습니다. 결정통지서의 공개 대상 문서이니 추가해 주세요.\"\n- status가 over_masked인 항목: \"- [문서] [쪽]쪽의 [항목]이 가려져 있습니다. 결정통지서상 공개 항목이니 원본에서 다시 준비해 주세요.\"\n- status가 검토 필요인 항목: \"- [문서] [쪽]쪽의 [항목]을 읽을 수 없습니다. 원본을 확인해 직접 처리해 주세요.\"\n- review_reasons의 결정통지서 없음이나 간접 단서는 내용을 쓰고 \"직접 확인해 주세요.\"를 붙인다.\n- 코드는 한국어로 바꾼다: decision_notice=결정통지서, complaint_form=민원 신청서, reply_letter=민원 회신문, id_card_copy=신분증 사본, site_inspection_report=현장 조사보고서, name=성명, resident_number=주민등록번호, address=주소, phone=전화번호, account_number=계좌번호, photo=사진, official_name=담당 공무원 성명·직위, text=글자, handwriting=자필 서명, seal=도장.\n- 조사는 앞 단어 받침에 맞게 하나만 쓴다. 이(가)처럼 괄호로 쓰지 않는다.\n- 개인정보의 실제 값은 절대 쓰지 않는다. 인사말, 중복 설명, 근거 없는 추측은 붙이지 않는다."  # 팀이 고친 안내문(설정 #7) + [공개본] 줄

SUMMARY_PROMPT = ('한국어로 2~3문장으로 요약하세요. 신호등 결과와 그 이유(빠진 공개 대상 문서, 공개 항목인데 가린 항목, 읽을 수 '
                  '없는 항목, 결정통지서 없음·간접 단서)를 문서 이름과 쪽까지 적으세요. auto_masked 항목은 자동으로 가린다고 '
                  '안내하세요. 개인정보의 실제 값은 쓰지 마세요.')

EXTRACT = 'disclosure_check_schema'
VALIDATE = '검증-1'
INSTRUCT = 'instruct-default'
ENUM = ['공개 가능', '수정 필요', '검토 필요']


def L(field, **kw):
    return dict(nodeType='extract', nodeName=EXTRACT, field=field, **kw)


VALIDATE_CHECKS = [
    dict(name='공개 대상 문서 누락 없음', severity='error', condition=dict(left=L('missing_documents'), operator='empty')),
    dict(name='공개할 정보 가림 없음', severity='error',
         condition=dict(left=L('checks', rowField='status', scope='all'), operator='matches',
                        right={'const': '^(ok|auto_masked|검토 필요)$'})),
    dict(name='판독 불가 항목 없음', severity='warning',
         condition=dict(left=L('checks', rowField='status', scope='all'), operator='neq', right={'const': '검토 필요'})),
    dict(name='결정통지서 기준 확인', severity='warning',
         condition=dict(left=L('criteria_source'), operator='eq', right={'const': 'decision_notice'})),
    dict(name='검토 사유 없음', severity='warning', condition=dict(left=L('review_reasons'), operator='empty')),
]


def layout():
    cols = [dict(name=k, source='root') for k, v in SCHEMA['properties'].items()
            if not (v['type'] == 'array' and v['items']['type'] == 'object')]
    for g in ('rules', 'checks'):
        cols += [dict(name=k, source='group_table', groupTableKey=g)
                 for k in SCHEMA['properties'][g]['items']['properties']]
    return dict(version=1, columns=cols)



# ── 공개본 갈래: 문서 마스킹하기(Extract mask 모드) ──
MASK = 'disclosure_mask'
LOG = 'processing_log'
COMMON = ('문서에 보이는 글자 그대로(띄어쓰기·하이픈 포함) 값만 적는다. 라벨 글자(예: "민원인 주소", "연락처")는 넣지 않는다. '
          '이미 검은 박스·흰 덮개·*로 가려져 안 보이는 값과 "(기재 없음)"은 넣지 않는다. 결정통지서 쪽의 글자는 넣지 않는다.')
FIELDS = {
    'resident_number': '민원 신청서·민원 회신문·신분증 사본·현장 조사보고서에 보이는 주민등록번호. 일부만 보이면 보이는 부분만 그대로 적는다'
                       '(예: 900101-1234567, 880214-2). ' + COMMON,
    'address': '민원인·제3자 등 개인의 주소(도로명·지번·동·호수). 주소가 두 줄이면 줄마다 하나씩 적는다. 기관 주소, 민원이 가리키는 장소'
               '(신고한 도로·공원·학교 앞 등)는 넣지 않는다. ' + COMMON,
    'phone': '민원인 등 개인의 연락처·전화번호(예: 010-0000-0000). 기관 대표번호·담당 부서 전화는 넣지 않는다. ' + COMMON,
    'account_number': '개인의 금융 계좌번호의 숫자 부분만 적는다(예: 110-0000-000000). 앞에 붙은 은행명(예: 가상은행)은 개인정보가 '
                      '아니므로 넣지 않는다. 숫자는 맨 앞 자리부터 끝까지 빠짐없이 적고, 숫자 사이에 띄어쓰기가 끼어 보여도'
                      '(예: 1 10-0000-000000) 그 띄어쓰기까지 그대로 한 값으로 적는다. ' + COMMON,
}
MASK_PROMPT = (
    '이 PDF는 정보공개 청구 1건의 공개 준비 문서 묶음이다. 공개본을 만들기 위해 결정통지서의 "비공개 대상"에 든 주민등록번호·주소·'
    '연락처·계좌번호가 결정통지서 밖의 문서(민원 신청서, 민원 회신문, 신분증 사본, 현장 조사보고서)에 보이는 곳을 빠짐없이 찾는다. '
    '결정통지서가 없으면 이 네 항목을 모두 비공개로 본다. 결정통지서가 어떤 항목을 공개로 정했으면 그 항목은 찾지 않는다. '
    '직무를 수행한 공무원의 성명·직위, 기관명·기관 주소·기관 전화·직인은 찾지 않는다. 성명·자필 서명·도장·사진은 이 단계에서 다루지 않는다. '
    '같은 값이 여러 쪽에 나오면 나올 때마다 적는다.'
)
LOG_PROMPT = "너는 정보공개 담당자를 돕는 도우미다. 앞 단계(문서 마스킹)가 찾아서 가린 값 목록과 문서를 보고, 공개본의 가림 처리 내역서를 한국어로 만든다.\n\n규칙\n- 개인정보의 실제 값(번호·주소·이름 등)은 절대 쓰지 않는다. 몇 건인지, 어느 문서·쪽인지, 어떤 모양이었는지만 쓴다(예: \"주민등록번호 1건, 앞 6자리와 뒷자리 전체\").\n- 항목 이름은 한국어로: resident_number=주민등록번호, address=주소, phone=전화번호, account_number=계좌번호.\n- 찾은 값이 없는 항목은 \"가린 곳 없음\"으로 쓴다.\n\n출력 형식\n1. 첫 줄: \"가림 처리 내역서\"\n2. \"[자동으로 가린 항목]\" 아래에 항목마다 한 줄: \"- [항목]: [건수]건 ([문서] [쪽]쪽, 모양)\". 문서·쪽을 알 수 없으면 생략한다.\n3. \"[자동 가림 대상이 아닌 항목]\" 아래에: \"- 성명·자필 서명·도장·사진은 자동으로 가리지 않았습니다. 결정통지서 기준으로 담당자가 확인해 주세요.\" 그리고 결정통지서가 공개로 정한 항목(예: 담당 공무원 성명·직위)이 있으면 \"- [항목]은 공개 항목이라 가리지 않았습니다.\"\n4. \"[다음 단계]\" 아래에: \"- 성명·사진·번진 칸 등 남은 항목은 같은 실행의 점검 결과를 보고 담당자가 처리하세요.\"\n인사말이나 다른 설명은 붙이지 않는다. "  # 끝의 NBSP는 Studio 편집 중 들어간 것(설정 #13과 같게 둠)

# ── 분할(Classify) ──
CLASSIFY = '분류-1'
CLASS_CHECK, CLASS_MASK = '점검용', '공개본용'
CLASS_DESC = ('정보공개 청구 1건의 문서 묶음 전체(정보공개 결정통지서와 민원 신청서·민원 회신문·신분증 사본·현장 조사보고서). '
              '쪽을 나누지 말고 1쪽부터 마지막 쪽까지 모두 하나의 문서로 넣는다.')
CLASSIFY_PROMPT = ('이 PDF는 정보공개 청구 1건의 문서 묶음이다. 쪽을 나누지 않는다. 1쪽부터 마지막 쪽까지 전체를 "점검용" 문서 하나로, '
                   '그리고 같은 전체를 "공개본용" 문서 하나로 각각 만든다. 두 문서는 같은 쪽 범위를 겹쳐서 가진다.')

# ── 병합 후 최종 처리 결과 ──
MERGE = '병합-1'
FINAL = 'final_report'
FINAL_PROMPT = "너는 공공기관 정보공개 담당자를 돕는 도우미다. 이 워크플로우는 같은 문서 묶음(원본)을 두 갈래로 동시에 처리했다. 점검 갈래(disclosure_check_schema 추출 결과와 instruct-default 판정)는 원본의 개인정보 가림 상태를 점검했고, 공개본 갈래(disclosure_mask와 processing_log)는 주민등록번호·주소·전화번호·계좌번호를 찾아 가린 공개본 PDF와 가림 처리 내역서를 만들었다. 두 결과를 서로 맞춰 보고 담당자에게 줄 최종 처리 결과를 한국어로 쓴다.\n\n출력 형식\n1. 첫 줄: 점검 갈래의 판정을 그대로 \"판정: 공개 가능\", \"판정: 수정 필요\", \"판정: 검토 필요\" 중 하나로 쓴다.\n2. \"[자동 가림 확인]\" 아래에 점검 결과 checks에서 status가 auto_masked이고 field가 resident_number·address·phone·account_number인 곳마다 한 줄씩 쓴다. 공개본 갈래가 같은 문서·쪽에서 같은 항목의 값을 가렸는지 맞춰 본다.\n- 가렸으면: \"- [문서] [쪽]쪽 [항목]: 가림 확인\"\n- 가린 값이 없으면: \"- [문서] [쪽]쪽 [항목]: 자동 가림 실패, 직접 가려 주세요\"\n공개본 갈래가 가렸는데 점검 결과에 같은 문서·쪽·항목의 auto_masked 행이 없으면 \"- [문서] [쪽]쪽 [항목]: 점검에서 노출로 보지 않은 곳을 가렸습니다. 공개본에서 확인해 주세요\"를 쓴다.\n해당하는 곳이 하나도 없으면 \"- 자동 가림 대상 없음\". 마지막 줄에 \"- 공개본 PDF는 이 실행의 공개본 결과에서 내려받을 수 있습니다.\"를 쓴다.\n3. \"[담당자가 직접 처리할 항목]\" 아래에 다음에 해당하는 것만 한 줄씩 쓴다.\n- 2번에서 \"자동 가림 실패\"인 곳: 같은 문장을 다시 쓴다.\n- checks의 status가 auto_masked이고 field가 name 또는 photo인 곳: \"- [문서] [쪽]쪽 [항목]([형태]): 직접 가려 주세요.\"\n- checks의 status가 검토 필요인 곳: \"- [문서] [쪽]쪽 [항목]: 읽을 수 없습니다. 원본을 확인해 직접 처리해 주세요.\"\n- missing_documents의 각 문서: \"- [문서]: 묶음에 없습니다. 추가해 주세요.\"\n- checks의 status가 over_masked인 곳: \"- [문서] [쪽]쪽 [항목]: 공개 항목인데 가려져 있습니다. 원본으로 다시 준비해 주세요.\"\n- review_reasons 중 결정통지서 없음이나 간접 단서만: 내용을 쓰고 \"직접 확인해 주세요.\"를 붙인다. 빠진 문서, 공개 항목 가림, 번짐·판독 불가 사유는 위 줄들과 겹치므로 review_reasons에서 다시 옮기지 않는다(같은 내용은 한 번만 쓴다).\nstatus가 ok인 곳과 rule이 keep인 공개 항목은 쓰지 않는다. 해당하는 것이 없으면 \"- 없음\". 일반적인 안내 문장은 덧붙이지 않는다.\n4. \"[다음 단계]\" 아래에 한 줄: 3번이 \"- 없음\"이면 \"- 공개본 PDF로 공개를 준비하세요.\", 아니면 \"- 위 항목을 처리한 뒤 공개본 PDF로 공개하세요.\"\n\n코드는 한국어로 바꾼다: decision_notice=결정통지서, complaint_form=민원 신청서, reply_letter=민원 회신문, id_card_copy=신분증 사본, site_inspection_report=현장 조사보고서, name=성명, resident_number=주민등록번호, address=주소, phone=전화번호, account_number=계좌번호, photo=사진, official_name=담당 공무원 성명·직위, text=글자, handwriting=자필 서명, seal=도장. review_reasons를 옮길 때도 코드를 한국어로 바꾼다.\n개인정보의 실제 값은 쓰지 않는다. 인사말이나 다른 설명은 붙이지 않는다."


def config():
    E = lambda i, s, t, cond=None: dict(id=f'e{i}', source=s, target=t, **({'condition': {'conditionName': cond}} if cond else {}))
    n = lambda t, name=None: {'nodeType': t, **({'name': name} if name else {})}
    edges = [E(0, n('parse'), n('classify', CLASSIFY)),
             E(1, n('classify', CLASSIFY), n('extract', EXTRACT), CLASS_CHECK),
             E(2, n('classify', CLASSIFY), n('extract', MASK), CLASS_MASK),
             E(3, n('extract', EXTRACT), n('validate', VALIDATE)),
             E(4, n('extract', MASK), n('instruct', LOG))]
    edges += [E(5 + i, n('validate', VALIDATE), n('instruct', INSTRUCT), c) for i, c in enumerate(('red', 'yellow', 'green'))]
    edges += [E(8, n('instruct', LOG), n('merge', MERGE))]
    edges += [E(9 + i, n('instruct', INSTRUCT), n('merge', MERGE), c) for i, c in enumerate(ENUM)]
    edges += [E(12, n('merge', MERGE), n('instruct', FINAL))]
    wc = {
        'workflow_name': NAME, 'pipelineType': 'instruct',
        'documentParseConfiguration': {
            'modelName': 'document-parse', 'mode': 'standard', 'ocrMode': 'force', 'lang': '',
            'chartRecognition': False, 'coordinates': True, 'mergeMultipageTables': False,
            'outputFormats': ['html', 'text'], 'base64Encoding': ['figure']},
        'documentClassifyConfiguration': {
            'modelName': '',
            'schema': {'type': 'json_schema', 'json_schema': {'name': 'document-classify', 'schema': {
                'type': 'string', 'oneOf': [{'const': CLASS_CHECK, 'description': CLASS_DESC},
                                            {'const': CLASS_MASK, 'description': CLASS_DESC}]}}},
            'customName': CLASSIFY, 'split': True,
            'splitCriteria': [{'criterion': '묶음 전체',
                               'description': '쪽을 나누지 않고 전체를 하나의 문서로 본다. 같은 전체를 점검용과 공개본용에 모두 넣는다.'}],
            'userSystemPrompt': CLASSIFY_PROMPT, 'allowOverlap': True},
        'informationExtractConfiguration': {
            'modelName': '',
            'confidenceThreshold': 0.9676,  # Studio가 가져오기 때 채우는 기본값(설정 #14부터 내보내기에 들어감)
            'schemas': [
                {'type': 'json_schema', 'json_schema': {'name': EXTRACT, 'schema': SCHEMA}, 'schemaLayout': layout(),
                 'mode': 'enhanced', 'modelName': '', 'nodeMode': 'extract', 'manyRowsThreshold': 50,
                 'manyRowsMaxRowsPerBatch': 400, 'manyRowsMaxConcurrent': 5, 'userSystemPrompt': SYSTEM_PROMPT},
                {'type': 'json_schema', 'json_schema': {'name': MASK, 'schema': {
                    'type': 'object',
                    'properties': {k: {'type': 'array', 'items': {'type': 'string'}, 'description': v} for k, v in FIELDS.items()}}},
                 'mode': 'standard', 'modelName': '', 'manyRowsThreshold': 50, 'manyRowsMaxRowsPerBatch': 400,
                 'manyRowsMaxConcurrent': 5, 'extractType': 'masking', 'nodeMode': 'mask',
                 'maskOutputFormat': ['pdf', 'image'], 'userSystemPrompt': MASK_PROMPT}],
            'categorySchemaMapping': {CLASS_CHECK: EXTRACT, CLASS_MASK: MASK}},
        'instructConfiguration': {
            'nodes': [{'name': LOG, 'modelName': '', 'prompt': LOG_PROMPT},
                      {'name': INSTRUCT, 'modelName': '', 'prompt': INSTRUCT_PROMPT, 'enumEnabled': True, 'enumValues': ENUM},
                      {'name': FINAL, 'modelName': '', 'prompt': FINAL_PROMPT}],
            'connectionMapping': {LOG: {'targetType': 'extract', 'schemaName': MASK}}},
        'pipelineEdges': edges,
        'validateChecksByName': {VALIDATE: VALIDATE_CHECKS},
        'validateSummaryPromptByName': {VALIDATE: SUMMARY_PROMPT},
    }
    return {'kind': 'studio.workflow-config-draft', 'schemaVersion': 4, 'exportedFrom': {'workflowName': NAME},
            'workflowConfig': wc}


def canon_sums(wc):
    """Studio 내보내기와 비교하려고 최상위 키마다 (길이, 코드포인트 합)을 낸다."""
    def canon(o):
        if isinstance(o, list):
            return [canon(x) for x in o]
        if isinstance(o, dict):
            return {k: canon(o[k]) for k in sorted(o)}
        return o
    out = {}
    for k in sorted(wc):
        s = json.dumps(canon(wc[k]), ensure_ascii=False, separators=(',', ':'))
        out[k] = (len(s), sum(map(ord, s)))
    return out


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, '정보공개점검_workflow_config.json')
    c = config()
    json.dump(c, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    json.dump({'type': 'json_schema', 'json_schema': {'name': 'document-schema', 'schema': SCHEMA}},
              open(os.path.join(OUT, '정보공개점검_extract_schema.json'), 'w', encoding='utf-8'), ensure_ascii=False,
              indent=2)
    print('wrote', path, os.path.getsize(path), 'bytes')
    if '--sums' in sys.argv:
        for k, v in canon_sums(c['workflowConfig']).items():
            print(k, *v)
