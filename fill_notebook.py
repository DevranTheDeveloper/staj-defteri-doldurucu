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


def process_internship_notebook(
    pdf_bytes: bytes,
    entries: List[Dict[str, Any]],
    start_date_str: str = "2026-08-10",
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

    # 1. Fill Attendance Sheets
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
