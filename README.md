# 정보공개 문서 개인정보 가림 점검 에이전트

공공기관·지자체 정보공개 담당자가 정보공개(부분 공개)·외부 제공 전에 문서 묶음을 PDF 하나로 넣으면,
정보공개 결정통지서 기준대로 개인정보가 가려졌는지 점검해 판정합니다.

| 판정 | 언제 |
|---|---|
| **공개 가능** | 문제가 없거나, 가려야 할 정보가 노출돼 **자동 가림 대상**(`auto_masked`)으로 표시만 된 경우. 공개 승인이 아니라 후속 마스킹에 넘길 수 있다는 뜻 |
| **수정 필요** | 공개 대상 문서가 빠졌거나, 공개해야 할 정보(직무 수행 공무원 성명·직위 등)까지 가린 경우 |
| **검토 필요** | 번져서 읽을 수 없는 정보, 무엇을 가렸는지 알 수 없는 가림, 결정통지서 없음, 개인을 추정할 수 있는 간접 단서 |

우선순위: 수정 필요 > 검토 필요 > 공개 가능. U108(의무기록 개인정보 가림 점검) 카드를 참고했습니다.

## 판정 기준

- 결정통지서의 "비공개 대상"에 적힌 항목은 가리고(`mask`), "공개 가능 정보"의 직무 수행 공무원 성명·직위는 남깁니다(`keep`).
  비공개 목록에 없는 항목은 점검하지 않습니다.
- 결정통지서가 없으면 기본 항목(성명·주민등록번호·주소·연락처·계좌번호·사진 가림, 공무원 성명·직위 공개)으로 점검하고 검토 필요로 넘깁니다.
- 참고 조항: 「공공기관의 정보공개에 관한 법률」 제9조 제1항 제6호(개인정보 비공개)와 같은 호 단서 라목(직무를 수행한 공무원의 성명·직위),
  제14조(부분 공개). 이 에이전트는 공개 여부를 법적으로 판단하지 않고, 결정통지서대로 가려졌는지만 점검합니다.

## Upstage Studio 워크플로우

