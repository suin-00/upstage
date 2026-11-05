"""정보공개 문서 개인정보 가림 점검 — 테스트용 가상 문서 + 정답지 생성기.

청구 1건 = PDF 1개: 정보공개 결정통지서 → 민원 신청서 → 민원 회신문 → 신분증 사본
모든 인물·기관·번호는 가상이며 각 쪽 아래에 '해커톤 테스트용 가상 문서' 표기가 들어간다.
출력: dataset/case_XX.pdf, dataset/pages/case_XX_pN.png, answers/case_XX.json, dataset/manifest.json
"""
import json, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

random.seed(17)
W, H = 1240, 1754  # A4 @150dpi
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'dataset')
ANS = os.path.join(ROOT, 'answers')

FONT_CANDIDATES = [
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 1),
    ('/System/Library/Fonts/AppleSDGothicNeo.ttc', '/System/Library/Fonts/AppleSDGothicNeo.ttc', 0),
    ('C:/Windows/Fonts/malgun.ttf', 'C:/Windows/Fonts/malgunbd.ttf', 0),
]
FONT = next((c for c in FONT_CANDIDATES if os.path.exists(c[0])), FONT_CANDIDATES[0])
_fonts = {}


def font(size, bold=False):
    k = (size, bold)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(FONT[1] if bold else FONT[0], size, index=FONT[2])
    return _fonts[k]


# ─────────────────────────────────────────── 판정표 (설계서 기준)
VIS = {'none': 'full', 'highlight': 'full', 'black': 'hidden', 'white': 'hidden', 'star': 'hidden',
       'blur': 'unreadable', 'partial': 'partial'}
STATUS = {
    'mask': {'full': 'auto_masked', 'partial': 'auto_masked', 'hidden': 'ok',
             'unreadable': '검토 필요', 'absent': '검토 필요'},
    'keep': {'full': 'ok', 'partial': 'over_masked', 'hidden': 'over_masked',
             'unreadable': '검토 필요', 'absent': '검토 필요'},
}

