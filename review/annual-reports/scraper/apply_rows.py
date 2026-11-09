"""Append scraped rows to the Region 5 summary CSV, applying any review edits.

Idempotent: rows are keyed on Source PDF, so re-running after more review
replaces those rows rather than duplicating them.
"""
import argparse, os, re, shutil, sys
from collections import Counter
import pandas as pd
import pipeline

REPO = pipeline.REPO
TARGET = f"{REPO}/outputs/review/annual-reports/Dairy_Report_Summary_Region_5_2024_with_source_pdf_scraping.csv"
OUT = f"{REPO}/review/annual-reports"

FLAG = "Scraped August 2026"
PROV = ["Source Form Type", "Manure Basis", "Extraction Method", "Extraction Notes"]
BASIS = pipeline.BASIS
# Facility-wide crop N removal, written by crop_removal.py for every summary
# report on the standard or IAS form. A value is carried into the CSV when the
# page's own check holds or a reviewer confirmed or corrected it.
CROP_KEY = "Total Crop-Removed N"
CROP_CSV = f"{OUT}/crop_removal_extracted.csv"
CROP_CHECKED = {"check passes"}


# The reviewer writes its decisions wherever the file picker was pointed: the
# review folder, or the review outputs folder that holds the shipped file.
REVIEW_PATHS = [f"{OUT}/scrape_review.csv",
                f"{REPO}/outputs/review/annual-reports/scrape_review.csv"]


def review_path():
    """First decisions file that exists, or None."""
    for p in REVIEW_PATHS:
        if os.path.exists(p):
            return p
    return None


def load_review():
    """Source PDF -> (verdict, {field: corrected value})."""
    path = review_path()
    if path is None:
        print("WARNING: no scrape_review.csv found at any of:")
        for p in REVIEW_PATHS:
            print(f"           {p}")
        print("         every staged row will be appended unreviewed and no "
              "correction will be applied.")
        return {}
    print(f"review decisions: {path}")
    rv = pd.read_csv(path)
    out = {}
    for _, r in rv.iterrows():
        pdf = str(r["Source PDF"])
        e = out.setdefault(pdf, {"verdict": "", "fields": {}, "notes": [],
                                 "ratio_ok": False, "form_type": "", "crop_ok": False})
        if isinstance(r.get("verdict"), str) and r["verdict"]:
            e["verdict"] = r["verdict"]
        # Written by the review page; carried back so a rebuilt page knows which
        # applied-to-removed ratios have already been looked at.
        if str(r.get("ratio_ok", "")).strip() not in ("", "nan", "0", "False"):
            e["ratio_ok"] = True
        # Likewise for the facility-wide crop N removal.
        if str(r.get("crop_ok", "")).strip() not in ("", "nan", "0", "False"):
            e["crop_ok"] = True
        # The report form the reviewer confirmed, which overrides the
        # detector's guess when the two disagree.
        ft = r.get("form_type")
        if isinstance(ft, str) and ft.strip():
            e["form_type"] = ft.strip()
        f = r.get("field")
        if isinstance(f, str) and f:
            e["fields"][f] = r.get("corrected_value")
        # Optional free-text column, for recording why a reviewed value was
        # changed after the fact.
        nt = r.get("note")
        if isinstance(nt, str) and nt.strip() and nt.strip() not in e["notes"]:
            e["notes"].append(nt.strip())
    return out


AMMONIA_RETENTION = pipeline.AMMONIA_RETENTION


