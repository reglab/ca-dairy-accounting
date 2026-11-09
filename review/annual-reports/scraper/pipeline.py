"""Scrape one dairy annual report PDF into a Region 5 summary CSV row."""
import os, re, unicodedata
import pymupdf
import geom, detect, standard, ias, provost, livingston_form, ocr

# Repository root and the annual-report PDFs inside it. The pickles and
# crop_removal_extracted.csv record each report under its original OneDrive
# folder; local_pdf maps those paths onto the same office and form-type
# folders under PDF_ROOT.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PDF_ROOT = os.path.join(REPO, "data", "annual-reports")
ONEDRIVE_ROOT = ("/Users/ianbick/Library/CloudStorage/OneDrive-Stanford/CAFO/"
                 "CAFO_Water_Reports/2024/R5_analysis")


def local_pdf(path):
    """The report's path under PDF_ROOT when it is recorded under ONEDRIVE_ROOT."""
    if isinstance(path, str) and path.startswith(ONEDRIVE_ROOT + "/"):
        return os.path.join(PDF_ROOT, path[len(ONEDRIVE_ROOT) + 1:])
    return path

AMMONIA_RETENTION = 0.70          # regulatory factor; exact on 588/588 existing rows
OCR_BAND = 4.0                    # row tolerance for OCR'd pages
NATIVE_BAND = 1.8
HERD = ["Milk Cows", "Dry Cows", "Bred Heifers", "Heifers",
        "Calves (4-6 mo.)", "Calves (0-3 mo.)"]
REQUIRED = ["Dairy Name", "Total Herd Size", "Total Manure Excreted (tons)",
            "Total Process Wastewater Generated (gals)"]
# Scored when choosing between candidate layouts: richer than REQUIRED alone, so a
# layout that merely stumbles onto a herd total does not outrank the correct one.
SCORED = REQUIRED + [
    "Total Dry Manure Generated N (lbs)",
    "Total Dry Manure Generated N After Ammonia Losses (lbs)",
    "Total Process Wastewater Generated N (lbs)",
    "Applied N Dry Manure (lbs)", "Applied Process Wastewater N (lbs)",
    "Total Exports N (lbs)"]
# The six herd categories are deliberately excluded: the Livingston reader
# zero-fills absent columns, which would otherwise inflate its score.

# Plausibility bands, from the existing 588 rows (p5-p95).
BANDS = {
    "tons_per_head": (9.33, 25.10),
    "n_per_ton": (10.0, 14.0),
    "n_per_head": (95.16, 324.76),
    "wwn_per_kgal": (1.15, 7.00),
}
BASIS = {"Standard": "as-excreted", "IAS": "as-excreted",
         "Livingston": "40pct-moisture", "ProvostPritchard": "solid-as-is"}


def county_from_path(path):
    """County from the filename's trailing segment, else the office folder."""
    base = os.path.basename(path)
    stem = re.sub(r"\.pdf$", "", base, flags=re.I)
    parts = [p.strip() for p in re.split(r"[_+]", stem) if p.strip()]
    if len(parts) >= 2:
        tail = parts[-1]
        m = re.match(r"^(?:[NSEW]\s+)?(Tulare|Kern|Kings|Fresno|Madera|Merced|Stanislaus|"
                     r"San Joaquin|Sacramento|Glenn|Colusa|Tehama|Butte|Yolo|Solano)$",
                     tail, re.I)
        if m:
            return m.group(1).title()
    folder = os.path.basename(os.path.dirname(os.path.dirname(path)))
    m = re.match(r"^(Tulare|Kern|Kings|Fresno)", folder)
    return m.group(1) if m else ""


def name_addr_from_filename(path):
    """'2024AR_<name>_<street>_<county>.pdf' -> (name, street). Tolerates variants."""
    stem = re.sub(r"\.pdf\s*$", "", os.path.basename(path), flags=re.I).strip()
    stem = re.sub(r"^2024A[Rr]_", "", stem)
    parts = [p.strip() for p in re.split(r"[_+]", stem) if p.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1]
    if len(parts) == 2:
        return parts[0], ""
    return (parts[0] if parts else ""), ""


