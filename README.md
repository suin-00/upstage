# 블라인드 채용 지원 서류 셀프 점검 에이전트

지원자가 채용 공고문(또는 블라인드 가림 요청서)과 증빙서류를 PDF 하나로 넣으면, 공고의 블라인드 기준대로
가려졌는지 한 번 점검해

- 가려야 하는데 남아 있는 정보 → **자동 가림 대상**으로 표시 (`auto_masked`, 그 밖에 문제가 없으면 **통과**)
- 남겨야 할 정보(성명·자격 종목 등)까지 가렸거나 필수 서류가 빠짐 → **보완 필요**
- 흐려서 읽을 수 없는 정보, 공고문 없이 요청서만 있음, 학교를 짐작할 수 있는 간접 단서 → **검토 필요**

를 판정합니다. U108(의무기록 개인정보 가림 점검) 카드를 참고해, 대상을 블라인드 채용 증빙서류로,
사용자를 심사 담당자에서 제출 전 지원자로 바꿨습니다.

## Upstage Studio 워크플로우

`당신의눈동자에치얼스_미션2_블라인드 채용 지원 서류 셀프 점검` (`agt_FqRXCSYhSnWtZxXHGNDGFp`, 설정 #6)

```
시작 → Parse(OCR 강제, 좌표 ON)
     → Extract "blind_check_schema" (고급형 = VLM, 사용자 시스템 프롬프트)
     → Validate "검증-1"  (Green / Yellow / Red 모두 →)
     → Instruct "instruct-default" (결정: 통과 / 보완 필요 / 검토 필요 + 안내 문구)
     → Export "내보내기-1" (Extract 결과를 컬렉션에 그대로 저장)
```

Validate 규칙

| 규칙 | 등급 | 조건 |
|---|---|---|
| 필수 서류 누락 없음 | 필수 | `missing_documents` 비어 있음 |
| 남겨야 할 정보 가림 없음 | 필수 | `checks.status` 모든 항목이 `^(ok\|auto_masked\|검토 필요)$` (over_masked 없음) |
| 판독 불가 항목 없음 | 선택 | `checks.status` 모든 항목 ≠ `검토 필요` |
| 채용 공고문 기준 확인 | 선택 | `criteria_source` = `notice` |
| 검토 사유 없음 | 선택 | `review_reasons` 비어 있음 |

→ 필수 실패 = Red(보완 필요), 선택 실패 = Yellow(검토 필요), 전부 통과 = Green(통과)

Studio는 **한 경로에 Extract 노드를 하나만** 둘 수 있어서, 실제로 가린 제출용 PDF를 만드는 자동 가림은
별도 워크플로우로 나눌 계획입니다(아래 '주의' 참고).

## 사용법

```bash
pip install -r requirements.txt

python3 gen_docs.py          # dataset/case_01~10.pdf, dataset/pages/*.png, answers/case_XX.json, dataset/manifest.json 생성
python3 build_types_xlsx.py  # 유형표 xlsx 생성 (dataset/manifest.json 필요)
python3 build_config.py      # workflow/*.json 다시 생성
python3 compare.py results   # results/case_XX.json(Studio Extract 결과 JSON)과 정답지 비교
```

- 한글 글꼴은 Linux(Noto CJK) → macOS(Apple SD Gothic Neo) → Windows(맑은 고딕) 순서로 찾습니다. 다른 글꼴을 쓰려면
  `MASKING_FONT`(필요하면 `MASKING_FONT_BOLD`, `MASKING_FONT_INDEX`) 환경변수로 경로를 지정하세요.
  Linux + Noto CJK 환경에서만 실행해 봤습니다.
- `compare.py`에 넣을 결과는 Studio 결과 패널의 JSON 탭 내용을 `results/case_01.json`처럼 케이스 이름으로 저장하면 됩니다.

## 파일

| 경로 | 내용 |
|---|---|
| `gen_docs.py` | 가상 서류 + 정답지 생성기 |
| `build_types_xlsx.py` | 유형표(문서마다 한 줄 + 유형·판정 요약 시트) 생성기 |
| `build_config.py` | 워크플로우 설정 JSON 생성기 |
| `compare.py` | Studio 결과 ↔ 정답지 비교 (항목 정확도, 최종 판정 일치) |
| `workflow/셀프점검_workflow_config.json` | 워크플로우 전체 설정(Export 포함). Studio ⋯ → **워크플로우 설정 가져오기**로 그대로 import |
| `workflow/셀프점검_extract_schema.json` | 추출 항목만 (Extract 노드 ⋯ → JSON 추출 항목 가져오기) |

`dataset/`, `answers/`, 결과 폴더, xlsx는 생성물이라 `.gitignore`로 제외했습니다. 스크립트를 실행하면 같은 데이터가 다시
만들어집니다. 모든 인물·학교·기관·번호는 가상이며 서류마다 "해커톤 테스트용 가상 문서" 표기가 있습니다.

## 출력 스키마 (snake_case 고정, 정답지와 같음)

```
applicant_name, criteria_source(notice|masking_request),
rules[{document_type, field, rule}],
submitted_documents[](기준 문서 포함), missing_documents[],
checks[{document_type, page, field, form, rule, visibility, status}],
review_reasons[], result(통과|보완 필요|검토 필요)
```
- `document_type`: `notice` / `masking_request` / `graduation_certificate` / `transcript` / `license_copy` / `id_card_copy` (가림 요청서 규칙은 `all`)
- `field`: `school_name` / `student_id` / `admission_date` / `graduation_date` / `birth_date` / `resident_number_back` / `address` / `photo` / `name` / `license_type` / `semester_year`
- `form`: `text` / `logo` / `seal` / `watermark` / `english` / `email` / `photo`
- `rule`: `mask`(가려야 함) / `keep`(확인용이라 가리면 안 됨)
- `visibility`: `full` / `partial` / `hidden` / `unreadable` / `absent` (입력한 원본 기준)
- `status`: `ok` / `auto_masked` / `over_masked` / `검토 필요`
- `checks`는 (쪽, 항목, 형태)마다 한 행. 같은 쪽에 같은 항목·형태가 여러 번 나와도 한 행

판정표 (정답지도 이 표로 생성)

| rule | ok | auto_masked | over_masked | 검토 필요 |
|---|---|---|---|---|
| mask | hidden | full, partial | – | unreadable, absent |
| keep | full | – | partial, hidden | unreadable, absent |

`result`: 누락 또는 over_masked → 보완 필요 / 아니고 검토 필요 행이나 review_reasons가 있으면 → 검토 필요 / 나머지(auto_masked만 있는 경우 포함) → 통과

## 데이터셋 10케이스

가상 인물 5세트(S1~S5)의 원본 서류를 변형해 만들었습니다. 공고 A는 학교명·학번·입학/졸업일·생년월일, 신분증 주민번호
뒷자리·주소·사진을 가리고 자격증 성명·자격 종목은 남기라고 하고, 공고 B는 학교명·학번·성명·학기별 연도, 신분증 주민번호
뒷자리·사진을 가리라고 합니다.

| # | 세트 | 유형 | 내용 | 정답 |
|---|---|---|---|---|
| 01 | S1 | 단순 | 공고 A 기준대로 모두 가린 정상 제출 | 통과 |
| 02 | S2 | 양식 | 학교명 글자는 가렸지만 로고·영문명·직인·워터마크에 남음 | 통과 (자동 가림 4) |
| 03 | S3 | 양식 | 표 양식 졸업증명서, 흰 덮개·별표 가림, 성적증명서 2쪽만 학번 노출 | 통과 (자동 가림 1) |
| 04 | S4 | 예외 | 남겨야 할 자격증 성명·자격 종목까지 가림 | 보완 필요 (over_masked 2) |
| 05 | S5 | 예외 | 필수 서류(자격증 사본) 누락 | 보완 필요 |
| 06 | S3 | 저품질 | 반투명 형광펜(학교명 비침) + 흐린 스캔(자격 종목 판독 불가) | 검토 필요 |
| 07 | S1 | 결합 | case_01과 같은 서류에 공고 B 적용 → 성명·학기 연도 노출 | 통과 (자동 가림 5) |
| 08 | S4 | 예외 | 공고문 없이 가림 요청서(학교명·학번·주민번호 뒷자리·사진)로 점검 | 검토 필요 |
| 09 | S5 | 결합 | 학교 이메일 도메인 노출 + 학교 주소·대표전화(간접 단서) | 검토 필요 |
| 10 | S2 | 저품질 | 기울어진 저화질 신분증(성별 자리·주소·사진 노출) + 성적증명서 누락 | 보완 필요 |

## 테스트 결과 (10케이스, Studio 실행)

`dataset/case_XX.pdf`를 그대로 올려 돌렸습니다.

| 설정 | 변경 | 항목 정확도 | 최종 판정 |
|---|---|---|---|
| #1 | 첫 설정 | 509/596 (85.4%) | 6/10 |
| #2 | 덮개가 있으면 hidden, rules에 없는 항목은 행 만들지 않기, 결과 우선순위 | 573/588 (97.4%) | 9/10 |
| #3 | 머리글 학교명·중복 행·absent 규칙 추가, result에 '검토 필요 행' 조건 추가 | 563/588 (95.7%) | 6/10 |
| **#4** | #3에서 result 문구 정리(auto_masked·공고문 없음은 보완 필요 이유가 아님), 블러는 덮개가 아님 | **574/588 (97.6%)** | **8/10** |
| #5 | #4 + manyRows 끔 | case_04 추출 실패(FAILED) | – |
| #6 (최종) | #4와 같은 Extract 설정 + Validate 요약 문구 한 줄 | #4 결과를 재사용 | – |

- 최종(#4/#6)에서 틀린 판정: case_04는 over_masked 2건을 찾고도 `result`를 통과로 씀(Validate는 Red, Instruct는 보완 필요로 바로잡음), case_06은 흐린 자격 종목을 full로 읽음.
- 항목 오류: case_02 워터마크 행 누락, case_05 신분증 주소 행 누락, case_08 직인·영문 표기를 unreadable로 판단.
- 같은 설정이라도 실행마다 1~2건씩 흔들립니다. 제출 전 2~3회 돌려 안정성을 확인하세요.

## 개선하면서 확인한 것

- 검은 박스로 가린 학교명을 `unreadable`·`absent`로 보거나, 로고·이메일에 학교명이 보이면 머리글 글자까지 `full`로 보는 경우가 많았음 → visibility를 "덮개가 있으면 hidden → 일부만 덮이면 partial → 읽히면 full → 덮개 없이 번지면 unreadable" 순서로 정하게 하고, 학교명은 형태마다 따로 판단하게 하자 크게 줄어듦
- 공고에 없는 학기별 연도 행을 스스로 만들어 넣음 → "rules에 (서류, 항목) 조합이 없으면 행을 만들지 않는다"로 해결
- #3에서 보완 필요·통과를 서로 바꿔 쓰는 오판이 늘었음(원인은 확인 못 함, 실행 편차일 수 있음) → #4에서 result 문구를 정리하고 "auto_masked는 보완 필요의 이유가 아니다", "공고문이 없는 것도 검토 필요다"를 넣음
- manyRows를 끄면 `result`가 `checks`와 더 잘 맞을 것으로 기대했지만, case_04 추출이 실패(FAILED)했고 나머지도 나아지지 않음(#5) → 켜 둠
- Studio의 목록(String list) 항목은 배열 자체 설명을 저장하지 않고 items 설명만 씀 → 지시문을 items 설명에 넣음
- Extract 설정이 이전 버전과 같으면 다시 실행해도 Extract 결과가 이전 실행과 글자까지 똑같이 나왔음(#6 = #4). 프롬프트를 바꾸지 않은 재실행은 새 측정으로 보지 않는 게 안전함

## 주의

- `build_config.py`의 `EXPORT_TABLE`은 이 Studio 워크플로우가 만든 컬렉션 테이블 ID입니다. 다른 워크플로우에 가져오면 Export 노드를 다시 확인하세요.
- 채점에 쓰이는 출력은 Export가 저장하는 Extract 결과입니다. Instruct의 판정·안내 문구는 Instruct 출력에 따로 남습니다.
- 자동 가림 워크플로우(제출용 PDF 생성)는 아직 블라인드 채용용으로 바꾸지 않았습니다. 로고·직인·사진처럼 글자가 아닌 부분이 실제로 가려지는지, 가린 글자가 텍스트 복사로 남는지도 확인하지 않았습니다.
