import sys, json, re, os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Frame, BaseDocTemplate, PageTemplate
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── REGISTER FONTS ────────────────────────────────────────────────────────
FONT_DIR = '/usr/share/fonts/truetype'
GOOGLE_FONTS = f'{FONT_DIR}/google-fonts'
CROSEXTRA    = f'{FONT_DIR}/crosextra'
DEJAVU       = f'{FONT_DIR}/dejavu'
LIBERATION   = f'{FONT_DIR}/liberation'

def reg(name, path):
    try:
        pdfmetrics.registerFont(TTFont(name, path))
        return True
    except:
        return False

# Body: Lora — beautiful Google serif, highly readable
reg('Lora',        f'{GOOGLE_FONTS}/Lora-Variable.ttf')
reg('Lora-Italic', f'{GOOGLE_FONTS}/Lora-Italic-Variable.ttf')
reg('Lora-Bold',   f'{GOOGLE_FONTS}/Lora-Variable.ttf')  # variable font covers bold

# Headings: Caladea — Times-like, elegant, excellent for titles
reg('Caladea',            f'{CROSEXTRA}/Caladea-Regular.ttf')
reg('Caladea-Bold',       f'{CROSEXTRA}/Caladea-Bold.ttf')
reg('Caladea-Italic',     f'{CROSEXTRA}/Caladea-Italic.ttf')
reg('Caladea-BoldItalic', f'{CROSEXTRA}/Caladea-BoldItalic.ttf')

# UI labels: DejaVu Sans — clean, modern, great for small caps labels
reg('DejaVu',      f'{DEJAVU}/DejaVuSans.ttf')
reg('DejaVu-Bold', f'{DEJAVU}/DejaVuSans-Bold.ttf')

# Fallback
BODY_REG    = 'Lora'        if reg('Lora','') or True else 'Times-Roman'
BODY_BOLD   = 'Caladea-Bold'
BODY_ITALIC = 'Lora-Italic'
HEAD_FONT   = 'Caladea-Bold'
LABEL_FONT  = 'DejaVu-Bold'
UI_FONT     = 'DejaVu'

# ── DBH BRAND COLORS ──────────────────────────────────────────────────────
GOLD       = colors.HexColor('#C9A84C')
AMBER      = colors.HexColor('#E8B84B')
DARK_GOLD  = colors.HexColor('#9A7530')
LIGHT_GOLD = colors.HexColor('#F0CC70')
NAVY       = colors.HexColor('#060E18')
NAVY2      = colors.HexColor('#0C1A28')
NAVY3      = colors.HexColor('#142236')
NAVY4      = colors.HexColor('#1A2E44')
CREAM      = colors.HexColor('#EDE8E0')
WARM_WHITE = colors.HexColor('#F5F0E8')
MUTED      = colors.HexColor('#6A7F96')
WHITE      = colors.HexColor('#FFFFFF')
RED_DARK   = colors.HexColor('#8B2020')

W, H = letter

# ── PAGE HEADER/FOOTER ────────────────────────────────────────────────────
class DBHPageTemplate:
    def __init__(self, topic, guide_type):
        self.topic      = topic[:60] + ('...' if len(topic) > 60 else '')
        self.guide_type = guide_type

    def __call__(self, canv, doc):
        canv.saveState()

        # ── HEADER ──
        canv.setFillColor(NAVY)
        canv.rect(0, H - 0.55*inch, W, 0.55*inch, fill=1, stroke=0)
        canv.setFillColor(GOLD)
        canv.rect(0, H - 0.58*inch, W, 0.04*inch, fill=1, stroke=0)

        canv.setFont(LABEL_FONT, 8)
        canv.setFillColor(GOLD)
        canv.drawString(0.45*inch, H - 0.35*inch, 'DEEP BIBLE HISTORY')

        canv.setFont(UI_FONT, 7.5)
        canv.setFillColor(CREAM)
        canv.drawRightString(W - 0.45*inch, H - 0.35*inch, self.topic)

        # ── FOOTER ──
        canv.setFillColor(NAVY)
        canv.rect(0, 0, W, 0.46*inch, fill=1, stroke=0)
        canv.setFillColor(GOLD)
        canv.rect(0, 0.46*inch, W, 0.025*inch, fill=1, stroke=0)

        canv.setFont(UI_FONT, 7.5)
        canv.setFillColor(CREAM)
        canv.drawCentredString(W/2, 0.16*inch, f'Page {doc.page}')

        canv.setFont(UI_FONT, 6.5)
        canv.setFillColor(MUTED)
        canv.drawString(0.45*inch, 0.16*inch, f'© Deep Bible History. All rights reserved.')
        canv.drawRightString(W - 0.45*inch, 0.16*inch, self.guide_type)

        canv.restoreState()

