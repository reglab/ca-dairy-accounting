"""Post-process the scraped rows, then rebuild the review set.

Three corrections, applied on top of the raw extraction:
  1. Provost & Pritchard rows switch to Attachment A's ASAE whole-herd table.
  2. A blank export figure becomes 0 where the form states no exports were made.
  3. The UCCE nitrogen estimator and its ratio are filled, giving every row a
     nitrogen figure that does not depend on the form's reporting basis.
"""
import os, pickle, re, sys
import numpy as np
import pandas as pd
import pymupdf
import geom, ocr, pipeline, provost

# Working directory for the run: the review folder that contains this package.
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = pipeline.REPO
BASE = f"{S}/backup_before_append.csv"
HERD = pipeline.HERD
NO_EXPORTS = re.compile(r"No\s+(solid|liquid)\s+nutrient\s+exports\s+entered", re.I)
DERIVED_NOTE = re.compile(r"^(After-ammonia N derived|Total Applied N derived|"
                          r"Unaccounted-for N derived)")
VERDUGA = os.path.join(pipeline.PDF_ROOT, "Rancho Cordova", "Correct_Forms",
                       "1008 N. Verduga Rd, Turlock 2024 Dairy AR.pdf")


def ucce_factors():
    """Recover the per-category UCCE rates from the existing rows.

    Fitted rather than hard-coded so the new values are guaranteed consistent
    with the 546 rows that already carry this column.
    """
    b = pd.read_csv(BASE)
    X = b[HERD].apply(pd.to_numeric, errors="coerce")
    y = pd.to_numeric(b["UCCE Nitrogen from Manure (lbs)"], errors="coerce")
    m = y.notna() & X.notna().all(axis=1) & (X.sum(axis=1) > 0)
    A, Y = X[m].to_numpy(float), y[m].to_numpy(float)
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    err = np.abs(A @ coef - Y)
    assert (err < 0.01).all(), f"UCCE fit is not exact: max error {err.max()}"
    print(f"  UCCE factors recovered from {int(m.sum())} existing rows "
          f"(all reproduce within 0.01 lb):")
    for c, k in zip(HERD, coef):
        print(f"     {c:<20}{k:>14.6f} lb N/head/yr")
    return dict(zip(HERD, coef))


def _doc(rec):
    geom.set_band(pipeline.OCR_BAND if rec["meta"]["method"] == "ocr"
                  else pipeline.NATIVE_BAND)
    d = pymupdf.open(pipeline.local_pdf(rec["path"]))
    return ocr.OcrDoc(d, max_pages=25) if rec["meta"]["method"] == "ocr" else d


def fix_provost(rec):
    """Replace the solid-stream figures with the ASAE whole-herd totals."""
    row, meta = rec["row"], rec["meta"]
    a, pi = provost.asae_totals(_doc(rec))
    if not a or a.get("n") is None:
        meta["notes"].append("Provost & Pritchard ASAE table not readable; "
                             "solid-manure figures retained")
        return False
    old_t, old_n = row.get("Total Manure Excreted (tons)"), row.get(
        "Total Dry Manure Generated N (lbs)")
    row["Total Manure Excreted (tons)"] = a["tons"]
    row["Total Dry Manure Generated N (lbs)"] = a["n"]
    row["Total Dry Manure Generated N After Ammonia Losses (lbs)"] = round(
        a["n"] * pipeline.AMMONIA_RETENTION, 2)
    meta["basis_override"] = "asae-total-solids"
    meta["pages"]["asae"] = None if pi is None else pi + 1
    meta["notes"].append(
        f"Manure and nitrogen taken from Attachment A's ASAE D384.2 whole-herd "
        f"table (page {pi + 1 if pi is not None else '?'}) instead of the "
        f"'Solid Manure Generated' table, which covers only the separated solid "
        f"stream. Superseded solid-stream values: {old_t:,.0f} tons and "
        f"{old_n:,.0f} lb N. The ASAE tonnage is on a total-solids (dry) basis, "
        f"not as-excreted; its nitrogen is whole-herd and comparable with the "
        f"standard Water Board form.")
    return True


