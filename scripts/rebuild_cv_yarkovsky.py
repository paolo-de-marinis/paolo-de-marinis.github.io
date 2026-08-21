from __future__ import annotations

from pathlib import Path
import io
import sys

import fitz
from PIL import Image, ImageChops

FILES = [
    Path("documents/paolo-de-marinis-cv-generale.pdf"),
    Path("documents/paolo-de-marinis-cv-genai.pdf"),
    Path("documents/paolo-de-marinis-cv-crypto.pdf"),
]

OLD = "for Planetary Systems."
NEW = "for the Planetary Systems exam."
ZOOM = 2.0


def render(page: fitz.Page) -> Image.Image:
    pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def rgb_from_int(value: int) -> tuple[float, float, float]:
    return fitz.sRGB_to_pdf(value)


def intersect_area(a: fitz.Rect, b: fitz.Rect) -> float:
    r = a & b
    if r.is_empty:
        return 0.0
    return max(0.0, r.width) * max(0.0, r.height)


def target_style(page: fitz.Page, target: fitz.Rect):
    candidates = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                rect = fitz.Rect(span["bbox"])
                area = intersect_area(rect, target)
                if area > 0:
                    candidates.append((area, span))
    if not candidates:
        raise RuntimeError("No text span overlaps the target phrase")
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def changed_bbox(before: Image.Image, after: Image.Image):
    return ImageChops.difference(before, after).getbbox()


def edit_one(path: Path) -> None:
    original_bytes = path.read_bytes()
    before_doc = fitz.open(stream=original_bytes, filetype="pdf")
    before_text = "\n".join(p.get_text("text") for p in before_doc)
    before_pages = before_doc.page_count
    if before_text.count(OLD) != 1:
        raise RuntimeError(f"{path}: expected exactly one {OLD!r}; found {before_text.count(OLD)}")

    page_index = None
    target = None
    style = None
    before_image = None
    for page in before_doc:
        rects = page.search_for(OLD)
        if rects:
            if len(rects) != 1:
                raise RuntimeError(f"{path}: expected one target rectangle on page {page.number + 1}; found {len(rects)}")
            page_index = page.number
            target = rects[0]
            style = target_style(page, target)
            before_image = render(page)
            break
    if page_index is None or target is None or style is None or before_image is None:
        raise RuntimeError(f"{path}: target phrase was not located")

    font_size = float(style["size"])
    color = rgb_from_int(int(style.get("color", 0)))
    origin = fitz.Point(target.x0, float(style.get("origin", (target.x0, target.y1))[1]))
    span_font = str(style.get("font", ""))
    before_doc.close()

    if "NimbusSan" not in span_font and "Helvetica" not in span_font:
        raise RuntimeError(f"{path}: unexpected body font {span_font!r}; refusing a non-equivalent replacement")

    doc = fitz.open(stream=original_bytes, filetype="pdf")
    page = doc[page_index]
    measure_font = fitz.Font("helv")
    fontname = "helv"

    new_width = measure_font.text_length(NEW, fontsize=font_size)
    old_width = target.width
    right_limit = page.rect.x1 - 28.0
    print(
        f"{path}: page={page_index + 1}, target={target}, source_font={span_font!r}, "
        f"size={font_size:.2f}, origin=({origin.x:.2f},{origin.y:.2f}), "
        f"old_width={old_width:.2f}, proposed_width={new_width:.2f}, right_limit={right_limit:.2f}"
    )

    if origin.x + new_width > right_limit:
        fitted = font_size * (right_limit - origin.x) / new_width
        if fitted < font_size * 0.88:
            raise RuntimeError(
                f"{path}: replacement needs excessive shrinking: {font_size:.2f} -> {fitted:.2f} pt"
            )
        print(f"  fitting replacement: {font_size:.2f} -> {fitted:.2f} pt")
        font_size = fitted
        new_width = measure_font.text_length(NEW, fontsize=font_size)

    erase = fitz.Rect(
        target.x0 - 0.6,
        target.y0 - 0.8,
        min(page.rect.x1 - 1, max(target.x1 + 0.6, origin.x + new_width + 0.8)),
        target.y1 + 0.8,
    )
    page.add_redact_annot(erase, fill=(1, 1, 1))
    page.apply_redactions()
    page.insert_text(
        origin,
        NEW,
        fontsize=font_size,
        fontname=fontname,
        color=color,
        overlay=True,
    )

    out = io.BytesIO()
    doc.save(out, garbage=4, deflate=True, clean=True)
    doc.close()
    new_bytes = out.getvalue()

    after_doc = fitz.open(stream=new_bytes, filetype="pdf")
    after_text = "\n".join(p.get_text("text") for p in after_doc)
    if after_doc.page_count != before_pages:
        raise RuntimeError(f"{path}: page count changed {before_pages} -> {after_doc.page_count}")
    if OLD in after_text:
        raise RuntimeError(f"{path}: old wording still present")
    if after_text.count(NEW) != 1:
        raise RuntimeError(f"{path}: new wording occurrence count is {after_text.count(NEW)}, expected 1")
    if after_text.replace(NEW, OLD) != before_text:
        raise RuntimeError(f"{path}: extracted text changed outside the requested wording")

    after_image = render(after_doc[page_index])
    diff_bbox = changed_bbox(before_image, after_image)
    if diff_bbox is None:
        raise RuntimeError(f"{path}: no visual change detected")

    expected = (
        max(0, int((target.x0 - 4) * ZOOM)),
        max(0, int((target.y0 - 4) * ZOOM)),
        min(after_image.width, int((origin.x + new_width + 4) * ZOOM)),
        min(after_image.height, int((target.y1 + 4) * ZOOM)),
    )
    if not (
        diff_bbox[0] >= expected[0]
        and diff_bbox[1] >= expected[1]
        and diff_bbox[2] <= expected[2]
        and diff_bbox[3] <= expected[3]
    ):
        raise RuntimeError(f"{path}: visual diff escaped target region: diff={diff_bbox}, expected={expected}")
    after_doc.close()

    path.write_bytes(new_bytes)
    print(
        f"OK {path}: page={page_index + 1}, final_size={font_size:.2f}, "
        f"new_width={new_width:.2f}, diff={diff_bbox}"
    )


def main() -> int:
    for path in FILES:
        if not path.exists():
            raise FileNotFoundError(path)
        edit_one(path)
    print("All three site PDFs rebuilt and validated from the GitHub checkout.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