# ─────────────────────────────────────────── 가상 민원 5세트
PERSONAS = {
    'S1': dict(name='김가람', rrn='850315-1845273', addr='가상시 예시구 연습로 12, 101동 1001호', phone='010-0123-4567',
               org='가상시', mayor='가상시장', req='2026-가상-0412', recv='민원여권과 주무관 도은결',
               off='도로과 주무관 연서진', dept='도로과', subject='보도블록 파손 보수 요청',
               body=['연습로 12 앞 보도블록 여러 장이 깨져 있어 보행자가 걸려 넘어질 위험이 있습니다.',
                     '비가 오면 물이 고여 통행이 어렵습니다. 빠른 보수를 요청합니다.'],
               reply=['신청하신 연습로 12 앞 보도블록은 현장 확인 후 2026. 9. 27. 보수를 마쳤습니다.',
                      '앞으로도 정기 순찰로 보도 상태를 점검하겠습니다.'],
               issue='2019. 4. 3.', office='가상시 예시구청장'),
    'S2': dict(name='이나래', rrn='920721-2123856', addr='예시시 모의구 샘플길 45-3, 2층', phone='010-0234-5678',
               org='예시시', mayor='예시시장', req='2026-예시-0587', recv='민원봉사과 주무관 표하람',
               off='환경과 주무관 남윤슬', dept='환경과', subject='야간 공사 소음 민원',
               body=['샘플길 공사 현장에서 밤 10시 이후에도 굴착 작업이 계속되어 잠을 잘 수 없습니다.',
                     '작업 시간 준수 여부를 확인해 주시기 바랍니다.'],
               reply=['현장 점검 결과 야간 작업 사실이 확인되어 시공사에 작업 시간 준수를 명령했습니다.',
                      '같은 일이 반복되면 과태료를 부과할 예정입니다.'],
               issue='2020. 8. 11.', office='예시시 모의구청장'),
    'S3': dict(name='박다솜', rrn='881102-2736145', addr='샘플시 가상구 표본대로 230, 305호', phone='010-0345-6789',
               org='샘플시', mayor='샘플시장', req='2026-샘플-0233', recv='종합민원과 주무관 길도현',
               off='교통과 주무관 채온유', dept='교통과', subject='어린이보호구역 불법 주정차 단속 요청',
               body=['표본초등학교 정문 앞 어린이보호구역에 등하교 시간마다 차량이 주차되어 있습니다.',
                     '아이들이 차 사이로 뛰어나와 위험하니 단속을 요청합니다.'],
               reply=['해당 구역에 고정형 단속 카메라 설치를 검토하고, 등하교 시간 현장 단속을 늘렸습니다.',
                      '단속 결과는 분기마다 시 누리집에 공개하겠습니다.'],
               issue='2018. 1. 22.', office='샘플시 가상구청장'),
    'S4': dict(name='최하늘', rrn='010130-3584216', addr='모의시 시험구 연습로 8, 1203호', phone='010-0456-7890',
               org='모의시', mayor='모의시장', req='2026-모의-0119', recv='민원지적과 주무관 반지율',
               off='공원녹지과 주무관 육해솔', dept='공원녹지과', subject='공원 가로등 고장 수리 요청',
               body=['연습근린공원 산책로 가로등 세 개가 한 달째 꺼져 있어 밤에 산책하기 무섭습니다.',
                     '수리 일정을 알려 주시기 바랍니다.'],
               reply=['고장 난 가로등 세 개의 안정기를 교체하여 2026. 9. 30. 수리를 마쳤습니다.',
                      '공원 조명은 매월 점검하겠습니다.'],
               issue='2021. 3. 9.', office='모의시 시험구청장'),
    'S5': dict(name='정보람', rrn='770509-2615384', addr='시험시 예제구 시험로 77, 3층', phone='010-0567-8901',
               org='시험시', mayor='시험시장', req='2026-시험-0348', recv='민원과 주무관 석다원',
               off='건축과 주무관 탁이현', dept='건축과', subject='공사장 가림막 파손 신고',
               body=['시험로 신축 공사장 가림막이 바람에 넘어져 인도를 막고 있습니다.',
                     '보행자가 차도로 걸어 다니고 있어 조치가 필요합니다.'],
               reply=['시공사에 가림막 재설치와 보행로 확보를 명령했고, 2026. 9. 24. 조치를 확인했습니다.',
                      '공사 기간 동안 주 1회 현장을 점검하겠습니다.'],
               issue='2017. 6. 30.', office='시험시 예제구청장',
               clue_line="저는 공사장 바로 맞은편에서 '다온분식'을 운영하는 사장입니다.",
               account_line=('가게 앞 화분 파손 보상금은 ', '가상은행 302-0000-1234-56', '으로 보내 주십시오.')),
}