def redrive(row):
    """Recompute the two derived nitrogen columns; return the ones that moved.

    Mirrors pipeline.derive, which runs at scrape time and therefore sees the
    values before review.
    """
    n = lambda c: pd.to_numeric(row.get(c), errors="coerce")
    out = []
    am, aw = n("Applied N Dry Manure (lbs)"), n("Applied Process Wastewater N (lbs)")
    if pd.notna(am) or pd.notna(aw):
        v = round((0 if pd.isna(am) else am) + (0 if pd.isna(aw) else aw), 2)
        if pd.isna(n("Total Applied N (lbs)")) or abs(v - n("Total Applied N (lbs)")) > 0.01:
            row["Total Applied N (lbs)"] = v
            out.append("Total Applied N (lbs)")
    a = n("Total Dry Manure Generated N After Ammonia Losses (lbs)")
    g = n("Total Dry Manure Generated N (lbs)")
    if pd.isna(a) and pd.notna(g):
        a = round(g * AMMONIA_RETENTION, 2)
        row["Total Dry Manure Generated N After Ammonia Losses (lbs)"] = a
        out.append("Total Dry Manure Generated N After Ammonia Losses (lbs)")
    ww, ex = n("Total Process Wastewater Generated N (lbs)"), n("Total Exports N (lbs)")
    ta = n("Total Applied N (lbs)")
    if not any(pd.isna(x) for x in (a, ww, ta, ex)):
        v = round(a + ww - ta - ex, 2)
        if pd.isna(n("Unaccounted-for N (lbs)")) or abs(v - n("Unaccounted-for N (lbs)")) > 0.01:
            row["Unaccounted-for N (lbs)"] = v
            out.append("Unaccounted-for N (lbs)")
    return out


def add_crop_column(out, review):
    """Append Total Crop-Removed N to every row, keyed on Source PDF.

    A value corrected in review wins, including one cleared to blank. Otherwise
    the extracted value is written when it passes the page's own check (total
    N applied / removal = printed ratio) or a reviewer confirmed it; anything
    else stays blank. Returns the frame and a tally of where values came from.
    """
    tally = Counter()
    if not os.path.exists(CROP_CSV):
        print(f"note: {CROP_CSV} not found; {CROP_KEY} left blank")
        out[CROP_KEY] = pd.NA
        return out, tally
    ex = pd.read_csv(CROP_CSV).drop_duplicates("Source PDF").set_index("Source PDF")
    vals = {}
    for pdf, x in ex.iterrows():
        rv = review.get(pdf, {})
        fields = rv.get("fields", {})
        if CROP_KEY in fields:
            v = pd.to_numeric(fields[CROP_KEY], errors="coerce")
            vals[pdf] = v
            tally["corrected in review" if pd.notna(v) else "cleared in review"] += 1
        elif x["Status"] == "no PDF":
            tally["no PDF to read"] += 1
        elif rv.get("crop_ok") and pd.notna(x[CROP_KEY]):
            vals[pdf] = x[CROP_KEY]
            tally["confirmed in review"] += 1
        elif x["Status"] in CROP_CHECKED:
            vals[pdf] = x[CROP_KEY]
            tally["passes the page check"] += 1
        else:
            tally[f"blank until reviewed ({x['Status']})"] += 1
    out[CROP_KEY] = pd.to_numeric(out["Source PDF"].map(vals), errors="coerce")
    return out, tally


# Rows whose identity fields were overwritten with the Water Board letterhead.
# Their numbers are real but belong to six other dairies, each of which is now
# present under its own correctly identified row, so these are superseded.
BROKEN_SOURCE = "1008 N. Verduga Rd, Turlock 2024 Dairy AR.pdf"
# Two rows identical across all 56 columns; one is dropped.
EXACT_DUP_SOURCE = "26290 S Union Rd Manteca 2024 Dairy AR.pdf"
# Rows that carry no Source PDF, identified by address from the scraped set.
MISSING_SOURCE = {
    "8940 E Melton": "8940 E Melton Rd Manteca 2024 Dairy AR.pdf",
    "9500 Linwood": "9500 W. Linwood Ave, Turlock 2024 GoatDairy AR.pdf",
    "15276 Ivanhoe": "2024AR_Double D Dairy_15276 Ivanhoe Dr_Tulare.pdf",
}


