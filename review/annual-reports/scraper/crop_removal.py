"""Facility-wide crop nitrogen removal for the summary's standard and IAS reports.

Writes crop_removal_extracted.csv beside the review page, one row per summary
report filed on the standard Water Board form or the Innovative Ag Services
form, and renders the page each value was read from into crops/. Livingston
reports print removal only per field and are left out.

Each value is checked against two other figures printed on the same page. The
ratio there is total N applied from every source over crop removal, so a
correctly read page satisfies total / removal = ratio to within the ratio's
two-decimal rounding.
"""
import os, pickle, time
import pandas as pd
import pymupdf
import crops, geom, ias, ocr, pipeline, standard

# Working directory for the run: the review folder that contains this package.
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = pipeline.REPO
TARGET = f"{REPO}/outputs/review/annual-reports/Dairy_Annual_Report_Summary_Table_Region_5_2024.csv"
FORMATS = f"{REPO}/outputs/review/annual-reports/Annual_Report_Formats.csv"
PDF_ROOT = pipeline.PDF_ROOT
OUT_CSV = f"{S}/crop_removal_extracted.csv"

KEY = "Total Crop-Removed N"
RATIO_KEY = "Applied to Remove Ratio N"
FLAG = "Scraped August 2026"
RATIO_TOL = 0.01
OCR_MAX_PAGES = 45
# Annual_Report_Formats form type -> readers to try, in order.
READERS = {"Standard form": ("Standard",),
           "Innovative Ag Services form": ("IAS",),
           "Standard + Innovative Ag Services": ("Standard", "IAS")}
READ = {"Standard": standard.crop_removal, "IAS": ias.crop_removal}
# The page tag the main scrape recorded for the page carrying the ratio.
PAGE_TAG = {"Standard": "applied", "IAS": "attachment_b"}
# Review order: values that cannot stand without a reviewer come first.
STATUS_ORDER = ["check fails", "removal not read", "page not found",
                "check unavailable", "zero removal", "check passes", "no PDF"]


def is_true(v):
    """The scraped-row flag, read as True only when it says so; blank is False."""
    return v is True or str(v).strip().lower() == "true"


def pdf_index(root=PDF_ROOT):
    """Lower-cased file name -> path. Suffix case varies (.pdf and .PDF)."""
    out = {}
    for dp, _dirs, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith(".pdf"):
                out[fn.lower()] = os.path.join(dp, fn)
    return out


def scraped_meta(pkl="results_final.pkl"):
    """Source PDF -> the path, read method and page numbers of the main scrape."""
    out = {}
    for rec in pickle.load(open(f"{S}/{pkl}", "rb")):
        if rec.get("status") == "ok":
            m = rec["meta"]
            out[rec["Source PDF"]] = {"path": pipeline.local_pdf(rec["path"]), "method": m.get("method", "text"),
                                      "pages": m.get("pages") or {}, "form": m.get("form")}
    return out


def status_of(found, r, t, q):
    """One of STATUS_ORDER for a read, from the removal and its two check terms."""
    if not found:
        return "page not found"
    if r is None:
        return "removal not read"
    if r == 0:
        return "zero removal"
    if t is None or q is None:
        return "check unavailable"
    return "check passes" if abs(t / r - q) <= RATIO_TOL else "check fails"


def read_doc(doc, readers, pages_known):
    """First reader that locates a removal value; else the last page it found."""
    best = None
    for rd in readers:
        known = pages_known.get(rd)
        vals, i = READ[rd](doc, None if known is None else known - 1)
        if i is None:
            continue
        hit = (rd, vals, i)
        if vals.get(KEY) is not None:
            return hit
        best = best or hit
    return best


def extract_one(path, readers, method, pages_known):
    """Read one report as text, falling back to OCR of the relevant page.

    The text layer is tried even when the main scrape fell back to OCR: a packet
    can carry text on the summary page while its cover pages are scans.
    """
    raw = pymupdf.open(path)
    notes = []
    used = "text"
    geom.set_band(pipeline.NATIVE_BAND)
    got = read_doc(raw, readers, {} if method == "ocr" else pages_known)
    if got is None or got[1].get(KEY) is None:
        # Only the page that carries the figure is OCR'd when its number is
        # known; a scan with no known page is searched page by page.
        known = dict(pages_known)
        if got is not None:
            known.setdefault(got[0], got[2] + 1)
        geom.set_band(pipeline.OCR_BAND)
        odoc = ocr.OcrDoc(raw, max_pages=min(len(raw), OCR_MAX_PAGES))
        ogot = read_doc(odoc, readers, known)
        if ogot is not None and (got is None or ogot[1].get(KEY) is not None):
            got, used = ogot, "ocr"
            notes.append("read by OCR")
        geom.set_band(pipeline.NATIVE_BAND)
    return got, used, notes, len(raw)