# ─────────────────────────────────────────── 쪽(page) 그리기
class Page:
    def __init__(self, doc_type):
        self.doc_type = doc_type
        self.img = Image.new('RGB', (W, H), 'white')
        self.d = ImageDraw.Draw(self.img)
        self.items = {}      # (field, form) -> style
        self.masks = []      # (bbox, style)
        self.clues = []      # 간접 단서 설명

    def reg(self, field, form, style):
        k = (field, form)
        if k in self.items and self.items[k] != style:
            raise ValueError(f'{self.doc_type} {k}: 같은 쪽에서 가림 방식이 다름')
        self.items[k] = style

    def text(self, xy, s, size=26, bold=False, fill='black', anchor='la'):
        f = font(size, bold)
        self.d.text(xy, s, font=f, fill=fill, anchor=anchor)
        return self.d.textbbox(xy, s, font=f, anchor=anchor)

    def item(self, field, form, style, xy, s, size=26, bold=False, fill='black', anchor='la'):
        self.reg(field, form, style)
        shown = ''.join('*' if ch not in ' -.,' else ch for ch in s) if style == 'star' else s
        bb = self.text(xy, shown, size, bold, fill, anchor)
        if style not in ('none', 'star'):
            self.masks.append(((bb[0] - 4, bb[1] - 5, bb[2] + 4, bb[3] + 5), style))
        return bb

    def mask_box(self, field, form, style, box):
        self.reg(field, form, style)
        if style not in ('none', 'star'):
            self.masks.append((box, style))

    def finish(self):
        for box, style in self.masks:
            box = tuple(int(v) for v in box)
            if style == 'black':
                self.d.rectangle(box, fill='black')
            elif style == 'white':  # 수정테이프: 흰 덮개 + 옅은 테두리 자국
                self.d.rectangle(box, fill=(252, 252, 250), outline=(200, 200, 196), width=2)
            elif style == 'highlight':
                ov = Image.new('RGBA', self.img.size, (0, 0, 0, 0))
                ImageDraw.Draw(ov).rectangle(box, fill=(255, 214, 0, 120))
                self.img = Image.alpha_composite(self.img.convert('RGBA'), ov).convert('RGB')
                self.d = ImageDraw.Draw(self.img)
            elif style == 'blur':
                region = self.img.crop(box).filter(ImageFilter.GaussianBlur(7))
                self.img.paste(region, box[:2])
            elif style == 'partial':  # 오른쪽 45%만 가림
                x0, y0, x1, y1 = box
                self.d.rectangle((x0 + int((x1 - x0) * 0.55), y0, x1, y1), fill='black')
        self.text((W // 2, H - 70), '※ 해커톤 테스트용 가상 문서입니다. 실존 인물·기관과 관계없습니다.', 19,
                  fill=(120, 120, 120), anchor='mm')
        return self


def degrade(page, angle=1.8, scale=0.55, blur=0.6, noise=10):
    """스캔·촬영본처럼: 기울임, 해상도 저하, 잡음, 대비 저하 (글자는 읽히는 수준)"""
    img = page.img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(244, 244, 240))
    img = img.resize((int(W * scale), int(H * scale)), Image.BILINEAR).resize((W, H), Image.BILINEAR)
    img = img.filter(ImageFilter.GaussianBlur(blur))
    px = img.load()
    for _ in range(9000):
        x, y = random.randrange(W), random.randrange(H)
        r, g, b = px[x, y]
        n = random.randint(-noise, noise)
        px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)))
    page.img = Image.blend(img, Image.new('RGB', (W, H), (236, 234, 226)), 0.12)
    return page


# ─────────────────────────────────────────── 서명·도장·사진
def signature(pg, x, y, name, style, size=64):
    """자필 서명처럼: 기울인 획 + 밑줄 꼬리 (field=name, form=handwriting)"""
    f = font(size)
    tw = pg.d.textbbox((0, 0), name, font=f)
    w, h = tw[2] - tw[0] + 60, tw[3] - tw[1] + 50
    layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ink = (25, 40, 110, 255)
    ld.text((20, 10), name, font=f, fill=ink)
    ld.text((21, 11), name, font=f, fill=ink)
    layer = layer.transform(layer.size, Image.AFFINE, (1, 0.35, -18, 0, 1, 0), resample=Image.BICUBIC)
    layer = layer.rotate(6, resample=Image.BICUBIC, expand=True)
    ld = ImageDraw.Draw(layer)
    lw, lh = layer.size
    ld.line([(10, lh - 22), (lw * 0.45, lh - 14), (lw - 8, lh - 34)], fill=ink, width=4)
    base = pg.img.convert('RGBA')
    base.alpha_composite(layer, (int(x), int(y)))
    pg.img = base.convert('RGB')
    pg.d = ImageDraw.Draw(pg.img)
    pg.mask_box('name', 'handwriting', style, (x - 4, y - 4, x + lw + 4, y + lh + 4))
    return (x, y, x + lw, y + lh)


def person_seal(pg, cx, cy, name, style, r=48):
    """개인 도장: 붉은 원 안에 성명 (field=name, form=seal)"""
    red = (200, 30, 30)
    pg.d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=red, width=5)
    n = len(name)
    for i, ch in enumerate(name):
        pg.text((cx, cy + (i - (n - 1) / 2) * 27), ch, 24, True, fill=red, anchor='mm')
    pg.mask_box('name', 'seal', style, (cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6))


