"""제출 서류 마스킹 검수 에이전트 - 테스트용 가상 서류 + 정답지 생성기.

모든 인물, 번호, 기관은 가상이며 각 문서에 '테스트용 가상 문서' 표기가 들어간다.
출력: dataset/case_XX/{bundle.pdf, pages/*.png, answer.json, truth_boxes.json}
"""
import json, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

random.seed(7)
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
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dataset')


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size, index=FONT_INDEX)


# ---------------------------------------------------------------- personas
PERSONAS = {
    'P1': dict(name='김민준', rrn='990315-1478263', addr='테스트시 가상구 예시로 12, 101동 1001호',
               bank='110-482-736519', school_id='2019123456', dept='컴퓨터학부', grade='4',
               birth='1999년 03월 15일',
               family=[('모', '이서연', '720811-2593104'), ('동생', '김하준', '030127-3816452')]),
    'P2': dict(name='박지우', rrn='010622-4127385', addr='테스트시 샘플구 연습길 45-3',
               bank='302-1157-8842-61', school_id='2020456789', dept='경영학부', grade='3',
               birth='2001년 06월 22일',
               family=[('부', '박성호', '680204-1352718')]),
    'P3': dict(name='최예린', rrn='000909-4265813', addr='테스트시 모의구 가상대로 230',
               bank='1002-374-559201', school_id='2019778812', dept='전자공학부', grade='4',
               birth='2000년 09월 09일',
               family=[('부', '최동현', '700517-1748362'), ('모', '한지민', '730228-2186450')]),
    'P4': dict(name='정도윤', rrn='020403-3591746', addr='테스트시 예제구 시험로 8',
               bank='351-0927-4416-83', school_id='2021334455', dept='기계공학부', grade='2',
               birth='2002년 04월 03일',
               family=[('부', '정재원', '741109-1825370'), ('모', '오수정', '760301-2459816')]),
    'P5': dict(name='이수아', rrn='010118-4836290', addr='테스트시 가상구 표본로 77, 3층',
               bank='220-718-394052', school_id='2020112233', dept='화학공학부', grade='3',
               birth='2001년 01월 18일',
               family=[('모', '윤미경', '750614-2307185'), ('동생', '이준서', '040822-3964127')]),
}

# ---------------------------------------------------------------- drawing helpers

def new_page():
    img = Image.new('RGB', (W, H), 'white')
    return img, ImageDraw.Draw(img)