def fix_exports(rec):
    """A blank export figure means zero when the form says nothing was exported."""
    row, meta = rec["row"], rec["meta"]
    if row.get("Total Exports N (lbs)") is not None:
        return False
    doc = _doc(rec)
    i, pg = geom.find_page(doc, "NUTRIENT EXPORTS")
    if pg is None:
        i, pg = geom.find_page(doc, "Transferred Off-Site")
    if pg is None:
        return False
    t = pg.get_text()
    if NO_EXPORTS.search(t) and "Total exports for all materials" not in t:
        row["Total Exports N (lbs)"] = 0.0
        meta["notes"].append("Export section states no nutrient exports were "
                             "entered; Total Exports N recorded as 0")
        return True
    return False


def add_ucce(row, fac, notes=None):
    """UCCE nitrogen from herd counts, independent of the form's basis.

    A category the form does not list means the dairy keeps none of that animal,
    so it contributes zero rather than voiding the whole estimate. Livingston
    forms in particular have no 4-6 month calf column at all.
    """
    missing = [c for c in HERD if row.get(c) is None]
    tot = sum(float(row.get(c) or 0) for c in HERD)
    if tot <= 0:
        return
    u = sum(float(row.get(c) or 0) * fac[c] for c in HERD)
    if missing and notes is not None:
        notes.append("UCCE nitrogen treats these unlisted herd categories as "
                     "zero: " + ", ".join(missing))
    row["UCCE Nitrogen from Manure (lbs)"] = round(u, 2)
    g = row.get("Total Dry Manure Generated N (lbs)")
    if g:
        row["Ratio of UCCE N to Reported N"] = round(u / float(g), 4)


def main():
    fac = ucce_factors()
    recs = [r for r in pickle.load(open(f"{S}/results.pkl", "rb"))]

    print("\nscraping the report whose filename was reused by the broken rows...")
    vrow, vmeta = pipeline.scrape(VERDUGA)
    recs.append({"path": VERDUGA, "Source PDF": vmeta["Source PDF"],
                 "status": "ok" if not vmeta.get("error") else "error",
                 "row": vrow, "meta": vmeta})
    print(f"  {vmeta['Source PDF']}: {vrow.get('Dairy Name')!r} "
          f"/ {vrow.get('Dairy Address')!r}  grade={vmeta.get('grade')}")

    n_pp = n_ex = n_uc = 0
    for rec in recs:
        if rec["status"] != "ok":
            continue
        if rec["meta"]["form"] == "ProvostPritchard" and fix_provost(rec):
            n_pp += 1
        if fix_exports(rec):
            n_ex += 1
        # Drop the derivation notes recorded during extraction: the values they
        # describe are recomputed below from the corrected figures, so the
        # originals would describe superseded arithmetic.
        rec["meta"]["notes"] = [n for n in rec["meta"]["notes"]
                                if not DERIVED_NOTE.match(n)]
        pipeline.derive(rec["row"], rec["meta"]["form"], rec["meta"]["notes"])
        add_ucce(rec["row"], fac, rec["meta"]["notes"])
        if rec["row"].get("UCCE Nitrogen from Manure (lbs)") is not None:
            n_uc += 1
        seen, uniq = set(), []
        for note in rec["meta"]["notes"]:
            if note not in seen:
                seen.add(note)
                uniq.append(note)
        rec["meta"]["notes"] = uniq
        g, f, w, ratios = pipeline.qa(rec["row"], rec["meta"]["form"])
        rec["meta"].update(grade=g, fails=f, warns=w, ratios=ratios)
    geom.set_band(pipeline.NATIVE_BAND)
    print(f"\nProvost & Pritchard rows switched to the ASAE table : {n_pp}")
    print(f"blank export figures resolved to 0                  : {n_ex}")
    print(f"rows given a UCCE nitrogen estimate                 : {n_uc}")
    with open(f"{S}/results_final.pkl", "wb") as fh:
        pickle.dump(recs, fh)
    print(f"wrote {S}/results_final.pkl  ({len(recs)} records)")


if __name__ == "__main__":
    main()