def repair_existing(have):
    """Fix the identity defects found in the pre-existing rows."""
    n0 = len(have)
    src = have["Source PDF"].astype(str).str.strip()
    drop_broken = src == BROKEN_SOURCE
    print(f"  dropping {int(drop_broken.sum())} rows whose identity was overwritten "
          f"with '{BROKEN_SOURCE}'")
    have = have[~drop_broken].copy()

    src = have["Source PDF"].astype(str).str.strip()
    dup = src == EXACT_DUP_SOURCE
    if dup.sum() > 1:
        keep_first = dup & ~dup.duplicated(keep="first")
        drop = dup & ~keep_first
        print(f"  dropping {int(drop.sum())} exact duplicate row(s) of "
              f"'{EXACT_DUP_SOURCE}'")
        have = have[~drop].copy()

    filled = 0
    for frag, pdf in MISSING_SOURCE.items():
        m = have["Source PDF"].isna() & have["Dairy Address"].astype(str).str.contains(
            frag, na=False, regex=False)
        if m.any():
            have.loc[m, "Source PDF"] = pdf
            filled += int(m.sum())
    print(f"  filled {filled} blank Source PDF value(s) from the scraped set")
    print(f"  existing rows {n0} -> {len(have)}")
    return have.reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="actually modify the CSV")
    ap.add_argument("--include-duplicates", action="store_true")
    args = ap.parse_args()

    # Always rebuild from the pristine baseline so the run is idempotent.
    baseline = f"{OUT}/backup_before_append.csv"
    have = pd.read_csv(baseline if os.path.exists(baseline) else TARGET)
    orig_cols = list(have.columns)
    print("repairing pre-existing rows:")
    have = repair_existing(have)
    staged = pd.read_csv(f"{OUT}/scraped_rows.csv")
    review = load_review()

    skipped_dup, skipped_unusable, applied_edits = [], [], 0
    derived_fixed = []
    new_rows = []
    for _, s in staged.iterrows():
        pdf = str(s["Source PDF"])
        rv = review.get(pdf, {})
        if rv.get("verdict") == "unusable":
            skipped_unusable.append(pdf)
            continue
        if isinstance(s.get("_duplicate_risk"), str) and s["_duplicate_risk"] \
                and not args.include_duplicates:
            skipped_dup.append(f"{pdf} ({s['_duplicate_risk']})")
            continue
        row = {c: None for c in orig_cols}
        for c in orig_cols:
            if c in staged.columns and not str(c).startswith("_"):
                v = s[c]
                row[c] = None if pd.isna(v) else v
        row["Source PDF"] = pdf
        changed = []
        for k, v in rv.get("fields", {}).items():
            if k in row:
                row[k] = None if (v is None or (isinstance(v, float) and pd.isna(v))) else v
                applied_edits += 1
                changed.append(k)
        # Total Applied N and Unaccounted-for N are arithmetic on the other
        # columns, so a correction to any of their inputs leaves them stale.
        # Recomputing here keeps each row internally consistent, which is what
        # the notebook's nitrogen-balance assertions check.
        if changed:
            redone = redrive(row)
            if redone:
                changed += redone
                derived_fixed.append((pdf, redone))

        form = s.get("_form")
        notes = [] if pd.isna(s.get("_notes")) else [str(s["_notes"])]
        grade = s.get("_grade")
        prefix = f"QA {grade}" + (f"; review {rv['verdict']}" if rv.get("verdict") else "")
        row[FLAG] = True
        row["Source Form Type"] = form
        # A row may override the form's default basis, as the Provost & Pritchard
        # rows do once they are read from the ASAE whole-herd table.
        ov = s.get("_basis")
        row["Manure Basis"] = (ov if isinstance(ov, str) and ov
                               else BASIS.get(form, ""))
        row["Extraction Method"] = s.get("_method")
        if changed:
            notes.append("review corrected: " + ", ".join(sorted(changed)))
        notes.extend(rv.get("notes", []))
        row["Extraction Notes"] = " | ".join([prefix] + notes)
        new_rows.append(row)

    add = pd.DataFrame(new_rows)
    base = have.copy()
    for c in [FLAG] + PROV:
        if c not in base.columns:
            base[c] = False if c == FLAG else pd.NA
    base[FLAG] = base[FLAG].fillna(False)
    # Replacing rather than appending keeps re-runs idempotent.
    if not add.empty:
        base = base[~base["Source PDF"].astype(str).isin(set(add["Source PDF"]))]
    out = pd.concat([base, add], ignore_index=True)
    out = out[[c for c in orig_cols if c in out.columns] + [FLAG] + PROV]
    out, crop_tally = add_crop_column(out, review)

    print(f"existing rows            {len(have)}")
    print(f"staged rows              {len(staged)}")
    print(f"  skipped, duplicate     {len(skipped_dup)}")
    print(f"  skipped, unusable      {len(skipped_unusable)}")
    print(f"appended                 {len(add)}")
    print(f"review edits applied     {applied_edits}")
    if derived_fixed:
        print(f"{'derived columns redone':<24} {len(derived_fixed):>6}"
              "   (a correction changed one of their inputs)")
        for _pdf, _cols in derived_fixed[:10]:
            print(f"    {_pdf[:54]:<56} {', '.join(_cols)}")
    print(f"{CROP_KEY:<24} {int(out[CROP_KEY].notna().sum()):>6} rows filled")
    for why, n in sorted(crop_tally.items(), key=lambda kv: -kv[1]):
        print(f"    {why:<44}{n:>6}")
    print(f"final rows               {len(out)}  ({len(out.columns)} columns)")
    assert list(out.columns)[:len(orig_cols)] == orig_cols, "original column order changed"
    # The appended rows must be unique among themselves and must not collide with a
    # row already present. Duplicates that were already in the file are reported
    # rather than treated as an error introduced here.
    if not add.empty:
        new_ids = add["Source PDF"].astype(str).str.strip()
        assert new_ids.duplicated().sum() == 0, "appended rows contain duplicates"
        old_ids = set(have["Source PDF"].dropna().astype(str).str.strip().str.lower())
        clash = sorted(set(new_ids.str.lower()) & old_ids)
        assert not clash, f"appended rows collide with existing rows: {clash[:5]}"
    pre = have["Source PDF"].dropna().astype(str).str.strip()
    pre_dup = pre[pre.duplicated(keep=False)].value_counts()
    if len(pre_dup):
        print("\nnote: Source PDF values already duplicated in the file before this run:")
        for v, c in pre_dup.items():
            print(f"    {c}x  {v}")
    n_blank = int(have["Source PDF"].isna().sum())
    if n_blank:
        print(f"note: {n_blank} existing rows have no Source PDF value")
    assert int((out[FLAG] == True).sum()) == len(add)
    assert int((out[FLAG] == False).sum()) == len(have)
    if skipped_dup:
        print("\nduplicate-risk rows held back:")
        for d in skipped_dup[:15]:
            print("   ", d)
        if len(skipped_dup) > 15:
            print(f"    ... and {len(skipped_dup)-15} more")
    if args.write:
        bak = f"{OUT}/backup_before_append.csv"
        # Never overwrite an existing baseline: it is the pre-append state that
        # every later run rebuilds from, so copying the current file over it would
        # make the run non-idempotent and destroy the reference.
        if not os.path.exists(bak):
            shutil.copy2(TARGET, bak)
        out.to_csv(TARGET, index=False)
        print(f"\nWROTE {TARGET}\nbackup at {bak}")
    else:
        out.to_csv(f"{OUT}/preview_merged.csv", index=False)
        print(f"\ndry run; preview at {OUT}/preview_merged.csv (pass --write to apply)")


if __name__ == "__main__":
    main()
