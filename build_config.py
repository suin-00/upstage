"""블라인드 채용 셀프 점검 워크플로우 설정 생성기.

workflow/셀프점검_workflow_config.json : Studio '워크플로우 설정 가져오기'용
  Parse(OCR 강제) → Extract(고급형) → Validate → Instruct(결정: 통과/보완 필요/검토 필요)
  (Export 노드는 Studio에서 Instruct 뒤에 붙인다)
workflow/셀프점검_extract_schema.json : 추출 항목만
"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'workflow')
NAME = '당신의눈동자에치얼스_미션2_블라인드 채용 지원 서류 셀프 점검'

DOC = ('서류 코드: notice(채용 공고문·제출 안내문), masking_request(블라인드 가림 요청서), '
       'graduation_certificate(졸업증명서), transcript(성적증명서), license_copy(자격증·어학성적 사본), '
       'id_card_copy(신분증 사본)')
FIELD = ('항목 코드: school_name(학교명), student_id(학번), admission_date(입학일자), graduation_date(졸업일자), '
         'birth_date(생년월일), resident_number_back(주민등록번호 뒷자리), address(주소), photo(사진), name(성명), '
         'license_type(자격 종목), semester_year(성적표의 학기별 연도, 예: 2019학년도)')
FORM = ('형태 코드: text(글자로 쓴 값. 학교명이면 머리글 제목 위·앞의 학교 이름과 "총장"·"학사지원팀" 앞 서명란), '
        'logo(원형 로고·엠블럼), seal(서명란 옆 붉은 사각 직인), watermark(배경에 옅고 크게 비스듬히 찍힌 학교명), '
        'english(학교 이름 아래·옆의 영문 학교명), email(이메일 주소의 학교 도메인), photo(사진)')
RULE = '규칙 코드: mask(가려야 함), keep(확인용이라 가리면 안 됨)'


def s(desc):
    return {'type': 'string', 'description': desc}


def arr(desc):
    # Studio는 문자열 목록의 설명을 items.description만 쓴다.
    return {'type': 'array', 'items': s(desc), 'description': ''}


SCHEMA = {'type': 'object', 'properties': {
    'applicant_name': s('표시가 허용된 지원자 성명. 기준 문서가 성명을 가리라고 했으면(rules에 field=name, rule=mask가 '
                        '있으면) 빈 문자열 "". 어느 서류에서도 읽을 수 없으면 빈 문자열.'),
    'criteria_source': s('가림 기준 문서. 묶음에 채용 공고문·제출 안내문이 있으면 notice, 공고문 없이 블라인드 가림 '
                         '요청서만 있으면 masking_request.'),
    'rules': {'type': 'array',
              'description': '기준 문서에 적힌 블라인드 규칙을 (서류, 항목)마다 한 행씩 적는다. "졸업증명서·성적증명서: '
                             '학교명, 학번…"처럼 여러 서류에 함께 적힌 규칙은 서류마다 따로 행을 만든다. 가림 요청서는 '
                             '체크(✓)된 항목만 document_type=all, rule=mask로 적고 체크 안 된 항목은 넣지 않는다. '
                             '"학교명(로고·직인·영문 표기 포함)"은 school_name 한 행이다. 기준 문서에 없는 항목, '
                             '"적지 않은 항목은 가리지 않아도 된다" 같은 일반 문장은 행으로 만들지 않는다.',
              'items': {'type': 'object', 'properties': {
                  'document_type': s('규칙이 적용되는 서류 코드. 가림 요청서 규칙은 all. ' + DOC),
                  'field': s(FIELD),
                  'rule': s(RULE)}}},
    'submitted_documents': arr('묶음에 들어 있는 서류 코드(중복 없이 쪽 순서대로). 기준 문서(notice 또는 '
                               'masking_request)도 포함한다. ' + DOC),
    'missing_documents': arr('공고문이 제출하라고 한 서류 중 묶음에 없는 서류 코드. 없거나, 가림 요청서처럼 필수 서류를 '
                             '지정하지 않았으면 빈 목록. ' + DOC),
    'checks': {'type': 'array',
               'description': 'rules가 적용되는 제출 서류에서 그 항목이 나오는 곳을 (쪽, 항목, 형태)마다 한 행씩 적는다. '
                              '같은 쪽에 같은 항목·형태가 여러 번 나오면(예: 머리글과 서명란의 학교명) 한 행만 적고 '
                              '중복 행을 만들지 않는다. '
                              '학교명은 형태별로 따로 적는다. 졸업증명서는 학교명 글자(text)·로고(logo)·직인(seal)·'
                              '영문 표기(english)가 항상 있으므로 네 행을 모두 적고, 검은 박스나 흰 덮개 자국만 '
                              '남았으면 hidden이다. 워터마크(watermark)와 이메일(email)은 실제로 보일 때만 적는다. '
                              '성적증명서는 쪽마다 머리글 학교명(text)이 있다. 학교명은 형태마다 따로 판단한다: 로고·'
                              '이메일 등 다른 형태에 학교명이 보여도 text 자리가 가려졌으면 text는 hidden이다. rules에 '
                              '(서류, 항목) 조합이 없으면 그 항목이 보여도 행을 만들지 않는다(예: rules에 semester_year가 '
                              '없으면 학기 연도 행 없음). 기준 문서 자체는 넣지 않는다.',
               'items': {'type': 'object', 'properties': {
                   'document_type': s(DOC),
                   'page': {'type': 'number', 'description': '그 항목이 있는 쪽 번호(묶음 PDF 전체 기준, 1부터)'},
                   'field': s(FIELD),
                   'form': s(FORM),
                   'rule': s('rules에서 이 서류·항목에 해당하는 규칙(mask 또는 keep)'),
                   'visibility': s('이미지에서 그 형태 자리가 사람 눈에 어떻게 보이는지. rule과 상관없이 아래 순서로 '
                                   '정한다. ① 그 자리가 검은 박스, 흰 덮개(옅은 테두리만 남은 빈 칸), * 기호로 덮여 값이 '
                                   '안 보이면 hidden. 박스 아래 글자를 읽을 수 없다고 unreadable로 적지 않는다. '
                                   '② 박스가 값의 일부만 덮고 일부 글자가 보이면 partial(예: 주민등록번호 뒷자리 첫 숫자만 '
                                   '보임). 학교 이름이 박스로 다 덮이고 옆의 "성적증명서"·"총장"·"학사지원팀" 같은 다른 '
                                   '글자만 보이면 partial이 아니라 hidden이다. ③ 덮개 없이 값이 읽히면 full(반투명 '
                                   '형광펜 아래로 비치는 글자도 full). '
                                   '④ 덮개 없이 글자 자체가 흐리게 번져(블러) 읽을 수 없으면 unreadable. 블러는 덮개가 '
                                   '아니므로 hidden으로 적지 않는다. '
                                   'absent는 그 서류에 항목 자리 자체가 없을 때만 쓴다(졸업증명서의 학교명 네 형태는 '
                                   'absent로 적지 않는다).'),
                   'status': s('판정. rule=mask: full·partial → auto_masked, hidden → ok, unreadable·absent → 검토 필요. '
                               'rule=keep: full → ok, partial·hidden → over_masked, unreadable·absent → 검토 필요.')}}},
    'review_reasons': arr('직접 확인이 필요한 사항 한 줄씩: status가 검토 필요인 항목은 빠짐없이 하나씩(예: "자격증 사본 5쪽 자격 종목 판독 '
                          '불가"), 공고문 없이 가림 요청서만 있으면 "공고문이 없어 가림 요청서 기준으로만 점검함", 규칙에 '
                          '없지만 학교를 짐작할 수 있는 간접 단서(학교 주소·대표전화 등)가 보이면 그 서류와 쪽. 실제 값은 '
                          '적지 않는다. 없으면 빈 목록.'),
    'result': s('최종 판정. 순서대로 정한다. ① missing_documents가 하나라도 있거나 checks의 status에 over_masked가 '
                '하나라도 있으면 "보완 필요". ② 아니고 checks의 status에 "검토 필요"가 있거나 review_reasons가 하나라도 '
                '있으면 "검토 필요". ③ 나머지는 "통과". auto_masked는 에이전트가 자동으로 가리므로 지원자가 고칠 일이 아니고 '
                '보완 필요의 이유가 되지 않는다(auto_masked만 있으면 통과). 공고문이 없는 것도 보완 필요가 아니라 검토 필요다.'),
}}

SYSTEM_PROMPT = (
    '이 PDF는 지원자 한 명의 서류 묶음이다. 첫 쪽은 기준 문서(채용 공고문 또는 블라인드 가림 요청서)이고, 그 뒤는 지원자가 '
    '제출할 증빙서류다. 가려졌는지는 OCR 글자가 아니라 이미지에서 사람 눈에 보이는 대로 판단한다. 검은 박스, 흰 덮개·'
    '수정테이프 자국, 별표(*)가 늘어선 값은 가린 것이다. 반투명 형광펜 아래로 글자가 읽히면 가리지 않은 것이다. 학교명은 '
    '형태마다 따로 본다. 로고·영문 표기·직인·워터마크·이메일에 학교명이 보여도, 머리글·서명란의 학교 이름 글자가 덮여 '
    '있으면 text는 hidden이다. 흐림(블러)은 덮개가 아니다. 글자가 흐리게 번져 '
    '읽을 수 없으면 unreadable이며, 이를 가려진 것으로 바꾸지 않는다. 기준 문서가 요구하지 않은 항목은 판정하지 않는다. '
    '주민등록번호·학번 같은 개인정보의 실제 값은 어떤 필드에도 적지 않는다. checks는 rules에 있는 (서류, 항목)만 넣고, '
    '같은 쪽에서 같은 항목·형태는 여러 번 나와도 한 행으로 적는다.')

INSTRUCT_PROMPT = (
    '너는 블라인드 채용 지원 서류를 제출 전에 점검해 주는 도우미다. 앞 단계의 추출 결과(missing_documents, checks, '
    'review_reasons, result)와 검증 신호등(빨강=보완 필요, 노랑=검토 필요, 초록=통과)을 보고 최종 판정을 하나 고른 뒤, '
    '지원자가 할 일을 한국어로 안내한다. 판정은 순서대로 정한다: ① missing_documents가 있거나 checks의 status에 '
    'over_masked가 있으면 보완 필요(신호등 빨강). ② 아니고 checks의 status에 검토 필요가 있거나 review_reasons가 있으면 '
    '검토 필요(노랑). ③ 나머지는 통과(초록).\n\n안내 문구 규칙\n'
    '- 첫 줄: "판정: 통과", "판정: 보완 필요", "판정: 검토 필요" 중 하나.\n'
    '- missing_documents의 각 서류: "[서류]가 빠져 있습니다. 추가로 제출해 주세요."\n'
    '- status가 over_masked인 항목: "[서류] [쪽]쪽의 [항목]이 가려져 있습니다. [항목]이 보이는 사본을 다시 준비해 주세요."\n'
    '- status가 검토 필요인 항목: "[서류] [쪽]쪽의 [항목]을 읽을 수 없습니다. 더 선명한 사본으로 확인해 주세요."\n'
    '- review_reasons에 공고문 없음이나 간접 단서가 있으면 그 내용을 한 줄씩 안내한다.\n'
    '- status가 auto_masked인 항목은 "자동으로 가릴 항목: [서류] [쪽]쪽 [항목]" 형식으로 한 줄에 모아 쓴다. 지원자가 '
    '고칠 일은 아니다.\n'
    '- 코드는 한국어로 바꾼다: graduation_certificate=졸업증명서, transcript=성적증명서, license_copy=자격증 사본, '
    'id_card_copy=신분증 사본, school_name=학교명, student_id=학번, admission_date=입학일자, graduation_date=졸업일자, '
    'birth_date=생년월일, resident_number_back=주민등록번호 뒷자리, address=주소, photo=사진, name=성명, '
    'license_type=자격 종목, semester_year=학기별 연도, logo=로고, seal=직인, watermark=워터마크, english=영문 표기, '
    'email=이메일.\n'
    '- 조사는 앞 단어 받침에 맞게 하나만 쓴다(예: 성명이, 학번이, 사본이, 주소가, 사진이). 이(가)처럼 괄호로 쓰지 않는다.\n'
    '- 개인정보의 실제 값은 쓰지 않는다. 인사말이나 설명은 붙이지 않는다.')

SUMMARY_PROMPT = ('한국어로 2~3문장으로 요약하세요. 신호등 결과와 그 이유(빠진 서류, 가리면 안 되는데 가린 항목, 읽을 수 '
                  '없는 항목, 공고문 없음·간접 단서)를 서류 이름과 쪽까지 적으세요. auto_masked 항목은 자동으로 가린다고 '
                  '안내하세요. 개인정보의 실제 값은 쓰지 마세요.')

EXTRACT = 'blind_check_schema'
VALIDATE = '검증-1'
INSTRUCT = 'instruct-default'
EXPORT = '내보내기-1'
EXPORT_TABLE = 'tbl_857b809828ff478b9815a86b7c4cad29'  # Studio가 만든 컬렉션 테이블


def L(field, **kw):
    return dict(nodeType='extract', nodeName=EXTRACT, field=field, **kw)


VALIDATE_CHECKS = [
    dict(name='필수 서류 누락 없음', severity='error', condition=dict(left=L('missing_documents'), operator='empty')),
    dict(name='남겨야 할 정보 가림 없음', severity='error',
         condition=dict(left=L('checks', rowField='status', scope='all'), operator='matches',
                        right={'const': '^(ok|auto_masked|검토 필요)$'})),
    dict(name='판독 불가 항목 없음', severity='warning',
         condition=dict(left=L('checks', rowField='status', scope='all'), operator='neq', right={'const': '검토 필요'})),
    dict(name='채용 공고문 기준 확인', severity='warning',
         condition=dict(left=L('criteria_source'), operator='eq', right={'const': 'notice'})),
    dict(name='검토 사유 없음', severity='warning', condition=dict(left=L('review_reasons'), operator='empty')),
]


def layout():
    cols = [dict(name=k, source='root') for k, v in SCHEMA['properties'].items()
            if not (v['type'] == 'array' and v['items']['type'] == 'object')]
    for g in ('rules', 'checks'):
        cols += [dict(name=k, source='group_table', groupTableKey=g)
                 for k in SCHEMA['properties'][g]['items']['properties']]
    return dict(version=1, columns=cols)


def config():
    edges = [{'id': 'e0', 'source': {'nodeType': 'parse'}, 'target': {'nodeType': 'extract', 'name': EXTRACT}},
             {'id': 'e1', 'source': {'nodeType': 'extract', 'name': EXTRACT},
              'target': {'nodeType': 'validate', 'name': VALIDATE}}]
    for i, c in enumerate(('red', 'yellow', 'green')):
        edges.append({'id': f'e{i + 2}', 'source': {'nodeType': 'validate', 'name': VALIDATE},
                      'target': {'nodeType': 'instruct', 'name': INSTRUCT}, 'condition': {'conditionName': c}})
    for i, c in enumerate(('통과', '보완 필요', '검토 필요')):
        edges.append({'id': f'e{i + 5}', 'source': {'nodeType': 'instruct', 'name': INSTRUCT},
                      'target': {'nodeType': 'export', 'name': EXPORT}, 'condition': {'conditionName': c}})
    return {
        'kind': 'studio.workflow-config-draft', 'schemaVersion': 4,
        'exportedFrom': {'workflowName': NAME},
        'workflowConfig': {
            'workflow_name': NAME, 'pipelineType': 'instruct',
            'documentParseConfiguration': {
                'modelName': 'document-parse', 'mode': 'standard', 'ocrMode': 'force', 'lang': '',
                'chartRecognition': False, 'coordinates': True, 'mergeMultipageTables': False,
                'outputFormats': ['html', 'text'], 'base64Encoding': ['figure']},
            'informationExtractConfiguration': {
                'modelName': '',
                'schemas': [{
                    'type': 'json_schema', 'json_schema': {'name': EXTRACT, 'schema': SCHEMA},
                    'schemaLayout': layout(), 'mode': 'enhanced', 'modelName': '', 'nodeMode': 'extract',
                    'manyRows': True, 'manyRowsThreshold': 50, 'manyRowsMaxRowsPerBatch': 400,
                    'manyRowsMaxConcurrent': 5, 'userSystemPrompt': SYSTEM_PROMPT}],
                'categorySchemaMapping': {}, 'confidenceThreshold': 0.9676},
            'instructConfiguration': {'nodes': [{'name': INSTRUCT, 'modelName': '', 'prompt': INSTRUCT_PROMPT,
                                                 'enumEnabled': True,
                                                 'enumValues': ['통과', '보완 필요', '검토 필요']}],
                                      'connectionMapping': {}},
            'pipelineEdges': edges,
            'validateChecksByName': {VALIDATE: VALIDATE_CHECKS},
            'validateSummaryPromptByName': {VALIDATE: SUMMARY_PROMPT},
            'exportNodeNames': [EXPORT],
            'exportCollectionsByName': {EXPORT: {'tableKeys': {f'extract:{EXTRACT}': EXPORT_TABLE}}},
            'exportDestinationsByName': {},
        }}


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    json.dump(config(), open(os.path.join(OUT, '셀프점검_workflow_config.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    json.dump({'type': 'json_schema', 'json_schema': {'name': 'document-schema', 'schema': SCHEMA}},
              open(os.path.join(OUT, '셀프점검_extract_schema.json'), 'w', encoding='utf-8'), ensure_ascii=False,
              indent=2)
    print('system', len(SYSTEM_PROMPT), 'instruct', len(INSTRUCT_PROMPT),
          'config bytes', os.path.getsize(os.path.join(OUT, '셀프점검_workflow_config.json')))