def footer(d):
    d.text((W // 2, H - 70), '※ 해커톤 테스트용 가상 문서 (실존 인물·기관 아님)', font=font(20),
           fill=(120, 120, 120), anchor='mm')


def text(d, xy, s, size=26, bold=False, fill='black', anchor='la'):
    d.text(xy, s, font=font(size, bold), fill=fill, anchor=anchor)
    return d.textbbox(xy, s, font=font(size, bold), anchor=anchor)


def rrn_cell(img, d, xy, rrn, style, size=24, scope='back7'):
    """주민등록번호를 그리고 지정한 방식으로 가린다. truth bbox들을 반환.

    style: none | black | star | white | highlight | black_back6
    scope: back7 (뒷 7자리) | all (13자리)
    반환: dict(full_bbox, back_bbox, visible_after)
    """
    f = font(size)
    front, back = rrn.split('-')
    x, y = xy
    if style == 'star':
        shown = front + '-' + '*' * 7 if scope == 'back7' else '******-*******'
        d.text((x, y), shown, font=f, fill='black')
        bb = d.textbbox((x, y), rrn, font=f)
        fb = d.textbbox((x, y), front + '-', font=f)
        return dict(full_bbox=bb, back_bbox=(fb[2], bb[1], bb[2], bb[3]))
    d.text((x, y), rrn, font=f, fill='black')
    bb = d.textbbox((x, y), rrn, font=f)
    fb = d.textbbox((x, y), front + '-', font=f)
    back_box = (fb[2] - 1, bb[1] - 4, bb[2] + 3, bb[3] + 4)
    if style == 'black_back6':  # 성별 자리는 보이고 뒤 6자리만 가림 (불완전)
        g = d.textbbox((x, y), front + '-' + back[0], font=f)
        d.rectangle((g[2], bb[1] - 4, bb[2] + 3, bb[3] + 4), fill='black')
    elif style in ('black', 'white', 'highlight'):
        box = back_box if scope == 'back7' else (bb[0] - 3, bb[1] - 4, bb[2] + 3, bb[3] + 4)
        if style == 'black':
            d.rectangle(box, fill='black')
        elif style == 'white':
            d.rectangle(box, fill='white')
        else:
            ov = Image.new('RGBA', img.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            od.rectangle(box, fill=(255, 200, 0, 140))  # 반투명 형광펜
            img.paste(Image.alpha_composite(img.convert('RGBA'), ov).convert('RGB'))
    return dict(full_bbox=bb, back_bbox=back_box)


def table(d, x, y, col_w, headers, row_h=58, size=24):
    xs = [x]
    for w in col_w:
        xs.append(xs[-1] + w)
    d.rectangle((x, y, xs[-1], y + row_h), fill=(235, 235, 235), outline='black', width=2)
    for i, h in enumerate(headers):
        d.text(((xs[i] + xs[i + 1]) // 2, y + row_h // 2), h, font=font(size, True), fill='black', anchor='mm')
    for xx in xs:
        d.line((xx, y, xx, y + row_h), fill='black', width=2)
    return xs


def table_row(d, xs, y, row_h=58):
    d.rectangle((xs[0], y, xs[-1], y + row_h), outline='black', width=2)
    for xx in xs:
        d.line((xx, y, xx, y + row_h), fill='black', width=2)


# ---------------------------------------------------------------- documents

def notice_A():
    img, d = new_page()
    text(d, (W // 2, 140), '2026 테스트시 청년 도약 지원사업', 46, True, anchor='mm')
    text(d, (W // 2, 205), '제출 서류 안내', 38, True, anchor='mm')
    d.line((120, 250, W - 120, 250), fill='black', width=3)
    y = 300
    lines = [
        ('1. 제출 서류', True),
        ('   가. 주민등록표 등본 1부 (최근 3개월 이내 발급)', False),
        ('   나. 본인 명의 통장사본 1부', False),
        ('   다. 재학증명서 1부', False),
        ('', False),
        ('2. 개인정보 가림 안내', True),
        ('   가. 주민등록번호는 앞 6자리(생년월일)만 보이게 하고,', False),
        ('       뒷자리 7자리는 반드시 가려서 제출합니다.', False),
        ('   나. 등본에 함께 기재된 세대원의 주민등록번호도', False),
        ('       같은 방식으로 뒷자리 7자리를 가립니다.', False),
        ('   다. 통장사본의 예금주와 계좌번호는 지원금 지급에 필요하므로', False),
        ('       가리지 말고 그대로 보이게 제출합니다.', False),
        ('', False),
        ('3. 제출 기한 및 방법', True),
        ('   2026. 11. 20.(금) 18:00까지 온라인 접수 (PDF 1개 파일로 제출)', False),
        ('', False),
        ('4. 유의 사항', True),
        ('   서류가 누락되거나 필요한 정보가 가려진 경우 보완을 요청할 수 있습니다.', False),
    ]
    for s, b in lines:
        text(d, (130, y), s, 28, b)
        y += 50
    text(d, (W // 2, 1450), '테스트시 청년정책과', 32, True, anchor='mm')
    footer(d)
    return img, {}


def notice_B():
    img, d = new_page()
    text(d, (W // 2, 140), '2026 테스트구 가족 돌봄 지원 신청', 44, True, anchor='mm')
    text(d, (W // 2, 205), '구비 서류 안내', 38, True, anchor='mm')
    d.line((120, 250, W - 120, 250), fill='black', width=3)
    y = 300
    lines = [
        ('1. 구비 서류', True),
        ('   가족관계증명서(일반) 1부', False),
        ('', False),
        ('2. 개인정보 가림 안내', True),
        ('   가. 가족관계증명서의 주민등록번호는 13자리 전체를 가려 주세요.', False),
        ('   나. 가족 구성원의 성명과 출생연월일은 확인에 필요하므로', False),
        ('       가리지 말고 보이게 제출합니다.', False),
        ('', False),
        ('3. 접수 기간', True),
        ('   2026. 11. 2.(월) ~ 11. 27.(금)', False),
    ]
    for s, b in lines:
        text(d, (130, y), s, 28, b)
        y += 50
    text(d, (W // 2, 1450), '테스트구청 가족복지팀', 32, True, anchor='mm')
    footer(d)
    return img, {}


def masking_request():
    """서비스 화면에서 '가리고 싶은 정보'를 고르면 자동 생성되는 기준 문서."""
    img, d = new_page()
    text(d, (W // 2, 150), '가림 요청서', 48, True, anchor='mm')
    text(d, (W // 2, 215), '(가림체크 서비스에서 사용자가 선택한 항목으로 자동 생성)', 24, anchor='mm', fill=(90, 90, 90))
    d.line((120, 260, W - 120, 260), fill='black', width=3)
    y = 320
    text(d, (130, y), '■ 가릴 정보', 30, True); y += 65
    items = [(True, '주민등록번호 뒷자리 7자리'), (False, '주소'), (False, '계좌번호'), (False, '휴대전화번호')]
    for chk, label in items:
        d.rectangle((160, y, 192, y + 32), outline='black', width=3)
        if chk:
            d.line((166, y + 16, 176, y + 27), fill='black', width=4)
            d.line((176, y + 27, 188, y + 5), fill='black', width=4)
        text(d, (215, y - 3), label, 28)
        y += 60
    y += 30
    text(d, (130, y), '■ 필수 제출 서류', 30, True); y += 60
    text(d, (160, y), '지정하지 않음', 28)
    footer(d)
    return img, {}


def resident_registration(p, styles, issue='2026년 10월 20일'):
    """styles: [본인 style, 세대원1 style, ...]"""
    img, d = new_page()
    text(d, (W // 2, 120), '주 민 등 록 표', 46, True, anchor='mm')
    text(d, (W // 2, 180), '( 등 본 )', 32, anchor='mm')
    text(d, (110, 250), f'발급일: {issue}', 24)
    text(d, (110, 300), f'세대주 성명: {p["name"]}', 26)
    text(d, (110, 345), f'주소: {p["addr"]}', 26)
    col_w = [80, 170, 170, 330, 140, 130]
    y0 = 420
    xs = table(d, 110, y0, col_w, ['번호', '세대주 관계', '성명', '주민등록번호', '전입일', '변동사유'])
    rows = [('본인', p['name'], p['rrn'])] + list(p['family'])
    truth = {}
    for i, (rel, nm, rrn) in enumerate(rows):
        y = y0 + 58 * (i + 1)
        table_row(d, xs, y)
        for j, v in enumerate([str(i + 1), rel, nm]):
            d.text(((xs[j] + xs[j + 1]) // 2, y + 29), v, font=font(24), fill='black', anchor='mm')
        t = rrn_cell(img, d, (xs[3] + 40, y + 13), rrn, styles[i])
        d = ImageDraw.Draw(img)
        d.text(((xs[4] + xs[5]) // 2, y + 29), '2020-03-02', font=font(22), fill='black', anchor='mm')
        d.text(((xs[5] + xs[6]) // 2, y + 29), '전입', font=font(22), fill='black', anchor='mm')
        truth[nm] = t
    text(d, (110, y0 + 58 * (len(rows) + 1) + 60), '위 등본은 주민등록표의 원본 내용과 틀림없음을 증명합니다.', 24)
    text(d, (W // 2, 1400), '테스트시 가상구청장', 30, True, anchor='mm')
    footer(d)
    return img, truth


def family_certificate(p, styles, name_hidden=()):
    img, d = new_page()
    text(d, (W // 2, 130), '가족관계증명서 (일반)', 44, True, anchor='mm')
    text(d, (110, 220), '등록기준지: 테스트시 가상구 기준로 1', 24)
    col_w = [110, 170, 230, 330, 100]
    y0 = 300
    xs = table(d, 110, y0, col_w, ['구분', '성명', '출생연월일', '주민등록번호', '성별'])
    rows = [('본인', p['name'], p['rrn'])] + list(p['family'])
    truth = {}
    for i, (rel, nm, rrn) in enumerate(rows):
        y = y0 + 58 * (i + 1)
        table_row(d, xs, y)
        yy = rrn[:2]
        century = '19' if rrn.split('-')[1][0] in '12' else '20'
        birth = f'{century}{yy}년 {rrn[2:4]}월 {rrn[4:6]}일'
        sex = '남' if rrn.split('-')[1][0] in '13' else '여'
        d.text(((xs[0] + xs[1]) // 2, y + 29), rel, font=font(24), fill='black', anchor='mm')
        nb = d.textbbox(((xs[1] + xs[2]) // 2, y + 29), nm, font=font(24), anchor='mm')
        d.text(((xs[1] + xs[2]) // 2, y + 29), nm, font=font(24), fill='black', anchor='mm')
        if nm in name_hidden:
            d.rectangle((nb[0] - 6, nb[1] - 6, nb[2] + 6, nb[3] + 6), fill='black')
        d.text(((xs[2] + xs[3]) // 2, y + 29), birth, font=font(22), fill='black', anchor='mm')
        t = rrn_cell(img, d, (xs[3] + 40, y + 13), rrn, styles[i][0], scope=styles[i][1])
        d = ImageDraw.Draw(img)
        d.text(((xs[4] + xs[5]) // 2, y + 29), sex, font=font(24), fill='black', anchor='mm')
        truth[nm] = t
    text(d, (110, y0 + 58 * (len(rows) + 1) + 60), '위 가족관계증명서는 가족관계등록부의 기록사항과 틀림없음을 증명합니다.', 22)
    text(d, (W // 2, 1400), '테스트시 가상구청장', 30, True, anchor='mm')
    footer(d)
    return img, truth


def bankbook(p, acct_style='none', holder_style='none'):
    img, d = new_page()
    # 통장 표지 느낌의 박스
    d.rounded_rectangle((140, 200, W - 140, 900), radius=30, outline=(30, 80, 160), width=6)
    text(d, (200, 250), '테스트은행', 40, True, fill=(30, 80, 160))
    text(d, (200, 320), '보통예금 통장 (사본)', 32)
    text(d, (200, 450), '예금주', 28, fill=(80, 80, 80))
    hb = text(d, (420, 445), p['name'], 34, True)
    text(d, (200, 540), '계좌번호', 28, fill=(80, 80, 80))
    ab = text(d, (420, 535), p['bank'], 34, True)
    text(d, (200, 630), '개설일', 28, fill=(80, 80, 80))
    text(d, (420, 625), '2019-03-04', 30)
    text(d, (200, 760), '이 통장은 테스트용 가상 통장입니다.', 22, fill=(120, 120, 120))
    if acct_style == 'black':
        d.rectangle((ab[0] - 8, ab[1] - 8, ab[2] + 8, ab[3] + 8), fill='black')
    elif acct_style == 'blur':
        box = (ab[0] - 10, ab[1] - 10, ab[2] + 10, ab[3] + 10)
        region = img.crop(box).filter(ImageFilter.GaussianBlur(9))
        img.paste(region, box[:2])
    if holder_style == 'black':
        d.rectangle((hb[0] - 8, hb[1] - 8, hb[2] + 8, hb[3] + 8), fill='black')
    footer(d)
    return img, {'account_number': ab, 'account_holder': hb}


def enrollment(p):
    img, d = new_page()
    text(d, (W // 2, 160), '재 학 증 명 서', 50, True, anchor='mm')
    y = 330
    for k, v in [('성        명', p['name']), ('생 년 월 일', p['birth']), ('소        속', f'가상대학교 {p["dept"]}'),
                 ('학        번', p['school_id']), ('학        년', f'{p["grade"]}학년'), ('학 적 상 태', '재학')]:
        text(d, (200, y), k, 30)
        text(d, (480, y), ':  ' + v, 30)
        y += 70
    text(d, (W // 2, 900), '위 사람은 본교에 재학 중임을 증명합니다.', 32, anchor='mm')
    text(d, (W // 2, 1000), '2026년 10월 21일', 30, anchor='mm')
    text(d, (W // 2, 1120), '가상대학교 총장', 38, True, anchor='mm')
    footer(d)
    return img, {}


def degrade(img, angle=2.6):
    """폰 촬영 느낌: 회전 + 밝기 불균일 + 노이즈 + 약한 블러 + JPEG."""
    bg = Image.new('RGB', (W + 120, H + 120), (205, 200, 190))
    bg.paste(img, (60, 60))
    rot = bg.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(190, 185, 175))
    px = rot.load()
    for _ in range(60000):
        x, y = random.randrange(rot.width), random.randrange(rot.height)
        v = random.randint(-45, 45)
        r, g, b = px[x, y]
        px[x, y] = (max(0, min(255, r + v)), max(0, min(255, g + v)), max(0, min(255, b + v)))
    shade = Image.linear_gradient('L').resize(rot.size).point(lambda t: 255 - t // 5)
    rot = Image.composite(rot, Image.new('RGB', rot.size, (150, 145, 135)), shade)
    rot = rot.filter(ImageFilter.GaussianBlur(0.9))
    import io
    buf = io.BytesIO(); rot.save(buf, 'JPEG', quality=55); buf.seek(0)
    return Image.open(buf).convert('RGB').resize((W, H))


# ---------------------------------------------------------------- answer key helpers
NOTICE_A_REQ = dict(
    required_documents=['resident_registration', 'bankbook_copy', 'enrollment_certificate'],
    rules=[
        dict(document_type='resident_registration', field='resident_number', rule='mask_back_7'),
        dict(document_type='bankbook_copy', field='account_holder', rule='must_be_visible'),
        dict(document_type='bankbook_copy', field='account_number', rule='must_be_visible'),
    ])
NOTICE_B_REQ = dict(
    required_documents=['family_relation_certificate'],
    rules=[
        dict(document_type='family_relation_certificate', field='resident_number', rule='mask_all'),
        dict(document_type='family_relation_certificate', field='name', rule='must_be_visible'),
        dict(document_type='family_relation_certificate', field='birth_date', rule='must_be_visible'),
    ])
REQUEST_REQ = dict(
    required_documents=[],
    rules=[dict(document_type='all', field='resident_number', rule='mask_back_7')])


def chk(doc, page, field, person, rule, status, visibility):
    return dict(document_type=doc, page=page, field=field, person_name=person, rule=rule,
                visibility=visibility, status=status)


RRN_VIS = {'none': 'full', 'highlight': 'full', 'black': 'front_only', 'star': 'front_only',
           'white': 'front_only', 'black_back6': 'front_and_gender'}
VIS_STATUS = {
    'mask_back_7': {'full': 'auto_masked', 'front_and_gender': 'auto_masked', 'front_only': 'ok', 'hidden': 'ok',
                    'unreadable': 'auto_masked'},
    'mask_all': {'full': 'auto_masked', 'front_and_gender': 'auto_masked', 'front_only': 'auto_masked',
                 'hidden': 'ok', 'unreadable': 'auto_masked'},
    'must_be_visible': {'full': 'ok', 'hidden': 'over_masked', 'unreadable': '검토 필요', 'absent': 'missing_field'},
}


def vchk(doc, page, field, person, rule, visibility):
    return chk(doc, page, field, person, rule, VIS_STATUS[rule][visibility], visibility)


def finalize(checks, missing):
    if missing or any(c['status'] in ('over_masked', 'missing_field') for c in checks):
        result = '보완 필요'
    elif any(c['status'] == '검토 필요' for c in checks):
        result = '검토 필요'
    else:
        result = '통과'
    return result


# ---------------------------------------------------------------- cases

def build_cases():
    P = PERSONAS
    cases = []

    def bank_checks(page, p, acct='full', holder='full'):
        return [vchk('bankbook_copy', page, 'account_holder', p['name'], 'must_be_visible', holder),
                vchk('bankbook_copy', page, 'account_number', p['name'], 'must_be_visible', acct)]

    def rr_checks(page, p, styles):
        rows = [p['name']] + [f[1] for f in p['family']]
        return [vchk('resident_registration', page, 'resident_number', nm, 'mask_back_7', RRN_VIS[s])
                for nm, s in zip(rows, styles)]

    # case 01 단순: 정상 가림
    p = P['P1']; st = ['black', 'black', 'black']
    cases.append(dict(id='case_01', type='단순', desc='등본 3명 모두 정상 가림, 통장·재학 정상',
                      applicant=p['name'], req=NOTICE_A_REQ,
                      pages=[('notice', notice_A()), ('resident_registration', resident_registration(p, st)),
                             ('bankbook_copy', bankbook(p)), ('enrollment_certificate', enrollment(p))],
                      checks=rr_checks(2, p, st) + bank_checks(3, p), missing=[]))
    # case 02 단순: 본인 노출
    p = P['P2']; st = ['none', 'star']
    cases.append(dict(id='case_02', type='단순', desc='등본 본인 주민번호 노출(세대원은 * 가림)',
                      applicant=p['name'], req=NOTICE_A_REQ,
                      pages=[('notice', notice_A()), ('resident_registration', resident_registration(p, st)),
                             ('bankbook_copy', bankbook(p)), ('enrollment_certificate', enrollment(p))],
                      checks=rr_checks(2, p, st) + bank_checks(3, p), missing=[]))
    # case 03 양식 다양성: 가림 요청서(사용자 선택) + 가림 방식 혼합 + 체크 안 한 계좌번호
    p = P['P3']; fs = [('star', 'back7'), ('white', 'back7'), ('black', 'back7')]
    rows = [p['name']] + [f[1] for f in p['family']]
    cases.append(dict(id='case_03', type='양식·문맥 다양성',
                      desc='가림 요청서 기준, 가족관계증명서 가림 방식 3종(*, 흰 덮개, 검은 박스), 계좌번호는 요청 안 함',
                      applicant=p['name'], req=REQUEST_REQ,
                      pages=[('masking_request', masking_request()), ('family_relation_certificate', family_certificate(p, fs)),
                             ('bankbook_copy', bankbook(p))],
                      checks=[vchk('family_relation_certificate', 2, 'resident_number', nm, 'mask_back_7', 'front_only') for nm in rows],
                      missing=[]))
    # case 04 양식 다양성: 공고 B (13자리 전체 가림) - 뒷자리만 가린 서류
    p = P['P4']; fs = [('black', 'back7')] * 3
    rows = [p['name']] + [f[1] for f in p['family']]
    ck = []
    for nm in rows:
        ck += [vchk('family_relation_certificate', 2, 'resident_number', nm, 'mask_all', 'front_only'),
               vchk('family_relation_certificate', 2, 'name', nm, 'must_be_visible', 'full'),
               vchk('family_relation_certificate', 2, 'birth_date', nm, 'must_be_visible', 'full')]
    cases.append(dict(id='case_04', type='양식·문맥 다양성', desc='공고 B는 13자리 전체 가림 요구, 서류는 뒷자리만 가림',
                      applicant=p['name'], req=NOTICE_B_REQ,
                      pages=[('notice', notice_B()), ('family_relation_certificate', family_certificate(p, fs))],
                      checks=ck, missing=[]))
    # case 05 문서 결합: 세대원 1명만 노출, 공고문이 마지막 페이지
    p = P['P5']; st = ['black', 'black', 'none']
    cases.append(dict(id='case_05', type='문서 결합', desc='등본 세대원(동생)만 노출, 공고문이 묶음 맨 뒤',
                      applicant=p['name'], req=NOTICE_A_REQ,
                      pages=[('resident_registration', resident_registration(p, st)), ('bankbook_copy', bankbook(p)),
                             ('enrollment_certificate', enrollment(p)), ('notice', notice_A())],
                      checks=rr_checks(1, p, st) + bank_checks(2, p), missing=[]))
    # case 06 문서 결합: 통장 계좌번호 과잉 가림
    p = P['P2']; st = ['black', 'black']
    cases.append(dict(id='case_06', type='문서 결합', desc='통장사본 계좌번호까지 가림(과잉)',
                      applicant=p['name'], req=NOTICE_A_REQ,
                      pages=[('notice', notice_A()), ('resident_registration', resident_registration(p, st)),
                             ('bankbook_copy', bankbook(p, acct_style='black')), ('enrollment_certificate', enrollment(p))],
                      checks=rr_checks(2, p, st) + bank_checks(3, p, acct='hidden'), missing=[]))
    # case 07 문서 결합: 통장 누락 + 본인 노출
    p = P['P5']; st = ['none', 'black', 'black']
    cases.append(dict(id='case_07', type='문서 결합', desc='통장사본 누락 + 등본 본인 노출',
                      applicant=p['name'], req=NOTICE_A_REQ,
                      pages=[('notice', notice_A()), ('resident_registration', resident_registration(p, st)),
                             ('enrollment_certificate', enrollment(p))],
                      checks=rr_checks(2, p, st), missing=['bankbook_copy']))
    # case 08 저품질: 폰 촬영 등본, 본인 노출
    p = P['P1']; st = ['none', 'black', 'black']
    rr_img, rr_truth = resident_registration(p, st)
    cases.append(dict(id='case_08', type='저품질', desc='폰으로 기울게 찍은 등본(노이즈·그림자), 본인 노출',
                      applicant=p['name'], req=NOTICE_A_REQ,
                      pages=[('notice', notice_A()), ('resident_registration', (degrade(rr_img), rr_truth)),
                             ('bankbook_copy', bankbook(p)), ('enrollment_certificate', enrollment(p))],
                      checks=rr_checks(2, p, st) + bank_checks(3, p), missing=[], degraded=True))
    # case 09 함정: 반투명 형광펜 + 성별 자리 노출(뒤 6자리만 가림)
    p = P['P4']; st = ['highlight', 'black_back6', 'black']
    cases.append(dict(id='case_09', type='예외·함정', desc='본인은 반투명 형광펜(글자 보임), 부는 뒤 6자리만 가림(성별 자리 노출)',
                      applicant=p['name'], req=NOTICE_A_REQ,
                      pages=[('notice', notice_A()), ('resident_registration', resident_registration(p, st)),
                             ('bankbook_copy', bankbook(p)), ('enrollment_certificate', enrollment(p))],
                      checks=rr_checks(2, p, st) + bank_checks(3, p), missing=[]))
    # case 10 함정: 계좌번호 판독 불가(흐림)
    p = P['P3']; st = ['black', 'black', 'black']
    cases.append(dict(id='case_10', type='예외·함정', desc='통장사본 계좌번호가 흐려서 판독 불가',
                      applicant=p['name'], req=NOTICE_A_REQ,
                      pages=[('notice', notice_A()), ('resident_registration', resident_registration(p, st)),
                             ('bankbook_copy', bankbook(p, acct_style='blur')), ('enrollment_certificate', enrollment(p))],
                      checks=rr_checks(2, p, st) + bank_checks(3, p, acct='unreadable'), missing=[]))
    return cases


REQUEST_TEMPLATES = {
    'over_masked': '{doc} {page}페이지의 {field}({person})이(가) 가려져 있어요. 확인에 필요한 정보이니 가리지 않은 사본으로 다시 제출해 주세요.',
    'missing_field': '{doc} {page}페이지에서 {field}({person})을(를) 찾을 수 없어요. 해당 정보가 보이는 서류로 다시 제출해 주세요.',
    'missing_doc': '{doc}이(가) 제출 서류에 없어요. 추가로 제출해 주세요.',
}
DOC_KO = dict(notice='공고문', masking_request='가림 요청서', resident_registration='주민등록표 등본',
              family_relation_certificate='가족관계증명서', bankbook_copy='통장사본',
              enrollment_certificate='재학증명서')
FIELD_KO = dict(resident_number='주민등록번호', account_number='계좌번호', account_holder='예금주',
                name='성명', birth_date='출생연월일')


def request_message(checks, missing):
    msgs = []
    for c in checks:
        if c['status'] in ('over_masked', 'missing_field'):
            msgs.append(REQUEST_TEMPLATES[c['status']].format(doc=DOC_KO[c['document_type']], page=c['page'],
                                                              field=FIELD_KO[c['field']], person=c['person_name']))
    for m in missing:
        msgs.append(REQUEST_TEMPLATES['missing_doc'].format(doc=DOC_KO[m]))
    return ' '.join(msgs)


def main():
    os.makedirs(OUT, exist_ok=True)
    index = []
    for c in build_cases():
        cdir = os.path.join(OUT, c['id'])
        pdir = os.path.join(cdir, 'pages')
        os.makedirs(pdir, exist_ok=True)
        imgs, truth = [], {}
        for i, (kind, (img, t)) in enumerate(c['pages'], 1):
            fn = f'p{i}_{kind}.png'
            img.save(os.path.join(pdir, fn))
            imgs.append(img)
            if t:
                truth[f'page_{i}'] = {k: {kk: list(vv) for kk, vv in v.items()} if isinstance(v, dict) else list(v)
                                      for k, v in t.items()}
        imgs[0].save(os.path.join(cdir, 'bundle.pdf'), save_all=True, append_images=imgs[1:], resolution=150)
        review = [f"{DOC_KO[x['document_type']]} {x['page']}페이지 {FIELD_KO[x['field']]}({x['person_name']}) 판독 불가"
                  for x in c['checks'] if x['status'] == '검토 필요']
        answer = dict(
            applicant_name=c['applicant'],
            criteria_source='masking_request' if c['req'] is REQUEST_REQ else 'notice',
            required_documents=c['req']['required_documents'],
            rules=c['req']['rules'],
            submitted_documents=list(dict.fromkeys(k for k, _ in c['pages'])),
            missing_documents=c['missing'],
            checks=c['checks'],
            result=finalize(c['checks'], c['missing']),
            review_reasons=review,
            request_message=request_message(c['checks'], c['missing']),
        )
        with open(os.path.join(cdir, 'answer.json'), 'w', encoding='utf-8') as f:
            json.dump(answer, f, ensure_ascii=False, indent=2)
        with open(os.path.join(cdir, 'truth_boxes.json'), 'w', encoding='utf-8') as f:
            json.dump(truth, f, ensure_ascii=False, indent=2)
        index.append(dict(id=c['id'], type=c['type'], desc=c['desc'], result=answer['result'],
                          auto_masked=sum(1 for x in c['checks'] if x['status'] == 'auto_masked'), pages=len(imgs)))
    with open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    for r in index:
        print(r)


if __name__ == '__main__':
    main()
