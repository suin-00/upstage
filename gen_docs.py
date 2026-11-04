"""블라인드 채용 지원 서류 셀프 점검 — 테스트용 가상 서류 + 정답지 생성기.

모든 인물·학교·기관·번호는 가상이며 각 쪽 아래에 '해커톤 테스트용 가상 문서' 표기가 들어간다.
출력: dataset/case_XX.pdf, dataset/pages/case_XX_pN.png, answers/case_XX.json, dataset/manifest.json
"""
import json, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

random.seed(11)
W, H = 1240, 1754  # A4 @150dpi
# 한글 글꼴: 환경변수 MASKING_FONT / MASKING_FONT_BOLD(/ MASKING_FONT_INDEX)로 지정하거나,
# 아래 후보 중 처음 찾은 것을 쓴다. (경로, 굵은 글꼴 경로, TTC 내부 번호)
FONT_CANDIDATES = [
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
     '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 1),   # Linux (fonts-noto-cjk), 1 = KR
    ('/System/Library/Fonts/AppleSDGothicNeo.ttc',
     '/System/Library/Fonts/AppleSDGothicNeo.ttc', 0),             # macOS
    ('C:/Windows/Fonts/malgun.ttf', 'C:/Windows/Fonts/malgunbd.ttf', 0),  # Windows
]


def _pick_font():
    env = os.environ.get('MASKING_FONT')
    if env:
        return env, os.environ.get('MASKING_FONT_BOLD', env), int(os.environ.get('MASKING_FONT_INDEX', '0'))
    for reg, bold, idx in FONT_CANDIDATES:
        if os.path.exists(reg):
            return reg, bold if os.path.exists(bold) else reg, idx
    raise SystemExit('한글 글꼴을 찾지 못했어요. MASKING_FONT 환경변수로 .ttf/.ttc/.otf 경로를 지정해 주세요.')


FONT, FONT_B, FONT_INDEX = _pick_font()
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'dataset')
ANS = os.path.join(ROOT, 'answers')

_fonts = {}


def font(size, bold=False):
    k = (size, bold)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(FONT_B if bold else FONT, size, index=FONT_INDEX)
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

# ─────────────────────────────────────────── 가상 인물 5세트
PERSONAS = {
    'S1': dict(name='김가람', birth='1999년 03월 15일', rrn='990315-1845273', school='가상대학교',
               en='GASANG UNIVERSITY', domain='gasang.ac.kr', mail='garam.kim', sid='2018123456',
               dept='컴퓨터공학과', degree='공학사', adm='2018년 03월 02일', grad='2024년 02월 23일', y0=2018,
               addr=('가상시 예시구 연습로 12', '101동 1001호'), lic='정보처리기사', lic_no='24201030123P',
               saddr='가상시 북구 대학로 80', stel='012-345-6789', issue='2019. 4. 3.', office='가상시 예시구청장'),
    'S2': dict(name='이나래', birth='2000년 07월 21일', rrn='000721-4123856', school='예시대학교',
               en='YESI UNIVERSITY', domain='yesi.ac.kr', mail='narae.lee', sid='2019234567',
               dept='경영학과', degree='경영학사', adm='2019년 03월 04일', grad='2025년 02월 21일', y0=2019,
               addr=('예시시 모의구 샘플길 45-3', '2층'), lic='사회조사분석사 2급', lic_no='25301120456Q',
               saddr='예시시 동구 학교로 21', stel='023-456-7890', issue='2020. 8. 11.', office='예시시 모의구청장'),
    'S3': dict(name='박다솜', birth='1998년 11월 02일', rrn='981102-2736145', school='샘플대학교',
               en='SAMPLE UNIVERSITY', domain='sample.ac.kr', mail='dasom.park', sid='2017345678',
               dept='전자공학과', degree='공학사', adm='2017년 03월 02일', grad='2023년 08월 18일', y0=2017,
               addr=('샘플시 가상구 표본대로 230', '305호'), lic='전기기사', lic_no='23401250789R',
               saddr='샘플시 서구 캠퍼스길 7', stel='034-567-8901', issue='2018. 1. 22.', office='샘플시 가상구청장'),
    'S4': dict(name='최하늘', birth='2001년 01월 30일', rrn='010130-3584216', school='모의대학교',
               en='MOUI UNIVERSITY', domain='moui.ac.kr', mail='haneul.choi', sid='2020456789',
               dept='산업디자인학과', degree='디자인학사', adm='2020년 03월 02일', grad='2026년 02월 20일', y0=2020,
               addr=('모의시 시험구 연습로 8', '1203호'), lic='컬러리스트기사', lic_no='26101030234S',
               saddr='모의시 남구 배움로 55', stel='045-678-9012', issue='2021. 3. 9.', office='모의시 시험구청장'),
    'S5': dict(name='정보람', birth='1997년 05월 09일', rrn='970509-2615384', school='시험대학교',
               en='SIHEOM UNIVERSITY', domain='siheom.ac.kr', mail='boram.jung', sid='2016567890',
               dept='화학공학과', degree='공학사', adm='2016년 03월 02일', grad='2022년 02월 18일', y0=2016,
               addr=('시험시 예제구 시험로 77', '3층'), lic='화공기사', lic_no='22501040567T',
               saddr='시험시 북구 연구로 3', stel='056-789-0123', issue='2017. 6. 30.', office='시험시 예제구청장'),
}