def org_seal(pg, x, y, text1, text2, size=130):
    """기관 직인: 개인정보 아님, 점검 행 없음"""
    red = (200, 30, 30)
    pg.d.rectangle((x, y, x + size, y + size), outline=red, width=6)
    pg.d.rectangle((x + 10, y + 10, x + size - 10, y + size - 10), outline=red, width=2)
    pg.text((x + size // 2, y + size // 2 - 20), text1, 24, True, fill=red, anchor='mm')
    pg.text((x + size // 2, y + size // 2 + 22), text2, 24, True, fill=red, anchor='mm')


def photo(pg, x, y, style, w=190, h=240):
    pg.d.rectangle((x, y, x + w, y + h), fill=(210, 214, 220), outline=(140, 140, 140), width=2)
    pg.d.ellipse((x + w * 0.3, y + h * 0.16, x + w * 0.7, y + h * 0.52), fill=(120, 126, 136))
    pg.d.pieslice((x + w * 0.12, y + h * 0.56, x + w * 0.88, y + h * 1.25), 180, 360, fill=(120, 126, 136))
    pg.mask_box('photo', 'photo', style, (x - 4, y - 4, x + w + 4, y + h + 4))


def rrn_item(pg, style, xy, rrn, size):
    """주민등록번호. partial = 앞 6자리와 성별 자리만 보이고 뒤 6자리 가림"""
    if style == 'partial':
        pg.reg('resident_number', 'text', 'partial')
        bb = pg.text(xy, rrn, size)
        gx = pg.d.textbbox(xy, rrn[:8], font=font(size))[2]
        pg.masks.append(((gx + 2, bb[1] - 5, bb[2] + 4, bb[3] + 5), 'black'))
        return bb
    return pg.item('resident_number', 'text', style, xy, rrn, size)


# ─────────────────────────────────────────── 문서
NOTICE = {
    'A': dict(closed=['민원인의 성명(서명·도장 포함), 주민등록번호, 주소, 전화번호,', '계좌번호, 신분증 사진'],
              opened=['직무를 수행한 공무원의 성명·직위', '그 밖에 위 2에 적지 않은 내용'],
              rules=[('all', f, 'mask') for f in ('name', 'resident_number', 'address', 'phone', 'account_number',
                                                  'photo')] + [('all', 'official_name', 'keep')]),
    'B': dict(closed=['민원인의 주민등록번호, 주소, 전화번호, 계좌번호, 신분증 사진'],
              opened=['민원인의 성명(서명·도장 포함): 제3자 의견 청취 결과 공개에 동의함',
                      '직무를 수행한 공무원의 성명·직위', '그 밖에 위 2에 적지 않은 내용'],
              rules=[('all', f, 'mask') for f in ('resident_number', 'address', 'phone', 'account_number', 'photo')]
              + [('all', 'name', 'keep'), ('all', 'official_name', 'keep')]),
}
DEFAULT_RULES = NOTICE['A']['rules']
REQUIRED = ['complaint_form', 'reply_letter', 'id_card_copy']


def notice_page(p, kind):
    n = NOTICE[kind]
    pg = Page('decision_notice')
    pg.text((W // 2, 150), '정보공개 결정 통지서', 48, True, anchor='mm')
    pg.text((W // 2, 215), '(부분 공개)', 30, anchor='mm')
    pg.d.line((110, 265, W - 110, 265), fill='black', width=3)
    y = 310
    for label, val in (('접수번호', p['req']), ('접수일자', '2026. 10. 12.'),
                       ('청구 내용', f"{p['org']} '{p['subject']}' 민원 처리 관련 문서 일체"),
                       ('결정 내용', '부분 공개')):
        pg.text((130, y), label, 28, True)
        pg.text((330, y), val, 28)
        y += 58
    y += 30
    lines = [('1. 공개 대상 문서', True), ('   가. 민원 신청서 1부', False), ('   나. 민원 회신문 1부', False),
             ('   다. 신분증 사본(민원 신청서 첨부) 1부', False), ('', False),
             ('2. 비공개 부분 (공공기관의 정보공개에 관한 법률 제9조 제1항 제6호)', True)]
    lines += [('   ' + s, False) for s in n['closed']] + [('', False), ('3. 공개 부분', True)]
    lines += [('   ' + s, False) for s in n['opened']]
    lines += [('', False), ('4. 공개 방법: 전자파일(PDF) 교부', True)]
    for s, b in lines:
        if s:
            pg.text((130, y), s, 27, b)
        y += 52 if s else 26
    pg.text((W - 130, y + 70), p['mayor'], 34, True, anchor='ra')
    return pg.finish()


def complaint_form(p, st, layout=1, sealed=False, clue=False, account=None):
    g = lambda k: st.get(k, 'none')
    pg = Page('complaint_form')
    pg.text((W // 2, 140), '민 원 신 청 서', 56, True, anchor='mm')
    pg.text((W - 120, 210), '접수일 2026. 9. 21.', 22, anchor='ra')
    body = list(p['body'])
    if layout == 1:
        y = 270
        pg.d.line((110, y, W - 110, y), fill='black', width=3)
        y += 40
        pg.text((130, y), '신청인', 30, True)
        y += 60
        for label, field, val in (('성      명', 'name', p['name']), ('주민등록번호', 'resident_number', p['rrn']),
                                  ('주      소', 'address', p['addr']), ('전화번호', 'phone', p['phone'])):
            pg.text((160, y), label, 27)
            if field == 'resident_number':
                rrn_item(pg, g(field), (400, y), val, 27)
            else:
                pg.item(field, 'text', g(field), (400, y), val, 27)
            y += 56
        y += 20
        pg.d.line((110, y, W - 110, y), fill=(120, 120, 120), width=1)
        y += 30
        pg.text((130, y), '민원 제목', 28, True)
        pg.text((330, y), p['subject'], 28)
        y += 70
        pg.text((130, y), '민원 내용', 28, True)
        y += 56
        top_body = y
    else:  # 표 양식
        y = 260
        rows = [('성명', 'name', p['name']), ('주민등록번호', 'resident_number', p['rrn']),
                ('주소', 'address', p['addr']), ('전화번호', 'phone', p['phone']), ('민원 제목', None, p['subject'])]
        for label, field, val in rows:
            pg.d.rectangle((110, y, 400, y + 78), fill=(236, 238, 242), outline=(90, 90, 90), width=2)
            pg.d.rectangle((400, y, W - 110, y + 78), outline=(90, 90, 90), width=2)
            pg.text((255, y + 39), label, 27, True, anchor='mm')
            if field == 'resident_number':
                rrn_item(pg, g(field), (430, y + 22), val, 27)
            elif field:
                pg.item(field, 'text', g(field), (430, y + 22), val, 27)
            else:
                pg.text((430, y + 22), val, 27)
            y += 78
        pg.d.rectangle((110, y, W - 110, y + 60), fill=(236, 238, 242), outline=(90, 90, 90), width=2)
        pg.text((W // 2, y + 30), '민원 내용', 27, True, anchor='mm')
        y += 60
        top_body = y + 26
    y = top_body
    lines = body[:]
    if clue:
        lines.insert(0, p['clue_line'])
        pg.clues.append('본문의 상호·위치')
    for s in lines:
        pg.text((150, y), s, 25)
        y += 48
    if account:
        a, b, c = account
        bb = pg.text((150, y), a, 25)
        bb = pg.item('account_number', 'text', g('account_number'), (bb[2], y), b, 25)
        pg.text((bb[2] + 4, y), c, 25)
        y += 48
    if layout == 2:
        pg.d.rectangle((110, top_body - 26, W - 110, y + 20), outline=(90, 90, 90), width=2)
    y = max(y + 70, 1060)
    pg.text((W // 2, y), '위와 같이 민원을 신청합니다.', 28, anchor='mm')
    y += 80
    pg.text((W // 2, y), '2026년 9월 21일', 28, anchor='mm')
    y += 90
    bb = pg.text((430, y), '신청인', 30, True)
    sb = signature(pg, bb[2] + 30, y - 36, p['name'], g('handwriting'), size=56)
    lb = pg.text((sb[2] + 24, y + 4), '(서명 또는 인)', 22, fill=(90, 90, 90))
    if sealed:
        person_seal(pg, lb[2] + 80, y + 16, p['name'], g('seal'))
    y += 110
    pg.text((130, y), f"{p['mayor']} 귀하", 32, True)
    y += 90
    pg.d.line((110, y, W - 110, y), fill=(120, 120, 120), width=1)
    y += 26
    bb = pg.text((130, y), '접수 담당', 25, True)
    pg.item('official_name', 'text', g('official_name'), (bb[2] + 30, y), p['recv'], 25)
    return pg.finish()


def reply_letter(p, st):
    g = lambda k: st.get(k, 'none')
    pg = Page('reply_letter')
    pg.text((W // 2, 140), p['org'], 52, True, anchor='mm')
    pg.d.line((110, 210, W - 110, 210), fill=(30, 60, 130), width=5)
    y = 260
    pg.text((130, y), '수신', 28, True)
    bb = pg.item('name', 'text', g('name'), (260, y), p['name'], 28)
    pg.text((bb[2] + 12, y), '귀하', 28)
    y += 56
    pg.text((130, y), '주소', 28, True)
    pg.item('address', 'text', g('address'), (260, y), p['addr'], 28)
    y += 56
    pg.text((130, y), '제목', 28, True)
    pg.text((260, y), f"민원 처리 결과 알림 ({p['subject']})", 28)
    y += 90
    lines = ['1. 귀하의 가정에 행복이 가득하시기를 바랍니다.',
             f"2. 귀하께서 2026. 9. 21. 신청하신 민원의 처리 결과를 다음과 같이 알려 드립니다.", '']
    lines += ['   ' + s for s in p['reply']]
    lines += ['', '3. 더 궁금하신 점은 담당 부서로 문의해 주시기 바랍니다.  끝.']
    for s in lines:
        if s:
            pg.text((130, y), s, 25)
        y += 50 if s else 24
    y += 100
    bb = pg.text((W // 2, y), p['mayor'], 46, True, anchor='mm')
    org_seal(pg, bb[2] + 30, y - 66, p['org'] + '장', '의 인')
    y = 1380
    pg.d.line((110, y, W - 110, y), fill=(120, 120, 120), width=1)
    y += 30
    pg.text((130, y), f"시행  {p['dept']}-{random.randint(1000, 9999)} (2026. 9. 28.)", 24)
    y += 50
    bb = pg.text((130, y), '담당', 24, True)
    pg.item('official_name', 'text', g('official_name'), (bb[2] + 30, y), p['off'], 24)
    return pg.finish()


def id_card(p, st):
    g = lambda k: st.get(k, 'none')
    pg = Page('id_card_copy')
    pg.text((120, 120), '신분증 사본 (민원 신청서 첨부)', 30, True)
    x0, y0, x1, y1 = 170, 260, 1070, 820
    pg.d.rounded_rectangle((x0, y0, x1, y1), radius=36, fill=(240, 246, 252), outline=(110, 130, 160), width=4)
    pg.text((x0 + 60, y0 + 50), '주민등록증', 50, True, fill=(30, 50, 90))
    pg.item('name', 'text', g('name'), (x0 + 60, y0 + 150), p['name'], 40, True)
    rrn_item(pg, g('resident_number'), (x0 + 60, y0 + 225), p['rrn'], 36)
    a1, a2 = p['addr'].split(', ')
    pg.item('address', 'text', g('address'), (x0 + 60, y0 + 310), a1, 28)
    pg.item('address', 'text', g('address'), (x0 + 60, y0 + 355), a2, 28)
    pg.text((x0 + 380, y0 + 440), p['issue'], 26)
    pg.text((x0 + 340, y0 + 482), p['office'], 28, True)
    photo(pg, x1 - 260, y0 + 120, g('photo'))
    return pg.finish()


# ─────────────────────────────────────────── 케이스
C_HID = dict(name='black', handwriting='black', seal='black', resident_number='black', address='black',
             phone='black', account_number='black')
R_HID = dict(name='black', address='black')
I_HID = dict(name='black', resident_number='black', address='black', photo='black')


def restyle(d, style, **over):
    out = {k: style for k in d}
    out.update(over)
    return out


def bundle(p, kind='A', cf=None, rl=None, ic=None, layout=1, sealed=False, clue=False, account=False, drop=()):
    pages = [notice_page(p, kind)] if kind else []
    pages.append(complaint_form(p, cf or C_HID, layout, sealed, clue, p['account_line'] if account else None))
    if 'reply_letter' not in drop:
        pages.append(reply_letter(p, rl or R_HID))
    if 'id_card_copy' not in drop:
        pages.append(id_card(p, ic or I_HID))
    return pages


def cases():
    P = PERSONAS
    out = []

    def add(cid, s, kind, purpose, crit, pages, note):
        out.append(dict(id=cid, set=s, type=kind, purpose=purpose, criteria=crit, pages=pages, note=note))

    # S1: 결정통지서대로 다 가림 / 같은 문서 + 성명 공개 결정통지서
    add('case_01', 'S1', '단순', '결정통지서 기준대로 모두 가린 정상 공개본', 'A', bundle(P['S1']),
        '성명·서명·주민번호·주소·전화번호·사진은 검은 박스, 담당 공무원 성명·직위는 남김')
    add('case_07', 'S1', '결합', 'case_01과 같은 문서에 다른 결정통지서(B, 성명 공개) 적용 → 판정이 바뀌는지', 'B',
        bundle(P['S1'], 'B'), '결정통지서 B는 민원인 성명 공개 → 가린 성명·서명 4곳이 과잉 가림')
    # S2: 서명·도장 속 성명 노출 / 저품질 신분증 + 회신문 누락
    add('case_02', 'S2', '양식', '성명 글자는 가렸지만 자필 서명·도장에 성명이 남음', 'A',
        bundle(P['S2'], cf=dict(C_HID, handwriting='none', seal='none'), sealed=True),
        '민원 신청서 서명란의 자필 서명·개인 도장 노출 → 자동 가림 대상')
    p10 = bundle(P['S2'], sealed=True, ic=dict(name='black', resident_number='partial', address='none', photo='none'),
                 drop=('reply_letter',))
    p10[-1] = degrade(p10[-1], angle=2.4)
    add('case_10', 'S2', '저품질', '기울어진 저화질 신분증 스캔 + 공개 대상 문서(민원 회신문) 누락', 'A', p10,
        '주민번호 뒤 6자리만 가림(앞자리 노출), 주소·사진 노출, 민원 회신문 없음')
    # S3: 표 양식 + 흰 덮개·별표 + 회신문에만 성명 노출 / 형광펜 + 흐림
    cf3 = restyle(C_HID, 'white', resident_number='star', phone='star')
    add('case_03', 'S3', '양식', '표 양식 신청서, 흰색 수정테이프·별표 가림, 민원 회신문 수신란에만 성명 노출', 'A',
        bundle(P['S3'], cf=cf3, rl=dict(name='none', address='white'), ic=restyle(I_HID, 'white'), layout=2),
        '신청서·신분증은 모두 가렸지만 회신문 수신란 성명 노출 → 그 위치만 자동 가림')
    p6 = bundle(P['S3'], cf=dict(C_HID, resident_number='blur'), rl=dict(R_HID, name='highlight'), layout=2)
    p6[1] = degrade(p6[1], angle=-1.2, scale=0.6)
    add('case_06', 'S3', '저품질', '흐린 스캔 + 번진 주민번호(판독 불가) + 형광펜 덧칠(글자 비침)', 'A', p6,
        '신청서 주민번호가 번져 판독 불가 → 검토 필요, 회신문 수신 성명 위 형광펜 → 자동 가림')
    # S4: 공무원 성명 과잉 가림 / 결정통지서 없음
    add('case_04', 'S4', '예외', '공개해야 할 담당 공무원 성명·직위까지 가림(과잉 가림)', 'A',
        bundle(P['S4'], cf=dict(C_HID, official_name='black'), rl=dict(R_HID, official_name='black')),
        '신청서 접수 담당·회신문 담당 공무원 성명·직위 검은 박스')
    add('case_08', 'S4', '예외', '결정통지서 없이 문서만 넣어 기본 항목으로 점검', 'default',
        bundle(P['S4'], kind=None, ic=dict(I_HID, resident_number='none', photo='none'), drop=('reply_letter',)),
        '결정통지서 없음 → 기본 항목 적용·검토 필요, 신분증 주민번호·사진 노출 → 자동 가림')
    # S5: 신분증 사본 누락 / 계좌번호 노출 + 상호 단서
    cf5 = restyle(C_HID, 'star', handwriting='black')
    add('case_05', 'S5', '예외', '공개 대상 문서(신분증 사본) 누락', 'A',
        bundle(P['S5'], cf=cf5, rl=restyle(R_HID, 'star'), layout=2, drop=('id_card_copy',)),
        '신분증 사본 없음, 나머지는 별표로 기준대로 가림')
    cf9 = restyle(C_HID, 'white', account_number='none')
    add('case_09', 'S5', '결합', '본문 속 계좌번호 노출 + 상호·위치로 민원인을 특정할 수 있는 간접 단서', 'A',
        bundle(P['S5'], cf=cf9, rl=restyle(R_HID, 'white'), ic=restyle(I_HID, 'white'), layout=2, clue=True,
               account=True),
        '민원 내용의 계좌번호 노출 → 자동 가림, "맞은편 분식집 사장" 문장 → 검토 필요')
    return sorted(out, key=lambda c: c['id'])


# ─────────────────────────────────────────── 정답지
DOC_KO = dict(decision_notice='결정통지서', complaint_form='민원 신청서', reply_letter='민원 회신문',
              id_card_copy='신분증 사본')
FIELD_KO = dict(name='성명', resident_number='주민등록번호', address='주소', phone='전화번호',
                account_number='계좌번호', photo='사진', official_name='공무원 성명·직위')
FORM_ORDER = ['text', 'handwriting', 'seal', 'photo']
FIELD_ORDER = list(FIELD_KO)


def answer(c):
    p = PERSONAS[c['set']]
    if c['criteria'] == 'default':
        crit, rules, required, req_no = 'default', DEFAULT_RULES, [], ''
    else:
        crit, rules, required, req_no = 'decision_notice', NOTICE[c['criteria']]['rules'], REQUIRED, p['req']
    rmap = {f: r for _, f, r in rules}
    sub = []
    for pg in c['pages']:
        if pg.doc_type not in sub:
            sub.append(pg.doc_type)
    checks, reasons = [], []
    for i, pg in enumerate(c['pages'], 1):
        if pg.doc_type == 'decision_notice':
            continue
        rows = []
        for (field, form), style in pg.items.items():
            rule = rmap.get(field)
            if not rule:
                continue
            vis = VIS[style]
            status = STATUS[rule][vis]
            rows.append(dict(document_type=pg.doc_type, page=i, field=field, form=form, rule=rule,
                             visibility=vis, status=status))
            if status == '검토 필요':
                reasons.append(f"{DOC_KO[pg.doc_type]} {i}쪽 {FIELD_KO[field]} 판독 불가")
        rows.sort(key=lambda r: (FIELD_ORDER.index(r['field']), FORM_ORDER.index(r['form'])))
        checks += rows
        for cl in pg.clues:
            reasons.append(f"{DOC_KO[pg.doc_type]} {i}쪽 {cl}로 민원인을 특정할 수 있음")
    if crit == 'default':
        reasons.insert(0, '결정통지서가 없어 기본 항목으로 점검함')
    missing = [d for d in required if d not in sub]
    statuses = [r['status'] for r in checks]
    if missing or 'over_masked' in statuses:
        result = '수정 필요'
    elif reasons:
        result = '검토 필요'
    else:
        result = '공개 가능'
    return dict(request_number=req_no, criteria_source=crit,
                rules=[dict(document_type=d, field=f, rule=r) for d, f, r in rules],
                submitted_documents=sub, missing_documents=missing, checks=checks,
                review_reasons=reasons, result=result)


def main():
    os.makedirs(os.path.join(DATA, 'pages'), exist_ok=True)
    os.makedirs(ANS, exist_ok=True)
    manifest = []
    for c in cases():
        imgs = [pg.img for pg in c['pages']]
        pdf = os.path.join(DATA, c['id'] + '.pdf')
        imgs[0].save(pdf, save_all=True, append_images=imgs[1:], resolution=150)
        for i, im in enumerate(imgs, 1):
            im.save(os.path.join(DATA, 'pages', f"{c['id']}_p{i}.png"))
        a = answer(c)
        json.dump(a, open(os.path.join(ANS, c['id'] + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        manifest.append(dict(file=c['id'] + '.pdf', set=c['set'], type=c['type'], purpose=c['purpose'],
                             criteria=c['criteria'], documents=[pg.doc_type for pg in c['pages']], note=c['note'],
                             result=a['result'], n_checks=len(a['checks'])))
        print(c['id'], c['type'], len(imgs), '쪽', a['result'], 'checks', len(a['checks']),
              'missing', a['missing_documents'])
    json.dump(manifest, open(os.path.join(DATA, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
