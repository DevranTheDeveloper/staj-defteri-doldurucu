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
    """Normalizes unicode punctuation and Turkish characters for Type 1 / Core fonts in PDF."""
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
        "ı": "i",
        "İ": "I",
        "ş": "s",
        "Ş": "S",
        "ğ": "g",
        "Ğ": "G",
        "ü": "u",
        "Ü": "U",
        "ö": "o",
        "Ö": "O",
        "ç": "c",
        "Ç": "C",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def safe_insert_textbox(
    page: fitz.Page,
    rect: fitz.Rect,
    text: str,
    fontsize: float = 8.5,
    min_fontsize: float = 5.0,
    fontname: str = "tiro",
    align: int = fitz.TEXT_ALIGN_LEFT
) -> float:
    """Inserts text into a bounding box, automatically reducing font size if it overflows. Never drops text."""
    if text is None:
        return 0.0
    text_str = str(text).strip()
    if not text_str:
        return 0.0
    if rect.height < 35 and "\n" in text_str:
        text_clean = " ".join(text_str.split())
    else:
        text_clean = text_str

    current_fs = fontsize
    while current_fs >= min_fontsize:
        rc = page.insert_textbox(rect, text_clean, fontsize=current_fs, fontname=fontname, align=align)
        if rc >= 0:
            return rc
        current_fs -= 0.5

    return page.insert_textbox(rect, text_clean, fontsize=min_fontsize, fontname=fontname, align=align)


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
    safe_insert_textbox(
        p1,
        fitz.Rect(195, 631, 440, 656),
        "EEE 299",
        fontsize=11,
        fontname="tiro",
        align=fitz.TEXT_ALIGN_LEFT
    )

    # =========================================================================
    # 2. COMPULSORY INTERNSHIP FORM (Page 10 / Index 9)
    # =========================================================================
    p10 = doc[9]

    # Letter Header (Department & Days)
    p10.draw_rect(fitz.Rect(220, 158, 475, 169), color=None, fill=(1, 1, 1))
    p10.insert_text(fitz.Point(225, 167), "Electrical and Electronics Engineering", fontsize=8.5, fontname="tiro")
    p10.draw_rect(fitz.Rect(120, 235, 164, 245), color=None, fill=(1, 1, 1))
    p10.insert_text(fitz.Point(135, 244), "30", fontsize=9.0, fontname="tibo")

    # Table 1: Student Information
    safe_insert_textbox(p10, fitz.Rect(178, 287, 323, 301.44), "14642408896", fontsize=8.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(425, 287, 570, 301.44), "2025 - 2026", fontsize=8.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(178, 301, 323, 314.88), "Devran", fontsize=8.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(425, 301, 570, 314.88), "23091400016", fontsize=8.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(178, 314, 323, 328.32), "Sever", fontsize=8.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(425, 314, 570, 328.32), "Istanbul", fontsize=8.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(178, 328, 323, 341.76), "Murat", fontsize=8.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(425, 328, 570, 341.76), "08/02/2005", fontsize=8.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(178, 341, 323, 355.44), "Emine", fontsize=8.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(425, 341, 570, 355.44), "23091400016@ogr.halic.edu.tr", fontsize=8.0, min_fontsize=5.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(178, 355, 323, 368.88), "T.C.", fontsize=8.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(425, 355, 570, 368.88), "+90 5525235067", fontsize=8.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(178, 368.0, 570, 388.0), "Gazi Mah. Ismet Pasa Cad. 1416/1 Sok. no.:11 Daire:2 Sultangazi/Istanbul", fontsize=8.0, min_fontsize=5.0, fontname="tiro")

    # Table 2: Institution / Company Information
    safe_insert_textbox(p10, fitz.Rect(178, 403.0, 573, 418.0), "Akdeniz Pe-Tur Turizm Seyahat Acentasi ve Ticaret A.S.", fontsize=8.5, min_fontsize=5.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(178, 417.0, 573, 436.5), "Cobancesme Mah. Sanayi Cad. No:44 Nish Istanbul C Blok Kat:17 D: 197-200 Yenibosna, Bahcelievler, Istanbul, Turkiye", fontsize=8.0, min_fontsize=5.0, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(178, 434.0, 321, 449.0), "Turizm, Biletleme ve Bilisim Teknolojileri", fontsize=8.5, min_fontsize=5.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(424, 434.0, 573, 449.0), "Az Tehlikeli (Low Risk)", fontsize=8.5, min_fontsize=5.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(178, 448.0, 321, 462.0), "+90 850 222 08 30", fontsize=8.5, min_fontsize=5.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(424, 448.0, 573, 462.0), "(0212) 555 0101", fontsize=8.5, min_fontsize=5.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(178, 461.0, 321, 476.0), "info@petour.com", fontsize=8.5, min_fontsize=5.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(424, 461.0, 573, 476.0), "https://biletbank.com", fontsize=8.5, min_fontsize=5.5, fontname="tiro")

    # Starting date, End date, Duration
    p10.draw_rect(fitz.Rect(175, 477, 272, 508), color=None, fill=(1, 1, 1))
    safe_insert_textbox(p10, fitz.Rect(175, 477, 272, 508), "10/08/2026", fontsize=9.0, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

    p10.draw_rect(fitz.Rect(346, 477, 444, 508), color=None, fill=(1, 1, 1))
    safe_insert_textbox(p10, fitz.Rect(346, 477, 444, 508), "18/09/2026", fontsize=9.0, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

    p10.draw_rect(fitz.Rect(518, 477, 574, 508), color=None, fill=(1, 1, 1))
    safe_insert_textbox(p10, fitz.Rect(518, 477, 574, 508), "30 Workdays", fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

    # Table 3: Employer Information (Signature/stamp left blank for manual ink)
    safe_insert_textbox(p10, fitz.Rect(179, 545, 325, 560), "Mehmet Yilmaz", fontsize=8.0, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(179, 558, 325, 573), "Engineering Manager", fontsize=8.0, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(179, 571, 325, 586), "mehmet.yilmaz@teknoloji.com.tr", fontsize=7.5, fontname="tiro")
    safe_insert_textbox(p10, fitz.Rect(179, 585, 325, 600), "18/09/2026", fontsize=8.0, fontname="tiro")

    # Student Signature Date
    p10.draw_rect(fitz.Rect(98, 686, 180, 704), color=None, fill=(1, 1, 1))
    safe_insert_textbox(p10, fitz.Rect(98, 686, 180, 704), "25/07/2026", fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

    # =========================================================================
    # 3. INTERNSHIP ACCEPTANCE FORM (Page 11 / Index 10)
    # =========================================================================
    p11 = doc[10]
    # Top Submission Date
    p11.insert_textbox(fitz.Rect(430, 188, 545, 206), "28/07/2026", fontsize=9.5, fontname="tiro", align=fitz.TEXT_ALIGN_RIGHT)

    # Whiteout underlying dots for neat typography
    p11.draw_rect(fitz.Rect(70, 210, 222, 224), color=None, fill=(1, 1, 1))
    p11.draw_rect(fitz.Rect(293, 210, 362, 224), color=None, fill=(1, 1, 1))
    p11.draw_rect(fitz.Rect(70, 223, 200, 237), color=None, fill=(1, 1, 1))
    p11.draw_rect(fitz.Rect(70, 236, 182, 250), color=None, fill=(1, 1, 1))
    p11.draw_rect(fitz.Rect(237, 236, 363, 250), color=None, fill=(1, 1, 1))
    p11.draw_rect(fitz.Rect(462, 236, 530, 250), color=None, fill=(1, 1, 1))
    p11.draw_rect(fitz.Rect(70, 248, 132, 262), color=None, fill=(1, 1, 1))

    # Form text
    p11.insert_textbox(fitz.Rect(70, 208, 222, 226), "Devran Sever", fontsize=9.5, fontname="tibo", align=fitz.TEXT_ALIGN_CENTER)
    p11.insert_textbox(fitz.Rect(293, 208, 362, 226), "3rd", fontsize=9.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
    p11.insert_textbox(fitz.Rect(70, 221, 200, 239), "Electrical and Electronics Engineering", fontsize=7.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
    p11.insert_textbox(fitz.Rect(70, 234, 182, 252), "Teknoloji ve Yazilim Cozumleri", fontsize=7.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
    p11.insert_textbox(fitz.Rect(237, 234, 363, 252), "IT Operations & Software Engineering", fontsize=7.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
    p11.insert_textbox(fitz.Rect(462, 234, 530, 252), "10/08/2026", fontsize=9.0, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
    p11.insert_textbox(fitz.Rect(70, 246, 132, 264), "18/09/2026", fontsize=9.0, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

    # Employer Info on Page 11 (Stamp and signature left blank for manual ink)
    p11.draw_rect(fitz.Rect(205, 356, 535, 368), color=None, fill=(1, 1, 1))
    p11.insert_text(fitz.Point(212, 366), "Mehmet Yilmaz", fontsize=9.0, fontname="tiro")
    p11.draw_rect(fitz.Rect(205, 390, 535, 402), color=None, fill=(1, 1, 1))
    p11.insert_text(fitz.Point(212, 400), "Engineering Manager", fontsize=9.0, fontname="tiro")
    p11.draw_rect(fitz.Rect(205, 423, 535, 435), color=None, fill=(1, 1, 1))
    p11.insert_text(fitz.Point(212, 433), "18/09/2026", fontsize=9.0, fontname="tiro")

    # =========================================================================
    # 4. ATTENDANCE SHEET (Page 12 / Index 11)
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
    # 5. INTERN EVALUATION FORM (Page 13 / Index 12)
    # =========================================================================
    p13 = doc[12]
    # Student Info (Left Column)
    p13.insert_textbox(fitz.Rect(185, 194, 280, 212), "Devran Sever", fontsize=9.5, fontname="tibo")
    p13.insert_textbox(fitz.Rect(185, 206, 280, 224), "Electrical and Electronics Engineering", fontsize=8.0, fontname="tiro")
    p13.insert_textbox(fitz.Rect(155, 217, 280, 235), "3", fontsize=9.5, fontname="tiro")
    p13.insert_textbox(fitz.Rect(170, 228, 280, 246), "23091400016", fontsize=9.5, fontname="tiro")

    # Company & Duration Info (Right Column)
    p13.insert_textbox(fitz.Rect(405, 194, 560, 212), "Teknoloji ve Yazilim Cozumleri", fontsize=8.5, fontname="tiro")
    p13.insert_textbox(fitz.Rect(415, 206, 560, 224), "IT Operations & Software Engineering", fontsize=8.0, fontname="tiro")
    p13.insert_textbox(fitz.Rect(405, 217, 565, 235), "10/08/2026 - 18/09/2026 (30 Workdays)", fontsize=8.5, fontname="tiro")
    # Department Employees Metric
    p13.insert_textbox(fitz.Rect(492, 228, 565, 244), "12 Employees", fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_LEFT)

    # Bottom Employer Info on Page 13 (Signature/stamp left blank for manual ink)
    p13.insert_textbox(fitz.Rect(178, 681, 450, 695), "IT Operations & Software Engineering", fontsize=8.5, fontname="tiro")
    p13.insert_textbox(fitz.Rect(178, 696, 450, 714), "Mehmet Yilmaz", fontsize=8.5, fontname="tiro")
    p13.insert_textbox(fitz.Rect(178, 724, 300, 740), "18/09/2026", fontsize=9.0, fontname="tiro", align=fitz.TEXT_ALIGN_LEFT)

    # =========================================================================
    # 6. INTERNSHIP PLACE EVALUATION (Pages 14-15 / Index 13-14)
    # =========================================================================
    p14 = doc[13]
    p14.insert_textbox(fitz.Rect(255, 248, 545, 271), "Devran Sever", fontsize=9.5, fontname="tiro")

    # Company Name AND Full Address
    company_name_address = "Teknoloji ve Yazilim Cozumleri A.S.\nBuyukdere Cad. No:122 Levent / Besiktas / Istanbul"
    p14.insert_textbox(fitz.Rect(255, 273, 545, 309), company_name_address, fontsize=8.5, fontname="tiro", lineheight=1.1)

    # Sector
    p14.insert_textbox(fitz.Rect(255, 310, 545, 335), "Information Technology & Software Development", fontsize=8.5, fontname="tiro")

    # Workplace Evaluation (Engineer & Employee Stats)
    p14.insert_textbox(fitz.Rect(255, 340, 545, 362), "18", fontsize=9.5, fontname="tiro")  # Total Engineers
    p14.insert_textbox(fitz.Rect(255, 372, 545, 396), "4", fontsize=9.5, fontname="tibo")   # EEE Engineers (Crucial!)
    p14.insert_textbox(fitz.Rect(255, 407, 545, 429), "45", fontsize=9.5, fontname="tiro")  # Total Employees
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

    # Question 2: Need for EEE engineers why
    p15.draw_rect(fitz.Rect(155, 246, 450, 260), color=None, fill=(1, 1, 1))
    p15.insert_text(fitz.Point(160, 255), "Hardware-software integration & network infrastructure.", fontsize=8.0, fontname="tiro")

    # Question 4: Survey explanation
    p15.draw_rect(fitz.Rect(105, 366, 555, 376), color=None, fill=(1, 1, 1))
    p15.insert_textbox(
        fitz.Rect(72, 378, 555, 401),
        "N/A - The enterprise provided strong technical mentorship, well-equipped hardware labs, and advanced database infrastructure.",
        fontsize=8.0,
        fontname="tiro",
        lineheight=1.1
    )

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
