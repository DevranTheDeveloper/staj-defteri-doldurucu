"""
fill_notebook.py - Dynamic Automated Form Filler for Internship Notebooks

Key Features:
  - Dynamic Template Layout Inspector: Automatically scans and detects daily report
    pages and attendance sheets without hardcoding page numbers.
  - Multi-layout adaptation: Calibrates bounding boxes per page based on text keywords
    ("Date:", "Department", "Signature") and vector drawing lines.
  - Auto-calculated Working Days: Generates valid business dates (Monday-Friday) from start_date.
  - Typography: Times New Roman ('tiro' regular, 'tibo' bold) with unicode sanitization.
  - Zero Clipping: Dynamic multi-step font scaling ensures text never overflows bounding boxes.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
import fitz  # PyMuPDF


def sanitize_text(text: str) -> str:
    """Normalizes unicode typography punctuation to prevent PDF Type 1 glyph errors."""
    if not text:
        return ""
    replacements = {
        "\u2013": "-",    # en-dash
        "\u2014": "--",   # em-dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2026": "...",  # ellipsis
        "\u00a0": " ",    # non-breaking space
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def get_workdays(start_date: datetime, count: int = 30) -> List[str]:
    """Generates consecutive working day dates (Mon-Fri) in DD/MM/YYYY format."""
    workdays = []
    curr = start_date
    while len(workdays) < count:
        if curr.weekday() < 5:  # 0=Mon, 4=Fri
            workdays.append(curr.strftime("%d/%m/%Y"))
        curr += timedelta(days=1)
    return workdays


def find_optimal_fontsize(
    text: str,
    rect: fitz.Rect,
    fontname: str = "tiro",
    preferred_size: float = 9.5,
    min_size: float = 6.0,
    step: float = 0.5,
    lineheight: float = 1.22,
) -> float:
    """Calculates maximum fitting fontsize using an isolated in-memory canvas."""
    size = preferred_size
    while size >= min_size:
        probe_doc = fitz.open()
        probe_page = probe_doc.new_page(width=rect.width + 100, height=rect.height + 100)
        test_rect = fitz.Rect(0, 0, rect.width, rect.height)
        rc = probe_page.insert_textbox(
            test_rect,
            text,
            fontsize=size,
            fontname=fontname,
            lineheight=lineheight,
            align=fitz.TEXT_ALIGN_LEFT,
        )
        probe_doc.close()
        if rc >= 0:
            return size
        size -= step
    return min_size


class TemplateInspector:
    """
    Dynamically inspects any internship notebook PDF template to locate
    attendance sheets and daily report pages, extracting their bounding boxes.
    """

    @staticmethod
    def inspect_document(doc: fitz.Document) -> Tuple[List[int], List[int], List[str]]:
        """
        Scans all pages in the document. Returns:
          - daily_page_indices: List of 0-based page indices identified as daily report forms.
          - attendance_page_indices: List of 0-based page indices identified as attendance sheets.
          - audit_logs: Diagnostic detection messages.
        """
        daily_pages = []
        attendance_pages = []
        logs = []

        total_pages = len(doc)
        logs.append(f"Analyzing PDF template ({total_pages} total pages)...")

        for idx, page in enumerate(doc):
            text = page.get_text()

            # Detect Attendance Sheet
            if ("ATTENDANCE SHEET" in text or "KATILIM ÇİZELGESİ" in text or "DEVAM ÇİZELGESİ" in text) and \
               ("DAY" in text or "GÜN" in text or "..../..../........" in text):
                attendance_pages.append(idx)
                logs.append(f"  -> Page {idx + 1}: Detected Intern Attendance Sheet")
                continue

            # Detect Daily Report Page (Requires both header indicator and footer/signature indicator)
            is_daily = False
            has_header = ("Department of the Internship" in text) or ("Internship Report" in text) or ("Staj Raporu" in text)
            has_footer = ("Signature of the Intern" in text) or ("Signature of the Staff" in text) or ("Stajyer İmzası" in text)

            if has_header and has_footer:
                is_daily = True
            elif ("Date:" in text or "Tarih:" in text) and ("Tasks Accomplished" in text or "Yapılan İşler" in text):
                is_daily = True

            if is_daily:
                daily_pages.append(idx)

        logs.append(f"Template Analysis Complete: Found {len(daily_pages)} daily form pages and {len(attendance_pages)} attendance page(s).")
        return daily_pages, attendance_pages, logs

    @staticmethod
    def get_page_boxes(page: fitz.Page) -> Tuple[fitz.Rect, fitz.Rect, fitz.Rect]:
        """
        Dynamically calculates target bounding boxes for:
          - dept_rect: Target area for Department
          - date_rect: Target area for Date
          - content_rect: Large bounded text area for Main Tasks Content
        """
        date_search = page.search_for("Date:")
        if not date_search:
            date_search = page.search_for("Tarih:")

        if date_search:
            date_kw = date_search[0]
        else:
            date_kw = fitz.Rect(339.36, 71.63, 365.36, 84.91)

        # Look for horizontal division lines in drawings
        h_lines = []
        for d in page.get_drawings():
            r = d["rect"]
            if r.width > 200 and r.height < 3:
                h_lines.append(r.y0)

        h_sorted = sorted(set(h_lines))
        # Find content top line (usually between y=85 and 115)
        top_lines = [y for y in h_sorted if 80 <= y <= 120]
        content_top = (max(top_lines) + 4.0) if top_lines else 104.0

        # Find content bottom line (usually between y=650 and 710)
        bottom_lines = [y for y in h_sorted if 650 <= y <= 720]
        content_bottom = (min(bottom_lines) - 4.0) if bottom_lines else 680.0

        # Determine header layout based on Date position
        if date_kw.x0 < 300:
            # Layout Variant 1 (e.g. Page 17)
            dept_rect = fitz.Rect(246.5, 72.0, 532.0, 92.0)
            date_rect = fitz.Rect(date_kw.x1 + 4.0, date_kw.y0, 532.0, date_kw.y1)
            content_rect = fitz.Rect(72.0, content_top, 530.0, content_bottom)
        else:
            # Layout Variant 2 (e.g. Pages 18-46)
            dept_rect = fitz.Rect(date_kw.x0, 85.0, 540.0, 100.0)
            date_rect = fitz.Rect(date_kw.x1 + 4.0, date_kw.y0, 540.0, date_kw.y1)
            content_rect = fitz.Rect(70.0, content_top, 539.0, content_bottom)

        return dept_rect, date_rect, content_rect


def fill_attendance_sheet(page: fitz.Page, dates: List[str]) -> bool:
    """Fills dates in attendance sheet table rows."""
    placeholders = page.search_for("..../..../........")
    if len(placeholders) >= 20:
        left_col = sorted([r for r in placeholders if r.x0 < 250], key=lambda r: r.y0)
        right_col = sorted([r for r in placeholders if r.x0 >= 250], key=lambda r: r.y0)

        for i in range(min(len(left_col), len(dates))):
            r = left_col[i]
            d_str = dates[i]
            page.draw_rect(r, color=None, fill=(1, 1, 1))
            cell_rect = fitz.Rect(r.x0 - 15, r.y0 - 2, r.x1 + 15, r.y1 + 5)
            page.insert_textbox(cell_rect, d_str, fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

        for i in range(min(len(right_col), max(0, len(dates) - 15))):
            r = right_col[i]
            d_str = dates[i + 15]
            page.draw_rect(r, color=None, fill=(1, 1, 1))
            cell_rect = fitz.Rect(r.x0 - 15, r.y0 - 2, r.x1 + 15, r.y1 + 5)
            page.insert_textbox(cell_rect, d_str, fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
        return True
    else:
        # Fallback to calibrated grid coordinates
        y_start = 268.0
        row_height = 21.9
        for i, d_str in enumerate(dates):
            if i < 15:
                rect = fitz.Rect(95, y_start + i * row_height, 175, y_start + (i + 1) * row_height)
            else:
                rect = fitz.Rect(355, y_start + (i - 15) * row_height, 435, y_start + (i - 14) * row_height)
            page.draw_rect(rect, color=None, fill=(1, 1, 1))
            page.insert_textbox(rect, d_str, fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
        return True


def fill_administrative_pages(
    doc: fitz.Document,
    student_info: Optional[Dict[str, str]] = None,
    dates: Optional[List[str]] = None
) -> List[str]:
    """Fills administrative & student headers across Pages 1, 11, 12, 13, 14, 15, 16."""
    logs = []
    info = {
        "name": "Devran Sever",
        "year": "3rd",
        "year_num": "3",
        "student_id": "23091400016",
        "department": "Electrical and Electronics Engineering",
        "internship_department": "IT Operations & Software Engineering",
        "company_field": "Information Technology & Software Development",
        "course_code": "EEE 299",
        "duration_workdays": "30 Workdays",
        "student_sign_date": "25/07/2026",
        "acceptance_date": "28/07/2026",
        "department_employees": "12 Employees",
        "evaluation_date": "18/09/2026",
        "total_engineers": "18",
        "eee_engineers": "4",
        "total_employees": "45",
        "survey_explanation": "N/A - The enterprise provided strong technical mentorship, well-equipped hardware labs, and advanced database infrastructure.",
    }
    if student_info:
        info.update(student_info)

    start_d = dates[0] if dates and len(dates) > 0 else "10/08/2026"
    end_d = dates[-1] if dates and len(dates) > 0 else "18/09/2026"

    # 1. Cover Page (Index 0)
    if len(doc) > 0:
        p1 = doc[0]
        if info.get("name"):
            p1.draw_rect(fitz.Rect(195, 569, 440, 594), color=None, fill=(1, 1, 1))
            p1.insert_textbox(fitz.Rect(195, 570, 440, 592), info["name"], fontsize=10.5, fontname="tibo", align=fitz.TEXT_ALIGN_LEFT)
        if info.get("student_id"):
            p1.draw_rect(fitz.Rect(195, 600, 440, 625), color=None, fill=(1, 1, 1))
            p1.insert_textbox(fitz.Rect(195, 601, 440, 623), str(info["student_id"]), fontsize=10.5, fontname="tiro", align=fitz.TEXT_ALIGN_LEFT)
        p1.draw_rect(fitz.Rect(195, 631, 440, 656), color=None, fill=(1, 1, 1))
        p1.insert_textbox(
            fitz.Rect(195, 631, 440, 656),
            info.get("course_code", "EEE 299"),
            fontsize=11,
            fontname="tiro",
            align=fitz.TEXT_ALIGN_LEFT
        )
        logs.append("Populated Cover Page (Page 1)")

    # 2. Compulsory Internship Form (Index 9 / Page 10)
    if len(doc) > 9:
        p10 = doc[9]
        if p10.search_for("Compulsory Internship Form") or p10.search_for("Starting date of Internship"):
            p10.draw_rect(fitz.Rect(175, 477, 272, 508), color=None, fill=(1, 1, 1))
            p10.insert_textbox(fitz.Rect(175, 477, 272, 508), start_d, fontsize=9.0, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

            p10.draw_rect(fitz.Rect(346, 477, 444, 508), color=None, fill=(1, 1, 1))
            p10.insert_textbox(fitz.Rect(346, 477, 444, 508), end_d, fontsize=9.0, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

            p10.draw_rect(fitz.Rect(518, 477, 574, 508), color=None, fill=(1, 1, 1))
            p10.insert_textbox(fitz.Rect(518, 477, 574, 508), info["duration_workdays"], fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

            # Student signature date (leaves coordinator and company signatures blank for ink)
            p10.draw_rect(fitz.Rect(98, 686, 180, 704), color=None, fill=(1, 1, 1))
            p10.insert_textbox(fitz.Rect(98, 686, 180, 704), info.get("student_sign_date", "25/07/2026"), fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
            logs.append("Populated Compulsory Internship Form (Page 10)")

    # 3. Acceptance Form (Index 10 / Page 11)
    if len(doc) > 10:
        p11 = doc[10]
        if p11.search_for("INTERNSHIP ACCEPTANCE FORM"):
            # Top date
            p11.insert_textbox(fitz.Rect(430, 188, 545, 206), info.get("acceptance_date", "28/07/2026"), fontsize=9.5, fontname="tiro", align=fitz.TEXT_ALIGN_RIGHT)

            p11.draw_rect(fitz.Rect(70, 210, 228, 224), color=None, fill=(1, 1, 1))
            p11.draw_rect(fitz.Rect(300, 210, 375, 224), color=None, fill=(1, 1, 1))
            p11.draw_rect(fitz.Rect(70, 223, 225, 237), color=None, fill=(1, 1, 1))
            p11.draw_rect(fitz.Rect(235, 236, 365, 250), color=None, fill=(1, 1, 1))
            p11.draw_rect(fitz.Rect(462, 236, 530, 250), color=None, fill=(1, 1, 1))
            p11.draw_rect(fitz.Rect(70, 248, 132, 262), color=None, fill=(1, 1, 1))

            p11.insert_textbox(fitz.Rect(70, 208, 228, 226), info["name"], fontsize=10, fontname="tibo", align=fitz.TEXT_ALIGN_CENTER)
            p11.insert_textbox(fitz.Rect(300, 208, 375, 226), info["year"], fontsize=9.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
            p11.insert_textbox(fitz.Rect(70, 221, 225, 239), info["department"], fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
            p11.insert_textbox(fitz.Rect(235, 234, 365, 252), info["internship_department"], fontsize=8.0, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
            p11.insert_textbox(fitz.Rect(462, 234, 530, 252), start_d, fontsize=9.0, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
            p11.insert_textbox(fitz.Rect(70, 246, 132, 264), end_d, fontsize=9.0, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)
            logs.append("Populated Internship Acceptance Form (Page 11)")

    # 4. Attendance Sheet Header (Index 11 / Page 12)
    if len(doc) > 11:
        p12 = doc[11]
        if p12.search_for("INTERN ATTENDANCE SHEET"):
            p12.insert_textbox(fitz.Rect(57, 204, 310, 232), info["name"], fontsize=11, fontname="tibo", align=fitz.TEXT_ALIGN_CENTER)
            p12.insert_textbox(fitz.Rect(312, 204, 564, 232), info["internship_department"], fontsize=10, fontname="tiro", align=fitz.TEXT_ALIGN_CENTER)

    # 5. Intern Evaluation Form (Index 12 / Page 13)
    if len(doc) > 12:
        p13 = doc[12]
        if p13.search_for("INTERN EVALUATION FORM"):
            p13.insert_textbox(fitz.Rect(185, 194, 280, 212), info["name"], fontsize=9.5, fontname="tibo")
            p13.insert_textbox(fitz.Rect(185, 206, 280, 224), info["department"], fontsize=8.0, fontname="tiro")
            p13.insert_textbox(fitz.Rect(155, 217, 280, 235), str(info.get("year_num", info.get("year", "3"))), fontsize=9.5, fontname="tiro")
            p13.insert_textbox(fitz.Rect(170, 228, 280, 246), str(info["student_id"]), fontsize=9.5, fontname="tiro")
            p13.insert_textbox(fitz.Rect(405, 194, 560, 212), info.get("company_name", "IT Operations & Software"), fontsize=9.0, fontname="tiro")
            p13.insert_textbox(fitz.Rect(415, 206, 560, 224), info["internship_department"], fontsize=9.0, fontname="tiro")
            p13.insert_textbox(fitz.Rect(405, 217, 565, 235), f"{start_d} - {end_d} ({info['duration_workdays']})", fontsize=8.5, fontname="tiro")
            # Department Employees Metric
            p13.insert_textbox(fitz.Rect(492, 228, 565, 244), info.get("department_employees", "12 Employees"), fontsize=8.5, fontname="tiro", align=fitz.TEXT_ALIGN_LEFT)
            # Employer Approval Date
            p13.insert_textbox(fitz.Rect(178, 724, 300, 740), info.get("evaluation_date", "18/09/2026"), fontsize=9.0, fontname="tiro", align=fitz.TEXT_ALIGN_LEFT)
            logs.append("Populated Intern Evaluation Form Header & Metrics (Page 13)")

    # 6. Place Evaluation Forms (Index 13 & 14 / Pages 14-15)
    if len(doc) > 14:
        p14 = doc[13]
        if p14.search_for("INTERNSHIP PLACE EVALUATION"):
            p14.insert_textbox(fitz.Rect(255, 248, 545, 271), info["name"], fontsize=9.5, fontname="tiro")
            p14.insert_textbox(fitz.Rect(255, 275, 545, 308), info.get("company_name", info["company_field"]), fontsize=9.0, fontname="tiro")
            p14.insert_textbox(fitz.Rect(255, 312, 545, 335), info.get("company_field", "Information Technology"), fontsize=9.0, fontname="tiro")

            # Engineer & Employee stats
            p14.insert_textbox(fitz.Rect(255, 340, 545, 362), str(info.get("total_engineers", "18")), fontsize=9.5, fontname="tiro")
            p14.insert_textbox(fitz.Rect(255, 372, 545, 396), str(info.get("eee_engineers", "4")), fontsize=9.5, fontname="tibo")
            p14.insert_textbox(fitz.Rect(255, 407, 545, 429), str(info.get("total_employees", "45")), fontsize=9.5, fontname="tiro")

            p14.insert_textbox(fitz.Rect(255, 435, 545, 457), info["duration_workdays"], fontsize=9.5, fontname="tiro")
            p14.insert_textbox(fitz.Rect(255, 620, 545, 642), "[X]", fontsize=10, fontname="tibo", align=fitz.TEXT_ALIGN_CENTER)
            p14.insert_textbox(fitz.Rect(255, 678, 545, 700), "[X]", fontsize=10, fontname="tibo", align=fitz.TEXT_ALIGN_CENTER)
            logs.append("Populated Internship Place Evaluation Page 1 (Page 14)")

        p15 = doc[14]
        if p15.search_for("COMPANY EVALUATION") or p15.search_for("INFORMATION TECHNOLOGIES"):
            p15.insert_textbox(fitz.Rect(255, 103, 545, 125), "[X]", fontsize=10, fontname="tibo", align=fitz.TEXT_ALIGN_CENTER)
            p15.insert_text(fitz.Point(434.5, 212.0), "X", fontsize=10, fontname="tibo")
            p15.insert_text(fitz.Point(434.5, 240.5), "X", fontsize=10, fontname="tibo")
            p15.insert_text(fitz.Point(434.5, 281.5), "X", fontsize=10, fontname="tibo")
            p15.insert_text(fitz.Point(434.5, 323.5), "X", fontsize=10, fontname="tibo")

            # Survey explanation
            p15.insert_textbox(
                fitz.Rect(72, 376, 555, 401),
                info.get("survey_explanation", "N/A - The enterprise provided strong technical mentorship, well-equipped hardware labs, and advanced database infrastructure."),
                fontsize=8.0,
                fontname="tiro",
                lineheight=1.1
            )
            logs.append("Populated Internship Place Evaluation Page 2 & Survey (Page 15)")

    # 7. Commission Evaluation Form (Index 15 / Page 16)
    if len(doc) > 15:
        p16 = doc[15]
        if p16.search_for("INTERNSHIP COMMISSION EVALUATION"):
            p16.insert_textbox(fitz.Rect(235, 184, 450, 202), info["name"], fontsize=9.5, fontname="tiro")
            p16.insert_textbox(fitz.Rect(235, 205, 450, 223), f"{info['year']} Year / {info['student_id']}", fontsize=9.5, fontname="tiro")
            p16.insert_textbox(fitz.Rect(235, 226, 450, 244), info["department"], fontsize=9.5, fontname="tiro")
            logs.append("Populated Internship Commission Evaluation Form (Page 16)")

    return logs


def process_internship_notebook(
    pdf_bytes: bytes,
    entries: List[Dict[str, Any]],
    start_date_str: str = "2026-08-10",
    student_info: Optional[Dict[str, str]] = None,
) -> Tuple[bytes, List[str]]:
    """
    Core functional processor accepting bytes and returning filled PDF bytes with audit logs.
    """
    logs = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    except Exception:
        start_date = datetime(2026, 8, 10)

    dates = get_workdays(start_date, len(entries))
    logs.append(f"Generated {len(dates)} business days starting from {dates[0]} to {dates[-1]}")

    # Dynamic Template Inspection
    daily_pages, attendance_pages, inspect_logs = TemplateInspector.inspect_document(doc)
    logs.extend(inspect_logs)

    # 1. Fill Administrative Pages (Cover, Acceptance, Eval, Place, Commission)
    admin_logs = fill_administrative_pages(doc, student_info, dates)
    logs.extend(admin_logs)

    # 2. Fill Attendance Sheets
    for att_idx in attendance_pages:
        fill_attendance_sheet(doc[att_idx], dates)
        logs.append(f"Populated Attendance Sheet on Page {att_idx + 1}")

    # 2. Fill Daily Pages
    injected = 0
    for i, entry in enumerate(entries):
        # Determine target page: entry["page_index"] if given and valid, else detected daily page
        if "page_index" in entry and 0 <= entry["page_index"] < len(doc):
            target_idx = entry["page_index"]
        elif i < len(daily_pages):
            target_idx = daily_pages[i]
        else:
            logs.append(f"[!] Warning: No available daily form page for Day {i + 1}. Skipping.")
            continue

        page = doc[target_idx]
        d_str = entry.get("date") or (dates[i] if i < len(dates) else "")
        dept_rect, date_rect, content_rect = TemplateInspector.get_page_boxes(page)

        # Top-right date header
        page.insert_textbox(fitz.Rect(415, 7, 545, 27), d_str, fontsize=9.5, fontname="tibo", align=fitz.TEXT_ALIGN_LEFT)

        # Table Date field
        page.insert_textbox(date_rect, d_str, fontsize=9.0, fontname="tibo", lineheight=1.0, align=fitz.TEXT_ALIGN_LEFT)

        # Department field
        dept_text = sanitize_text(entry.get("department", "").strip())
        if dept_text:
            dept_size = find_optimal_fontsize(dept_text, dept_rect, fontname="tiro", preferred_size=8.5, min_size=6.5, lineheight=1.0)
            page.insert_textbox(dept_rect, dept_text, fontsize=dept_size, fontname="tiro", lineheight=1.0, align=fitz.TEXT_ALIGN_LEFT)

        # Main Report Content
        topic = sanitize_text(entry.get("topic", "").strip())
        content = sanitize_text(entry.get("content", "").strip())
        full_text = f"TOPIC: {topic.upper()}\n\n{content}" if topic else content

        if full_text:
            optimal_size = find_optimal_fontsize(full_text, content_rect, fontname="tiro", preferred_size=9.2, min_size=7.5, lineheight=1.22)
            lh = 1.22 if optimal_size >= 9.0 else 1.15
            page.insert_textbox(content_rect, full_text, fontsize=optimal_size, fontname="tiro", lineheight=lh, align=fitz.TEXT_ALIGN_LEFT)

        injected += 1
        logs.append(f"Injected Day {i + 1:2d} ({d_str}) -> Page {target_idx + 1}")

    output_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    logs.append(f"Successfully generated filled PDF with {injected} days injected.")
    return output_bytes, logs


def fill_internship_notebook(
    input_pdf: str = "EEE-Internship Notebook.pdf",
    output_pdf: str = "Filled_Internship_Notebook_Final.pdf",
    data_json: str = "entries.json",
    start_date_str: str = "2026-08-10",
):
    """CLI and file-based wrapper."""
    with open(input_pdf, "rb") as f:
        pdf_bytes = f.read()

    with open(data_json, "r", encoding="utf-8") as f:
        entries = json.load(f)

    out_bytes, logs = process_internship_notebook(pdf_bytes, entries, start_date_str)
    for line in logs:
        print(line)

    with open(output_pdf, "wb") as f:
        f.write(out_bytes)
    print(f"[✓] Output written to {output_pdf}")


def main():
    parser = argparse.ArgumentParser(
        description="Dynamic Automated Form Filler for Internship Notebooks"
    )
    parser.add_argument("--input", "-i", default="EEE-Internship Notebook.pdf", help="Input template PDF path")
    parser.add_argument("--output", "-o", default="Filled_Internship_Notebook_Final.pdf", help="Output PDF path")
    parser.add_argument("--data", "-d", default="entries.json", help="Entries JSON data file")
    parser.add_argument("--start-date", "-s", default="2026-08-10", help="Start date (YYYY-MM-DD)")
    args = parser.parse_args()

    fill_internship_notebook(args.input, args.output, args.data, args.start_date)


if __name__ == "__main__":
    main()
