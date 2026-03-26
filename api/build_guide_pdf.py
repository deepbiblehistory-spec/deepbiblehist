import sys, json, re, os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, Circle, Line, String, Polygon
from reportlab.graphics import renderPDF
import math

# ── REGISTER FONTS ────────────────────────────────────────────────────────
FONT_DIR  = '/usr/share/fonts/truetype'
CROSEXTRA = f'{FONT_DIR}/crosextra'
DEJAVU    = f'{FONT_DIR}/dejavu'
GOOGLE    = f'{FONT_DIR}/google-fonts'
LORA      = f'{GOOGLE}/Lora-Variable.ttf'
LORA_I    = f'{GOOGLE}/Lora-Italic-Variable.ttf'
CAL_R     = f'{CROSEXTRA}/Caladea-Regular.ttf'
CAL_B     = f'{CROSEXTRA}/Caladea-Bold.ttf'
CAL_I     = f'{CROSEXTRA}/Caladea-Italic.ttf'
CAL_BI    = f'{CROSEXTRA}/Caladea-BoldItalic.ttf'
DVS       = f'{DEJAVU}/DejaVuSans.ttf'
DVS_B     = f'{DEJAVU}/DejaVuSans-Bold.ttf'

def reg(name, path):
    try: pdfmetrics.registerFont(TTFont(name, path)); return True
    except: return False

reg('Lora',    LORA);   reg('Lora-I', LORA_I)
reg('Cal',     CAL_R);  reg('Cal-B',  CAL_B)
reg('Cal-I',   CAL_I);  reg('Cal-BI', CAL_BI)
reg('DVS',     DVS);    reg('DVS-B',  DVS_B)

# ── BRAND COLORS ──────────────────────────────────────────────────────────
GOLD      = colors.HexColor('#C9A84C')
GOLD_DARK = colors.HexColor('#9A7020')
GOLD_LITE = colors.HexColor('#F0CC70')
AMBER     = colors.HexColor('#E8B84B')
NAVY      = colors.HexColor('#060E18')
NAVY2     = colors.HexColor('#0A1520')
NAVY3     = colors.HexColor('#112030')
NAVY4     = colors.HexColor('#1A3050')
CREAM     = colors.HexColor('#EDE8E0')
CREAM2    = colors.HexColor('#F5F0E8')
MUTED     = colors.HexColor('#6A7F96')
WHITE     = colors.HexColor('#FFFFFF')
BLACK     = colors.HexColor('#000000')
RED_DARK  = colors.HexColor('#8B2020')

W, H = letter
PW = W - 1.2*inch   # printable width

# ── DECORATIVE FLOWABLES ──────────────────────────────────────────────────

