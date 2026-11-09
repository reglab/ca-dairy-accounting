"""Extractor for the standard Water Board Annual Report form (R5-2007-0035)."""
import re
import geom

HERD_ORDER = ["Milk Cows", "Dry Cows", "Bred Heifers", "Heifers",
              "Calves (4-6 mo.)", "Calves (0-3 mo.)"]

# Every page carries a footer: "<name> | <street> | <city>, CA <zip> | <county> County | <basin>"
FOOTER = re.compile(
    r"^(?P<name>[^|\n]+)\|(?P<street>[^|\n]+)\|(?P<city>[^,|\n]+),\s*[A-Z]{2}\s*(?P<zip>\d{5})"
    r"\s*\|\s*(?P<county>[^|]+?)\s+County", re.M)


def identity(doc):
    """Dairy name and CSV-formatted address from the running page footer."""
    for pg in doc[:6]:
        m = FOOTER.search(re.sub(r"[ \t]+", " ", pg.get_text()))
        if m:
            d = {k: v.strip() for k, v in m.groupdict().items()}
            return {"Dairy Name": d["name"],
                    "Dairy Address": f"{d['street']} {d['city']} {d['county']} {d['zip']}"}
    return {}


def herd(doc):
    i, pg = geom.find_page(doc, "A. HERD INFORMATION")
    if pg is None:
        return {}, None
    vals = geom.row_values(pg, "Average number")
    if len(vals) < 6:
        return {}, i
    out = dict(zip(HERD_ORDER, [int(round(v)) for v in vals[:6]]))
    out["Total Herd Size"] = sum(out[c] for c in HERD_ORDER)
    return out, i


def nutrients(doc):
    i, pg = geom.find_page(doc, "AVAILABLE NUTRIENTS", "MANURE GENERATED")
    if pg is None:
        return {}, None
    g = lambda lab: geom.value_right_of(pg, lab)
    return {
        "Total Manure Excreted (tons)": g("Total manure excreted by the herd:"),
        "Total Dry Manure Generated N (lbs)": g("Total nitrogen from manure:"),
        "Total Dry Manure Generated N After Ammonia Losses (lbs)":
            g("After ammonia losses (30% loss applied):"),
        "Total Process Wastewater Generated (gals)": g("Process wastewater generated:"),
        "Total Process Wastewater Generated N (lbs)": g("Total nitrogen generated:"),
    }, i


def applied(doc):
    i, pg = geom.find_page(doc, "SUMMARY OF NUTRIENT APPLICATIONS")
    if pg is None:
        return {}, None
    return {"Applied N Dry Manure (lbs)": geom.value_right_of(pg, "Dry manure"),
            "Applied Process Wastewater N (lbs)": geom.value_right_of(pg, "Process wastewater"),
            "Applied to Remove Ratio N": geom.value_right_of(pg, "Applied to removed ratio"),
            "Total Crop-Removed N": geom.value_right_of(pg, "Actual crop nutrient removal")}, i


def crop_removal(doc, page=None):
    """Facility-wide crop N removal, with the two printed figures that check it.

    The ratio printed beneath it is total N applied from every source over
    actual crop removal, so the three agree on a correctly read page. Keys
    starting with an underscore are check terms, not summary columns.
    """
    if page is None:
        i, pg = geom.find_page(doc, "SUMMARY OF NUTRIENT APPLICATIONS")
    else:
        i, pg = page, doc[page]
    if pg is None:
        return {}, None
    return {"Total Crop-Removed N": geom.value_right_of(pg, "Actual crop nutrient removal"),
            "_n_applied_all": geom.value_right_of(pg, "Total nutrients applied"),
            "_ratio_printed": geom.value_right_of(pg, "Applied to removed ratio")}, i


def exports(doc):
    i, pg = geom.find_page(doc, "NUTRIENT EXPORTS")
    if pg is None:
        return {}, None
    return {"Total Exports N (lbs)":
            geom.value_right_of(pg, "Total exports for all materials")}, i


def extract(doc):
    row, pages = {}, {}
    row.update(identity(doc))
    for fn, tag in ((herd, "herd"), (nutrients, "nutrients"),
                    (applied, "applied"), (exports, "exports")):
        vals, pi = fn(doc)
        row.update(vals)
        pages[tag] = None if pi is None else pi + 1
    return row, pages
