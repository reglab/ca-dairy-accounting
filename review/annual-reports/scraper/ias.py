"""Extractor for Innovative Ag Services annual reports (Attachments A, B, C)."""
import re
import geom

HERD_ORDER = ["Milk Cows", "Dry Cows", "Bred Heifers", "Heifers",
              "Calves (4-6 mo.)", "Calves (0-3 mo.)"]


def _col(page, *header_words):
    """x-range spanned by the given header tokens (first occurrence of each)."""
    xs = []
    for x0, y0, x1, y1, t in geom.words(page):
        if t in header_words:
            xs.append((x0, x1))
    if not xs:
        return None
    xs.sort()
    return xs[0][0] - 6, xs[0][1] + 6


def _in(x0, x1, col):
    return col is not None and min(x1, col[1]) - max(x0, col[0]) > 0


# IAS lists only the animal types a dairy actually keeps, so rows must be matched
# by their label rather than by position or count. The age range is the reliable
# signal: labels wrap, lose their breed prefix, and pick up OCR damage
# ("Heifers{15-24)", "(7-1 4)"), but the range itself survives once whitespace is
# stripped.
AGE_RANGES = [("15-24", "Bred Heifers"), ("7-14", "Heifers"),
              ("4-6", "Calves (4-6 mo.)"), ("0-3", "Calves (0-3 mo.)")]


def _classify(label):
    c = re.sub(r"\s+", "", str(label).lower()).replace("{", "(").replace("}", ")")
    if "milkcow" in c:
        return "Milk Cows"
    if "drycow" in c:
        return "Dry Cows"
    for rng, col in AGE_RANGES:
        if rng in c:
            return col
    # A bare "Milk" or "Dry" is a wrapped row label; breed-only fragments such as
    # "Hol" carry no information and are left unmatched.
    if c in ("milk", "milkcows"):
        return "Milk Cows"
    if c in ("dry", "drycows"):
        return "Dry Cows"
    return None


def attachment_a(doc):
    """Herd (average head), total manure produced, manure N, wastewater, wastewater N."""
    i, pg = geom.find_page(doc, "Estimated Manure and Nutrients Generated")
    if pg is None:
        return {}, None, []
    avg_col = _col(pg, "Head*")                       # 'Average No. of Head*'
    man_col = _col(pg, "(tons/year)")                 # 'Total Manure Produced'
    n_col = _col(pg, "NITROGEN")
    notes = []
    if avg_col is None:
        return {}, i, ["IAS average-head column not found"]
    # The animal-type label ends before the first numeric column. Anchor on the
    # Maximum-head column, not the Average one, or the totals row's maximum value
    # is mistaken for a row label and the totals row is never recognised.
    max_col = _col(pg, "Head")
    label_max = (max_col[0] if max_col else avg_col[0]) - 8

    cats, totals = {}, None
    for y, row in sorted(geom.bands(pg).items()):
        a = [geom.num(t) for x0, x1, yy, t in row
             if _in(x0, x1, avg_col) and geom.num(t) is not None]
        if not a:
            continue
        # Include any token that starts left of the first numeric column: the
        # age-band suffix ("(15-24)") often overruns the label cell, and dropping
        # it left rows reading as a bare "Hol Heifers" that matched nothing.
        label = " ".join(t for x0, x1, yy, t in row if x0 < label_max)
        col = _classify(label)
        if col:
            cats[col] = int(round(a[0]))
        elif not label.strip():
            totals = (y, row, a[0])       # unlabelled row = the table total

    out = {}
    if cats:
        out.update(cats)
        out["Total Herd Size"] = sum(cats.values())
        missing = [c for c in HERD_ORDER if c not in cats]
        if missing:
            notes.append("IAS form lists no row for " + ", ".join(missing)
                         + "; left blank")
        if totals and abs(totals[2] - out["Total Herd Size"]) > 1:
            notes.append(f"IAS herd total mismatch: summed {out['Total Herd Size']} "
                         f"vs printed {totals[2]:.0f}")
    if totals:
        # Rows in this layout often wrap: the head counts sit on one line and the
        # manure and nutrient figures on the next, so search a small y window.
        ty = min(yy for _, _, yy, _ in totals[1])
        for key, col in (("Total Manure Excreted (tons)", man_col),
                         ("Total Dry Manure Generated N (lbs)", n_col)):
            vals = [(y0, geom.num(t)) for x0, y0, x1, y1, t in geom.words(pg)
                    if _in(x0, x1, col) and geom.num(t) is not None
                    and -2.0 <= y0 - ty <= 9.0]
            if vals:
                out[key] = sorted(vals)[0][1]

    # Wastewater totals sit in a second table lower on the same page.
    gal = geom.value_right_of(pg, "Generated***")
    if gal is None:
        gal = geom.value_below(pg, "Generated***")
    if gal is not None:
        out["Total Process Wastewater Generated (gals)"] = gal
    wwn_col = _col(pg, "(lb)**")
    if wwn_col:
        ytab = (geom.find_label(pg, "Estimated Amount of Total Process Wastewater")
                or (0, 0, 0))[0]
        for y, row in sorted(geom.bands(pg).items()):
            vals = [geom.num(t) for x0, x1, yy, t in row
                    if _in(x0, x1, wwn_col) and geom.num(t) is not None]
            if vals and y > ytab:
                out["Total Process Wastewater Generated N (lbs)"] = vals[0]
                break
    return out, i, notes