def compose_address(row, path):
    """Match the existing convention: '<street> <city> <county> <zip>'."""
    if row.get("Dairy Address"):
        return row["Dairy Address"]
    county = county_from_path(path)
    street = row.pop("_street", "") or ""
    city = row.pop("_city", "") or ""
    zipc = row.pop("_zip", "") or ""
    raw = row.pop("_addr", "") or ""
    if raw and not street:
        # Livingston prints '<street> <city>, <zip>' with no county.
        m = re.match(r"^(.*?)\s+([A-Za-z .'-]+),\s*(\d{5})", raw)
        if m:
            street, city, zipc = m.group(1), m.group(2), m.group(3)
        else:
            street = raw
    if not street:
        _, street = name_addr_from_filename(path)
    bits = [b for b in (street.strip(), city.strip(), county, str(zipc).strip()) if b]
    return " ".join(bits)


def _num(v):
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def derive(row, form, notes):
    """Fill the columns that are pure arithmetic on what was scraped."""
    g = _num(row.get("Total Dry Manure Generated N (lbs)"))
    a = _num(row.get("Total Dry Manure Generated N After Ammonia Losses (lbs)"))
    if a is None and g is not None:
        a = round(g * AMMONIA_RETENTION, 2)
        row["Total Dry Manure Generated N After Ammonia Losses (lbs)"] = a
        notes.append(f"After-ammonia N derived as 0.70 x {g:,.2f} (form prints no value)")
    am = _num(row.get("Applied N Dry Manure (lbs)"))
    aw = _num(row.get("Applied Process Wastewater N (lbs)"))
    if am is not None or aw is not None:
        row["Total Applied N (lbs)"] = round((am or 0) + (aw or 0), 2)
        notes.append("Total Applied N derived as applied manure N + applied wastewater N")
    ww = _num(row.get("Total Process Wastewater Generated N (lbs)"))
    ex = _num(row.get("Total Exports N (lbs)"))
    ta = _num(row.get("Total Applied N (lbs)"))
    if None not in (a, ww, ta) and ex is not None:
        row["Unaccounted-for N (lbs)"] = round(a + ww - ta - ex, 2)
        notes.append("Unaccounted-for N derived as after-ammonia N + wastewater N "
                     "- total applied - exports")


def derive_livingston_exports(row, pending, notes):
    """Livingston reports exported mass only, so nitrogen must be derived."""
    tons = _num(pending.get("exported_tons"))
    gals = _num(pending.get("exported_gals"))
    if tons is None and gals is None:
        return
    g = _num(row.get("Total Dry Manure Generated N (lbs)"))
    mt = _num(row.get("Total Manure Excreted (tons)"))
    wn = _num(row.get("Total Process Wastewater Generated N (lbs)"))
    wg = _num(row.get("Total Process Wastewater Generated (gals)"))
    total, why = 0.0, []
    if tons and g and mt:
        v = tons * (g / mt)
        total += v
        why.append(f"{tons:,.0f} tons x {g/mt:.3f} lb N/ton = {v:,.0f} lb")
    if gals and wn and wg:
        v = gals * (wn / wg)
        total += v
        why.append(f"{gals:,.0f} gal x {wn/wg:.6f} lb N/gal = {v:,.0f} lb")
    if why:
        row["Total Exports N (lbs)"] = round(total, 2)
        notes.append("Exports N derived from exported mass because the Livingston form "
                     "reports no exported nitrogen: " + "; ".join(why))