# ── COVER BACKGROUND FLOWABLE ─────────────────────────────────────────────
class CoverBG(Flowable):
    def draw(self):
        c = self.canv
        mL, mR, mT, mB = 0.6*inch, 0.6*inch, 0.55*inch, 0.46*inch
        cW = W - mL - mR

        # Dark navy fill
        c.setFillColor(NAVY)
        c.rect(-mL, -mB, W, H, fill=1, stroke=0)

        # Subtle texture bars
        c.setFillColor(NAVY2)
        for y in range(0, int(H), 40):
            c.rect(-mL, y - mB, W, 18, fill=1, stroke=0)

        # Left gold accent bar
        c.setFillColor(GOLD)
        c.rect(-mL, -mB, 6, H, fill=1, stroke=0)

        # Large decorative cross watermark
        c.setFillColor(NAVY3)
        cx, cy = cW/2, H*0.42 - mB
        c.rect(cx - 3, cy - H*0.28, 6, H*0.56, fill=1, stroke=0)
        c.rect(cx - H*0.16, cy, H*0.32, 6, fill=1, stroke=0)

        # Gold horizontal rules
        c.setFillColor(GOLD)
        c.rect(-mL, H*0.62 - mB, W, 2.5, fill=1, stroke=0)
        c.rect(-mL, H*0.62 - mB + 5, W, 0.8, fill=1, stroke=0)
        c.rect(-mL, H*0.20 - mB, W, 2, fill=1, stroke=0)

    def wrap(self, *a): return 0, 0