COURSES = ['자료구조', '선형대수', '확률과 통계', '글쓰기와 소통', '회로이론', '경영학원론', '데이터베이스', '운영체제',
           '전공종합설계', '공학윤리', '마케팅', '재무관리', '인공지능', '디지털신호처리', '캡스톤디자인', '현장실습']
GRADES = ['A+', 'A0', 'B+', 'A+', 'B0', 'A0', 'A+', 'B+']


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

    def width(self, s, size=26, bold=False):
        b = self.d.textbbox((0, 0), s, font=font(size, bold))
        return b[2] - b[0]

    def item(self, field, form, style, xy, s, size=26, bold=False, fill='black', anchor='la'):
        self.reg(field, form, style)
        shown = ''.join('*' if ch not in ' -.' else ch for ch in s) if style == 'star' else s
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
            elif style == 'partial':  # 오른쪽 60%만 가림
                x0, y0, x1, y1 = box
                self.d.rectangle((x0 + int((x1 - x0) * 0.4), y0, x1, y1), fill='black')
        self.text((W // 2, H - 70), '※ 해커톤 테스트용 가상 문서입니다. 실존 인물·학교·기관과 관계없습니다.', 19,
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


# ─────────────────────────────────────────── 학교 표지 요소
def emblem(pg, cx, cy, p, style, r=66):
    pg.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(222, 232, 248), outline=(30, 60, 130), width=5)
    pg.d.ellipse((cx - r + 12, cy - r + 12, cx + r - 12, cy + r - 12), outline=(30, 60, 130), width=2)
    pg.text((cx, cy - 12), p['en'][0], 46, True, fill=(30, 60, 130), anchor='mm')
    pg.text((cx, cy + 30), p['school'], 17, True, fill=(30, 60, 130), anchor='mm')
    pg.mask_box('school_name', 'logo', style, (cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6))


def seal(pg, x, y, text1, text2, field=None, form=None, style='none', size=138):
    red = (200, 30, 30)
    pg.d.rectangle((x, y, x + size, y + size), outline=red, width=6)
    pg.d.rectangle((x + 10, y + 10, x + size - 10, y + size - 10), outline=red, width=2)
    pg.text((x + size // 2, y + size // 2 - 22), text1, 22 if len(text1) <= 5 else 18, True, fill=red, anchor='mm')
    pg.text((x + size // 2, y + size // 2 + 24), text2, 24, True, fill=red, anchor='mm')
    if field:
        pg.mask_box(field, form, style, (x - 6, y - 6, x + size + 6, y + size + 6))


def watermark(pg, p):
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text((W // 2, H // 2), p['school'], font=font(190, True), fill=(150, 160, 190, 60), anchor='mm')
    layer = layer.rotate(28, resample=Image.BICUBIC)
    pg.img = Image.alpha_composite(pg.img.convert('RGBA'), layer).convert('RGB')
    pg.d = ImageDraw.Draw(pg.img)
    pg.reg('school_name', 'watermark', 'none')


def photo(pg, x, y, style, w=190, h=240):
    pg.d.rectangle((x, y, x + w, y + h), fill=(210, 214, 220), outline=(140, 140, 140), width=2)
    pg.d.ellipse((x + w * 0.3, y + h * 0.16, x + w * 0.7, y + h * 0.52), fill=(120, 126, 136))
    pg.d.pieslice((x + w * 0.12, y + h * 0.56, x + w * 0.88, y + h * 1.25), 180, 360, fill=(120, 126, 136))
    pg.mask_box('photo', 'photo', style, (x - 4, y - 4, x + w + 4, y + h + 4))


# ─────────────────────────────────────────── 서류
NOTICE = {
    'A': dict(
        title='2026 가상시설관리공단 신입사원 블라인드 채용', sub='제출 서류 및 블라인드 처리 안내',
        lines=[('1. 제출 서류 (PDF 1개 파일로 제출)', True),
               ('   가. 최종학교 졸업증명서 1부', False), ('   나. 성적증명서 1부', False),
               ('   다. 자격증 사본 1부', False), ('   라. 신분증 사본 1부', False), ('', False),
               ('2. 블라인드 처리 기준', True),
               ('   가. 졸업증명서·성적증명서: 학교명(로고·직인·영문 표기·워터마크 포함),', False),
               ('       학번, 입학일자, 졸업일자, 생년월일을 가립니다.', False),
               ('   나. 신분증 사본: 주민등록번호 뒷자리, 주소, 사진을 가립니다.', False),
               ('   다. 자격증 사본: 성명과 자격 종목은 확인을 위해 가리지 않습니다.', False),
               ('   라. 위에 적지 않은 항목은 가리지 않아도 됩니다.', False), ('', False),
               ('3. 유의 사항', True),
               ('   블라인드 처리를 지키지 않은 서류는 서류전형에서 감점될 수 있습니다.', False)],
        required=['graduation_certificate', 'transcript', 'license_copy', 'id_card_copy'],
        rules=[(d, f, 'mask') for d in ('graduation_certificate', 'transcript')
               for f in ('school_name', 'student_id', 'admission_date', 'graduation_date', 'birth_date')]
        + [('id_card_copy', f, 'mask') for f in ('resident_number_back', 'address', 'photo')]
        + [('license_copy', f, 'keep') for f in ('name', 'license_type')]),
    'B': dict(
        title='2026 가상문화재단 직원 공개채용', sub='제출 서류 안내',
        lines=[('1. 제출 서류', True),
               ('   가. 졸업증명서 1부', False), ('   나. 성적증명서 1부', False), ('   다. 신분증 사본 1부', False),
               ('', False),
               ('2. 블라인드 기준', True),
               ('   가. 졸업증명서·성적증명서: 학교명(로고·직인·영문 표기 포함), 학번,', False),
               ('       성명을 가립니다.', False),
               ('   나. 성적증명서의 학기별 연도(예: 2019학년도)도 가립니다.', False),
               ('   다. 신분증 사본: 주민등록번호 뒷자리와 사진을 가립니다.', False), ('', False),
               ('3. 접수: 2026. 11. 27.(금) 18:00까지 온라인 접수', True)],
        required=['graduation_certificate', 'transcript', 'id_card_copy'],
        rules=[(d, f, 'mask') for d in ('graduation_certificate', 'transcript')
               for f in ('school_name', 'student_id', 'name')]
        + [('transcript', 'semester_year', 'mask')]
        + [('id_card_copy', f, 'mask') for f in ('resident_number_back', 'photo')]),
}

REQUEST_ITEMS = [('학교명(로고·직인·영문 표기 포함)', 'school_name'), ('학번', 'student_id'),
                 ('입학·졸업일자', None), ('생년월일', 'birth_date'), ('주민등록번호 뒷자리', 'resident_number_back'),
                 ('주소', 'address'), ('사진', 'photo'), ('성명', 'name')]


def notice_page(kind):
    n = NOTICE[kind]
    pg = Page('notice')
    pg.text((W // 2, 150), n['title'], 44, True, anchor='mm')
    pg.text((W // 2, 215), n['sub'], 34, True, anchor='mm')
    pg.d.line((110, 265, W - 110, 265), fill='black', width=3)
    y = 320
    for s, b in n['lines']:
        if s:
            pg.text((130, y), s, 28, b)
        y += 56 if s else 30
    pg.text((W - 130, y + 60), '가상기관 인사팀', 28, True, anchor='ra')
    return pg.finish()


def request_page(checked):
    pg = Page('masking_request')
    pg.text((W // 2, 150), '블라인드 가림 요청서', 46, True, anchor='mm')
    pg.text((W // 2, 215), '(채용 공고문 없이 제출 서류를 점검할 때 작성)', 26, anchor='mm')
    pg.d.line((110, 265, W - 110, 265), fill='black', width=3)
    pg.text((130, 320), '제출처: 미정 (공고문 없음)', 28)
    pg.text((130, 380), '필수 제출 서류: 지정하지 않음', 28)
    pg.text((130, 470), '가릴 항목 (체크한 항목만 가립니다)', 30, True)
    y = 540
    for label, field in REQUEST_ITEMS:
        on = field in checked
        pg.d.rectangle((150, y, 186, y + 36), outline='black', width=3)
        if on:
            pg.text((168, y + 18), '✓', 32, True, anchor='mm')
        pg.text((210, y + 2), label, 28)
        y += 66
    pg.text((130, y + 40), '체크하지 않은 항목은 그대로 둡니다.', 26)
    return pg.finish()


def grad_cert(p, st, layout=1, wm=False):
    """st: field/form -> style. 기본 'none'."""
    g = lambda k: st.get(k, 'none')
    pg = Page('graduation_certificate')
    if wm:
        watermark(pg, p)
    if layout == 1:
        pg.text((W - 120, 90), '제 2026-01234 호', 22, anchor='ra')
        emblem(pg, 190, 190, p, g('logo'))
        pg.item('school_name', 'text', g('school'), (W // 2, 165), p['school'], 54, True, anchor='mm')
        pg.item('school_name', 'english', g('english'), (W // 2, 232), p['en'], 26, anchor='mm')
        pg.text((W // 2, 360), '졸 업 증 명 서', 62, True, anchor='mm')
        y = 500
        rows = [('성      명', 'name', p['name']), ('생 년 월 일', 'birth_date', p['birth']),
                ('학      번', 'student_id', p['sid']), ('학과(전공)', None, p['dept']),
                ('학      위', None, p['degree']), ('입 학 일 자', 'admission_date', p['adm']),
                ('졸 업 일 자', 'graduation_date', p['grad'])]
        for label, field, val in rows:
            pg.text((230, y), label, 30)
            pg.text((420, y), ':', 30)
            if field:
                pg.item(field, 'text', g(field), (460, y), val, 30)
            else:
                pg.text((460, y), val, 30)
            y += 82
        pg.text((W // 2, 1150), '위 사람은 본교 소정의 전 과정을 이수하고 졸업하였음을 증명합니다.', 30, anchor='mm')
        pg.text((W // 2, 1290), '2026년 10월 28일', 32, anchor='mm')
        sw = pg.width(p['school'], 40, True) + pg.width('  총  장', 40, True)
        x0 = W // 2 - sw // 2 - 60
        bb = pg.item('school_name', 'text', g('school'), (x0, 1400), p['school'], 40, True)
        bb2 = pg.text((bb[2], 1400), '  총  장', 40, True)
        seal(pg, bb2[2] + 50, 1355, p['school'], '총장의인', 'school_name', 'seal', g('seal'))
    else:  # 표 양식
        pg.text((120, 130), '졸업증명서', 56, True)
        pg.text((W - 120, 150), 'No. 2026-5678', 22, anchor='ra')
        pg.d.line((120, 225, W - 120, 225), fill=(40, 40, 40), width=4)
        y = 290
        rows = [('성명', 'name', p['name']), ('생년월일', 'birth_date', p['birth']), ('소속', None, p['dept']),
                ('학번', 'student_id', p['sid']), ('입학일자', 'admission_date', p['adm']),
                ('졸업일자', 'graduation_date', p['grad']), ('학위', None, p['degree'])]
        for label, field, val in rows:
            pg.d.rectangle((120, y, 400, y + 80), fill=(236, 238, 242), outline=(90, 90, 90), width=2)
            pg.d.rectangle((400, y, W - 120, y + 80), outline=(90, 90, 90), width=2)
            pg.text((260, y + 40), label, 28, True, anchor='mm')
            if field:
                pg.item(field, 'text', g(field), (430, y + 22), val, 28)
            else:
                pg.text((430, y + 22), val, 28)
            y += 80
        pg.text((120, y + 70), '위 사람은 본교의 학위과정을 마치고 위와 같이 졸업하였음을 증명함.', 28)
        pg.text((120, y + 130), '발급일: 2026년 10월 27일', 26)
        by = 1290
        emblem(pg, 220, by + 40, p, g('logo'), r=62)
        pg.item('school_name', 'text', g('school'), (320, by - 10), p['school'], 46, True)
        pg.item('school_name', 'english', g('english'), (322, by + 58), p['en'], 24)
        bb = pg.text((700, by - 6), '총장', 44, True)
        seal(pg, bb[2] + 60, by - 40, p['school'], '총장의인', 'school_name', 'seal', g('seal'))
    return pg.finish()


def transcript(p, st1, st2, email=False, clue=False):
    pages = []
    sems = [(p['y0'] + i // 2, i % 2 + 1) for i in range(8)]
    for n, st in ((1, st1), (2, st2)):
        g = lambda k: st.get(k, 'none')
        pg = Page('transcript')
        bb = pg.item('school_name', 'text', g('school'), (120, 110), p['school'], 44, True)
        pg.text((bb[2] + 14, 110), '성적증명서', 44, True)
        pg.text((W - 120, 126), f'({n}/2)', 24, anchor='ra')
        pg.d.line((120, 190, W - 120, 190), fill='black', width=3)
        if n == 1:
            y = 220
            pg.text((120, y), '성명', 26, True)
            pg.item('name', 'text', g('name'), (250, y), p['name'], 26)
            pg.text((640, y), '학번', 26, True)
            pg.item('student_id', 'text', g('student_id'), (770, y), p['sid'], 26)
            y += 54
            pg.text((120, y), '생년월일', 26, True)
            pg.item('birth_date', 'text', g('birth_date'), (250, y), p['birth'], 26)
            pg.text((640, y), '학과', 26, True)
            pg.text((770, y), p['dept'], 26)
            y += 54
            pg.text((120, y), '입학일자', 26, True)
            pg.item('admission_date', 'text', g('admission_date'), (250, y), p['adm'], 26)
            pg.text((640, y), '졸업일자', 26, True)
            pg.item('graduation_date', 'text', g('graduation_date'), (770, y), p['grad'], 26)
            y += 54
            if email:
                pg.text((120, y), '이메일', 26, True)
                pg.item('school_name', 'email', g('email'), (250, y), f"{p['mail']}@{p['domain']}", 26)
                y += 54
            top, rng = y + 30, sems[:4]
        else:
            pg.text((120, 220), '학번', 26, True)
            pg.item('student_id', 'text', g('student_id'), (200, 220), p['sid'], 26)
            pg.text((560, 220), '성명', 26, True)
            pg.item('name', 'text', g('name'), (640, 220), p['name'], 26)
            top, rng = 300, sems[4:]
        xs = [120, 450, 900, 1000, W - 120]
        pg.d.rectangle((xs[0], top, xs[-1], top + 54), fill=(232, 232, 232), outline='black', width=2)
        for i, h in enumerate(['학년도·학기', '교과목명', '학점', '성적']):
            pg.text(((xs[i] + xs[i + 1]) // 2, top + 27), h, 24, True, anchor='mm')
        y = top + 54
        for si, (yr, sm) in enumerate(rng):
            for ci in range(2):
                pg.d.rectangle((xs[0], y, xs[-1], y + 52), outline=(80, 80, 80), width=1)
                if ci == 0:
                    bb = pg.item('semester_year', 'text', g('semester_year'), (140, y + 12), f'{yr}학년도', 24)
                    pg.text((bb[2] + 10, y + 12), f'{sm}학기', 24)
                cn = COURSES[(si * 2 + ci + (n - 1) * 8 + len(p['name'])) % len(COURSES)]
                pg.text((470, y + 12), cn, 24)
                pg.text((950, y + 26), '3', 24, anchor='mm')
                pg.text((1060, y + 26), GRADES[(si * 2 + ci) % len(GRADES)], 24, anchor='mm')
                y += 52
        for xx in xs:
            pg.d.line((xx, top, xx, y), fill=(80, 80, 80), width=1)
        if n == 2:
            pg.text((120, y + 40), '총 취득학점 130 / 평점평균 3.87 (4.5 만점)', 26, True)
            pg.text((120, y + 130), '2026년 10월 28일', 26)
            bb = pg.item('school_name', 'text', g('school'), (120, y + 190), p['school'], 30, True)
            pg.text((bb[2] + 12, y + 190), '학사지원팀', 30, True)
            if clue:
                pg.text((120, H - 160), f"{p['saddr']} · 대표전화 {p['stel']}", 22, fill=(70, 70, 70))
                pg.clues.append('학교 주소·대표전화')
        pages.append(pg.finish())
    return pages


def license_copy(p, st, blur_type=False):
    g = lambda k: st.get(k, 'none')
    pg = Page('license_copy')
    pg.d.rectangle((140, 180, W - 140, 1300), outline=(30, 80, 60), width=8)
    pg.d.rectangle((160, 200, W - 160, 1280), outline=(30, 80, 60), width=2)
    pg.text((W // 2, 300), '국가기술자격증', 58, True, fill=(20, 70, 50), anchor='mm')
    pg.text((W // 2, 370), 'National Technical Qualification', 24, fill=(60, 90, 80), anchor='mm')
    y = 480
    rows = [('자격종목', 'license_type', p['lic']), ('성      명', 'name', p['name']),
            ('생년월일', 'birth_date', p['birth']), ('자격번호', None, p['lic_no']),
            ('합격연월일', None, '2024년 06월 14일')]
    for label, field, val in rows:
        pg.text((260, y), label, 32, True)
        style = 'blur' if (blur_type and field == 'license_type') else g(field)
        if field:
            pg.item(field, 'text', style, (500, y), val, 32)
        else:
            pg.text((500, y), val, 32)
        y += 95
    pg.text((W // 2, 1010), '위 사람은 국가기술자격법에 따른 자격을 취득하였음을 증명합니다.', 26, anchor='mm')
    pg.text((W // 2, 1080), '2024년 07월 01일', 28, anchor='mm')
    bb = pg.text((W // 2 - 60, 1170), '가상인력공단 이사장', 34, True, anchor='mm')
    seal(pg, bb[2] + 30, 1110, '가상인력', '공단인', size=120)
    return pg.finish()


def id_card(p, st):
    g = lambda k: st.get(k, 'none')
    pg = Page('id_card_copy')
    pg.text((120, 120), '신분증 사본', 30, True)
    x0, y0, x1, y1 = 170, 260, 1070, 820
    pg.d.rounded_rectangle((x0, y0, x1, y1), radius=36, fill=(240, 246, 252), outline=(110, 130, 160), width=4)
    pg.text((x0 + 60, y0 + 50), '주민등록증', 50, True, fill=(30, 50, 90))
    pg.item('name', 'text', g('name'), (x0 + 60, y0 + 150), p['name'], 40, True)
    front, back = p['rrn'].split('-')
    bb = pg.text((x0 + 60, y0 + 225), front + '-', 36)
    rs = g('resident_number_back')
    if rs == 'partial':  # 성별 자리만 보이고 뒤 6자리 가림
        pg.reg('resident_number_back', 'text', 'partial')
        b1 = pg.text((bb[2], y0 + 225), back, 36)
        gx = pg.d.textbbox((bb[2], y0 + 225), back[0], font=font(36))[2]
        pg.masks.append(((gx + 2, b1[1] - 5, b1[2] + 4, b1[3] + 5), 'black'))
    else:
        pg.item('resident_number_back', 'text', rs, (bb[2], y0 + 225), back, 36)
    pg.item('address', 'text', g('address'), (x0 + 60, y0 + 310), p['addr'][0], 28)
    pg.item('address', 'text', g('address'), (x0 + 60, y0 + 355), p['addr'][1], 28)
    pg.text((x0 + 380, y0 + 440), p['issue'], 26)
    pg.text((x0 + 340, y0 + 482), p['office'], 28, True)
    photo(pg, x1 - 260, y0 + 120, g('photo'))
    return pg.finish()


# ─────────────────────────────────────────── 케이스
HID = dict(school='black', logo='black', english='black', seal='black', student_id='black',
           admission_date='black', graduation_date='black', birth_date='black')
IDH = dict(resident_number_back='black', address='black', photo='black')


def with_style(d, style):
    return {k: style for k in d}


def bundle_A(p, gs=None, t1=None, t2=None, lic=None, ids=None, layout=1, wm=False, email=False, clue=False,
             blur_type=False, drop=()):
    pages = [notice_page('A')]
    if 'graduation_certificate' not in drop:
        pages.append(grad_cert(p, gs or HID, layout, wm))
    if 'transcript' not in drop:
        pages += transcript(p, t1 or HID, t2 or HID, email, clue)
    if 'license_copy' not in drop:
        pages.append(license_copy(p, lic or {}, blur_type))
    if 'id_card_copy' not in drop:
        pages.append(id_card(p, ids or IDH))
    return pages


def cases():
    P = PERSONAS
    out = []

    def add(cid, s, kind, purpose, crit, pages, note):
        out.append(dict(id=cid, set=s, type=kind, purpose=purpose, criteria=crit, pages=pages, note=note))

    # S1: 정상 / 같은 서류 + 다른 공고
    s1_docs = lambda: bundle_A(P['S1'])[1:]
    add('case_01', 'S1', '단순', '공고 기준대로 모두 가린 정상 제출', 'A', bundle_A(P['S1']),
        '학교명·학번·입학/졸업일·생년월일·주민번호 뒷자리·주소·사진 모두 검은 박스')
    add('case_07', 'S1', '결합', 'case_01과 같은 서류에 다른 공고(B) 적용 → 기준에 따라 판정이 바뀌는지', 'B',
        [notice_page('B')] + s1_docs(), '공고 B는 성명·학기별 연도도 가리라고 함 → 노출된 성명·연도는 자동 가림')
    # S2: 학교 표지 요소 노출 / 저품질 신분증 + 누락
    gs2 = dict(HID, logo='none', english='none', seal='none')
    add('case_02', 'S2', '양식', '학교명 글자는 가렸지만 로고·영문명·직인·워터마크에 학교명이 남음', 'A',
        bundle_A(P['S2'], gs=gs2, wm=True), '졸업증명서 로고·영문 표기·직인·워터마크 노출 → 자동 가림 대상')
    p10 = bundle_A(P['S2'], ids=dict(resident_number_back='partial', address='none', photo='none'),
                   drop=('transcript',))
    p10[-1] = degrade(p10[-1], angle=2.4)
    add('case_10', 'S2', '저품질', '기울어진 저화질 신분증 스캔 + 필수 서류(성적증명서) 누락', 'A', p10,
        '주민번호 성별 자리 노출(일부 가림), 주소·사진 노출, 성적증명서 없음')
    # S3: 표 양식 + 쪽별 가림 차이 / 반투명 덧칠 + 흐림
    w = lambda d: with_style(d, 'white')
    t1s3 = dict(w(HID), student_id='star')
    t2s3 = dict(w(HID), student_id='none')
    add('case_03', 'S3', '양식', '표 양식 졸업증명서, 흰색 덮개·별표 가림, 성적증명서 2쪽만 학번 노출', 'A',
        bundle_A(P['S3'], gs=w(HID), t1=t1s3, t2=t2s3, ids=w(IDH), layout=2),
        '성적증명서 1쪽 학번은 별표, 2쪽 학번은 그대로 → 2쪽만 자동 가림')
    p6 = bundle_A(P['S3'], t2=dict(HID, school='highlight'), blur_type=True)
    p6[4] = degrade(p6[4], angle=-1.2, scale=0.6)
    add('case_06', 'S3', '저품질', '반투명 형광펜 덧칠 + 흐린 스캔으로 필수 정보 판독 불가', 'A', p6,
        '성적증명서 2쪽 학교명 위 형광펜(글자 비침), 자격증 자격종목 흐림')
    # S4: 과도한 가림 / 공고문 없음
    add('case_04', 'S4', '예외', '남겨야 할 성명·자격 종목까지 가림(과도한 가림)', 'A',
        bundle_A(P['S4'], lic=dict(name='black', license_type='black')), '자격증 사본의 성명·자격종목 검은 박스')
    req = ('school_name', 'student_id', 'resident_number_back', 'photo')
    gs8 = dict(school='black', english='black', seal='black', logo='none', student_id='black')
    p8 = [request_page(req), grad_cert(P['S4'], gs8), id_card(P['S4'], dict(resident_number_back='none',
                                                                             photo='black'))]
    add('case_08', 'S4', '예외', '공고문 없이 가림 요청서로 점검', 'request', p8,
        '요청서: 학교명·학번·주민번호 뒷자리·사진 체크. 로고·주민번호 뒷자리 노출 → 자동 가림, 기준 미확인 → 검토 필요')
    # S5: 누락 / 이메일 도메인 + 간접 단서
    st = lambda d: with_style(d, 'star')
    gs5 = dict(HID, student_id='star', birth_date='star', admission_date='star', graduation_date='star')
    add('case_05', 'S5', '예외', '필수 서류(자격증 사본) 누락', 'A',
        bundle_A(P['S5'], gs=gs5, t1=gs5, t2=gs5, drop=('license_copy',)), '자격증 사본 없음, 나머지는 기준대로 가림')
    add('case_09', 'S5', '결합', '학교 이메일 도메인 노출 + 학교 주소·전화번호(간접 단서)', 'A',
        bundle_A(P['S5'], gs=w(HID), t1=dict(w(HID), email='none'), t2=w(HID), ids=w(IDH), layout=2,
                 email=True, clue=True),
        '성적증명서 1쪽 이메일(@siheom.ac.kr) 노출 → 자동 가림, 2쪽 하단 학교 주소·전화 → 검토 필요')
    return sorted(out, key=lambda c: c['id'])


# ─────────────────────────────────────────── 정답지
DOC_KO = dict(notice='공고문', masking_request='가림 요청서', graduation_certificate='졸업증명서',
              transcript='성적증명서', license_copy='자격증 사본', id_card_copy='신분증 사본')
FIELD_KO = dict(school_name='학교명', student_id='학번', admission_date='입학일자', graduation_date='졸업일자',
                birth_date='생년월일', resident_number_back='주민등록번호 뒷자리', address='주소', photo='사진',
                name='성명', license_type='자격 종목', semester_year='학기별 연도')
FORM_ORDER = ['text', 'logo', 'seal', 'watermark', 'english', 'email', 'photo']
FIELD_ORDER = list(FIELD_KO)


def answer(c):
    p = PERSONAS[c['set']]
    if c['criteria'] == 'request':
        crit = 'masking_request'
        req = [f for f in ('school_name', 'student_id', 'resident_number_back', 'photo')]
        rules = [('all', f, 'mask') for f in req]
        required = []
    else:
        crit = 'notice'
        rules = NOTICE[c['criteria']]['rules']
        required = NOTICE[c['criteria']]['required']
    rmap = {(d, f): r for d, f, r in rules}
    sub = []
    for pg in c['pages']:
        if pg.doc_type not in sub:
            sub.append(pg.doc_type)
    checks, reasons = [], []
    for i, pg in enumerate(c['pages'], 1):
        rows = []
        for (field, form), style in pg.items.items():
            rule = rmap.get((pg.doc_type, field)) or rmap.get(('all', field))
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
            reasons.append(f"{DOC_KO[pg.doc_type]} {i}쪽 하단 {cl}로 학교를 짐작할 수 있음")
    if crit == 'masking_request':
        reasons.insert(0, '공고문이 없어 가림 요청서 기준으로만 점검함')
    missing = [d for d in required if d not in sub]
    statuses = [r['status'] for r in checks]
    if missing or 'over_masked' in statuses:
        result = '보완 필요'
    elif reasons:
        result = '검토 필요'
    else:
        result = '통과'
    name_masked = any(f == 'name' and r == 'mask' for _, f, r in rules)
    name = '' if name_masked else p['name']
    return dict(applicant_name=name, criteria_source=crit,
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
                             criteria=a['criteria_source'] if c['criteria'] == 'request' else f"notice({c['criteria']})",
                             documents=[pg.doc_type for pg in c['pages']], note=c['note'], result=a['result'],
                             n_checks=len(a['checks'])))
        print(c['id'], c['type'], len(imgs), '쪽', a['result'], 'checks', len(a['checks']), 'missing', a['missing_documents'])
    json.dump(manifest, open(os.path.join(DATA, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
