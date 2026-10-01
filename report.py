import calendar
import io
import math
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, PageBreak, KeepInFrame)
VIOLET = colors.HexColor("#B2A1C7")
ORANGE = colors.HexColor("#FAC090")
SKY = colors.HexColor("#C5D9F1")
YELLOW = colors.HexColor("#FFFF00")
FILL = {"late": VIOLET, "present": colors.white, "leave": ORANGE, "holiday": SKY, "sunday": YELLOW}
W, H = landscape(letter)
M = 24
AVAIL_W, AVAIL_H = W - 2 * M, H - 2 * M
P = lambda **k: ParagraphStyle("x", fontName=k.pop("fn", "Helvetica"), **k)
S_TITLE = P(fontSize=13, leading=15, alignment=TA_CENTER, fn="Helvetica-Bold")
S_SUB = P(fontSize=8, leading=10, alignment=TA_CENTER)
S_H = P(fontSize=10, leading=12, alignment=TA_CENTER, fn="Helvetica-Bold")
S_CELL = P(fontSize=6.5, leading=7.5, alignment=TA_CENTER)
S_SHIFT = P(fontSize=5.2, leading=6, alignment=TA_CENTER)
S_LAB = P(fontSize=6.5, leading=7.5, fn="Helvetica-Bold")
S_INFO = P(fontSize=7.5, leading=9)
S_INFO_B = P(fontSize=7.5, leading=9, fn="Helvetica-Bold")
ROWS = [("Date", None), ("In time", "in"), ("Out time", "out"), ("Total duration", "total"),
        ("Shift code", "shift"), ("Late By", "late"), ("Early By", "early"),
        ("Permission Time", "perm"), ("Half-CL", "half")]
def _day_block(staff, days, month, year):
    cols = len(days)
    label_w = 58
    cw = (AVAIL_W - label_w) / 10.0
    data = []
    for label, key in ROWS:
        row = [Paragraph(label, S_LAB)]
        for d in days:
            info = staff["days"][d]
            if key is None:
                txt = f"{d:02d}-{month:02d}-{year % 100:02d}"
            else:
                txt = info[key]
            if key == "shift":
                row.append(Paragraph(txt, S_SHIFT))
            else:
                row.append(Paragraph(txt, S_CELL))
        data.append(row)
    t = Table(data, colWidths=[label_w] + [cw] * cols,
              rowHeights=[11, 11, 11, 11, 21, 11, 11, 11, 11])
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.black),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("LEFTPADDING", (0, 0), (-1, -1), 1.5), ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
          ("TOPPADDING", (0, 0), (-1, -1), 0.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5)]
    for i, d in enumerate(days, start=1):
        st.append(("BACKGROUND", (i, 0), (i, -1), FILL["late" if staff["days"][d]["is_late"] else staff["days"][d]["status"]]))
    t.setStyle(TableStyle(st))
    return t


def _legend():
    items = [(VIOLET, "Late (in time after 9:00 AM)"), (ORANGE, "Leave"),
             (SKY, "College holiday"), (YELLOW, "Sunday")]
    cells, widths = [], []
    for c, txt in items:
        cells += ["", Paragraph(txt, S_INFO)]
        widths += [14, 125]
    t = Table([cells], colWidths=widths, rowHeights=[11])
    st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i, (c, _) in enumerate(items):
        st += [("BACKGROUND", (2 * i, 0), (2 * i, 0), c),
               ("BOX", (2 * i, 0), (2 * i, 0), 0.4, colors.black)]
    t.setStyle(TableStyle(st))
    t.hAlign = "LEFT"
    return t
def _staff_story(staff, data):
    year, month = data["year"], data["month"]
    n = calendar.monthrange(year, month)[1]
    story = []
    for line in data["title"][:1]:
        story.append(Paragraph(line, S_TITLE))
    for line in data["title"][1:]:
        story.append(Paragraph(line, S_SUB))
    story.append(Spacer(1, 3))
    story.append(Paragraph(f"Monthly Attendance Report - {calendar.month_name[month].upper()} {year}", S_H))
    story.append(Spacer(1, 5))
    info = [[Paragraph("S/L", S_INFO_B), Paragraph("Employee Id", S_INFO_B), Paragraph("Name", S_INFO_B),
             Paragraph("Role", S_INFO_B), Paragraph("Department", S_INFO_B),
             Paragraph("Designation", S_INFO_B), Paragraph("Date of Joining", S_INFO_B)],
            [Paragraph(x or "-", S_INFO) for x in (staff["slno"], staff["emp_id"], staff["name"], staff["role"],
                                                    staff["dept"], staff["designation"], staff["doj"])]]
    ti = Table(info, colWidths=[24, 60, 100, 62, 100, 110, 58])
    ti.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.black),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    summ = [[Paragraph("No of Working Days", S_INFO_B), Paragraph(str(staff["working"]), S_INFO_B)],
            [Paragraph("No of Days Late", S_INFO_B), Paragraph(str(staff["late"]), S_INFO_B)],
            [Paragraph("No of Days Leave", S_INFO_B), Paragraph(str(staff["leave"]), S_INFO_B)],
            [Paragraph("No of Days Present", S_INFO), Paragraph(str(staff["present"]), S_INFO)]]
    ts = Table(summ, colWidths=[95, 35])
    ts.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.6, colors.black),
                            ("ALIGN", (1, 0), (1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    top = Table([[ti, ts]], colWidths=[AVAIL_W - 140, 140])
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [top, Spacer(1, 6)]

    per = math.ceil(n / 3)
    all_days = list(range(1, n + 1))
    for i in range(0, n, per):
        story += [_day_block(staff, all_days[i:i + per], month, year), Spacer(1, 6)]
    story.append(_legend())
    return [KeepInFrame(AVAIL_W, AVAIL_H, story, mode="shrink")]


def build_pdf(results, data, only=None):
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=landscape(letter), leftMargin=M, rightMargin=M,
                          topMargin=M, bottomMargin=M, title="Attendance Report")
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(M, M, AVAIL_W, AVAIL_H, 0, 0, 0, 0)])])
    story = []
    sel = [r for r in results if only is None or r["emp_id"] in only]
    for i, r in enumerate(sel):
        story += _staff_story(r, data)
        if i < len(sel) - 1:
            story.append(PageBreak())
    doc.build(story)
    return buf.getvalue()
