"""Extractor for Livingston Dairy Consulting annual reports."""
import re
import geom
import livingston            # per-field 'Nutrient Applications' table parser

# Livingston uses five age bands with different cut-points; there is no 4-6 month
# calf column, so that CSV field stays blank rather than being zero-filled.
LIV5 = ["Milk Cows", "Dry Cows", "Bred Heifers", "Heifers", "Calves (0-3 mo.)"]
LIV6 = ["Milk Cows", "Dry Cows", "Bred Heifers", "Heifers",
        "Calves (4-6 mo.)", "Calves (0-3 mo.)"]


def identity(doc):
    """Dairy name and address from the facility-information page."""
    i, pg = geom.find_page(doc, "Dairy Name:", limit=6)
    out = {}
    if pg is not None:
        ws = geom.words(pg)
        for lab, key in (("Dairy Name:", "Dairy Name"), ("Facility Address:", "_addr")):
            hit = geom.find_label(pg, lab)
            if not hit:
                continue
            ly, _ll, lright = hit
            # The filled value is the right-hand text block on the same visual row.
            same = sorted((x0, t) for x0, y0, x1, y1, t in ws
                          if abs(y0 - ly) <= geom.get_band() and x0 > lright)
            if same:
                out[key] = " ".join(t for _, t in same).strip()
    return out


def _herd_columns(pg, y_lo, y_hi):
    """Value-column centres, taken from whichever row has the most cells.

    Blank Maximum/Average cells emit no text at all, so their columns have to be
    established from a fully populated row (open confinement or under roof).
    """
    best = []
    for y, row in geom.bands(pg).items():
        if not (y_lo < y < y_hi):
            continue
        toks = [(x0, x1, t) for x0, x1, yy, t in row if x0 > 220]
        # Only a data row defines the value columns: header sub-lines such as
        # "(12-24 mo)" sit in the same x span and would otherwise win on count.
        if toks and all(geom.num(t) is not None or t in ("-", "\u2013") for _, _, t in toks):
            if len(toks) > len(best):
                best = toks
    return [((a + b) / 2) for a, b, _ in sorted(best)]


def herd(doc):
    i, pg = geom.find_page(doc, "Herd Information", "manure excreted")
    if pg is None:
        return {}, None, []
    y_hi = (geom.find_label(pg, "Manure Generated:") or (10_000, 0))[0]
    y_lo = (geom.find_label(pg, "Herd Information") or (0, 0))[0]
    centres = _herd_columns(pg, y_lo, y_hi)
    hit = geom.find_label(pg, "Average Number")
    if not hit or not centres:
        return {}, i, ["Livingston herd table not located"]
    ly, _ll, lright = hit
    order = LIV6 if len(centres) >= 6 else LIV5
    vals = {}
    for x0, y0, x1, y1, t in geom.words(pg):
        if abs(y0 - ly) > geom.get_band() or x0 <= lright:
            continue
        c = (x0 + x1) / 2
        j = min(range(len(centres)), key=lambda k: abs(centres[k] - c))
        if abs(centres[j] - c) < 30 and j < len(order):
            v = geom.num(t)
            vals[order[j]] = 0 if v is None else int(round(v))
    out = {k: vals.get(k, 0) for k in order}
    out["Total Herd Size"] = sum(out.values())
    notes = [] if len(centres) >= 6 else [
        "Livingston form has no Calves (4-6 mo.) column; left blank"]
    return out, i, notes


def nutrients(doc):
    i, pg = geom.find_page(doc, "manure excreted", "Process wastewater generated")
    if pg is None:
        return {}, None, []
    out = {
        "Total Manure Excreted (tons)":
            geom.value_right_of(pg, "Total manure excreted by the herd:"),
        "Total Dry Manure Generated N (lbs)":
            geom.value_right_of(pg, "Total nitrogen from manure:"),
        "Total Dry Manure Generated N After Ammonia Losses (lbs)":
            geom.value_below(pg, "After Ammonia (30% loss applied)", max_dy=45),
        "Total Process Wastewater Generated (gals)":
            geom.value_right_of(pg, "Process wastewater generated:"),
        "Total Process Wastewater Generated N (lbs)":
            geom.value_right_of(pg, "Total nitrogen generated:"),
    }
    notes = []
    if "@40%" in pg.get_text() or "40% Moisture" in pg.get_text():
        notes.append("Livingston manure reported @40% moisture, not as-excreted")
    return out, i, notes


def applied(doc):
    """Sum the per-field Nutrient Applications pages."""
    man = ww = 0.0
    fields = []
    for pg in doc:
        r = livingston.applied_n(pg)
        if r:
            man += r["manure_n_lbs"]
            ww += r["ww_n_lbs"]
            fields.append(r["field"])
    if not fields:
        return {}, ["No Livingston field pages parsed; applied N unavailable"]
    return ({"Applied N Dry Manure (lbs)": round(man, 2),
             "Applied Process Wastewater N (lbs)": round(ww, 2)},
            [f"Applied N summed over {len(fields)} field pages: "
             + ", ".join(str(f) for f in fields[:8])
             + ("..." if len(fields) > 8 else "")])


def exports(doc):
    """Exported nitrogen. The form reports only mass, so N must be derived."""
    i, pg = geom.find_page(doc, "Nutrient Import & Export")
    if pg is None:
        return {}, None, [], {}
    ws = geom.words(pg)
    # 'x No' / 'x Yes' checkbox: an x-marker immediately left of the word.
    answered_no = False
    for x0, y0, x1, y1, t in ws:
        if t == "No":
            for x0b, y0b, x1b, y1b, tb in ws:
                if tb.lower() == "x" and abs(y0b - y0) <= 6 and 0 < x0 - x1b < 12:
                    answered_no = True
    tons = geom.value_right_of(pg, "Total Dry Manure Exported")
    gals = geom.value_right_of(pg, "Total Process Water Exported")
    if answered_no and not tons and not gals:
        return ({"Total Exports N (lbs)": 0.0}, i,
                ['Export question answered "No"; exports recorded as 0'], {})
    return {}, i, [], {"exported_tons": tons, "exported_gals": gals}


def extract(doc):
    row, pages, notes = {}, {}, []
    row.update(identity(doc))
    for fn, tag in ((herd, "herd"), (nutrients, "nutrients")):
        vals, pi, n = fn(doc)
        row.update(vals); pages[tag] = None if pi is None else pi + 1; notes += n
    vals, n = applied(doc)
    row.update(vals); notes += n
    vals, pi, n, pend = exports(doc)
    row.update(vals); pages["exports"] = None if pi is None else pi + 1; notes += n
    return row, pages, notes, pend
