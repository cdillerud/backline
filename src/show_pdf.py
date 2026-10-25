"""Printable, band-scoped show production packet PDF."""
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether

def create_show_pdf(band, gig, packets):
    """Render a PDF from already-authorized band/gig records."""
    output=BytesIO()
    doc=SimpleDocTemplate(output,pagesize=(612,792),rightMargin=53,leftMargin=53,
        topMargin=57,bottomMargin=59,title=f"{gig['title']} - Show Packet",
        author=str(band['name']))
    base=getSampleStyleSheet()
    base.add(ParagraphStyle(name='CoverEyebrowX',parent=base['Normal'],
        fontSize=11,leading=17,textColor=colors.HexColor('#6c852b'),alignment=TA_CENTER))
    base.add(ParagraphStyle(name='CoverTitleX',parent=base['Heading1'],
        fontSize=30,leading=38,spaceAfter=16,alignment=TA_CENTER,
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
    notes=[]
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
    for n,packet in enumerate(packets,1):
        story.append(para(f"{n}. {packet['title']} — {packet['status'].upper()}"))
    if notes:
        story.extend([Spacer(1,.28*inch),para('Items requiring confirmation','SectionX')])
        for note in notes:
            story.append(para('• '+note,'NoticeX'))
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
        canvas.setFont('Helvetica',8)
        canvas.setFillColor(colors.HexColor('#526579'))
        canvas.drawString(53,30,str(band['name'])[:65])
        canvas.drawRightString(width-53,30,f"Show packet  |  Page {document.page}")
        canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
