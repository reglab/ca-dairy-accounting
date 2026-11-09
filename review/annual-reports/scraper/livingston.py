"""Parse Livingston Dairy Consulting 'Nutrient Applications' field pages."""
import re, pymupdf
from collections import defaultdict

# Column order on the field table, left to right, after the Date and Event/Source text cells.
COLS = ["dry_manure", "moist", "chem_fert", "fresh_water", "lagoon_water",
        "N", "P", "K", "salt", "tfs", "exp_yield", "act_yield"]
UNIT_ROW = re.compile(r"^\((tons/ac|ac-in/ac|lbs/Ac|Lbs/Ac|ton/ac|tons/ac)\)$|^%$|^lbs$|^TFS$")


def _num(tok):
    """'1,234.5'->1234.5, '(198.7)'->-198.7, '-'/''->None."""
    t = tok.strip()
    if t in ("-", "", "–"):
        return None
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()").replace(",", "")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def _column_edges(words):
    """Midpoint boundaries from the unit-label row, mapped positionally onto COLS."""
    by_y = defaultdict(list)
    for x0, y0, x1, y1, w, *_ in words:
        by_y[round(y0)].append((x0, x1, w))
    for y in sorted(by_y):
        toks = sorted(by_y[y])
        units = [(x0, x1) for x0, x1, w in toks if UNIT_ROW.match(w)]
        if len(units) >= 9:                      # the unit row for the numeric columns
            centers = [(a + b) / 2 for a, b in units][:len(COLS)]
            edges = []
            for i, c in enumerate(centers):
                lo = (centers[i - 1] + c) / 2 if i else c - 22
                hi = (c + centers[i + 1]) / 2 if i + 1 < len(centers) else c + 22
                edges.append((lo, hi))
            return dict(zip(COLS, edges)), y
    return None, None


def parse_field_page(page):
    """Return {'field','acres','rows':[{col:value}], 'totals':{col:value}} or None."""
    text = page.get_text()
    if "Nutrient Applications" not in text:
        return None
    words = page.get_text("words")
    edges, unit_y = _column_edges(words)
    if not edges:
        return None

    # Field name and acreage come from the header row by geometry: the flowed
    # reading order interleaves the two labels unpredictably.
    field, acres = None, None
    hdr = defaultdict(list)
    for x0, y0, x1, y1, w, *_ in words:
        if y0 < unit_y:
            hdr[round(y0 / 3) * 3].append((x0, w))
    for y in sorted(hdr):
        toks = sorted(hdr[y])
        joined = [w for _, w in toks]
        if any(w.startswith("Acres") for w in joined):
            ai = next(i for i, w in enumerate(joined) if w.startswith("Acres"))
            acres = _num(joined[ai + 1]) if ai + 1 < len(joined) else None
            ni = next((i for i, w in enumerate(joined)
                       if w.startswith("Name/Number")), None)
            if ni is not None:
                field = " ".join(joined[ni + 1:ai]).strip()
            break

    by_y = defaultdict(list)
    for x0, y0, x1, y1, w, *_ in words:
        if y0 > unit_y + 2:
            by_y[round(y0 / 3) * 3].append((x0, x1, w))

    rows, totals = [], {}
    for y in sorted(by_y):
        toks = sorted(by_y[y])
        label = " ".join(w for x0, x1, w in toks if x1 < min(e[0] for e in edges.values()))
        cells = {}
        for x0, x1, w in toks:
            mid = (x0 + x1) / 2
            for col, (lo, hi) in edges.items():
                if lo <= mid < hi:
                    v = _num(w)
                    if v is not None:
                        cells[col] = v
                    break
        if not cells:
            continue
        if "Total" in label:
            totals.update(cells)
        else:
            rows.append({"label": label, **cells})
    return {"field": field, "acres": acres, "rows": rows, "totals": totals}


def applied_n(page):
    """Applied manure N and process wastewater N in lbs for one field page."""
    p = parse_field_page(page)
    if not p or not p["acres"]:
        return None
    man = sum(r["N"] for r in p["rows"] if r.get("dry_manure") and "N" in r)
    lag = sum(r["N"] for r in p["rows"] if r.get("lagoon_water") and "N" in r)
    return {"field": p["field"], "acres": p["acres"],
            "manure_n_per_ac": man, "ww_n_per_ac": lag,
            "manure_n_lbs": man * p["acres"], "ww_n_lbs": lag * p["acres"],
            "parsed": p}
