# 제출 서류 마스킹 검수 에이전트

공고문(또는 가림 요청서)과 지원자 서류 묶음을 넣으면

- 가려야 하는데 노출된 정보 → **에이전트가 직접 가림** (`auto_masked`)
- 보여야 하는데 가려졌거나 없는 정보, 빠진 서류 → **보완 필요** + 보완 요청 문구
- 흐려서 판단할 수 없는 정보 → **검토 필요**

를 판정합니다.

## Upstage Studio 워크플로우 (2개)

Studio는 **한 경로에 Extract 노드를 하나만** 둘 수 있어서, 검수와 자동 가림을 두 워크플로우로 나눴습니다.

### 1. 가림체크 · 제출 서류 검수 (`agt_ALs66a9ed6iawrinxMJQPs`)
```
시작 → Parse(OCR 강제, 좌표 ON)
     → Extract "masking_check_schema" (고급형 = VLM, 사용자 시스템 프롬프트)
     → Validate "검증-1"
          Green  → 끝 (통과)
          Yellow → Instruct (검토 필요 사유)
          Red    → Instruct (보완 요청 문구)
```
Validate 규칙
| 규칙 | 등급 | 조건 |
|---|---|---|
| 필수 서류 누락 없음 | 필수 | `missing_documents` 값 없음 |
| 보여야 할 정보 가림·누락 없음 | 필수 | `checks.status` 모든 항목이 `^(ok\|auto_masked\|검토 필요)$` |
| 판독 불가 항목 없음 | 선택 | `checks.status` 모든 항목 ≠ `검토 필요` |
| 가림 기준 문서 확인 | 선택 | `criteria_source` 값 있음 |

→ 필수 실패 = Red(보완 필요), 선택 실패 = Yellow(검토 필요), 전부 통과 = Green(통과)

### 2. 가림체크 · 자동 가림 (`agt_AQWt3HkAxSf2qzwWs3YTkw`)
```
시작 → Parse → Extract(문서 마스킹하기) 필드 resident_number_to_mask
```
기준 문서를 읽고 "가려야 하는데 아직 보이는 부분"만 골라 가린 PDF를 만듭니다.
(뒷자리 기준이면 하이픈 뒤 숫자만, 13자리 기준이면 보이는 숫자 전체)

## 사용법

```bash
pip install -r requirements.txt

python3 gen_docs.py        # dataset/case_01~10 생성 (bundle.pdf, pages/*.png, answer.json, truth_boxes.json)
python3 build_config.py    # workflow/*.json 다시 생성
python3 compare.py results # results/case_XX.json(Studio Extract 결과 JSON)과 정답지 비교
```

- 한글 글꼴은 Linux(Noto CJK) → macOS(Apple SD Gothic Neo) → Windows(맑은 고딕) 순서로 찾습니다. 다른 글꼴을 쓰려면 `MASKING_FONT`(필요하면 `MASKING_FONT_BOLD`, `MASKING_FONT_INDEX`) 환경변수로 경로를 지정하세요. Linux + Noto CJK 환경에서만 실행해 봤습니다.
- `compare.py`에 넣을 결과는 Studio 결과 패널의 JSON 탭 내용을 `results/case_01.json`처럼 케이스 이름으로 저장하면 됩니다.

## 파일

| 경로 | 내용 |
|---|---|
| `gen_docs.py` | 가상 서류 + 정답지 생성기 |
| `build_config.py` | 워크플로우 설정 JSON 생성기 |
| `compare.py` | Studio 결과 ↔ 정답지 비교 (항목 정확도, 최종 판정 일치) |
| `workflow/검수_workflow_config.json` | 검수 워크플로우 전체 설정. Studio ⋯ → **워크플로우 설정 가져오기**로 그대로 import |
| `workflow/검수_extract_schema.json` | 추출 항목만 (Extract 노드 ⋯ → JSON 추출 항목 가져오기) |
| `workflow/자동가림_mask_field.json` | 자동 가림 워크플로우의 마스킹 필드 설명 |

`dataset/`과 결과 폴더는 생성물이라 `.gitignore`로 제외했습니다. `gen_docs.py`를 실행하면 같은 데이터가 다시 만들어집니다.
모든 인물·번호·기관은 가상이며 문서마다 "해커톤 테스트용 가상 문서" 표기가 있습니다.

## 출력 스키마 (snake_case 고정)