`당신의눈동자에치얼스_미션2_정보공개 문서 개인정보 가림 점검` (`agt_aexHxrfs6JrE9YyHTjtrCt`, 현재 **설정 #9**)

```
시작 → Parse(OCR 강제, 좌표 ON)
     → Extract "disclosure_check_schema" (고급형, 사용자 시스템 프롬프트, manyRows 끔)  ← 정답 값을 내는 노드
     → Validate "검증-1"  (Green / Yellow / Red 모두 →)
     → Instruct "instruct-default" (결정: 공개 가능 / 수정 필요 / 검토 필요 + 처리 우선순위·담당자 안내 문구)
     → Export "내보내기-1" (Extract 결과를 컬렉션에 저장)
```

- Extract는 먼저 쪽마다 개인정보 칸을 가림·노출·번짐·빈칸으로 나눠 봅니다. 번짐(블러)은 가림으로 인정하지 않고 검토 필요로 보냅니다.
- Instruct 안내문은 처리 우선순위(긴급/높음/보통/없음), 공개 조건, 자동 가림 대상·재제출 요청·담당자 확인·재점검 순서로 씁니다(팀이 설정 #7에서 고친 내용).

Validate 규칙

| 규칙 | 등급 | 조건 |
|---|---|---|
| 공개 대상 문서 누락 없음 | 필수 | `missing_documents` 비어 있음 |
| 공개할 정보 가림 없음 | 필수 | `checks.status`에 over_masked 없음 |
| 판독 불가 항목 없음 | 선택 | `checks.status`에 `검토 필요` 없음 |
| 결정통지서 기준 확인 | 선택 | `criteria_source` = `decision_notice` |
| 검토 사유 없음 | 선택 | `review_reasons` 비어 있음 |

→ 필수 실패 = Red(수정 필요), 선택 실패 = Yellow(검토 필요), 전부 통과 = Green(공개 가능)

## 출력 키 8개 (정답지 answer.json의 `answer`와 같음)

```
request_number, criteria_source(decision_notice|default),
rules[{document_type, field, rule}],
submitted_documents[](결정통지서 포함), missing_documents[],
checks[{document_type, page, field, form, rule, visibility, status}],
review_reasons[], result(공개 가능|수정 필요|검토 필요)
```
- `document_type`: `decision_notice` / `complaint_form` / `reply_letter` / `id_card_copy` / `site_inspection_report` (rules는 모두 `all`)
- `field`: `name`(민원인·제3자 성명, 영문 포함) / `resident_number` / `address` / `phone` / `account_number` / `photo` / `official_name`
- `form`: `text` / `handwriting`(자필 서명) / `seal`(개인 인장) / `photo`
- `visibility`: `full` / `partial` / `hidden` / `unreadable` / `absent`("기재 없음")
- `status`: `ok` / `auto_masked` / `over_masked` / `검토 필요`
- `checks`는 위치마다 한 행. 같은 쪽·항목·형태라도 가림 상태가 다르면 따로 적음(예: 가린 국문 성명 + 노출된 영문 성명 = 2행)
- `review_reasons`: 수정 필요·검토 필요의 근거를 모두 적음. 공개 가능이면 `[]`

판정표

| rule | ok | auto_masked | over_masked | 검토 필요 |
|---|---|---|---|---|
| mask | hidden, absent | full, partial | – | unreadable |
| keep | full | – | partial, hidden | unreadable, absent |

## 데이터셋

- **제출용(미션 2):** 데이터셋 팀이 만든 v2.3 `당신의눈동자에치얼스_미션2_set01~06.pdf`(6케이스, 문서 18건, 유형 ①~⑤ 모두 포함,
  set04가 저품질 스캔), `..._answer.json`, `..._유형표.xlsx`. 이 저장소에는 넣지 않았습니다.
- **내부 회귀 테스트:** `gen_docs.py`가 만드는 가상 10케이스(`dataset/case_01~10.pdf`, `answers/`). 과잉 가림·판독 불가·사진 노출·
  "성명 공개" 결정통지서 같은 경우를 보강하려고 만든 것이며 제출 형식(answer.json 한 파일, 문서당 1줄 유형표)은 아닙니다.

## 사용법

```bash
pip install -r requirements.txt

python3 gen_docs.py          # 내부 테스트 10케이스 + 정답 생성
python3 build_types_xlsx.py  # 내부 테스트 유형표
python3 build_config.py      # workflow/*.json 다시 생성 (Studio ⋯ → 워크플로우 설정 가져오기)

# 채점
python3 compare_answer.py 당신의눈동자에치얼스_미션2_answer.json results/   # 대회 형식 정답지
python3 compare.py results/                                                  # 내부 테스트 10케이스
```
- 결과 파일은 Studio 결과의 JSON을 `results/<PDF 이름에서 .pdf 뺀 것>.json`으로 저장하면 됩니다.
- 채점은 (문서, 쪽, 항목, 형태)로 행을 묶고, 같은 묶음 안에서는 visibility가 같은 행끼리 먼저 짝짓습니다. `review_reasons`(자유 문장)는 비교하지 않습니다.
- 한글 글꼴은 Linux(Noto CJK) → macOS → Windows 순서로 찾습니다. Linux + Noto CJK에서만 실행해 봤습니다.

## 파일

| 경로 | 내용 |
|---|---|
| `build_config.py` | 워크플로우 설정 JSON 생성기 (스키마·프롬프트·Validate 규칙) |
| `workflow/정보공개점검_workflow_config.json` | 설정 #9와 같은 내용의 가져오기용 JSON |
| `workflow/정보공개점검_extract_schema.json` | 추출 항목만 |
| `compare_answer.py` | 대회 형식 answer.json과 비교 |
| `compare.py` | 내부 테스트 정답(`answers/case_XX.json`)과 비교 |
| `gen_docs.py` · `build_types_xlsx.py` | 내부 테스트 문서·정답·유형표 생성기 |

## 테스트 결과 (Studio 실행)

항목 정확도는 rules·문서 목록·checks 각 칸을 센 값, "Extract 판정"은 Extract의 `result` 필드, "신호등/Instruct"는 Validate 색과 Instruct 결정입니다.

**제출용 6케이스 (데이터셋 팀 answer.json 기준)**

| 설정 | 데이터 | 바꾼 점 | 항목 정확도 | Extract 판정 | 신호등 / Instruct |
|---|---|---|---|---|---|
| #5 | v2.1 | 팀 정답 규칙 반영: 현장 조사보고서 코드, "(기재 없음)"=ok, 같은 칸 2행, 라벨 기준 위치, 제3자 성명, review_reasons에 수정 사유 | 203/207 (98.1%) | 4/6 | 4/6 / 4/6 |
| #6 | v2.1 | 노출된 주소를 간접 단서로 보지 않게, 옅은 회색 번짐 정의 추가 | 204/207 (98.6%) | 5/6 | 5/6 / 5/6 |
| #6 | v2.3 | (데이터 팀이 set04 번짐 이미지 수정) | 206/207 (99.5%) | 5/6 | 6/6 / 6/6 |
| **#9** | v2.3 | 번짐 칸을 result·review_reasons가 직접 잡게 함, 팀의 Instruct 안내문(#7) 반영 | **207/207 (100%)** | **6/6** | **6/6 / 6/6** |

- v2.1 set04: 번진 연락처가 글자 획 없는 균일한 회색 사각형이라 hidden으로 읽음 → 데이터 팀이 v2.3에서 수정.
- #6 + v2.3 set04: checks는 맞았지만(연락처 unreadable) Extract `result`가 checks보다 먼저 쓰여 "공개 가능"이 나옴 → #9에서 해결.
- #9는 두 번 전체 실행해 같은 결과를 확인했습니다(두 번째는 캐시일 수 있음).

**내부 회귀 테스트 10케이스**

| 설정 | 바꾼 점 | 항목 정확도 | Extract 판정 | 신호등 / Instruct |
|---|---|---|---|---|
| #1 | 첫 설정 | 408/429 (95.1%) | 6/10 | 8/10 / 8/10 |
| #2 | 흰 덮개=hidden 강조, 간접 단서 범위, "귀하" 옆 박스=hidden | 426/429 (99.3%) | 7/10 | 10/10 / 10/10 |
| #3 | result를 문서에서 직접 판단하게(Extract는 result를 checks보다 먼저 씀) | 426/429 (99.3%) | 8/10 | 10/10 / 10/10 |
| #4 | #3 + manyRows 끔 | 427/429 (99.5%) | 9/10 | 10/10 / 10/10 |
| #6 | 제출용 데이터 규칙으로 변경 | 422/429 (98.4%) | 8/10 | 9/10 / 9/10 |

- #6에서 case_05(신분증 사본 누락)를 "있다"고 읽어 공개 가능으로 판정한 회귀가 1건 있음. 실행 편차인지 프롬프트 변경 때문인지 아직 확인 못 함.
- #9는 내부 10케이스로 다시 재지 않았습니다.
- case_07("성명 공개" 결정통지서)은 checks는 맞지만 Extract `result`만 계속 틀림. Validate·Instruct는 수정 필요로 맞게 냄.

## 개선하면서 확인한 것

- Studio는 Extract 출력에서 단일 값(result·review_reasons)을 표(rules·checks)보다 먼저 씁니다. 그래서 result가 checks를 보지 못해 틀리는 일이 많았고,
  result 설명에 "문서에서 직접 이 순서로 확인하라"를 넣자 줄었습니다(#2 7/10 → #3 8/10 → #4 9/10).
- manyRows를 끄자(#4) result 정확도가 한 건 더 올랐습니다. 행 수가 15개 안팎이라 나눠 추출할 필요가 없습니다.
- 검은 박스·흰 수정테이프를 unreadable로, 민원 장소(학교 앞 등)를 간접 단서로 잡는 오류는 visibility 판단 순서와 단서 범위를 명시해 해결했습니다.
- 저품질 스캔(set04)에서 result는 번진 연락처를 가린 것으로 보고 넘겼습니다. 시스템 프롬프트 맨 앞에 "칸마다 가림·노출·번짐·빈칸 구분, 번짐은 가림 아님"을,
  review_reasons 첫 확인 항목에 번짐을, result에 "review_reasons가 있으면 공개 가능이 아니다"를 넣자 맞게 나왔습니다(#9).
- 같은 설정을 다시 돌리면 Extract 결과가 이전과 같게 나오는 경우가 있어(캐시로 보임) 프롬프트를 바꾸지 않은 재실행은 새 측정으로 보지 않았습니다.

## 남은 일

- [ ] 제출용 workflow JSON은 Studio ⋯ → **워크플로우 설정 내보내기**로 받은 설정 #9 파일로 교체 (`workflow/`의 JSON은 가져오기용 생성 파일)
- [x] Studio 워크플로우 파일을 제출용 6케이스만 남기기
- [x] set04(저품질) 데이터 수정 후 재측정 → #9에서 6/6
- [ ] 최종 제출(문서 20건 이상): 케이스 추가 후 재측정, 라이브러리 게시
- [ ] 내부 10케이스로 #9 재측정, case_05 회귀 재확인
- [ ] 현재 워크플로우는 점검만 함(`auto_masked`는 "가려야 할 위치" 표시이고 PDF를 고치지 않음). Studio에는 PDF에 박스를 그려 저장하는 노드가 없어
      별도 코드로 붙일 것: ① checks를 표로 만든 처리 내역서 ② OCR·Parse 좌표로 가린 공개본 PDF(페이지를 이미지로 바꿔 박스를 칠해 글자가 남지 않게)
      ③ 공개본을 설정 #9로 다시 돌려 재검증