def locate_gross_n(row, doc, pages, notes):
    """Find the printed gross manure N when its label was too garbled to match.

    OCR sometimes shuffles word order so "Total nitrogen from manure:" is no
    longer contiguous, yet the after-ammonia figure is read cleanly. Because that
    figure is exactly 0.70x the gross value, the gross number can be identified
    among the numerics already on the page. This reads the printed value; it does
    not compute it.
    """
    a = _num(row.get("Total Dry Manure Generated N After Ammonia Losses (lbs)"))
    if a is None or _num(row.get("Total Dry Manure Generated N (lbs)")) is not None:
        return
    pi = pages.get("nutrients") or pages.get("attachment_a") or pages.get("generated")
    if not pi or pi - 1 >= len(doc):
        return
    hits = []
    for x0, y0, x1, y1, t in geom.words(doc[pi - 1]):
        v = geom.num(t)
        if v and v > 0 and abs(v * AMMONIA_RETENTION - a) <= max(1.0, 0.002 * v):
            hits.append(v)
    uniq = sorted(set(hits))
    if len(uniq) == 1:
        row["Total Dry Manure Generated N (lbs)"] = uniq[0]
        notes.append(f"Gross manure N read as {uniq[0]:,.2f}: its label was garbled, "
                     f"so the printed value was identified by the exact 0.70 "
                     f"relationship to the after-ammonia figure {a:,.2f}")
    elif len(uniq) > 1:
        notes.append(f"Gross manure N label garbled and {len(uniq)} candidates fit "
                     f"the 0.70 relationship; left blank")


def qa(row, form):
    """Grade a scraped row FAIL / WARN / PASS with reasons."""
    fails, warns = [], []
    have = [c for c in HERD if row.get(c) is not None]
    tot = _num(row.get("Total Herd Size"))
    if have and tot is not None:
        s = sum(_num(row[c]) or 0 for c in have)
        if abs(s - tot) > 0.5:
            fails.append(f"herd total {tot:,.0f} != sum of categories {s:,.0f}")
    g = _num(row.get("Total Dry Manure Generated N (lbs)"))
    a = _num(row.get("Total Dry Manure Generated N After Ammonia Losses (lbs)"))
    if g and a and abs(a - g * AMMONIA_RETENTION) > max(1.0, 0.001 * g):
        fails.append(f"after-ammonia {a:,.0f} != 0.70 x gross {g:,.0f}")
    for c in REQUIRED:
        if row.get(c) in (None, ""):
            fails.append(f"missing {c}")

    mt, ww = _num(row.get("Total Manure Excreted (tons)")), _num(
        row.get("Total Process Wastewater Generated (gals)"))
    ratios = {}
    if mt and tot:
        ratios["tons_per_head"] = mt / tot
    if g and mt:
        ratios["n_per_ton"] = g / mt
    if g and tot:
        ratios["n_per_head"] = g / tot
    if _num(row.get("Total Process Wastewater Generated N (lbs)")) and ww:
        ratios["wwn_per_kgal"] = _num(
            row["Total Process Wastewater Generated N (lbs)"]) / (ww / 1000.0)
    for k, v in ratios.items():
        lo, hi = BANDS[k]
        if not (lo <= v <= hi):
            warns.append(f"{k}={v:,.2f} outside [{lo:,.2f}, {hi:,.2f}]")
    un = _num(row.get("Unaccounted-for N (lbs)"))
    if un is not None and un < 0:
        warns.append(f"applied+exports exceed available N by {-un:,.0f} lb")
    if BASIS.get(form) != "as-excreted":
        warns.append(f"manure basis is {BASIS.get(form)}, not as-excreted")
    grade = "FAIL" if fails else ("WARN" if warns else "PASS")
    return grade, fails, warns, ratios


def needs_ocr(doc, probe=8):
    """True when the leading pages carry no usable text layer."""
    n = min(probe, len(doc))
    chars = sum(len(doc[i].get_text().strip()) for i in range(n))
    return chars < 200 * n * 0.15


