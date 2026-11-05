"""유형표(문서마다 한 줄) + 유형·판정 요약 시트 생성."""
import json, os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.abspath(__file__))
man = json.load(open(os.path.join(ROOT, 'dataset', 'manifest.json'), encoding='utf-8'))
DOC_KO = dict(decision_notice='결정통지서', complaint_form='민원 신청서', reply_letter='민원 회신문',
              id_card_copy='신분증 사본')
SET_KO = {'S1': 'S1 가상시 도로과 민원', 'S2': 'S2 예시시 환경과 민원', 'S3': 'S3 샘플시 교통과 민원',
          'S4': 'S4 모의시 공원녹지과 민원', 'S5': 'S5 시험시 건축과 민원'}
CRIT_KO = {'A': '결정통지서 A (민원인 성명 비공개)', 'B': '결정통지서 B (민원인 성명 공개 동의)',
           'default': '기본 항목 (결정통지서 없음)'}

F = 'Arial'
head_font = Font(name=F, bold=True, color='FFFFFF', size=10)
head_fill = PatternFill('solid', fgColor='3B3F8F')
body = Font(name=F, size=10)
thin = Side(style='thin', color='BFBFBF')
box = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap = Alignment(wrap_text=True, vertical='top')

wb = Workbook()
ws = wb.active
ws.title = '유형표'
cols = ['파일명', '세트', '유형', '시험 목적', '기준', '문서 구성(쪽 순서)', '쪽 수', '핵심 변형', '기대 판정(result)',
        'checks 행 수', '정답지 파일']
widths = [12, 20, 9, 44, 24, 46, 7, 52, 14, 11, 16]
ws.append(cols)
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
for c in ws[1]:
    c.font, c.fill, c.border = head_font, head_fill, box
    c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
for r, m in enumerate(man, 2):
    docs = ' → '.join(DOC_KO[d] for d in m['documents'])
    ws.append([m['file'], SET_KO[m['set']], m['type'], m['purpose'], CRIT_KO[m['criteria']], docs,
               len(m['documents']), m['note'], m['result'], m['n_checks'], m['file'].replace('.pdf', '.json')])
    for c in ws[r]:
        c.font, c.border, c.alignment = body, box, wrap
    ws.cell(r, 7).alignment = ws.cell(r, 10).alignment = Alignment(horizontal='center', vertical='top')
ws.freeze_panes = 'A2'
last = len(man) + 1
note_r = last + 2
ws.cell(note_r, 1, '※ 모든 인물·기관·번호는 가상이며, 문서마다 하단에 "해커톤 테스트용 가상 문서" 표기가 있습니다.').font = \
    Font(name=F, size=9, italic=True, color='666666')
ws.cell(note_r + 1, 1, '※ 같은 세트는 같은 민원 문서를 변형한 것입니다(예: case_07은 case_01과 같은 문서에 결정통지서만 B로 바꿈).').font = \
    Font(name=F, size=9, italic=True, color='666666')

# 요약 시트 (수식으로 집계)
s2 = wb.create_sheet('요약')
s2.column_dimensions['A'].width = 16
s2.column_dimensions['B'].width = 10
s2.column_dimensions['D'].width = 16
s2.column_dimensions['E'].width = 10
s2['A1'], s2['B1'], s2['D1'], s2['E1'] = '유형', '문서 수', '기대 판정', '문서 수'
for c in (s2['A1'], s2['B1'], s2['D1'], s2['E1']):
    c.font, c.fill, c.border = head_font, head_fill, box
types = ['단순', '양식', '결합', '저품질', '예외']
for i, t in enumerate(types, 2):
    s2.cell(i, 1, t)
    s2.cell(i, 2, f"=COUNTIF('유형표'!$C$2:$C${last},A{i})")
tr = len(types) + 2
s2.cell(tr, 1, '합계').font = Font(name=F, bold=True, size=10)
s2.cell(tr, 2, f'=SUM(B2:B{tr - 1})')
results = ['공개 가능', '수정 필요', '검토 필요']
for i, t in enumerate(results, 2):
    s2.cell(i, 4, t)
    s2.cell(i, 5, f"=COUNTIF('유형표'!$I$2:$I${last},D{i})")
rr = len(results) + 2
s2.cell(rr, 4, '합계').font = Font(name=F, bold=True, size=10)
s2.cell(rr, 5, f'=SUM(E2:E{rr - 1})')
for row in s2.iter_rows(min_row=2, max_row=tr):
    for c in row:
        if c.value is not None:
            c.border = box
            if c.font.bold is not True:
                c.font = body

out = os.path.join(ROOT, '당신의눈동자에치얼스_미션2_유형표.xlsx')
wb.save(out)
print(out)
