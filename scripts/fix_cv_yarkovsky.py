from __future__ import annotations

from pathlib import Path
import io
import sys

import fitz  # PyMuPDF
from PIL import Image, ImageChops

FILES = [
    Path("documents/paolo-de-marinis-cv-generale.pdf"),
    Path("documents/paolo-de-marinis-cv-genai.pdf"),
    Path("documents/paolo-de-marinis-cv-crypto.pdf"),
]

OLD = "for Planetary Systems."
NEW = "for the Planetary Systems exam."


def color_to_pdf(value: int) -> tuple[float, float, float]:
    return fitz.sRGB_to_pdf(value)


def find_target_span(page: fitz.Page):
    candidates = []
    data = page.get_text("dict")
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if OLD in text:
                    candidates.append(span)
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected exactly one span containing {OLD!r} on page {page.number + 1}, found {len(candidates)}"
        )
    span = candidates[0]
    if span.get("text", "").strip() != OLD:
        raise RuntimeError(
            f"Target text is not isolated in one span: {span.get('text')!r}"
        )
    return span


def find_font_bytes(doc: fitz.Document, page: fitz.Page, span_font: str):
    normalized = span_font.replace(" ", "").lower()
    best = None
    for font in page.get_fonts(full=True):
        xref, ext, ftype, basefont, name, encoding, *rest = font
        keys = [str(basefont), str(name)]
        keys_norm = [k.replace(" ", "").lower() for k in keys]
        score = 0
        for key in keys_norm:
            if normalized == key:
                score = max(score, 3)
            elif normalized in key or key in normalized:
                score = max(score, 2)
            elif normalized.split("+")[-1] in key.split("+")[-1]:
                score = max(score, 1)
        if score and (best is None or score > best[0]):
            best = (score, xref, basefont, name)
    if best is None:
        raise RuntimeError(f"Could not map span font {span_font!r} to an embedded page font")
    _, xref, basefont, name = best
    basename, ext, ftype, content = doc.extract_font(xref)
    if not content:
        raise RuntimeError(f"Embedded font xref {xref} ({basefont}/{name}) has no extractable content")
    return xref, basefont, name, content


def render_page(page: fitz.Page, zoom: float = 2.0) -> Image.Image:
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def expanded_expected_bbox(rect: fitz.Rect, new_width: float, page: fitz.Page, zoom: float = 2.0):
    x0 = max(0.0, rect.x0 - 2.0)
    y0 = max(0.0, rect.y0 - 2.0)
    x1 = min(page.rect.x1, max(rect.x1, rect.x0 + new_width) + 3.0)
    y1 = min(page.rect.y1, rect.y1 + 2.0)
    return (
        int(x0 * zoom) - 3,
        int(y0 * zoom) - 3,
        int(x1 * zoom) + 3,
        int(y1 * zoom) + 3,
    )


def bbox_contains(outer, inner) -> bool:
    if inner is None:
        return False
    return (
        inner[0] >= outer[0]
        and inner[1] >= outer[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def edit_pdf(path: Path) -> None:
    original_bytes = path.read_bytes()
    original_doc = fitz.open(stream=original_bytes, filetype="pdf")
    before_text = "\n".join(page.get_text("text") for page in original_doc)
    if before_text.count(OLD) != 1:
        raise RuntimeError(f"{path}: expected one occurrence of {OLD!r}, found {before_text.count(OLD)}")

    target_page_index = None
    target_span = None
    for page in original_doc:
        if OLD in page.get_text("text"):
            target_page_index = page.number
            target_span = find_target_span(page)
            break
    if target_page_index is None or target_span is None:
        raise RuntimeError(f"{path}: target text not found")

    original_page = original_doc[target_page_index]
    before_image = render_page(original_page)
    span_rect = fitz.Rect(target_span["bbox"])
    origin = fitz.Point(target_span.get("origin", (span_rect.x0, span_rect.y1)))
    font_size = float(target_span["size"])
    text_color = color_to_pdf(int(target_span.get("color", 0)))
    span_font = str(target_span["font"])
    xref, basefont, font_resource_name, font_bytes = find_font_bytes(
        original_doc, original_page, span_font
    )
    original_doc.close()

    doc = fitz.open(stream=original_bytes, filetype="pdf")
    page = doc[target_page_index]

    replacement_font_name = "CvReplacementFont"
    page.insert_font(fontname=replacement_font_name, fontbuffer=font_bytes)
    replacement_font = fitz.Font(fontbuffer=font_bytes)
    new_width = replacement_font.text_length(NEW, fontsize=font_size)
    available_right = page.rect.x1 - 36.0
    if origin.x + new_width > available_right:
        raise RuntimeError(
            f"{path}: replacement text would exceed right margin: end={origin.x + new_width:.2f}, limit={available_right:.2f}"
        )

    redact_rect = fitz.Rect(
        span_rect.x0 - 0.5,
        span_rect.y0 - 0.5,
        max(span_rect.x1 + 0.5, origin.x + new_width + 0.8),
        span_rect.y1 + 0.5,
    )
    page.add_redact_annot(redact_rect, fill=(1, 1, 1))
    page.apply_redactions()
    page.insert_text(
        origin,
        NEW,
        fontsize=font_size,
        fontname=replacement_font_name,
        color=text_color,
        overlay=True,
    )

    output = io.BytesIO()
    doc.save(output, garbage=4, deflate=True, clean=True)
    doc.close()
    new_bytes = output.getvalue()

    check_doc = fitz.open(stream=new_bytes, filetype="pdf")
    after_text = "\n".join(p.get_text("text") for p in check_doc)
    if OLD in after_text:
        raise RuntimeError(f"{path}: old text still present after edit")
    if after_text.count(NEW) != 1:
        raise RuntimeError(f"{path}: expected one new phrase, found {after_text.count(NEW)}")

    normalized_after = after_text.replace(NEW, OLD)
    if normalized_after != before_text:
        raise RuntimeError(f"{path}: extracted text changed outside the intended phrase")

    after_page = check_doc[target_page_index]
    after_image = render_page(after_page)
    diff = ImageChops.difference(before_image, after_image)
    diff_bbox = diff.getbbox()
    expected_bbox = expanded_expected_bbox(span_rect, new_width, after_page)
    if not bbox_contains(expected_bbox, diff_bbox):
        raise RuntimeError(
            f"{path}: visual diff escaped target line; diff={diff_bbox}, expected within={expected_bbox}"
        )
    check_doc.close()

    path.write_bytes(new_bytes)
    print(
        f"OK {path}: page={target_page_index + 1}, font={span_font} "
        f"embedded={basefont}/{font_resource_name} size={font_size:.2f}, "
        f"origin=({origin.x:.2f},{origin.y:.2f}), new_width={new_width:.2f}, diff_bbox={diff_bbox}"
    )


def main() -> int:
    for path in FILES:
        if not path.exists():
            raise FileNotFoundError(path)
        edit_pdf(path)
    print("All three GitHub CV PDFs updated and validated.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
