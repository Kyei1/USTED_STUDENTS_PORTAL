"""Reusable PDF drawing helpers for portal exports."""

import os


def get_default_logo_path(app_root_path):
    """Return absolute path to the preferred USTED logo image with fallback."""
    preferred = os.path.join(app_root_path, 'static', 'images', 'usted-logo-with-full-sch-name.png')
    if os.path.exists(preferred):
        return preferred
    return os.path.join(app_root_path, 'static', 'images', 'usted-logo.png')


def draw_logo_and_titles(pdf, page_height, margin_left, colors, mm, logo_path, title_lines):
    """Draw logo and title lines, returning computed title-left x coordinate."""
    title_left = margin_left
    if os.path.exists(logo_path):
        try:
            from reportlab.lib.utils import ImageReader

            logo_img = ImageReader(logo_path)
            logo_w = 12 * mm
            logo_h = 12 * mm
            logo_x = margin_left
            logo_y = page_height - (18 * mm)
            pdf.drawImage(
                logo_img,
                logo_x,
                logo_y,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask='auto',
            )
            title_left = logo_x + logo_w + (3 * mm)
        except Exception:
            title_left = margin_left

    pdf.setFillColor(colors.HexColor('#7a0016'))
    for text, font_name, font_size, y_mm in title_lines:
        pdf.setFont(font_name, font_size)
        pdf.drawString(title_left, page_height - (y_mm * mm), text)

    return title_left


def draw_two_column_metadata(
    pdf,
    page_height,
    margin_left,
    details_left,
    details_right,
    colors,
    mm,
    detail_top_mm=34,
    row_gap_mm=7,
):
    """Draw a borderless two-column metadata block and return bottom y-position."""
    detail_top = page_height - (detail_top_mm * mm)
    label_x = margin_left + (1 * mm)
    value_x = margin_left + (34 * mm)
    right_label_x = margin_left + (102 * mm)
    right_value_x = margin_left + (131 * mm)
    row_gap = row_gap_mm * mm

    pdf.setFillColor(colors.HexColor('#7a0016'))
    pdf.setFont('Helvetica-Bold', 10)
    current_y = detail_top - (7 * mm)
    for label, value in details_left:
        pdf.drawString(label_x, current_y, f'{label}:')
        pdf.setFillColor(colors.black)
        pdf.setFont('Helvetica', 10)
        pdf.drawString(value_x, current_y, str(value))
        current_y -= row_gap
        pdf.setFillColor(colors.HexColor('#7a0016'))
        pdf.setFont('Helvetica-Bold', 10)

    current_y = detail_top - (7 * mm)
    for label, value in details_right:
        pdf.drawString(right_label_x, current_y, f'{label}:')
        pdf.setFillColor(colors.black)
        pdf.setFont('Helvetica', 10)
        pdf.drawString(right_value_x, current_y, str(value))
        current_y -= row_gap
        pdf.setFillColor(colors.HexColor('#7a0016'))
        pdf.setFont('Helvetica-Bold', 10)

    return detail_top - (34 * mm)
