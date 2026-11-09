"""Render tight evidence crops so a reviewer never has to open a 100-page PDF."""
import os, re
import pymupdf
import geom, ocr

DPI = 110
MARGIN_TOP = 26
MARGIN_BOT = 46
QUALITY = 72

# Any label worth showing next to a scraped value. Whichever ones appear on a
# recorded page define that page's crop band.
LABELS = [
    "A. HERD INFORMATION", "Average number", "Maximum number",
    "Total manure excreted by the herd:", "Total nitrogen from manure:",
    "After ammonia losses (30% loss applied):", "Process wastewater generated:",
    "Total nitrogen generated:", "SUMMARY OF NUTRIENT APPLICATIONS",
    "Dry manure", "Process wastewater", "Applied to removed ratio",
    "Existing soil nutrient content", "Total N (lbs)",
    "Total nutrients applied", "Actual crop nutrient removal",
    "Total Nitrogen Applied", "Crop Nitrogen Removal",
    "NUTRIENT EXPORTS", "Total exports for all materials",
    "Herd Information", "Average Number", "After Ammonia (30% loss applied)",
    "Nutrient Import & Export", "Total Dry Manure Exported",
    "Estimated Manure and Nutrients Generated", "Head*", "(tons/year)",
    "Summary of Nutrient Applications", "Solid Manure", "Nitrogen Ratio",
    "Transferred Off-Site", "Exported (lbs)**",
    "Average Herd Profile and Housing Type", "Manure Generated", "Nitrogen",
    "(1,000 gals.)", "Nutrients Transferred", "Nutrient Applications",
]


def slug(name):
    return re.sub(r"[^A-Za-z0-9]+", "_", re.sub(r"\.pdf$", "", name, flags=re.I)).strip("_")[:80]


def _band(page):
    """Vertical span covering every recognised label on the page."""
    ys = []
    for lab in LABELS:
        for y, _l, _r in geom.find_labels(page, lab):
            ys.append(y)
    if not ys:
        return None
    return max(0, min(ys) - MARGIN_TOP), min(page.rect.height, max(ys) + MARGIN_BOT)


def render(path, pages, out_dir, method="text", dpi=DPI):
    """Write one JPEG per recorded page. Returns [(tag, page_no, filename)]."""
    os.makedirs(out_dir, exist_ok=True)
    made = []
    try:
        raw = pymupdf.open(path)
    except Exception:
        return made
    doc = raw
    if method == "ocr":
        geom.set_band(4.0)
        doc = ocr.OcrDoc(raw, max_pages=len(raw))
    else:
        geom.set_band(1.8)
    seen = {}
    for tag, pno in sorted((pages or {}).items(), key=lambda kv: (kv[1] is None, kv[1])):
        if not pno or pno - 1 >= len(raw):
            continue
        if pno in seen:
            made.append((tag, pno, seen[pno]))
            continue
        fn = f"{slug(os.path.basename(path))}_p{pno}.jpg"
        if os.path.exists(os.path.join(out_dir, fn)):
            seen[pno] = fn
            made.append((tag, pno, fn))
            continue
        try:
            band = _band(doc[pno - 1])
            clip = None
            if band and band[1] - band[0] > 60:
                clip = pymupdf.Rect(0, band[0], raw[pno - 1].rect.width, band[1])
            pm = raw[pno - 1].get_pixmap(dpi=dpi, clip=clip)
            with open(os.path.join(out_dir, fn), "wb") as f:
                f.write(pm.tobytes("jpg", jpg_quality=QUALITY))
            seen[pno] = fn
            made.append((tag, pno, fn))
        except Exception:
            continue
    geom.set_band(1.8)
    return made