class GoldDivider(Flowable):
    """Triple-line gold divider with center diamond"""
    def __init__(self, width=None, spaceAbove=6, spaceBelow=6):
        super().__init__()
        self.w  = width or PW
        self.sa = spaceAbove
        self.sb = spaceBelow
    def wrap(self, *a): return self.w, 12 + self.sa + self.sb
    def draw(self):
        c = self.canv
        y = self.sb
        cx = self.w / 2
        # Outer thin lines
        c.setStrokeColor(GOLD_DARK)
        c.setLineWidth(0.4)
        c.line(0, y+10, cx-12, y+10)
        c.line(cx+12, y+10, self.w, y+10)
        # Main gold line
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.2)
        c.line(0, y+6, cx-8, y+6)
        c.line(cx+8, y+6, self.w, y+6)
        # Diamond center
        c.setFillColor(GOLD)
        c.setStrokeColor(GOLD_DARK)
        c.setLineWidth(0.5)
        pts = [cx, y+12,  cx+5, y+6,  cx, y+0,  cx-5, y+6]
        _p=c.beginPath();_pts=pts;[_p.moveTo(_pts[_j*2],_pts[_j*2+1]) if _j==0 else _p.lineTo(_pts[_j*2],_pts[_j*2+1]) for _j in range(len(_pts)//2)];_p.close();c.drawPath(_p,fill=1,stroke=0)
        # Bottom thin line
        c.setStrokeColor(GOLD_DARK)
        c.setLineWidth(0.4)
        c.line(0, y+2, self.w, y+2)


class SectionHeader(Flowable):
    """Premium full-width section header with number badge"""
    def __init__(self, title, number=None, width=None):
        super().__init__()
        self.title  = title
        self.number = number
        self.w      = width or PW
        self.h      = 46
    def wrap(self, *a): return self.w, self.h + 14
    def draw(self):
        c = self.canv
        # Dark background panel
        c.setFillColor(NAVY3)
        c.roundRect(0, 8, self.w, self.h, 4, fill=1, stroke=0)
        # Left gold accent bar
        c.setFillColor(GOLD)
        c.roundRect(0, 8, 5, self.h, 2, fill=1, stroke=0)
        # Gold top accent line
        c.setFillColor(GOLD)
        c.rect(0, 8 + self.h - 2, self.w, 2, fill=1, stroke=0)
        # Section number circle (if provided)
        if self.number:
            cx = 28
            cy = 8 + self.h/2
            c.setFillColor(GOLD)
            c.circle(cx, cy, 12, fill=1, stroke=0)
            c.setFillColor(NAVY)
            c.setFont('Cal-B', 10)
            c.drawCentredString(cx, cy - 4, str(self.number))
            tx = 50
        else:
            tx = 16
        # Title text
        c.setFillColor(GOLD_LITE)
        c.setFont('Cal-B', 14)
        c.drawString(tx, 8 + self.h/2 - 5, self.title.upper())
        # Subtle right decoration
        c.setFillColor(GOLD_DARK)
        for i, x in enumerate([self.w - 14, self.w - 22, self.w - 30]):
            r = 2.5 - i*0.5
            c.circle(x, 8 + self.h/2, r, fill=1, stroke=0)


class QuoteBox(Flowable):
    """Scripture quote box with decorative quotation mark"""
    def __init__(self, text, width=None):
        super().__init__()
        self.text = text
        self.w    = width or PW
        self._h   = None
    def wrap(self, aw, ah):
        style = ParagraphStyle('qs', fontName='Cal-I', fontSize=11,
            textColor=GOLD_LITE, leading=18, leftIndent=28, rightIndent=10)
        p = Paragraph(self.text, style)
        _, h = p.wrap(self.w - 48, ah)
        self._h = h + 36
        self._p = p
        return self.w, self._h
    def draw(self):
        c = self.canv
        h = self._h
        # Background
        c.setFillColor(NAVY3)
        c.roundRect(0, 0, self.w, h, 6, fill=1, stroke=0)
        # Left border
        c.setFillColor(GOLD)
        c.roundRect(0, 0, 4, h, 2, fill=1, stroke=0)
        # Decorative quotation mark
        c.setFillColor(GOLD)
        c.setFont('Cal-B', 52)
        c.setFillAlpha(0.15)
        c.drawString(8, h - 46, '\u201c')
        c.setFillAlpha(1.0)
        # Text
        c.setFillColor(GOLD_LITE)
        c.setFont('Cal-I', 11)
        self._p.drawOn(c, 28, 14)
        # Bottom reference line
        c.setStrokeColor(GOLD_DARK)
        c.setLineWidth(0.5)
        c.line(28, 10, self.w - 16, 10)


class QuestionCard(Flowable):
    """Question card with number badge and answer lines"""
    def __init__(self, text, number, width=None):
        super().__init__()
        self.text   = text
        self.number = number
        self.w      = width or PW
        self._h     = None
    def wrap(self, aw, ah):
        style = ParagraphStyle('qc', fontName='Cal-BI', fontSize=10.5,
            textColor=AMBER, leading=17, leftIndent=0, rightIndent=0)
        p = Paragraph(self.text, style)
        _, h = p.wrap(self.w - 56, ah)
        # Add space for 2 answer lines
        self._h = h + 52
        self._p = p
        return self.w, self._h
    def draw(self):
        c = self.canv
        h = self._h
        # Card background
        c.setFillColor(NAVY2)
        c.roundRect(0, 0, self.w, h, 5, fill=1, stroke=0)
        # Left accent
        c.setFillColor(AMBER)
        c.roundRect(0, 0, 4, h, 2, fill=1, stroke=0)
        # Number badge
        c.setFillColor(NAVY4)
        c.circle(22, h - 18, 13, fill=1, stroke=0)
        c.setFillColor(GOLD)
        c.setFont('Cal-B', 9)
        c.drawCentredString(22, h - 22, str(self.number))
        # Question text
        self._p.drawOn(c, 44, h - self._h + 38)
        # Answer lines
        c.setStrokeColor(NAVY4)
        c.setLineWidth(0.8)
        line_y = 22
        for _ in range(2):
            c.line(20, line_y, self.w - 20, line_y)
            line_y -= 16
        # Pencil icon area hint
        c.setFillColor(MUTED)
        c.setFont('DVS', 7)
        c.drawString(20, 5, 'Write your answer here...')


class FillInBox(Flowable):
    """Fill-in-the-blank box with styled blank lines"""
    def __init__(self, text, width=None):
        super().__init__()
        self.text = text
        self.w    = width or PW
    def wrap(self, aw, ah):
        self._h = 40
        return self.w, self._h
    def draw(self):
        c = self.canv
        # Background
        c.setFillColor(NAVY2)
        c.roundRect(0, 0, self.w, self._h, 4, fill=1, stroke=0)
        # Left accent
        c.setFillColor(GOLD_DARK)
        c.rect(0, 0, 3, self._h, fill=1, stroke=0)
        # Pencil icon
        c.setFillColor(GOLD_DARK)
        c.setFont('DVS', 9)
        c.drawString(10, self._h/2 - 5, '\u270e')
        # Text with blanks styled
        text = re.sub(r'_{2,}', '_' * 14, self.text)
        c.setFont('Lora', 10)
        c.setFillColor(CREAM)
        c.drawString(28, self._h/2 - 5, text[:80])


class CTABanner(Flowable):
    """Premium CTA banner with gradient-like layering"""
    def __init__(self, text, width=None):
        super().__init__()
        self.text = text
        self.w    = width or PW
        self._h   = None
    def wrap(self, aw, ah):
        style = ParagraphStyle('cta', fontName='Cal-B', fontSize=11,
            textColor=NAVY, leading=18, alignment=TA_CENTER)
        p = Paragraph(self.text[:300], style)
        _, h = p.wrap(self.w - 80, ah)
        self._h = h + 54
        self._p = p
        return self.w, self._h
    def draw(self):
        c = self.canv
        h = self._h
        # Outer dark border
        c.setFillColor(GOLD_DARK)
        c.roundRect(0, 0, self.w, h, 8, fill=1, stroke=0)
        # Inner amber fill
        c.setFillColor(AMBER)
        c.roundRect(2, 2, self.w-4, h-4, 7, fill=1, stroke=0)
        # Top highlight strip
        c.setFillColor(GOLD_LITE)
        c.setFillAlpha(0.3)
        c.roundRect(2, h-16, self.w-4, 14, 5, fill=1, stroke=0)
        c.setFillAlpha(1.0)
        # Book icon
        c.setFillColor(NAVY)
        c.setFont('DVS-B', 18)
        c.drawString(14, h/2 - 8, '\U0001f4d6')
        # Star decorations
        c.setFillColor(GOLD_DARK)
        c.setFont('DVS', 10)
        c.drawString(self.w - 28, h/2 - 5, '\u2605')
        c.drawString(self.w - 18, h/2 + 6, '\u2605')
        # Label
        c.setFillColor(NAVY3)
        c.setFont('DVS-B', 7)
        c.drawCentredString(self.w/2, h - 14, 'BIBLE STUDY COMPANION GUIDE')
        # Main text
        self._p.drawOn(c, 40, h/2 - self._h/2 + 20)
        # Bottom CTA line
        c.setFillColor(NAVY3)
        c.setFont('DVS-B', 8)
        c.drawCentredString(self.w/2, 8, '\u25bc  GET IT IN THE DESCRIPTION BELOW  \u25bc')


class PrayerBox(Flowable):
    """Prayer box with cross accent"""
    def __init__(self, text, width=None):
        super().__init__()
        self.text = text
        self.w    = width or PW
        self._h   = None
    def wrap(self, aw, ah):
        style = ParagraphStyle('pr', fontName='Cal-I', fontSize=10.5,
            textColor=CREAM, leading=18, leftIndent=20, rightIndent=20,
            alignment=TA_JUSTIFY)
        p = Paragraph(self.text, style)
        _, h = p.wrap(self.w - 60, ah)
        self._h = h + 44
        self._p = p
        return self.w, self._h
    def draw(self):
        c = self.canv
        h = self._h
        # Background
        c.setFillColor(NAVY3)
        c.roundRect(0, 0, self.w, h, 6, fill=1, stroke=0)
        # Dashed border
        c.setStrokeColor(GOLD_DARK)
        c.setLineWidth(0.8)
        c.setDash(4, 3)
        c.roundRect(3, 3, self.w-6, h-6, 5, fill=0, stroke=1)
        c.setDash()
        # Cross decoration top-right
        cx, cy = self.w - 22, h - 20
        c.setFillColor(GOLD)
        c.setFillAlpha(0.4)
        c.rect(cx-1.5, cy-10, 3, 20, fill=1, stroke=0)
        c.rect(cx-8, cy+2, 16, 3, fill=1, stroke=0)
        c.setFillAlpha(1.0)
        # PRAYER label
        c.setFillColor(GOLD)
        c.setFont('DVS-B', 8)
        c.drawString(16, h - 16, 'PRAYER')
        # Text
        self._p.drawOn(c, 20, 14)


# ── PAGE TEMPLATE ─────────────────────────────────────────────────────────
def _draw_cover_page(c, topic, guide_type, subtitle=''):
    """Draw premium cover directly on canvas"""
    w, h = W, H
    # Deep navy base
    c.setFillColor(NAVY); c.rect(0, 0, w, h, fill=1, stroke=0)
    # Layered panel
    c.setFillColor(NAVY2); c.rect(0, h*0.22, w, h*0.56, fill=1, stroke=0)
    # Diagonal texture
    c.setFillColor(colors.HexColor('#0A1828'))
    c.setFillAlpha(0.5)
    for xi in range(0, int(w*2), 28):
        p = c.beginPath()
        p.moveTo(xi-10, 0); p.lineTo(xi+14, 0)
        p.lineTo(xi+14-h*0.8, h); p.lineTo(xi-10-h*0.8, h); p.close()
        c.drawPath(p, fill=1, stroke=0)
    c.setFillAlpha(1.0)
    # Cross watermark
    cx = w*0.73; cy = h*0.48
    c.setFillColor(NAVY3); c.setFillAlpha(0.7)
    c.rect(cx-4, cy-h*0.25, 8, h*0.50, fill=1, stroke=0)
    c.rect(cx-h*0.16, cy+h*0.05, h*0.32, 8, fill=1, stroke=0)
    c.setFillAlpha(1.0)
    # Gold bars
    c.setFillColor(GOLD); c.rect(0, h*0.68, w, 3, fill=1, stroke=0)
    c.setFillColor(AMBER); c.rect(0, h*0.68+4, w, 1, fill=1, stroke=0)
    c.setFillColor(GOLD); c.rect(0, h*0.23, w, 1.5, fill=1, stroke=0)
    # Left accent
    c.setFillColor(GOLD); c.rect(0, 0, 7, h, fill=1, stroke=0)
    c.setFillColor(AMBER); c.rect(7, 0, 2, h, fill=1, stroke=0)
    # DBH label
    c.setFillColor(GOLD); c.setFont('DVS-B', 9)
    lbl = 'D E E P   B I B L E   H I S T O R Y'
    c.drawCentredString(w/2, h*0.87, lbl)
    lw = c.stringWidth(lbl, 'DVS-B', 9)
    c.setFont('DVS', 11)
    c.drawString(w/2-lw/2-22, h*0.87-2, '★')
    c.drawString(w/2+lw/2+10, h*0.87-2, '★')
    # Title panel
    c.setFillColor(colors.HexColor('#071020')); c.setFillAlpha(0.9)
    c.rect(16, h*0.68+6, w-22, h*0.18, fill=1, stroke=0); c.setFillAlpha(1.0)
    # Title
    words = topic.split(); lns = []; ln = ''
    for wd in words:
        test = (ln+' '+wd).strip()
        if c.stringWidth(test, 'Cal-B', 24) > w-80:
            if ln: lns.append(ln)
            ln = wd
        else: ln = test
    if ln: lns.append(ln)
    ty = h*0.68+6+h*0.18/2+len(lns)*16
    for ln in lns:
        ty -= 32
        c.setFillColor(GOLD_LITE); c.setFont('Cal-B', 24)
        c.drawCentredString(w/2, ty, ln)
    # Type badge
    bw = c.stringWidth(guide_type.upper(), 'DVS-B', 8)+30
    c.setFillColor(GOLD); c.roundRect(w/2-bw/2, h*0.68-26, bw, 18, 3, fill=1, stroke=0)
    c.setFillColor(NAVY); c.setFont('DVS-B', 8)
    c.drawCentredString(w/2, h*0.68-14, guide_type.upper())
    # Subtitle
    sub = subtitle or 'An evidence-based companion for the modern biblical explorer'
    c.setFillColor(MUTED); c.setFont('Cal-I', 10)
    c.drawCentredString(w/2, h*0.19, sub)
    # Copyright
    c.setFillColor(GOLD_DARK); c.setFont('DVS', 7)
    c.drawCentredString(w/2, h*0.07, '© Deep Bible History • All Rights Reserved')


class DBHPageTemplate:
    def __init__(self, topic, guide_type, total_pages=0):
        self.topic       = (topic[:52] + '...') if len(topic) > 52 else topic
        self.guide_type  = guide_type
        self.total_pages = total_pages

    def __call__(self, canv, doc):
        canv.saveState()
        # Draw cover on page 1, skip header/footer
        if doc.page == 1:
            _draw_cover_page(canv, self.topic, self.guide_type)
            canv.restoreState()
            return

        # ── FULL PAGE NAVY BACKGROUND ────────────────────────────────────
        canv.setFillColor(NAVY)
        canv.rect(0, 0, W, H, fill=1, stroke=0)
        # Subtle texture — slightly lighter band in content area
        canv.setFillColor(colors.HexColor('#080F1C'))
        canv.rect(0, 0.44*inch, W, H - 0.44*inch - 0.52*inch, fill=1, stroke=0)

        # ── HEADER ──────────────────────────────────────────────────────
        # Background
        canv.setFillColor(NAVY2)
        canv.rect(0, H - 0.52*inch, W, 0.52*inch, fill=1, stroke=0)
        # Gold bar
        canv.setFillColor(GOLD)
        canv.rect(0, H - 0.55*inch, W, 0.035*inch, fill=1, stroke=0)
        # Amber thin line
        canv.setFillColor(AMBER)
        canv.rect(0, H - 0.575*inch, W, 0.012*inch, fill=1, stroke=0)
        # DBH badge
        canv.setFillColor(GOLD)
        canv.roundRect(0.35*inch, H - 0.44*inch, 1.4*inch, 0.24*inch, 3, fill=1, stroke=0)
        canv.setFillColor(NAVY)
        canv.setFont('DVS-B', 7)
        canv.drawCentredString(0.35*inch + 0.7*inch, H - 0.33*inch, 'DEEP BIBLE HISTORY')
        # Topic
        canv.setFillColor(CREAM)
        canv.setFont('Cal-I', 8.5)
        canv.drawRightString(W - 0.38*inch, H - 0.33*inch, self.topic)

        # ── FOOTER ──────────────────────────────────────────────────────
        canv.setFillColor(NAVY2)
        canv.rect(0, 0, W, 0.44*inch, fill=1, stroke=0)
        canv.setFillColor(GOLD)
        canv.rect(0, 0.44*inch, W, 0.03*inch, fill=1, stroke=0)
        # Page number pill
        canv.setFillColor(NAVY3)
        canv.roundRect(W/2 - 18, 0.1*inch, 36, 0.2*inch, 4, fill=1, stroke=0)
        canv.setFillColor(GOLD)
        canv.setFont('DVS-B', 8)
        canv.drawCentredString(W/2, 0.155*inch, str(doc.page))
        # Copyright
        canv.setFillColor(MUTED)
        canv.setFont('DVS', 6.5)
        canv.drawString(0.38*inch, 0.155*inch, f'\u00a9 Deep Bible History. All rights reserved.')
        canv.drawRightString(W - 0.38*inch, 0.155*inch, self.guide_type)

        canv.restoreState()


# ── COVER PAGE ────────────────────────────────────────────────────────────
class CoverPage(Flowable):
    def __init__(self, topic, guide_type, subtitle=''):
        super().__init__()
        self.topic      = topic
        self.guide_type = guide_type
        self.subtitle   = subtitle

    def wrap(self, aw, ah):
        # Take full available frame space
        return aw, ah - 0.01

    def draw(self):
        c   = self.canv
        w   = PW
        h   = H - 1.25*inch  # safe frame height
        mL  = -0.6*inch

        # ── BACKGROUNDS ──
        # Deep navy base
        c.setFillColor(NAVY)
        c.rect(mL, -0.65*inch, W, H + 0.1*inch, fill=1, stroke=0)

        # Layered background panels
        c.setFillColor(NAVY2)
        c.rect(mL, h*0.25, W, h*0.55, fill=1, stroke=0)

        # Texture diagonal strips
        c.setFillColor(colors.HexColor('#0A1828'))
        for i in range(0, int(W*2), 28):
            c.setFillAlpha(0.5)
            pts = [mL + i, -0.65*inch,
                   mL + i + 18, -0.65*inch,
                   mL + i + 18 - h*0.8, h,
                   mL + i - h*0.8, h]
            p2=c.beginPath();[p2.moveTo(pts[j*2],pts[j*2+1]) if j==0 else p2.lineTo(pts[j*2],pts[j*2+1]) for j in range(len(pts)//2)];p2.close();c.drawPath(p2,fill=1,stroke=0)
        c.setFillAlpha(1.0)

        # ── DECORATIVE CROSS (large watermark) ──
        cx_cross = w * 0.72
        cy_cross = h * 0.46
        c.setFillColor(NAVY3)
        c.setFillAlpha(0.7)
        c.rect(cx_cross - 4, cy_cross - h*0.28, 8, h*0.56, fill=1, stroke=0)
        c.rect(cx_cross - h*0.18, cy_cross + h*0.06, h*0.36, 8, fill=1, stroke=0)
        c.setFillAlpha(1.0)

        # ── GOLD DECORATIVE LINES ──
        c.setFillColor(GOLD)
        c.rect(mL, h*0.68, W, 2.5, fill=1, stroke=0)
        c.setFillColor(AMBER)
        c.rect(mL, h*0.68 + 4, W, 0.8, fill=1, stroke=0)
        c.setFillColor(GOLD_DARK)
        c.rect(mL, h*0.68 - 1, W, 0.6, fill=1, stroke=0)

        c.setFillColor(GOLD)
        c.rect(mL, h*0.24, W, 1.5, fill=1, stroke=0)
        c.rect(mL, h*0.22, W, 0.5, fill=1, stroke=0)

        # ── LEFT ACCENT BAR ──
        c.setFillColor(GOLD)
        c.rect(mL, -0.65*inch, 6, H + 0.1*inch, fill=1, stroke=0)
        c.setFillColor(AMBER)
        c.rect(mL + 6, -0.65*inch, 2, H + 0.1*inch, fill=1, stroke=0)

        # ── TOP AREA — DBH LABEL ──
        c.setFillColor(GOLD)
        c.setFont('DVS-B', 9)
        label = 'D E E P   B I B L E   H I S T O R Y'
        c.drawCentredString(w/2, h*0.87, label)

        # Decorative stars
        c.setFont('DVS', 10)
        lw = c.stringWidth(label, 'DVS-B', 9)
        c.drawString(w/2 - lw/2 - 22, h*0.87 - 1, '\u2605')
        c.drawString(w/2 + lw/2 + 10, h*0.87 - 1, '\u2605')

        # ── TITLE AREA ──
        # Background panel for title
        c.setFillColor(colors.HexColor('#071020'))
        c.setFillAlpha(0.85)
        c.rect(mL + 14, h*0.68 + 6, W - 18, h*0.185, fill=1, stroke=0)
        c.setFillAlpha(1.0)

        # Main title — word wrap manually
        words = self.topic.split()
        lines_list = []
        line = ''
        for word in words:
            test = (line + ' ' + word).strip()
            if c.stringWidth(test, 'Cal-B', 26) > w - 0.3*inch:
                if line: lines_list.append(line)
                line = word
            else:
                line = test
        if line: lines_list.append(line)

        total_title_h = len(lines_list) * 34
        ty = h*0.68 + 6 + h*0.185/2 + total_title_h/2

        for ln in lines_list:
            ty -= 34
            c.setFillColor(GOLD_LITE)
            c.setFont('Cal-B', 26)
            c.drawCentredString(w/2, ty, ln)

        # ── GUIDE TYPE BADGE ──
        badge_y = h*0.68 - 28
        badge_w = c.stringWidth(self.guide_type.upper(), 'DVS-B', 8) + 32
        c.setFillColor(GOLD)
        c.roundRect(w/2 - badge_w/2, badge_y - 6, badge_w, 20, 4, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont('DVS-B', 8)
        c.drawCentredString(w/2, badge_y + 2, self.guide_type.upper())

        # ── LOWER AREA ──
        subtitle = self.subtitle or 'An evidence-based companion for the modern biblical explorer'
        c.setFillColor(MUTED)
        c.setFont('Cal-I', 10)
        c.drawCentredString(w/2, h*0.20, subtitle)

        # Diamond decorations
        c.setFillColor(GOLD_DARK)
        for dx in [-60, 60]:
            pts = [w/2 + dx, h*0.20 + 8,
                   w/2 + dx + 5, h*0.20 + 3,
                   w/2 + dx, h*0.20 - 2,
                   w/2 + dx - 5, h*0.20 + 3]
            p2=c.beginPath();[p2.moveTo(pts[j*2],pts[j*2+1]) if j==0 else p2.lineTo(pts[j*2],pts[j*2+1]) for j in range(len(pts)//2)];p2.close();c.drawPath(p2,fill=1,stroke=0)

        # ── BOTTOM ──
        c.setFillColor(GOLD_DARK)
        c.setFont('DVS', 7)
        c.drawCentredString(w/2, h*0.08,
            '\u00a9 Deep Bible History \u2022 All Rights Reserved')


# ── PDF BUILDER ───────────────────────────────────────────────────────────
def build_guide_pdf(guide_text, topic, guide_type, output_path):
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        rightMargin=0.6*inch, leftMargin=0.6*inch,
        topMargin=0.82*inch, bottomMargin=0.62*inch,
        title=f'DBH Study Guide — {topic}',
        author='Deep Bible History')

    tmpl  = DBHPageTemplate(topic, guide_type)
    story = []

    def S(nm, fn, sz, col, al=TA_LEFT, sb=5, sa=5, ld=None, li=0, ri=0):
        return ParagraphStyle(nm, fontName=fn, fontSize=sz, textColor=col,
            alignment=al, spaceBefore=sb, spaceAfter=sa,
            leading=ld or sz*1.55, leftIndent=li, rightIndent=ri)

    body   = S('b',  'Lora',  10.5, CREAM,    TA_JUSTIFY, 4, 6, 18)
    bold   = S('bb', 'Cal-B', 11,   CREAM2,   TA_LEFT,    4, 4, 17)
    italic = S('bi', 'Cal-I', 10.5, CREAM,    TA_JUSTIFY, 4, 6, 17, 16, 16)
    sub_h  = S('sh', 'Cal-B', 12,   GOLD_LITE,TA_LEFT,   10,  6, 18)
    bullet = S('bu', 'Lora',  10.5, CREAM,    TA_LEFT,    3,  3, 18, 22, 8)
    num_s  = S('nu', 'Lora',  10.5, CREAM,    TA_LEFT,    3,  3, 18, 22, 8)
    small  = S('sm', 'DVS',   7.5,  MUTED,    TA_LEFT,    2,  2, 12)

    # ── COVER ── drawn via page template callback
    # Cover drawn by page template on page 1
    story.append(PageBreak())

    # ── PARSE CONTENT ──
    # ── PRE-PROCESS: clean AI artifacts ──────────────────────────────
    # Strip any cover page section the AI may have generated
    guide_text = re.sub(
        r'=+\s*COVER PAGE\s*=+[\s\S]*?(?==+\s*SECTION|=+\s*WELCOME|=+\s*INTRODUCTION)',
        '', guide_text, flags=re.IGNORECASE)
    # Replace [DBH Logo] with proper credit
    guide_text = guide_text.replace('[DBH Logo]', 'DBH Research Biblical Team')
    guide_text = guide_text.replace('[DBH LOGO]', 'DBH Research Biblical Team')
    guide_text = guide_text.replace('Created by [DBH Research Biblical Team]',
                                    'Created by DBH Research Biblical Team')
    # Strip raw section markers that shouldn't appear in content
    guide_text = re.sub(r'-{3,}', '', guide_text)


    lines         = guide_text.split('\n')
    i             = 0
    sec_num       = 0
    current_sec   = ''
    q_num         = 0

    while i < len(lines):
        raw  = lines[i]
        line = raw.strip()

        if re.match(r'DELIVERABLE \d+', line, re.I):
            i += 1; continue

        # === SECTION === header
        m = re.match(r'=+\s*(?:SECTION\s*\d*:?\s*)?(.+?)\s*=+$', line, re.I)
        if m and len(line) > 4:
            title = m.group(1).replace('=','').strip()
            if title:
                sec_num += 1
                q_num    = 0
                story.append(Spacer(1, 0.12*inch))
                story.append(SectionHeader(title, sec_num))
                story.append(Spacer(1, 0.1*inch))
                current_sec = title.lower()
                i += 1; continue

        # ## / # subheading
        if re.match(r'^#{1,3}\s+', line):
            text = re.sub(r'^#{1,3}\s+', '', line)
            story.append(Spacer(1, 0.07*inch))
            story.append(GoldDivider(spaceAbove=2, spaceBelow=4))
            story.append(Paragraph(text, sub_h))
            i += 1; continue

        # **Bold heading**
        if re.match(r'^\*\*[^*]+\*\*$', line) and len(line) < 90:
            story.append(Spacer(1, 0.06*inch))
            story.append(Paragraph(re.sub(r'\*\*','',line), sub_h))
            i += 1; continue

        # CTA block
        if re.match(r'\[CTA MARKER', line, re.I) or 'CTA MARKER' in line.upper():
            cta_lines = []
            i += 1
            while i < len(lines) and not re.match(r'\[END CTA', lines[i], re.I):
                if lines[i].strip(): cta_lines.append(lines[i].strip())
                i += 1
            if cta_lines:
                story.append(Spacer(1, 0.14*inch))
                story.append(CTABanner(' '.join(cta_lines)[:350]))
                story.append(Spacer(1, 0.14*inch))
            i += 1; continue

        # Scripture quote — verse ref + quote marks
        if re.search(r'\b\d+:\d+', line) and ('"' in line or line.startswith('"') or '\u201c' in line):
            story.append(Spacer(1, 0.06*inch))
            story.append(QuoteBox(line))
            story.append(Spacer(1, 0.06*inch))
            i += 1; continue

        # Numbered question (has ?)
        if re.match(r'^\d+[\.\)]\s', line) and '?' in line:
            q_num += 1
            story.append(Spacer(1, 0.06*inch))
            story.append(QuestionCard(line, q_num))
            story.append(Spacer(1, 0.05*inch))
            i += 1; continue

        # Standalone question
        if line.endswith('?') and len(line) > 25 and not line.startswith('-'):
            q_num += 1
            story.append(Spacer(1, 0.05*inch))
            story.append(QuestionCard(line, q_num))
            story.append(Spacer(1, 0.04*inch))
            i += 1; continue

        # Fill in blank
        if '___' in line and len(line) > 8:
            story.append(FillInBox(line))
            story.append(Spacer(1, 0.03*inch))
            i += 1; continue

        # Prayer section
        if 'prayer' in current_sec and len(line) > 20:
            story.append(Spacer(1, 0.04*inch))
            story.append(PrayerBox(line))
            story.append(Spacer(1, 0.04*inch))
            i += 1; continue

        # Bullet
        if re.match(r'^[-\u2022]\s', line):
            text = re.sub(r'^[-\u2022]\s+','', line)
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            story.append(Paragraph(f'\u2022\u00a0 {text}', bullet))
            i += 1; continue

        # Numbered list (not question)
        if re.match(r'^\d+[\.\)]\s', line) and '?' not in line:
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
            story.append(Paragraph(text, num_s))
            i += 1; continue

        # HR
        if re.match(r'^[-_=]{3,}$', line):
            story.append(GoldDivider())
            i += 1; continue

        # Empty
        if not line:
            story.append(Spacer(1, 0.05*inch))
            i += 1; continue

        # Body text
        clean = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
        clean = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', clean)
        clean = clean.replace('&','&amp;')
        try:    story.append(Paragraph(clean, body))
        except: story.append(Paragraph(line,  body))
        i += 1

    # ── BACK COVER ──
    story.append(PageBreak())
    # Back cover drawn by last page template call

    # Count pages for back cover detection
    tmpl.total_pages_hint = len([x for x in story if isinstance(x, PageBreak)]) + 2
    doc.build(story, onFirstPage=tmpl, onLaterPages=tmpl)
    print(f'PDF built: {output_path}', file=sys.stderr)


if __name__ == '__main__':
    data = json.load(sys.stdin)
    build_guide_pdf(data['text'], data['topic'], data['guide_type'], data['output'])