```
applicant_name, criteria_source(notice|masking_request),
required_documents[], submitted_documents[](기준 문서 포함), missing_documents[],
rules[{document_type, field, rule}],
checks[{document_type, page, field, person_name, rule, visibility, status}],
review_reasons[], result(통과|보완 필요|검토 필요)
```
- `rule`: `mask_back_7` / `mask_all` / `must_be_visible`
- `visibility`: `full` / `front_and_gender` / `front_only` / `hidden` / `unreadable` / `absent`
- `status`: `ok` / `auto_masked` / `over_masked` / `missing_field` / `검토 필요`

판정표 (정답지도 이 표로 생성)

| rule | ok | auto_masked | over_masked | missing_field | 검토 필요 |
|---|---|---|---|---|---|
| mask_back_7 | front_only, hidden | full, front_and_gender, unreadable | – | – | – |
| mask_all | hidden | 나머지 전부 | – | – | – |
| must_be_visible | full | – | hidden | absent | unreadable |

## 데이터셋 10케이스

| # | 유형 | 내용 | 정답 |
|---|---|---|---|
| 01 | 단순 | 등본 3명 정상 가림 | 통과 |
| 02 | 단순 | 등본 본인 주민번호 노출 | 통과 (자동 가림 1) |
| 03 | 양식·문맥 | 가림 요청서 기준, 가림 방식 3종(*, 흰 덮개, 검은 박스), 체크 안 된 계좌번호 | 통과 |
| 04 | 양식·문맥 | 공고 B = 13자리 전체 가림, 서류는 뒷자리만 가림 | 통과 (자동 가림 3) |
| 05 | 문서 결합 | 세대원(동생)만 노출, 공고문이 맨 뒤 | 통과 (자동 가림 1) |
| 06 | 문서 결합 | 통장 계좌번호까지 가림 | 보완 필요 (over_masked) |
| 07 | 문서 결합 | 통장사본 누락 + 본인 노출 | 보완 필요 + 자동 가림 1 |
| 08 | 저품질 | 폰으로 기울게 찍은 등본, 본인 노출 | 통과 (자동 가림 1) |
| 09 | 함정 | 반투명 형광펜(글자 보임) + 성별 자리만 노출 | 통과 (자동 가림 2) |
| 10 | 함정 | 계좌번호 흐림(판독 불가) | 검토 필요 |

## 테스트 결과 (10케이스, Studio 실행)

| 설정 | 변경 | 항목 정확도 | 최종 판정 |
|---|---|---|---|
| #2 | 기본형 추출 | – (06 과잉 가림을 '없음'으로, 10 흐림을 '없음'으로 판단) | 9/10 |
| #3 | 고급형(VLM) + 시스템 프롬프트 | 260/262 (99.2%) | 10/10 |
| #4 | 목록 항목 설명 위치 수정, 조사 규칙 | 256/262 (97.7%) | 10/10 |
| **#5 (최종)** | visibility는 규칙과 무관하게 이미지 상태만 | **262/262 (100%)** | **10/10** |

- Validate 신호등도 10/10 일치 (통과=Green, 보완 필요=Red, 검토 필요=Yellow)
- 보완 요청 문구(Instruct) 예: "통장사본이 제출 서류에 없어요. 추가로 제출해 주세요."
- 자동 가림(case 02/04/09)은 가릴 값만 정확히 골라냄: `4127385` / `020403-`·`741109-`·`760301-` / `3591746`·`1` (글자 단위 좌표 포함)
- 같은 설정이라도 실행마다 조금씩 흔들릴 수 있음(#4에서 case_04의 visibility가 한 번 흔들림). 제출 전 2~3회 돌려 안정성을 확인하세요.

## 개선하면서 확인한 것

- 기본형(텍스트 기반)은 검은 박스·흐림·라벨만 남은 경우를 모두 "없음"으로 봄 → **고급형(VLM) + 시스템 프롬프트**로 바꾸자 과잉 가림(06)과 판독 불가(10)를 구분
- Studio의 목록(String list) 항목은 **배열 자체 설명을 저장하지 않고 items 설명만 씀** → 지시문을 items 설명에 넣어야 함 (설정 #4부터 반영)

## 주의

- Studio 테스트는 같은 생성 로직을 브라우저에서 그린 PNG 묶음으로 돌렸습니다(글꼴만 다름). 공식 데이터셋은 `dataset/case_XX/bundle.pdf`를 올리고 한 번 더 돌려 주세요.
- case_09의 성별 자리 `1`은 OCR이 `741109-1`을 한 단어로 묶어서, 가림 박스가 앞자리까지 덮을 수 있습니다. Masked PDF로 확인이 필요합니다.