# ── BUILD PDF ─────────────────────────────────────────────────────────────
def build_guide_pdf(guide_text, topic, guide_type, output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.65*inch, leftMargin=0.65*inch,
        topMargin=0.85*inch, bottomMargin=0.65*inch,
        title=f'DBH Study Guide — {topic}',
        author='Deep Bible History',
        subject=f'{guide_type}: {topic}'
    )
    tmpl = DBHPageTemplate(topic, guide_type)
    story = []

    # ── STYLES ────────────────────────────────────────────────────────────
    dw = W - 1.3*inch  # doc width

    def S(name, font, size, color, align=TA_LEFT, sb=6, sa=6, lead=None, li=0, ri=0):
        return ParagraphStyle(name, fontName=font, fontSize=size, textColor=color,
            alignment=align, spaceBefore=sb, spaceAfter=sa,
            leading=lead or size*1.5, leftIndent=li, rightIndent=ri)

    cover_title = S('ct', HEAD_FONT, 30, LIGHT_GOLD, TA_CENTER, 8, 8, 38)
    cover_sub   = S('cs', 'Caladea-Italic', 13, CREAM, TA_CENTER, 6, 6, 20)
    cover_label = S('cl', LABEL_FONT, 8, GOLD, TA_CENTER, 4, 4, 14)
    cover_type  = S('ctp', UI_FONT, 9, AMBER, TA_CENTER, 4, 4, 14)

    sec_head    = S('sh', HEAD_FONT, 14, WHITE, TA_LEFT, 14, 8, 20)
    sub_head    = S('sbh', 'Caladea-Bold', 12, LIGHT_GOLD, TA_LEFT, 10, 6, 18)
    body_text   = S('bt', BODY_REG, 11, CREAM, TA_JUSTIFY, 4, 6, 18)
    body_bold   = S('bb', BODY_BOLD, 11, WARM_WHITE, TA_LEFT, 4, 4, 17)
    body_italic = S('bi', BODY_ITALIC, 11, CREAM, TA_JUSTIFY, 4, 6, 18, 16, 16)
    question_s  = S('qs', 'Caladea-BoldItalic', 11, AMBER, TA_LEFT, 6, 4, 17, 12)
    fill_s      = S('fi', BODY_REG, 11, CREAM, TA_LEFT, 4, 6, 18, 12)
    scripture_s = S('sc', BODY_ITALIC, 11, LIGHT_GOLD, TA_LEFT, 6, 6, 18, 20, 20)
    prayer_s    = S('pr', BODY_ITALIC, 11, CREAM, TA_JUSTIFY, 6, 6, 18, 16, 12)
    cta_head_s  = S('cth', LABEL_FONT, 9, NAVY, TA_CENTER, 4, 2, 14)
    cta_body_s  = S('ctb', 'Caladea-Bold', 11, NAVY, TA_CENTER, 2, 4, 17)
    bullet_s    = S('bul', BODY_REG, 11, CREAM, TA_LEFT, 3, 3, 17, 20, 8)
    numbered_s  = S('num', BODY_REG, 11, CREAM, TA_LEFT, 3, 3, 17, 20, 8)
    small_s     = S('sm', UI_FONT, 8, MUTED, TA_LEFT, 2, 2, 12)
    back_title  = S('bct', HEAD_FONT, 18, GOLD, TA_CENTER, 8, 8, 26)
    back_sub    = S('bcs', 'Caladea-Italic', 11, CREAM, TA_CENTER, 6, 16, 18)
    back_cr     = S('bcr', UI_FONT, 8, MUTED, TA_CENTER, 4, 4, 12)

    # ── BOX HELPERS ───────────────────────────────────────────────────────
    def section_box(title):
        t = Table([[Paragraph(title, sec_head)]], colWidths=[dw])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), NAVY3),
            ('LEFTPADDING',   (0,0),(-1,-1), 14),
            ('RIGHTPADDING',  (0,0),(-1,-1), 14),
            ('TOPPADDING',    (0,0),(-1,-1), 9),
            ('BOTTOMPADDING', (0,0),(-1,-1), 9),
            ('LINEABOVE',     (0,0),(-1,0), 2.5, GOLD),
            ('LINEBELOW',     (0,-1),(-1,-1), 0.5, NAVY4),
        ]))
        return t

    def question_box(text):
        t = Table([[Paragraph(text, question_s)]], colWidths=[dw])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), NAVY2),
            ('LEFTPADDING',   (0,0),(-1,-1), 16),
            ('RIGHTPADDING',  (0,0),(-1,-1), 12),
            ('TOPPADDING',    (0,0),(-1,-1), 7),
            ('BOTTOMPADDING', (0,0),(-1,-1), 7),
            ('LINEBEFORE',    (0,0),(0,-1), 3.5, GOLD),
        ]))
        return t

    def fill_in_box(text):
        filled = re.sub(r'_{2,}', '...................................', text)
        t = Table([[Paragraph(filled, fill_s)]], colWidths=[dw])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), NAVY2),
            ('LEFTPADDING',   (0,0),(-1,-1), 14),
            ('RIGHTPADDING',  (0,0),(-1,-1), 14),
            ('TOPPADDING',    (0,0),(-1,-1), 5),
            ('BOTTOMPADDING', (0,0),(-1,-1), 5),
            ('LINEBEFORE',    (0,0),(0,-1), 2, AMBER),
        ]))
        return t

    def scripture_box(text):
        t = Table([[Paragraph(text, scripture_s)]], colWidths=[dw])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), NAVY3),
            ('LEFTPADDING',   (0,0),(-1,-1), 22),
            ('RIGHTPADDING',  (0,0),(-1,-1), 22),
            ('TOPPADDING',    (0,0),(-1,-1), 11),
            ('BOTTOMPADDING', (0,0),(-1,-1), 11),
            ('LINEABOVE',     (0,0),(-1,0), 1, DARK_GOLD),
            ('LINEBELOW',     (0,-1),(-1,-1), 1, DARK_GOLD),
            ('LINEBEFORE',    (0,0),(0,-1), 3, GOLD),
        ]))
        return t

    def cta_box(text):
        rows = [
            [Paragraph('✦  BIBLE STUDY COMPANION GUIDE  ✦', cta_head_s)],
            [Paragraph(text, cta_body_s)],
        ]
        t = Table(rows, colWidths=[dw])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), AMBER),
            ('LEFTPADDING',   (0,0),(-1,-1), 18),
            ('RIGHTPADDING',  (0,0),(-1,-1), 18),
            ('TOPPADDING',    (0,0),(-1,-1), 10),
            ('BOTTOMPADDING', (0,0),(-1,-1), 10),
            ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
            ('LINEABOVE',     (0,0),(-1,0), 3, DARK_GOLD),
            ('LINEBELOW',     (0,-1),(-1,-1), 3, DARK_GOLD),
        ]))
        return t

    def add(el, space_before=0, space_after=4):
        if space_before: story.append(Spacer(1, space_before))
        story.append(el)
        if space_after:  story.append(Spacer(1, space_after))

    # ── COVER PAGE ────────────────────────────────────────────────────────
    story.append(CoverBG())
    story.append(Spacer(1, 1.0*inch))
    story.append(Paragraph('DEEP BIBLE HISTORY', cover_label))
    story.append(Spacer(1, 0.08*inch))
    story.append(HRFlowable(width='75%', thickness=1.5, color=DARK_GOLD,
                             lineCap='round', spaceAfter=18))
    story.append(Paragraph(topic, cover_title))
    story.append(Spacer(1, 0.12*inch))
    story.append(Paragraph(guide_type, cover_type))
    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width='55%', thickness=0.8, color=NAVY4, spaceAfter=14))
    story.append(Paragraph(
        'An evidence-based companion for the modern biblical explorer',
        cover_sub))
    story.append(PageBreak())

    # ── PARSE GUIDE CONTENT ───────────────────────────────────────────────
    lines = guide_text.split('\n')
    i = 0
    current_section = ''

    while i < len(lines):
        raw  = lines[i]
        line = raw.strip()

        # Skip deliverable markers
        if re.match(r'DELIVERABLE \d+', line, re.I):
            i += 1; continue

        # === SECTION N: TITLE ===
        m = re.match(r'=+\s*(?:SECTION\s*\d*:?\s*)?(.+?)\s*=+', line, re.I)
        if m and len(line) > 4:
            title = m.group(1).strip().rstrip('=').strip()
            if title:
                story.append(Spacer(1, 0.12*inch))
                story.append(section_box(title))
                story.append(Spacer(1, 0.08*inch))
                current_section = title.lower()
                i += 1; continue

        # ## Heading / # Heading
        if re.match(r'^#{1,3}\s+', line):
            text = re.sub(r'^#{1,3}\s+', '', line).strip()
            story.append(Spacer(1, 0.08*inch))
            story.append(Paragraph(text, sub_head))
            i += 1; continue

        # **Bold heading** on its own line
        if re.match(r'^\*\*[^*]+\*\*$', line) and len(line) < 90:
            text = re.sub(r'\*\*', '', line)
            story.append(Spacer(1, 0.06*inch))
            story.append(Paragraph(text, sub_head))
            i += 1; continue

        # CTA MARKER block
        if '[CTA MARKER' in line.upper() or re.match(r'\[CTA MARKER', line, re.I):
            cta_lines = []
            i += 1
            while i < len(lines):
                l = lines[i].strip()
                if re.match(r'\[END CTA', l, re.I): break
                if l: cta_lines.append(l)
                i += 1
            if cta_lines:
                cta_text = ' '.join(cta_lines)[:400]
                story.append(Spacer(1, 0.12*inch))
                story.append(cta_box(cta_text))
                story.append(Spacer(1, 0.12*inch))
            i += 1; continue

        # Scripture quote — has verse ref AND quotes
        if re.search(r'\b\d+:\d+', line) and ('"' in line or line.startswith('"') or '—' in line):
            story.append(scripture_box(line))
            story.append(Spacer(1, 0.04*inch))
            i += 1; continue

        # Numbered question (has ?)
        if re.match(r'^\d+[\.\)]\s', line) and '?' in line:
            story.append(question_box(line))
            story.append(Spacer(1, 0.03*inch))
            i += 1; continue

        # Standalone question
        if line.endswith('?') and len(line) > 25 and not line.startswith('-'):
            story.append(question_box(line))
            story.append(Spacer(1, 0.03*inch))
            i += 1; continue

        # Fill in the blank
        if '___' in line and len(line) > 8:
            story.append(fill_in_box(line))
            story.append(Spacer(1, 0.03*inch))
            i += 1; continue

        # Prayer section
        if 'prayer' in current_section and len(line) > 20:
            story.append(Paragraph(line, prayer_s))
            i += 1; continue

        # Bullet point
        if re.match(r'^[-•]\s+', line):
            text = re.sub(r'^[-•]\s+', '', line)
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            story.append(Paragraph(f'• {text}', bullet_s))
            i += 1; continue

        # Numbered list (not question)
        if re.match(r'^\d+[\.\)]\s', line) and '?' not in line:
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
            story.append(Paragraph(text, numbered_s))
            i += 1; continue

        # Horizontal rule
        if re.match(r'^[-_=]{3,}$', line):
            story.append(Spacer(1, 0.06*inch))
            story.append(HRFlowable(width='100%', thickness=0.5, color=NAVY4))
            story.append(Spacer(1, 0.06*inch))
            i += 1; continue

        # Empty line
        if not line:
            story.append(Spacer(1, 0.05*inch))
            i += 1; continue

        # Regular body — convert markdown bold/italic
        clean = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
        clean = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', clean)
        clean = clean.replace('&', '&amp;').replace('<b>', '<b>').replace('</b>', '</b>')
        try:
            story.append(Paragraph(clean, body_text))
        except:
            story.append(Paragraph(line, body_text))
        i += 1

    # ── BACK COVER ────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(CoverBG())
    story.append(Spacer(1, 1.8*inch))
    story.append(HRFlowable(width='70%', thickness=2, color=GOLD, spaceAfter=20))
    story.append(Paragraph('DEEP BIBLE HISTORY', cover_label))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        'Evidence-based biblical history for the modern believer.',
        back_sub))
    story.append(HRFlowable(width='50%', thickness=0.8, color=NAVY4, spaceAfter=20))
    story.append(Paragraph(
        f'© {2025} Deep Bible History. All rights reserved.\nThis guide may not be reproduced without permission.',
        back_cr))

    doc.build(story, onFirstPage=tmpl, onLaterPages=tmpl)
    print(f'PDF built: {output_path}', file=sys.stderr)

if __name__ == '__main__':
    data = json.load(sys.stdin)
    build_guide_pdf(data['text'], data['topic'], data['guide_type'], data['output'])