def _run_extractors(doc, hint, meta):
    """Try the hinted layout first, then the others; keep the best-scoring result."""
    order = [hint] if hint != "Unknown" else []
    order += [f for f in ("Standard", "IAS", "ProvostPritchard", "Livingston")
              if f not in order]
    best = None
    for cand in order:
        try:
            if cand == "Standard":
                r, pg = standard.extract(doc); n, pd = [], {}
            elif cand == "IAS":
                r, pg, n = ias.extract(doc); pd = {}
            elif cand == "ProvostPritchard":
                r, pg, n = provost.extract(doc); pd = {}
            else:
                r, pg, n, pd = livingston_form.extract(doc)
        except Exception as e:
            meta["notes"].append(f"{cand} extractor errored: {type(e).__name__}: {e}")
            continue
        score = sum(1 for c in SCORED if r.get(c) not in (None, ""))
        req = sum(1 for c in REQUIRED if r.get(c) not in (None, ""))
        # Prefer the layout the cover page pointed to when scores are equal.
        rank = (score, 1 if cand == hint else 0)
        if best is None or rank > best[0]:
            best = (rank, cand, r, pg, n, pd, req)
        if req == len(REQUIRED) and cand == hint:
            break
    return best


def scrape(path, ocr_max_pages=45):
    """Extract one PDF, falling back to OCR when the text layer is insufficient."""
    meta = {"Source PDF": os.path.basename(path), "path": path,
            "notes": [], "pages": {}, "method": "text", "form": "Unknown"}
    try:
        raw = pymupdf.open(path)
    except Exception as e:
        meta["error"] = f"cannot open: {e}"
        return {}, meta
    meta["n_pages"] = len(raw)

    # OCR is expensive (about 1.2s per page), so it is a fallback rather than a
    # second opinion: it runs only when the text layer clearly did not work, not
    # merely because one field is genuinely absent from the form.
    text_first = not needs_ocr(raw)
    modes = ["text"] if text_first else ["ocr"]
    best, best_mode, best_doc = None, None, raw
    for mode in modes:
        if mode == "text":
            geom.set_band(NATIVE_BAND)
            doc = raw
        else:
            geom.set_band(OCR_BAND)
            doc = ocr.OcrDoc(raw, max_pages=min(len(raw), ocr_max_pages))
        hint = detect.form_type(doc, pages=min(12, len(doc)))
        got = _run_extractors(doc, hint, meta)
        if got and (best is None or got[0] > best[0]):
            best, best_mode, best_doc = got, mode, doc
        if best and best[6] == len(REQUIRED):
            break
        if mode == "text" and best is not None and best[6] <= 1 and "ocr" not in modes:
            # Almost nothing came out of the text layer: it is probably a scanned
            # report behind a typed cover sheet, so try reading it as an image.
            modes.append("ocr")
    if best is None:
        meta["error"] = "every extractor failed"
        geom.set_band(NATIVE_BAND)
        return {}, meta

    rank, form, row, pages, notes, pending, score = best
    meta.update(form=form, method=best_mode, pages=pages)
    meta["notes"] += notes
    if best_mode == "ocr" and "text" in modes:
        meta["notes"].append("text layer was insufficient; re-read with OCR")
    if score < len(REQUIRED):
        meta["notes"].append(f"only {score}/{len(REQUIRED)} required fields found "
                             f"using the {form} layout")

    if not row.get("Dairy Name"):
        nm, _ = name_addr_from_filename(path)
        if nm:
            row["Dairy Name"] = nm
            meta["notes"].append("Dairy Name taken from the filename")
    row["Dairy Address"] = compose_address(row, path)
    geom.set_band(OCR_BAND if best_mode == "ocr" else NATIVE_BAND)
    locate_gross_n(row, best_doc, pages, meta["notes"])
    if form == "Livingston" and pending:
        derive_livingston_exports(row, pending, meta["notes"])
    derive(row, form, meta["notes"])
    grade, fails, warns, ratios = qa(row, form)
    meta.update(grade=grade, fails=fails, warns=warns, ratios=ratios)
    geom.set_band(NATIVE_BAND)
    return row, meta
