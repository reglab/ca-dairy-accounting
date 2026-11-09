"""Tally which annual-report form each 2024 submission used, for SI Figure S1a.

Walks the report PDFs, reads the form markers with the scraper's own detector,
links each file back to a row of the report summary, and writes
Annual_Report_Formats.csv. The link is by filename, and the two naming
conventions in the corpus do not always agree, so it runs in three passes:
an exact match on normalised name tokens, a close-string match, and finally a
match on the street numbers alone within the files and rows still unclaimed.

Usage:
    python build_report_formats.py [--cache form_scan.csv]

--cache reuses a previous walk of the PDFs under data/annual-reports, which
takes about twenty minutes.
"""
import argparse, difflib, os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, f"{HERE}/scraper")

PDF_ROOT = os.path.join(REPO, "data", "annual-reports")
SUMMARY = f"{REPO}/outputs/review/annual-reports/Dairy_Report_Summary_Region_5_2024_with_source_pdf_scraping.csv"
OUT = f"{REPO}/outputs/review/annual-reports/Annual_Report_Formats.csv"

# Dropped before comparing two filenames: street types, compass points, the
# year, and the corporate suffixes that appear on one convention only.
STOP = {"ave", "avenue", "rd", "road", "st", "street", "dr", "drive", "ln", "lane",
        "blvd", "way", "ct", "court", "hwy", "highway", "pl", "place", "cir",
        "circle", "n", "s", "e", "w", "north", "south", "east", "west", "2024",
        "dairy", "ar", "pdf", "2024ar", "llc", "inc", "farms", "farm", "the"}
PRETTY = {"IAS": "Innovative Ag Services", "Livingston": "Livingston Dairy Consulting",
          "ProvostPritchard": "Provost & Pritchard"}
# The detector reads the cover pages, so it is blind to a packet filed as a
# scanned image. Where it finds nothing but this study's earlier scrape already
# recorded the form, that record is used instead.
FROM_SCRAPE = {"Standard": "Standard form",
               "IAS": "Innovative Ag Services form",
               "Livingston": "Livingston Dairy Consulting form",
               "ProvostPritchard": "Provost & Pritchard form"}
UNKNOWN = ("No form markers", "Not matched to a file")
# Robertson et al. admitted only machine-readable copies of the standard form,
# so a row of theirs whose document cannot be found is a standard-form report
# by their inclusion criterion. The corpus bears this out: every one of the
# 565 rows of theirs whose PDF was located reads as the standard form.
ROBERTSON_FORM = "Standard form"


def tokens(name):
    name = re.sub(r"\.pdf$", "", str(name), flags=re.I)
    return [t for t in re.split(r"[^a-z0-9]+", name.lower()) if t and t not in STOP]


def name_key(name):
    return " ".join(sorted(tokens(name)))


def number_key(name):
    """The street numbers only, with ZIP codes and facility suffixes dropped.

    Single digits are dropped because the Tulare files carry a "#1"/"#2"
    facility suffix in the dairy name that the summary's filename does not,
    which otherwise puts an extra token in the key and defeats the match.
    """
    n = [t for t in tokens(name) if t.isdigit() and t != "2024"]
    return tuple(sorted(t for t in n
                        if len(t) >= 2 and not (len(t) == 5 and t[0] == "9")))


def walk(root):
    """Classify every PDF under root with the scraper's form detector."""
    import pymupdf, detect
    paths = sorted(os.path.join(dp, fn) for dp, _, fns in os.walk(root)
                   for fn in fns if fn.lower().endswith(".pdf"))
    rows = []
    for i, p in enumerate(paths, 1):
        rel = os.path.relpath(p, root).split(os.sep)
        rec = {"Source PDF": os.path.basename(p), "office": rel[0],
               "folder": rel[1] if len(rel) > 1 else "", "consultant": "",
               "has_standard": "", "text_pages": "", "status": "ok"}
        try:
            with open(p, "rb") as fh:            # OneDrive leaves the dataless
                if not fh.read(65536):           # flag on files it still serves
                    raise OSError("empty read")
            with pymupdf.open(p) as doc:
                c, std, tp, _ = detect.scan(doc)
                rec.update(consultant=c or "", has_standard=int(std), text_pages=tp)
        except Exception as e:
            rec["status"] = f"{type(e).__name__}: {e}"[:80]
        rows.append(rec)
        if i % 50 == 0:
            print(f"  {i}/{len(paths)}", flush=True)
    return pd.DataFrame(rows)


def unique_index(series):
    """Map each value that occurs exactly once to its row index."""
    counts = series.value_counts()
    return {k: i for k, i in zip(series, series.index) if k and counts[k] == 1}


