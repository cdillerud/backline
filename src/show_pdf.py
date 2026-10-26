"""Printable, band-scoped show production packet PDF."""
from io import BytesIO
from pathlib import Path
import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .show_schedule import show_timeline
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, Flowable, Table, TableStyle


# Embed the fonts bundled with ReportLab for consistent spacing on every PDF viewer.
_FONT_DIR = Path(reportlab.__file__).parent / 'fonts'
for _name, _file in (('BacklineSans','Vera.ttf'),('BacklineSans-Bold','VeraBd.ttf')):
    if _name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(_name,str(_FONT_DIR / _file)))
pdfmetrics.registerFontFamily('BacklineSans',normal='BacklineSans',bold='BacklineSans-Bold')

class StageDiagram(Flowable):
    """Vector stage plot embedded directly in the PDF, no external images."""
    def __init__(self, items):
        super().__init__()
        self.items=items
        self.width=500
        self.height=295

    def draw(self):
        c=self.canv
        c.setStrokeColor(colors.HexColor('#71849b'))
        c.setFillColor(colors.HexColor('#f0f5f9'))
        c.roundRect(4,20,492,265,12,stroke=1,fill=1)
        c.setFont('BacklineSans-Bold',9)
        c.setFillColor(colors.HexColor('#36506a'))
        c.drawCentredString(250,273,'UPSTAGE')
        c.drawCentredString(250,7,'AUDIENCE / DOWNSTAGE')
        for item in self.items:
            x=20+max(0,min(100,item['x']))*4.6
            y=34+(100-max(0,min(100,item['y'])))*2.25
            c.setFillColor(colors.HexColor('#d1f3a9'))
            c.circle(x,y,12,stroke=1,fill=1)
            c.setFillColor(colors.HexColor('#203448'))
            c.setFont('BacklineSans',8)
            label=str(item.get('label',''))[:32]
            c.drawCentredString(x,max(24,y-24),label)