def main(pkl="results_final.pkl"):
    summ = pd.read_csv(TARGET, low_memory=False)
    fmt = pd.read_csv(FORMATS)[["Source PDF", "Form Type", "Matched File"]]
    meta = scraped_meta(pkl)
    idx = pdf_index()
    tgt = summ[["Source PDF", "Dairy Name", RATIO_KEY, FLAG]].merge(fmt, on="Source PDF", how="left")
    tgt = tgt[tgt["Form Type"].isin(READERS)].drop_duplicates("Source PDF")
    print(f"  {len(tgt)} standard / IAS reports in the summary "
          f"({int(tgt[FLAG].map(is_true).sum())} scraped here, the rest from the "
          f"earlier parse)")

    rows, t0 = [], time.time()
    for n, (_, r) in enumerate(tgt.iterrows(), 1):
        pdf, readers = r["Source PDF"], READERS[r["Form Type"]]
        m = meta.get(pdf, {})
        rec = {"Source PDF": pdf, "Dairy Name": r["Dairy Name"], "Form Type": r["Form Type"],
               "Set": "scraped" if is_true(r[FLAG]) else "earlier parse",
               "Reader": "", "Method": "", "Page": None, KEY: None,
               "Total N Applied (all sources)": None, "Printed Ratio": None,
               "Summary Ratio": pd.to_numeric(r[RATIO_KEY], errors="coerce"),
               "Ratio Agrees": None, "Status": "", "Crop File": "", "Source Path": "",
               "Pages": None, "Notes": ""}
        path = m.get("path") or (idx.get(str(r["Matched File"]).lower())
                                 if isinstance(r["Matched File"], str) else None)
        if not path or not os.path.exists(path):
            rec["Status"] = "no PDF"
            rows.append(rec)
            continue
        rec["Source Path"] = path
        pages_known = {rd: m["pages"].get(PAGE_TAG[rd]) for rd in readers
                       if m and m.get("form") == rd and m["pages"].get(PAGE_TAG[rd])}
        try:
            got, used, notes, npages = extract_one(path, readers, m.get("method", "text"),
                                                   pages_known)
        except Exception as e:
            rec.update(Status="page not found", Notes=f"read failed: {type(e).__name__}: {e}")
            rows.append(rec)
            continue
        rec["Pages"] = npages
        if got is None:
            rec.update(Method=used, Status="page not found", Notes="; ".join(notes))
            rows.append(rec)
            continue
        rd, vals, i = got
        rv, t, q = vals.get(KEY), vals.get("_n_applied_all"), vals.get("_ratio_printed")
        rec.update({"Reader": rd, "Method": used, "Page": i + 1, KEY: rv,
                    "Total N Applied (all sources)": t, "Printed Ratio": q,
                    "Status": status_of(True, rv, t, q)})
        if q is not None and pd.notna(rec["Summary Ratio"]):
            rec["Ratio Agrees"] = abs(q - rec["Summary Ratio"]) <= RATIO_TOL
            if not rec["Ratio Agrees"]:
                notes.append(f"printed ratio {q:.2f} differs from the summary's "
                             f"{rec['Summary Ratio']:.2f}")
        if len(readers) > 1:
            notes.append(f"{rd} summary page used")
        made = crops.render(path, {"crop_removal": i + 1}, f"{S}/crops", method=used)
        rec["Crop File"] = made[0][2] if made else ""
        rec["Notes"] = "; ".join(notes)
        rows.append(rec)
        if n % 50 == 0:
            print(f"    {n}/{len(tgt)}  {time.time() - t0:.0f}s", flush=True)

    out = pd.DataFrame(rows)
    out["_order"] = out["Status"].map({s: k for k, s in enumerate(STATUS_ORDER)})
    out = out.sort_values(["_order", "Source PDF"]).drop(columns="_order")
    out.to_csv(OUT_CSV, index=False)
    print(f"\n  wrote {OUT_CSV}  ({len(out)} reports, {time.time() - t0:.0f}s)")
    tab = pd.crosstab(out["Status"], out["Set"], margins=True)
    print(tab.reindex([s for s in STATUS_ORDER if s in tab.index] + ["All"]).to_string())
    bad = out["Ratio Agrees"].eq(False).sum()
    print(f"  printed ratio disagrees with the summary's ratio: {int(bad)}")
    return out


if __name__ == "__main__":
    main()
