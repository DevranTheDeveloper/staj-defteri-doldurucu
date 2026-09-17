"""
fill_all_notebook.py - Complete Automated Form Filler for Haliç University EEE Internship Notebook

Fills:
  1. Administrative header & student info across Pages 1, 11, 12, 13, 14, 15, and 16.
  2. 30-Day Attendance Sheet on Page 12 with whiteout and centered dates.
  3. 30-Day Daily Logs on Pages 17 to 46 using entries.json, Times New Roman, and autoscale typography.
  4. Leaves all signatures, company stamps, and official grade boxes blank for manual ink signatures.
"""

import os
import json
from datetime import datetime, timedelta
import fitz  # PyMuPDF


def get_workdays(start_date: datetime, count: int = 30):
    """Calculates consecutive business days (Monday to Friday)."""
    workdays = []
    curr = start_date
    while len(workdays) < count:
        if curr.weekday() < 5:
            workdays.append(curr.strftime("%d/%m/%Y"))
        curr += timedelta(days=1)
    return workdays


def sanitize_text(text: str) -> str:
    """Normalizes unicode punctuation for Type 1 / Core fonts in PDF."""
    if not text:
        return ""
    replacements = {
        "\u2013": "-",
        "\u2014": "--",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def run():
    input_pdf = "EEE-Internship Notebook.pdf"
    output_pdf = "EEE-Internship Notebook_Complete.pdf"
    entries_file = "entries.json"

    if not os.path.isfile(input_pdf):
        raise FileNotFoundError(f"Template PDF not found: {input_pdf}")

    if not os.path.isfile(entries_file):
        raise FileNotFoundError(f"Entries JSON not found: {entries_file}")

    doc = fitz.open(input_pdf)

    with open(entries_file, "r", encoding="utf-8") as f:
        entries = json.load(f)

    # 30 Workdays starting Aug 10, 2026 to Sep 18, 2026
    start_date = datetime(2026, 8, 10)
    dates = get_workdays(start_date, 30)

    print(f"[*] Total pages: {len(doc)}")
    print(f"[*] Date span: {dates[0]} -> {dates[-1]} ({len(dates)} business days)")

    # =========================================================================
    # 1. COVER PAGE (Page 1 / Index 0)
    # =========================================================================
    p1 = doc[0]
    # Internship Course ID box below Student ID
    p1.insert_textbox(
        fitz.Rect(195, 631, 440, 656),
        "EEE 299",
        fontsize=11,
        fontname="tiro",
        align=fitz.TEXT_ALIGN_LEFT
    )

    # =========================================================================
    # 2. INTERNSHIP ACCEPTANCE FORM (Page 11 / Index 10)
    # =========================================================================
    p11 = doc[10]
    # Whiteout underlying dots for neat typography
    p11.draw_rect(fitz.Rect(70, 210, 228, 224), color=None, fill=(1, 1, 1))
    p11.draw_rect(fitz.Rect(300, 210, 375, 224), color=None, fill=(1, 1, 1))
    p11.draw_rect(fitz.Rect(70, 223, 225, 237), color=None, fill=(1, 1, 1))
    p11.draw_rect(fitz.Rect(235, 236, 365, 250), color=None, fill=(1, 1, 1))
    p11.draw_rect(fitz.Rect(462, 236, 530, 250), color=None, fill=(1, 1, 1))
    p11.draw_rect(fitz.Rect(70, 248, 132, 262), color=None, fill=(1, 1, 1))

    p11.insert_textbox(fitz.Rect(70, 208, 228, 226), "Devran Sever", fontsize=10, fontname="tibo", align=fitz.TEXT_ALIGN_CENTER)
    p11.insert_textbox(fitz.Rect(300, 208, 375, 226), "3rd", fontsize=9.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
    p11.insert_textbox(fitz.Rect(70, 221, 225, 239), "Electrical and Electronics Engineering", fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
    p11.insert_textbox(fitz.Rect(235, 234, 365, 252), "IT Operations & Software Engineering", fontsize=8.0, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
    p11.insert_textbox(fitz.Rect(462, 234, 530, 252), "10/08/2026", fontsize=9.0, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
    p11.insert_textbox(fitz.Rect(70, 246, 132, 264), "18/09/2026", fontsize=9.0, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

    # =========================================================================
    # 3. ATTENDANCE SHEET (Page 12 / Index 11)
    # =========================================================================
    p12 = doc[11]
    # Header cells for Student Name and Department
    p12.insert_textbox(fitz.Rect(57, 204, 310, 232), "Devran Sever", fontsize=11, fontname="tibo", align=fitz.TEXT_ALIGN_CENTER)
    p12.insert_textbox(fitz.Rect(312, 204, 564, 232), "IT Operations & Software Engineering", fontsize=10, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

    # 30-Day table rows (Days 1 to 15 in col 1, Days 16 to 30 in col 2)
    placeholders = p12.search_for("..../..../........")
    left_col = sorted([r for r in placeholders if r.x0 < 250], key=lambda r: r.y0)
    right_col = sorted([r for r in placeholders if r.x0 >= 250], key=lambda r: r.y0)

    for i in range(min(len(left_col), 15)):
        r = left_col[i]
        p12.draw_rect(r, color=None, fill=(1, 1, 1))
        p12.insert_textbox(fitz.Rect(r.x0 - 15, r.y0 - 2, r.x1 + 15, r.y1 + 5), dates[i], fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

    for i in range(min(len(right_col), 15)):
        r = right_col[i]
        p12.draw_rect(r, color=None, fill=(1, 1, 1))
        p12.insert_textbox(fitz.Rect(r.x0 - 15, r.y0 - 2, r.x1 + 15, r.y1 + 5), dates[i + 15], fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

    # =========================================================================
    # 4. INTERN EVALUATION FORM (Page 13 / Index 12)
    # =========================================================================
    p13 = doc[12]
    # Student Info (Left Column)
    p13.insert_textbox(fitz.Rect(185, 194, 280, 212), "Devran Sever", fontsize=9.5, fontname="tibo")
    p13.insert_textbox(fitz.Rect(185, 206, 280, 224), "Electrical and Electronics Engineering", fontsize=8.0, fontname="tiro")
    p13.insert_textbox(fitz.Rect(155, 217, 280, 235), "3", fontsize=9.5, fontname="tiro")
    p13.insert_textbox(fitz.Rect(170, 228, 280, 246), "23091400016", fontsize=9.5, fontname="tiro")

    # Company & Duration Info (Right Column)
    p13.insert_textbox(fitz.Rect(405, 194, 560, 212), "IT Operations & Software", fontsize=9.0, fontname="tiro")
    p13.insert_textbox(fitz.Rect(415, 206, 560, 224), "Software Development", fontsize=9.0, fontname="tiro")
    p13.insert_textbox(fitz.Rect(405, 217, 565, 235), "10/08/2026 - 18/09/2026 (30 Workdays)", fontsize=8.5, fontname="tiro")

    # =========================================================================
    # 5. INTERNSHIP PLACE EVALUATION (Pages 14-15 / Index 13-14)
    # =========================================================================
    p14 = doc[13]
    p14.insert_textbox(fitz.Rect(255, 248, 545, 271), "Devran Sever", fontsize=9.5, fontname="tiro")
    p14.insert_textbox(fitz.Rect(255, 275, 545, 308), "Information Technology & Software Development", fontsize=9.0, fontname="tiro")
    p14.insert_textbox(fitz.Rect(255, 312, 545, 335), "Information Technology", fontsize=9.0, fontname="tiro")
    p14.insert_textbox(fitz.Rect(255, 435, 545, 457), "30 Workdays", fontsize=9.5, fontname="tiro")

    # Area tick boxes on Page 14
    p14.insert_textbox(fitz.Rect(255, 620, 545, 642), "[X]", fontsize=10, fontname="tibo", align=fitz.TEXT_ALIGN_CENTER)  # Product Design
    p14.insert_textbox(fitz.Rect(255, 678, 545, 700), "[X]", fontsize=10, fontname="tibo", align=fitz.TEXT_ALIGN_CENTER)  # Maintenance

    p15 = doc[14]
    p15.insert_textbox(fitz.Rect(255, 103, 545, 125), "[X]", fontsize=10, fontname="tibo", align=fitz.TEXT_ALIGN_CENTER)  # Information Technologies

    # Survey questions (YES checkmarks inside square boxes)
    p15.insert_text(fitz.Point(434.5, 212.0), "X", fontsize=10, fontname="tibo")  # R&D activities YES
    p15.insert_text(fitz.Point(434.5, 240.5), "X", fontsize=10, fontname="tibo")  # Need EEE engineers YES
    p15.insert_text(fitz.Point(434.5, 281.5), "X", fontsize=10, fontname="tibo")  # Suggest company YES
    p15.insert_text(fitz.Point(434.5, 323.5), "X", fontsize=10, fontname="tibo")  # Want to work YES

    # =========================================================================
    # 6. COMMISSION EVALUATION FORM (Page 16 / Index 15)
    # =========================================================================
    p16 = doc[15]
    p16.insert_textbox(fitz.Rect(235, 184, 450, 202), "Devran Sever", fontsize=9.5, fontname="tiro")
    p16.insert_textbox(fitz.Rect(235, 205, 450, 223), "3rd Year / 23091400016", fontsize=9.5, fontname="tiro")
    p16.insert_textbox(fitz.Rect(235, 226, 450, 244), "Electrical and Electronics Engineering", fontsize=9.5, fontname="tiro")
    # All evaluation checkboxes and signatures left BLANK for manual ink evaluation

    # =========================================================================
    # 7. DAILY REPORT PAGES (Pages 17-46 / Index 16-45)
    # =========================================================================
    for i, entry in enumerate(entries):
        page_idx = 16 + i
        if page_idx >= len(doc):
            break
        page = doc[page_idx]
        d_str = dates[i]

        # Top-Right Date Box
        page.insert_textbox(fitz.Rect(415, 7, 545, 27), d_str, fontsize=9.5, fontname="tibo", align=fitz.TEXT_ALIGN_LEFT)

        # Department Box
        dept = sanitize_text(entry.get("department", "").strip())
        page.insert_textbox(fitz.Rect(210, 52, 450, 72), dept, fontsize=9.5, fontname="tiro", align=fitz.TEXT_ALIGN_LEFT)

        # Date in table row if layout has Date: keyword
        date_kw = page.search_for("Date:")
        if date_kw:
            page.insert_textbox(fitz.Rect(date_kw[0].x1 + 4, date_kw[0].y0, 540, date_kw[0].y1), d_str, fontsize=9.0, fontname="tibo", lineheight=1.0)

        # Main Report Content
        content_rect = fitz.Rect(54, 115, 540, 720)
        topic = sanitize_text(entry.get("topic", "").strip()).upper()
        content = sanitize_text(entry.get("content", "").strip())
        full_text = f"TOPIC: {topic}\n\n{content}" if topic else content

        # Multi-step font scale to guarantee zero overflow
        rc = page.insert_textbox(
            content_rect,
            full_text,
            fontsize=9.2,
            fontname="tiro",
            lineheight=1.22,
            align=fitz.TEXT_ALIGN_LEFT
        )
        if rc < 0:
            rc = page.insert_textbox(
                content_rect,
                full_text,
                fontsize=8.3,
                fontname="tiro",
                lineheight=1.14,
                align=fitz.TEXT_ALIGN_LEFT
            )
            if rc < 0:
                page.insert_textbox(
                    content_rect,
                    full_text,
                    fontsize=7.6,
                    fontname="tiro",
                    lineheight=1.10,
                    align=fitz.TEXT_ALIGN_LEFT
                )

    doc.save(output_pdf, garbage=4, deflate=True)
    doc.close()
    print(f"[✓] Success! Generated complete internship notebook at: {output_pdf}")


if __name__ == "__main__":
    run()