def create_show_pdf(band, gig, packets, stage=None, advance=None):
    """Render a PDF from already-authorized band/gig records."""
    output=BytesIO()
    doc=SimpleDocTemplate(output,pagesize=(612,792),rightMargin=53,leftMargin=53,
        topMargin=57,bottomMargin=59,title=f"{gig['title']} - Show Packet",
        author=str(band['name']))
    base=getSampleStyleSheet()
    for style in base.byName.values():
        style.fontName='BacklineSans-Bold' if style.name.startswith(('Heading','Title')) else 'BacklineSans'
    base.add(ParagraphStyle(name='CoverEyebrowX',parent=base['Normal'],
        fontSize=11,leading=17,textColor=colors.HexColor('#6c852b'),alignment=TA_CENTER))
    base.add(ParagraphStyle(name='CoverTitleX',parent=base['Heading1'],
        fontSize=25,leading=33,spaceAfter=16,alignment=TA_CENTER,
        textColor=colors.HexColor('#162535')))
    base.add(ParagraphStyle(name='TitleX',parent=base['Heading1'],
        fontSize=20,leading=26,spaceAfter=18,textColor=colors.HexColor('#1c3043')))
    base.add(ParagraphStyle(name='SectionX',parent=base['Heading2'],
        fontSize=12,leading=17,spaceBefore=14,spaceAfter=6,
        textColor=colors.HexColor('#27425e')))
    base.add(ParagraphStyle(name='TextX',parent=base['BodyText'],
        fontSize=10,leading=15,spaceAfter=9))
    base.add(ParagraphStyle(name='NoticeX',parent=base['BodyText'],
        textColor=colors.HexColor('#a34732'),fontSize=9,leading=14,spaceAfter=8))
    e=lambda v:escape(str(v or ''))
    def para(value,style='TextX'):
        return Paragraph(e(value).replace('\n','<br/>'),base[style])
    stage=stage or {'items':[],'inputs':[],'notes':''}
    advance=advance or {}
    timeline=show_timeline(advance)
    notes=list(timeline["warnings"])
    if not stage.get('items'):notes.append('Stage plot has no equipment positions.')
    if not stage.get('inputs'):notes.append('Audio input list has no channels.')
    if not packets:notes.append('No show documents have been created.')
    for packet in packets:
        if packet['status']!='ready':
            notes.append(f"{packet['title']}: document is still a draft.")
        for section in packet['sections']:
            if 'TBD' in section['body'].upper() or 'TO CONFIRM' in section['body'].upper():
                notes.append(f"{packet['title']} / {section['heading']}: unresolved details.")
    story=[
        Spacer(1,1.7*inch),
        para(band['name'],'CoverEyebrowX'),
        Spacer(1,.22*inch),
        para('SHOW PRODUCTION PACKET','CoverTitleX'),
        para(gig['title'],'CoverTitleX'),
        Spacer(1,.23*inch),
        para(f"{gig['date']}  |  {gig['venue'] or 'Venue to confirm'}"),
        Spacer(1,.5*inch),
        para(f"Readiness: {sum(p['status']=='ready' for p in packets)} of {len(packets)} documents ready."),
    ]
    if notes:
        story.append(para('WORKING DRAFT — review missing or unconfirmed details before distribution.','NoticeX'))
    story.extend([PageBreak(),para('Contents','TitleX')])
    story.append(para('Venue contacts, logistics and day-of-show timeline'))
    story.append(para('Stage plot and audio inputs'))
    for n,packet in enumerate(packets,1):
        story.append(para(f"{n}. {packet['title']} — {packet['status'].upper()}"))
    if notes:
        story.extend([Spacer(1,.28*inch),para('Items requiring confirmation','SectionX')])
        for note in notes:
            story.append(para('• '+note,'NoticeX'))
    story.extend([PageBreak(),para('Venue advancement','TitleX'),
                  para('STATUS: '+advance.get('status','draft').upper()),
                  para('Venue time zone: '+(timeline['timezone'] or 'To confirm'))])
    for key,label in (('venue_contact','Venue contact'),('production_contact','Production contact'),
                      ('contact_email','Email'),('contact_phone','Phone'),('venue_address','Venue address'),
                      ('parking','Parking and access'),('lodging','Lodging'),
                      ('hospitality','Meals and hospitality'),('settlement','Settlement arrangements'),
                      ('open_questions','Outstanding questions')):
        if advance.get(key):story.extend([para(label,'SectionX'),para(advance[key])])
    story.extend([PageBreak(),para('Day-of-show timeline','TitleX'),para('Venue time zone: '+(timeline['timezone'] or 'To confirm')),para('STATUS: '+advance.get('status','draft').upper())])
    story.append(para('Day +1 and +2 are calendar days after the show date. Times are local to the venue.'))
    if timeline['entries']:
        rows=[[para(h) for h in ('Local time','Activity','Owner / location','Notes')]]
        for entry in timeline['entries']:
            day=f" (+{entry['day_offset']})" if entry['day_offset'] else ''
            rows.append([para(entry['time']+day),para(entry['title']),
                         para(' / '.join(filter(None,[entry.get('owner'),entry.get('location')]))),para(entry.get('notes',''))])
        table=Table(rows,colWidths=[70,120,130,180],repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef3')),
                                  ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.append(table)
    else:story.append(para('No schedule times recorded.','NoticeX'))
    if stage.get('items') or stage.get('inputs'):
        story.extend([PageBreak(),para('Stage plot and audio inputs','TitleX')])
        if stage.get('items'):
            story.extend([para('Stage layout','SectionX'),StageDiagram(stage['items'])])
        if stage.get('notes'):
            story.extend([Spacer(1,10),para('Stage notes','SectionX'),para(stage['notes'])])
        if stage.get('inputs'):
            story.append(para('Audio input list','SectionX'))
            rows=[[para(h) for h in ('CH','Source','Microphone / DI','Stand','Notes')]]
            for item in sorted(stage['inputs'],key=lambda x:x['channel']):
                rows.append([para(item.get(key,'')) for key in ('channel','source','microphone','stand','notes')])
            table=Table(rows,colWidths=[34,116,124,68,158],repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef3')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor('#71849b')),
                ('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#d8e1e9')),
                ('LEFTPADDING',(0,0),(-1,-1),4),
                ('RIGHTPADDING',(0,0),(-1,-1),4),
                ('TOPPADDING',(0,0),(-1,-1),5),
                ('BOTTOMPADDING',(0,0),(-1,-1),5)
            ]))
            story.append(table)
    for packet in packets:
        story.extend([PageBreak(),para(packet['title'],'TitleX'),
                      para('STATUS: '+packet['status'].upper(),'NoticeX' if packet['status']!='ready' else 'TextX')])
        for section in packet['sections']:
            story.append(KeepTogether([para(section['heading'],'SectionX'),
                                       para(section['body'])]))
    def footer(canvas,document):
        canvas.saveState()
        width,_=document.pagesize
        canvas.setStrokeColor(colors.HexColor('#b7c6d4'))
        canvas.line(53,43,width-53,43)
        canvas.setFont('BacklineSans',8)
        canvas.setFillColor(colors.HexColor('#526579'))
        canvas.drawString(53,30,str(band['name'])[:65])
        canvas.drawRightString(width-53,30,f"Show packet  |  Page {document.page}")
        canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