def attachment_b(doc):
    """Applied nitrogen, split into solid manure and process wastewater."""
    i, pg = geom.find_page(doc, "Summary of Nutrient Applications")
    if pg is None:
        return {}, None
    return {"Applied N Dry Manure (lbs)": geom.value_right_of(pg, "Solid Manure"),
            "Applied Process Wastewater N (lbs)": geom.value_right_of(pg, "Process Wastewater"),
            "Applied to Remove Ratio N": geom.value_right_of(pg, "Nitrogen Ratio"),
            "Total Crop-Removed N": geom.value_right_of(pg, "Crop Nitrogen Removal")}, i


def crop_removal(doc, page=None):
    """Facility-wide crop N removal from Attachment B's summary table.

    Returns the same keys as standard.crop_removal: the removal plus the
    printed total applied and ratio that check it. The summary page's own
    title is matched first, because per-field pages also say "Nitrogen Ratio".
    """
    if page is None:
        i, pg = geom.find_page(doc, "Summary of Nutrient Applications, Removal")
        if pg is None:
            i, pg = geom.find_page(doc, "Summary of Nutrient Applications")
    else:
        i, pg = page, doc[page]
    if pg is None:
        return {}, None
    return {"Total Crop-Removed N": geom.value_right_of(pg, "Crop Nitrogen Removal"),
            "_n_applied_all": geom.value_right_of(pg, "Total Nitrogen Applied"),
            "_ratio_printed": geom.value_right_of(pg, "Nitrogen Ratio")}, i


def attachment_c(doc):
    """Exported nitrogen. An empty attachment means nothing left the property."""
    i, pg = geom.find_page(doc, "Transferred Off-Site")
    if pg is None:
        return {}, None, []
    man = geom.value_below(pg, "Exported (lbs)**", max_dy=40)
    tot = 0.0 if man is None else man
    return {"Total Exports N (lbs)": tot}, i, ([] if man is not None else
            ["IAS Attachment C empty; exports recorded as 0"])


def identity(doc):
    """Dairy name from the '<name> 2024' page title; IAS pages carry no address."""
    i, pg = geom.find_page(doc, "Estimated Manure and Nutrients Generated")
    if pg is None:
        return {}
    for y, row in sorted(geom.bands(pg).items()):
        txt = " ".join(t for _, _, _, t in row).strip()
        if re.search(r"\b20\d{2}$", txt) and len(txt) > 6:
            return {"Dairy Name": re.sub(r"\s*20\d{2}$", "", txt).strip()}
    return {}


def extract(doc):
    row, pages, notes = {}, {}, []
    row.update(identity(doc))
    a, pi, n = attachment_a(doc)
    row.update(a); pages["attachment_a"] = None if pi is None else pi + 1; notes += n
    b, pi = attachment_b(doc)
    row.update(b); pages["attachment_b"] = None if pi is None else pi + 1
    c, pi, n = attachment_c(doc)
    row.update(c); pages["attachment_c"] = None if pi is None else pi + 1; notes += n
    return row, pages, notes