def agreeing_index(series, scan):
    """Map each name key to a file, allowing repeats that agree on the form.

    One dairy's report is sometimes filed twice under variant spellings that
    reduce to the same key ("26290 S Union Rd" and "26290 SOuth Union Road").
    Treating that as ambiguous drops the row into the close-string pass, which
    then matches it to a different dairy at a neighbouring street number. Where
    the duplicates report the same form, either will do; where they disagree,
    the key is left unmatched rather than guessed.
    """
    out = {}
    for key, group in series.groupby(series).groups.items():
        if not key:
            continue
        rows = scan.loc[group]
        if rows[["consultant", "has_standard"]].drop_duplicates().shape[0] == 1:
            out[key] = group[0]
    return out


def link(rep, scan):
    """Attach each summary row to a scanned file, in three widening passes."""
    scan["_name"] = scan["Source PDF"].map(name_key)
    rep["_name"] = rep["Source PDF"].map(name_key)
    by_name = agreeing_index(scan["_name"], scan)
    rep["_hit"] = rep["_name"].map(by_name)

    # The close-string pass may only consider rows with no exact counterpart at
    # all, and may only claim a file no other row has taken; without both
    # guards it reassigns a row to a near neighbour's document.
    exact_keys = set(scan["_name"])
    pool = [k for k in by_name if k not in set(rep["_name"])]
    for i in rep.index[rep["_hit"].isna()]:
        if rep.at[i, "_name"] in exact_keys:
            continue
        close = difflib.get_close_matches(rep.at[i, "_name"], pool, n=1, cutoff=0.88)
        if close and by_name[close[0]] not in set(rep["_hit"].dropna()):
            rep.at[i, "_hit"] = by_name[close[0]]

    # Tulare files name the dairy and county where the summary names the city,
    # so no token survives in common; the street numbers still do, and within
    # the leftovers they are specific enough to be safe. An empty key matches
    # nothing, so a name carrying no multi-digit number is left unmatched
    # rather than collapsed onto the first other such file.
    left_scan = scan[~scan.index.isin(set(rep["_hit"].dropna()))]
    left_rep = rep.index[rep["_hit"].isna()]
    scan_keys = left_scan["Source PDF"].map(number_key)
    by_number = {k: i for k, i in unique_index(scan_keys).items() if k}
    found = rep.loc[left_rep, "Source PDF"].map(number_key).map(by_number)
    rep.loc[found.dropna().index, "_hit"] = found.dropna()
    return rep


def label(row):
    if pd.isna(row.get("status")):
        return "Not matched to a file"
    consultant = row["consultant"] if isinstance(row["consultant"], str) else ""
    if row["has_standard"] == 1:
        return "Standard form" if not consultant else f"Standard + {PRETTY[consultant]}"
    if consultant:
        return f"{PRETTY[consultant]} form"
    return "No form markers"


def main(cache=None):
    scan = pd.read_csv(cache) if cache else walk(PDF_ROOT)
    if not cache:
        scan.to_csv(f"{HERE}/form_scan_raw.csv", index=False)
    rep = pd.read_csv(SUMMARY, low_memory=False)
    rep = link(rep, scan)
    cols = ["Source PDF", "consultant", "has_standard", "text_pages", "status"]
    joined = scan[cols].reindex(rep["_hit"]).set_axis(rep.index)
    detected = joined.apply(label, axis=1)
    recorded = rep.get("Source Form Type", pd.Series(index=rep.index, dtype=object))
    fallback = detected.isin(UNKNOWN) & recorded.map(FROM_SCRAPE).notna()
    form = detected.mask(fallback, recorded.map(FROM_SCRAPE))
    # Whatever is still unresolved and carries no recorded form type belongs to
    # the earlier parse, which only accepted the standard form.
    inherited = form.isin(UNKNOWN) & recorded.isna()
    form = form.mask(inherited, ROBERTSON_FORM)
    out = pd.DataFrame({
        "Source PDF": rep["Source PDF"],
        "Form Type": form,
        "Source": np.where(fallback, "report summary",
                           np.where(inherited, "earlier parse inclusion criterion",
                                    np.where(form.isin(UNKNOWN), "", "detector"))),
        "Consultant": joined["consultant"].fillna(""),
        "Has Standard Pages": joined["has_standard"].astype("Int64"),
        "Scanned Image Only": (joined["text_pages"] == 0).astype("Int64"),
        "Matched File": joined["Source PDF"],
    })
    out.to_csv(OUT, index=False)
    print(f"\nwrote {OUT}: {len(out)} rows, "
          f"{int(out['Source'].ne('').sum())} with a form type "
          f"({int(fallback.sum())} taken from the earlier scrape, "
          f"{int(inherited.sum())} inherited from the earlier parse's criterion)")
    print(out["Form Type"].value_counts().to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", help="a previous walk, to skip re-reading the PDFs")
    main(**vars(ap.parse_args()))
