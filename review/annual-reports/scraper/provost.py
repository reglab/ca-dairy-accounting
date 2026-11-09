"""Extractor for Provost & Pritchard annual reports (Attachment A tables)."""
import re
import geom

HERD_ORDER = ["Milk Cows", "Dry Cows", "Bred Heifers", "Heifers",
              "Calves (4-6 mo.)", "Calves (0-3 mo.)"]
# Attachment A row labels, in CSV column order.
PP_ROWS = ["Milk Cows", "Dry Cows", "Bred Heifers 15-24 Months",
           "Heifers 7-14 Months", "Calves 4-6 Months", "Calves 0-3 Months"]


def identity(doc):
    i, pg = geom.find_page(doc, "Herd Profile, Housing")
    if pg is None:
        return {}, None
    vals = geom.header_block(pg, x_min=100, x_max=600)
    out = {}
    if vals:
        out["Dairy Name"] = vals[0]
    if len(vals) >= 3:
        m = re.match(r"(.*?),\s*([A-Z]{2})\s*(\d{5})", vals[2])
        city, zipc = (m.group(1), m.group(3)) if m else (vals[2], "")
        out["_street"], out["_city"], out["_zip"] = vals[1], city, zipc
    return out, i


def herd(doc):
    """Average open confinement + average housed under roof, per category.

    The row labels wrap onto two visual lines ("Bred Heifers" / "15-24 Months")
    so they cannot be matched as single-row phrases. The value rows are instead
    found by column: the two "Confinement" headers mark the average and maximum
    open-confinement columns, and the two "Roof" headers their housed pairs.
    """
    i, pg = geom.find_page(doc, "Average Herd Profile and Housing Type")
    if pg is None:
        return {}, None
    ws = geom.words(pg)
    conf = sorted((x0, x1, y0) for x0, y0, x1, y1, t in ws if t == "Confinement")
    roof = sorted((x0, x1, y0) for x0, y0, x1, y1, t in ws if t == "Roof")
    under = sorted((x0, x1, y0) for x0, y0, x1, y1, t in ws if t == "Under")
    if not conf or not roof or not under:
        return {}, i
    avg_open = (conf[0][0] - 4, conf[0][1] + 4)
    avg_roof = (under[0][0] - 4, roof[0][1] + 4)
    # Only rows below the column headers: the dairy address and report period sit
    # in the same x columns higher up and would otherwise parse as herd counts.
    y_top = max(conf[0][2], roof[0][2], under[0][2]) + 4

    def in_col(x0, x1, col):
        return min(x1, col[1]) - max(x0, col[0]) > 0

    rows = []
    for y, row in geom.bands(pg).items():
        if y <= y_top:
            continue
        o = [geom.num(t) for x0, x1, yy, t in row
             if in_col(x0, x1, avg_open) and geom.num(t) is not None]
        r = [geom.num(t) for x0, x1, yy, t in row
             if in_col(x0, x1, avg_roof) and geom.num(t) is not None]
        if o and r:
            rows.append((y, o[0], r[0]))
    rows.sort()
    if len(rows) < 6:
        return {}, i
    out = {c: int(round(o + r)) for c, (_, o, r) in zip(HERD_ORDER, rows[:6])}
    out["Total Herd Size"] = sum(out[c] for c in HERD_ORDER)
    return out, i


def generated(doc):
    i, pg = geom.find_page(doc, "Estimated Total Amount of Solid Manure and Nutrients Generated")
    if pg is None:
        return {}, None
    y_ww, _ = geom.section_bounds(
        pg, "Estimated Total Amount of Process Wastewater and Nutrients Generated")
    out = {
        "Total Manure Excreted (tons)":
            geom.value_below(pg, "Manure Generated", y_hi=y_ww),
        "Total Dry Manure Generated N (lbs)":
            geom.value_below(pg, "Nitrogen", y_hi=y_ww),
    }
    ww_gal = geom.value_below(pg, "(1,000 gals.)")
    if ww_gal is not None:
        out["Total Process Wastewater Generated (gals)"] = ww_gal * 1000.0
    out["Total Process Wastewater Generated N (lbs)"] = geom.value_below(
        pg, "Nitrogen", y_lo=y_ww)
    return out, i


def _wrapped_row(pg, label, max_dy=20.0):
    """Numerics, left to right, on the first row at or below a label.

    The two ASAE total labels wrap onto a second line and their figures sit on
    that line rather than beside the first, so the value is below the label
    without sharing a column with it.
    """
    hits = geom.find_labels(pg, label)
    if not hits:
        return []
    ly = hits[0][0]
    for y, row in sorted(geom.bands(pg).items()):
        if not (ly - 2.0 < y <= ly + max_dy):
            continue
        vals = sorted((x0, geom.num(t)) for x0, x1, yy, t in row
                      if geom.NUM.match(t) and geom.num(t) is not None)
        if vals:
            return [v for _x, v in vals]
    return []


def asae_totals(doc):
    """The whole-herd ASAE D384.2 totals, reported separately from solid manure.

    Tonnage comes from the Total Manure column and nitrogen from the first of
    the N, P, K figures on the pounds row.
    """
    i, pg = geom.find_page(doc, "Estimated Total Amount of Manure and Nutrients Based On")
    if pg is None:
        return None, None
    tons = _wrapped_row(pg, "Total tons for")
    n = _wrapped_row(pg, "Total Pounds for")
    return {"tons": tons[0] if tons else None, "n": n[0] if n else None}, i


def applied(doc):
    i, pg = geom.find_page(doc, "Estimated Amount of Total Solid Manure And Nutrients Applied")
    if pg is None:
        return {}, None
    y_ww, _ = geom.section_bounds(
        pg, "Estimated Amount of Total Wastewater And Nutrients Applied")
    return {"Applied N Dry Manure (lbs)": geom.value_below(pg, "Nitrogen", y_hi=y_ww),
            "Applied Process Wastewater N (lbs)": geom.value_below(pg, "Nitrogen", y_lo=y_ww)}, i


def exports(doc):
    i, pg = geom.find_page(doc, "Nutrients Transferred")
    if pg is None:
        return {}, None
    y_ww, _ = geom.section_bounds(
        pg, "Estimated Amount of Total Wastewater And Nutrients Transferred")
    a = geom.value_below(pg, "Nitrogen", y_hi=y_ww)
    b = geom.value_below(pg, "Nitrogen", y_lo=y_ww)
    tot = None if a is None and b is None else (a or 0) + (b or 0)
    return {"Total Exports N (lbs)": tot}, i


def extract(doc):
    row, pages, notes = {}, {}, []
    for fn, tag in ((identity, "identity"), (herd, "herd"), (generated, "generated"),
                    (applied, "applied"), (exports, "exports")):
        vals, pi = fn(doc)
        row.update(vals)
        pages[tag] = None if pi is None else pi + 1
    asae, _pi = asae_totals(doc)
    if asae and asae.get("tons") is not None:
        notes.append(f"P&P ASAE D384.2 whole-herd total = {asae['tons']:,.0f} tons "
                     f"(not used; column holds Total Tons As Is of solid manure)")
    return row, pages, notes
